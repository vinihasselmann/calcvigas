# -*- coding: utf-8 -*-
"""Importa TAXA-CA e TAXA-CP do XLSX para tipos de vigas no Revit 2020.

Entradas:
    IN[0] - matriz da aba VPL (saida data do no ImportExcel)
    IN[1] - matriz da aba VPT (saida data do no ImportExcel)
    IN[2] - matriz da aba VR  (saida data do no ImportExcel)
    IN[3] - True para gravar; False para previa
    IN[4] - gatilho numerico para forcar nova execucao
"""

import clr
import math
import re
import unicodedata
from collections import defaultdict

clr.AddReference("RevitAPI")
clr.AddReference("RevitServices")
clr.AddReference("RevitNodes")

import Revit

clr.ImportExtensions(Revit.Elements)

from Autodesk.Revit.DB import (
    BuiltInCategory,
    BuiltInParameter,
    FilteredElementCollector,
    StorageType,
    SubTransaction,
    UnitUtils,
)
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager


doc = DocumentManager.Instance.CurrentDBDocument
ID_PARAMETER_NAMES = ("ID_ELEMENTO", "ID Elemento", "Marca de tipo", "Type Mark")
CA_PARAMETER = "TAXA-CA"
CP_PARAMETER = "TAXA-CP"
MODEL_PARAMETER_NAMES = ("Modelo", "Model", "Tipo Laje", "Tipo_Laje", "LP_TYPE")
SLAB_PREFIXES = ("LP15", "LP20", "LP265", "LP32", "LP40", "LP50")
HEADER_ALIASES = {
    "id": ("IDELEMENTO",),
    "status": ("STATUS",),
    "ca": ("TAXAARMADURAPASSIVA", "TAXACA"),
    "cp": ("TAXAARMADURAPROTENDIDA", "TAXACP"),
}
TOLERANCE = 1e-6
CA_RATE_STEP = 5.0


def _input(index, default=None):
    try:
        value = IN[index]
    except Exception:
        return default
    return default if value is None else value


def _unwrap(value):
    try:
        return UnwrapElement(value)
    except Exception:
        return value


def _text(value):
    if value is None:
        return ""
    try:
        return unicode(value).strip()
    except Exception:
        return str(value).strip()


def _normalized(value):
    text = _text(value)
    try:
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
    except Exception:
        pass
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _rows(value):
    if value is None:
        return []
    return [list(row) for row in value]


def _number(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _text(value).replace(" ", "")
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", text)
    if not match:
        return None
    return float(match.group(0).replace(",", "."))


def _rounded_ca_rate(value):
    """Arredonda CA ao multiplo de 5 mais proximo; empate sobe."""
    if value is None:
        return None
    return math.floor((float(value) / CA_RATE_STEP) + 0.5) * CA_RATE_STEP


def _rounded_cp_rate(value):
    """Arredonda CP ao inteiro mais proximo; empate sobe."""
    if value is None:
        return None
    return float(math.floor(float(value) + 0.5))


def _column_indexes(headers, needs_cp):
    normalized = [_normalized(value) for value in headers]
    indexes = {}
    required = ("id", "status", "ca", "cp") if needs_cp else ("id", "status", "ca")
    for key in required:
        aliases = HEADER_ALIASES[key]
        for index, header in enumerate(normalized):
            if header in aliases:
                indexes[key] = index
                break
        if key not in indexes:
            raise ValueError("Cabecalho obrigatorio nao encontrado: {}.".format(key))
    return indexes


def _read_sheet(data, sheet_name, needs_cp, records, ignored, conflicts):
    rows = _rows(data)
    if not rows:
        return
    indexes = _column_indexes(rows[0], needs_cp)
    for row_number, row in enumerate(rows[1:], start=2):
        identifier = _text(row[indexes["id"]]) if indexes["id"] < len(row) else ""
        if not identifier:
            continue
        status = _text(row[indexes["status"]]).upper() if indexes["status"] < len(row) else ""
        if status != "PASSA":
            ignored.append({
                "status": "IGNORADO_STATUS",
                "aba": sheet_name,
                "linha": row_number,
                "id_elemento": identifier,
                "status_excel": status,
            })
            continue
        ca = (
            _rounded_ca_rate(_number(row[indexes["ca"]]))
            if indexes["ca"] < len(row)
            else None
        )
        cp = (
            _rounded_cp_rate(_number(row[indexes["cp"]]))
            if needs_cp and indexes["cp"] < len(row)
            else 0.0
        )
        if ca is None or cp is None:
            conflicts.append({
                "status": "CONFLITO",
                "aba": sheet_name,
                "linha": row_number,
                "id_elemento": identifier,
                "mensagem": "Taxa CA ou CP vazia/invalida.",
            })
            continue
        key = _normalized(identifier)
        record = {"id_elemento": identifier, "key": key, "ca": ca, "cp": cp, "aba": sheet_name}
        if key in records:
            current = records[key]
            if abs(current["ca"] - ca) > TOLERANCE or abs(current["cp"] - cp) > TOLERANCE:
                conflicts.append({
                    "status": "CONFLITO",
                    "id_elemento": identifier,
                    "mensagem": "Mesmo ID possui taxas diferentes no XLSX.",
                })
            continue
        records[key] = record


def _parameter_text(parameter):
    if parameter is None:
        return ""
    if parameter.StorageType == StorageType.String:
        return _text(parameter.AsString())
    return _text(parameter.AsValueString())


def _type_texts(element_type):
    texts = []
    try:
        if element_type.Name:
            texts.append(element_type.Name)
    except Exception:
        pass
    for built_in in (BuiltInParameter.ALL_MODEL_MODEL, BuiltInParameter.SYMBOL_NAME_PARAM):
        try:
            text = _parameter_text(element_type.get_Parameter(built_in))
            if text:
                texts.append(text)
        except Exception:
            pass
    for name in MODEL_PARAMETER_NAMES:
        text = _parameter_text(element_type.LookupParameter(name))
        if text:
            texts.append(text)
    try:
        if element_type.FamilyName:
            texts.append(element_type.FamilyName)
    except Exception:
        pass
    return texts


def _is_alveolar_type(element_type):
    for text in _type_texts(element_type):
        normalized = _normalized(text)
        if normalized.startswith(SLAB_PREFIXES):
            return True
        if "LAJEALVEOLAR" in normalized or "ALVEOLARSLAB" in normalized:
            return True
    return False


def _type_identifier(element_type):
    for name in ID_PARAMETER_NAMES[:2]:
        text = _parameter_text(element_type.LookupParameter(name))
        if text:
            return text
    try:
        text = _parameter_text(element_type.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_MARK))
        if text:
            return text
    except Exception:
        pass
    for name in ID_PARAMETER_NAMES[2:]:
        text = _parameter_text(element_type.LookupParameter(name))
        if text:
            return text
    try:
        return _text(element_type.Name)
    except Exception:
        return ""


def _element_identifier(element, element_type):
    for name in ID_PARAMETER_NAMES[:2]:
        text = _parameter_text(element.LookupParameter(name))
        if text:
            return text
    return _type_identifier(element_type)


def _collect_beam_types():
    by_id = defaultdict(list)
    seen_type_ids = set()
    elements = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_StructuralFraming)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    for element in elements:
        type_id = element.GetTypeId().IntegerValue
        if type_id in seen_type_ids:
            continue
        seen_type_ids.add(type_id)
        element_type = doc.GetElement(element.GetTypeId())
        if element_type is None or _is_alveolar_type(element_type):
            continue
        identifier = _element_identifier(element, element_type)
        if identifier:
            by_id[_normalized(identifier)].append({
                "type": element_type,
                "type_id": type_id,
                "identifier": identifier,
            })
    return by_id


def _normalized_parameter_name(value):
    return _normalized(value)


def _find_parameter(element, target_name):
    parameter = element.LookupParameter(target_name)
    if parameter is not None:
        return parameter
    target = _normalized_parameter_name(target_name)
    for candidate in element.Parameters:
        try:
            if _normalized_parameter_name(candidate.Definition.Name) == target:
                return candidate
        except Exception:
            continue
    return None


def _density_internal_value(parameter, kg_m3):
    if parameter.StorageType != StorageType.Double:
        return kg_m3
    try:
        return UnitUtils.ConvertToInternalUnits(float(kg_m3), parameter.DisplayUnitType)
    except Exception as exc:
        raise ValueError("Falha ao converter kg/m3 para unidade interna: {}".format(str(exc)))


def _prepare_parameter(element_type, name):
    parameter = _find_parameter(element_type, name)
    if parameter is None:
        raise ValueError("Parametro de tipo '{}' nao encontrado.".format(name))
    if parameter.IsReadOnly:
        raise ValueError("Parametro de tipo '{}' e somente leitura.".format(name))
    if parameter.StorageType not in (StorageType.Double, StorageType.String):
        raise ValueError("Parametro '{}' deve ser Densidade de massa ou Texto.".format(name))
    return parameter


def _set_value(parameter, value):
    if parameter.StorageType == StorageType.Double:
        return parameter.Set(_density_internal_value(parameter, value))
    return parameter.Set(("{:.6f}".format(value)).rstrip("0").rstrip("."))


vpl_data = _input(0)
vpt_data = _input(1)
vr_data = _input(2)
write_parameters = bool(_input(3, False))
refresh_trigger = _input(4, 0)  # Mantem dependencia explicita para invalidar o cache do Dynamo.

records = {}
ignored = []
conflicts = []
report = []

try:
    _read_sheet(vpl_data, "VPL", True, records, ignored, conflicts)
    _read_sheet(vpt_data, "VPT", True, records, ignored, conflicts)
    _read_sheet(vr_data, "VR", False, records, ignored, conflicts)
except Exception as exc:
    conflicts.append({"status": "CONFLITO", "mensagem": str(exc)})

beam_types = _collect_beam_types()
for key, candidates in beam_types.items():
    if len(candidates) > 1 and key in records:
        conflicts.append({
            "status": "CONFLITO",
            "id_elemento": records[key]["id_elemento"],
            "mensagem": "Mais de um tipo Revit possui o mesmo identificador.",
            "type_ids": [candidate["type_id"] for candidate in candidates],
        })

blocked = len(conflicts) > 0
matched_keys = set()

if write_parameters and not blocked:
    TransactionManager.Instance.EnsureInTransaction(doc)

try:
    for key in sorted(records.keys()):
        record = records[key]
        candidates = beam_types.get(key, [])
        if not candidates:
            report.append({
                "status": "NAO_ENCONTRADO",
                "id_elemento": record["id_elemento"],
                "aba": record["aba"],
                "taxa_ca": record["ca"],
                "taxa_cp": record["cp"],
            })
            continue
        if len(candidates) != 1:
            continue
        matched_keys.add(key)
        candidate = candidates[0]
        item = {
            "status": "BLOQUEADO" if blocked and write_parameters else "PREVIA",
            "id_elemento": record["id_elemento"],
            "type_id": candidate["type_id"],
            "taxa_ca": record["ca"],
            "taxa_cp": record["cp"],
            "aba": record["aba"],
            "mensagem": "",
        }
        if blocked and write_parameters:
            item["mensagem"] = "Gravacao bloqueada por conflitos no arquivo ou no Revit."
        elif write_parameters:
            subtransaction = SubTransaction(doc)
            sub_started = False
            try:
                ca_parameter = _prepare_parameter(candidate["type"], CA_PARAMETER)
                cp_parameter = _prepare_parameter(candidate["type"], CP_PARAMETER)
                subtransaction.Start()
                sub_started = True
                ca_ok = _set_value(ca_parameter, record["ca"])
                cp_ok = _set_value(cp_parameter, record["cp"])
                if not ca_ok or not cp_ok:
                    raise ValueError("A API do Revit recusou a gravacao de uma das taxas.")
                subtransaction.Commit()
                sub_started = False
                item["status"] = "GRAVADO"
                item["valor_revit_ca"] = _parameter_text(ca_parameter)
                item["valor_revit_cp"] = _parameter_text(cp_parameter)
            except Exception as exc:
                try:
                    if sub_started:
                        subtransaction.RollBack()
                except Exception:
                    pass
                item["status"] = "ERRO"
                item["mensagem"] = str(exc)
        report.append(item)
finally:
    if write_parameters and not blocked:
        TransactionManager.Instance.TransactionTaskDone()

report.extend(ignored)
report.extend(conflicts)
report.insert(0, {
    "status": "RESUMO",
    "gatilho": refresh_trigger,
    "linhas_aprovadas_excel": len(records),
    "tipos_viga_revit": sum(len(value) for value in beam_types.values()),
    "correspondencias": len(matched_keys),
    "ignoradas_por_status": len(ignored),
    "conflitos": len(conflicts),
    "gravacao_solicitada": write_parameters,
    "gravacao_bloqueada": blocked,
})

OUT = report
