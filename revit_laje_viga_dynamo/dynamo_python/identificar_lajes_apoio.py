# -*- coding: utf-8 -*-
"""No IronPython 2.7 do Dynamo/Revit 2020 para identificar lajes alveolares apoiadas em vigas.

Entradas:
    IN[0] - vigas opcionais (null = todas as vigas estruturais)
    IN[1] - pecas alveolares opcionais (null = classificacao automatica)
    IN[2] - folga alem da face da viga em centimetros (padrao 5)
    IN[3] - tolerancia vertical em centimetros (padrao 150)
    IN[4] - True para gravar; False para apenas visualizar
"""

import clr
import re
from collections import Counter, defaultdict

clr.AddReference("RevitAPI")
clr.AddReference("RevitServices")
clr.AddReference("RevitNodes")

import Revit  # noqa: E402

clr.ImportExtensions(Revit.Elements)

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    BuiltInParameter,
    FilteredElementCollector,
    GeometryInstance,
    Line,
    LocationCurve,
    Options,
    Solid,
    SolidCurveIntersectionOptions,
    StorageType,
    ViewDetailLevel,
    XYZ,
)
from RevitServices.Persistence import DocumentManager  # noqa: E402
from RevitServices.Transactions import TransactionManager  # noqa: E402


doc = DocumentManager.Instance.CurrentDBDocument
CM_TO_FT = 1.0 / 30.48
SAMPLE_FRACTIONS = (0.15, 0.35, 0.50, 0.65, 0.85)
LEFT_PARAMETER = "LAJE_Marca_E"
RIGHT_PARAMETER = "LAJE_Marca_D"
SLAB_MARK_NAMES = ("Marca de tipo", "Type Mark", "ID_ELEMENTO", "ID Elemento")
SLAB_MODEL_NAMES = ("Modelo", "Model", "Tipo Laje", "Tipo_Laje", "LP_TYPE")
SLAB_MODEL_PREFIXES = ("LP15", "LP20", "LP265", "LP32", "LP40", "LP50")
BEAM_WIDTH_NAMES = (
    "PECA-Largura Preo",
    u"PE\u00c7A-Largura Preo",
    "PECA-Largura Pre",
    u"PE\u00c7A-Largura Pre",
    "Largura",
    "Width",
    "b",
    "bw",
)


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


def _as_list(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [_unwrap(item) for item in value]
    return [_unwrap(value)]


def _element_id_value(element):
    # ElementId.IntegerValue e a propriedade disponivel na API do Revit 2020.
    return element.Id.IntegerValue


def _collect_structural_framing():
    return list(
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_StructuralFraming)
        .WhereElementIsNotElementType()
        .ToElements()
    )


def _type_and_family_texts(element):
    texts = []
    element_type = doc.GetElement(element.GetTypeId())
    for owner in (element, element_type):
        if owner is None:
            continue
        try:
            if owner.Name:
                texts.append(owner.Name)
        except Exception:
            pass
        for built_in in (BuiltInParameter.ALL_MODEL_MODEL, BuiltInParameter.SYMBOL_NAME_PARAM):
            try:
                text = _parameter_text(owner.get_Parameter(built_in))
                if text:
                    texts.append(text)
            except Exception:
                pass
        for name in SLAB_MODEL_NAMES:
            text = _parameter_text(owner.LookupParameter(name))
            if text:
                texts.append(text)
    try:
        family = element_type.Family
        if family is not None and family.Name:
            texts.append(family.Name)
    except Exception:
        pass
    return texts


def _is_alveolar_piece(element):
    for text in _type_and_family_texts(element):
        normalized = _normalized_parameter_name(text)
        if normalized.startswith(SLAB_MODEL_PREFIXES):
            return True
        if "LAJEALVEOLAR" in normalized or "ALVEOLARSLAB" in normalized:
            return True
    return False


def _collect_beams_and_slabs():
    beams = []
    slabs = []
    for element in _collect_structural_framing():
        try:
            if _is_alveolar_piece(element):
                slabs.append(element)
            else:
                beams.append(element)
        except Exception:
            beams.append(element)
    return beams, slabs


def _parameter(element, name):
    parameter = element.LookupParameter(name)
    if parameter is not None:
        return parameter
    element_type = doc.GetElement(element.GetTypeId())
    return element_type.LookupParameter(name) if element_type is not None else None


def _parameter_text(parameter):
    if parameter is None:
        return ""
    if parameter.StorageType == StorageType.String:
        return (parameter.AsString() or "").strip()
    return (parameter.AsValueString() or "").strip()


def _slab_mark(slab):
    slab_type = doc.GetElement(slab.GetTypeId())
    if slab_type is None:
        return ""
    try:
        mark = slab_type.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_MARK)
        text = _parameter_text(mark)
        if text:
            return text
    except Exception:
        pass
    for owner in (slab, slab_type):
        for name in SLAB_MARK_NAMES:
            text = _parameter_text(owner.LookupParameter(name))
            if text:
                return text
    return ""


def _numeric_parameter_feet(element, names):
    for owner in (element, doc.GetElement(element.GetTypeId())):
        if owner is None:
            continue
        for name in names:
            parameter = owner.LookupParameter(name)
            if parameter is None or not parameter.HasValue:
                continue
            if parameter.StorageType == StorageType.Double:
                value = parameter.AsDouble()
                if value > 0:
                    return value
    return None


def _beam_half_width(beam):
    width = _numeric_parameter_feet(beam, BEAM_WIDTH_NAMES)
    if width is not None:
        return width / 2.0
    # Bounding boxes globais nao sao usados: em vigas diagonais eles confundem
    # comprimento com largura. Sem parametro conhecido, adota bw = 40 cm.
    return 20.0 * CM_TO_FT


def _solids_from_geometry(geometry):
    solids = []
    if geometry is None:
        return solids
    for item in geometry:
        if isinstance(item, Solid) and item.Volume > 1e-9:
            solids.append(item)
        elif isinstance(item, GeometryInstance):
            solids.extend(_solids_from_geometry(item.GetInstanceGeometry()))
    return solids


def _slab_data(slabs):
    options = Options()
    options.DetailLevel = ViewDetailLevel.Fine
    options.IncludeNonVisibleObjects = False
    data = []
    for slab in slabs:
        mark = _slab_mark(slab)
        if not mark:
            continue
        solids = _solids_from_geometry(slab.get_Geometry(options))
        box = slab.get_BoundingBox(None)
        if solids and box is not None:
            data.append({"element": slab, "mark": mark, "solids": solids, "box": box})
    return data


def _box_contains_xy(box, point, margin):
    return (
        box.Min.X - margin <= point.X <= box.Max.X + margin
        and box.Min.Y - margin <= point.Y <= box.Max.Y + margin
    )


def _vertical_distance(box, z):
    if box.Min.Z <= z <= box.Max.Z:
        return 0.0
    return min(abs(z - box.Min.Z), abs(z - box.Max.Z))


def _intersects_vertical_probe(slab_item, point, vertical_tolerance):
    box = slab_item["box"]
    if not _box_contains_xy(box, point, 2.0 * CM_TO_FT):
        return False
    if box.Max.Z < point.Z - vertical_tolerance or box.Min.Z > point.Z + vertical_tolerance:
        return False
    start = XYZ(point.X, point.Y, point.Z - vertical_tolerance)
    end = XYZ(point.X, point.Y, point.Z + vertical_tolerance)
    line = Line.CreateBound(start, end)
    options = SolidCurveIntersectionOptions()
    for solid in slab_item["solids"]:
        try:
            if solid.IntersectWithCurve(line, options).SegmentCount > 0:
                return True
        except Exception:
            continue
    return False


def _slab_at_point(point, slab_items, vertical_tolerance):
    hits = [
        item
        for item in slab_items
        if _intersects_vertical_probe(item, point, vertical_tolerance)
    ]
    if not hits:
        return None
    return min(hits, key=lambda item: _vertical_distance(item["box"], point.Z))


def _point_and_normal(curve, fraction):
    point = curve.Evaluate(fraction, True)
    tangent = curve.ComputeDerivatives(fraction, True).BasisX
    tangent_xy = XYZ(tangent.X, tangent.Y, 0.0)
    if tangent_xy.GetLength() < 1e-9:
        raise ValueError("Eixo da viga sem direcao horizontal valida.")
    tangent_xy = tangent_xy.Normalize()
    return point, XYZ(-tangent_xy.Y, tangent_xy.X, 0.0)


def _choose_side(samples):
    if not samples:
        return None, False, ""
    counts = Counter(item["mark"] for item in samples)
    highest = max(counts.values())
    winners = sorted(mark for mark, count in counts.items() if count == highest)
    if len(winners) != 1:
        return None, True, ", ".join(winners)
    return winners[0], False, ""


def _detect_for_beam(beam, slab_items, clearance, vertical_tolerance):
    location = beam.Location
    if not isinstance(location, LocationCurve):
        raise ValueError("A viga nao possui LocationCurve.")
    curve = location.Curve
    probe_offset = _beam_half_width(beam) + clearance
    samples = defaultdict(list)
    for fraction in SAMPLE_FRACTIONS:
        point, normal = _point_and_normal(curve, fraction)
        left_point = point.Add(normal.Multiply(probe_offset))
        right_point = point.Subtract(normal.Multiply(probe_offset))
        left_slab = _slab_at_point(left_point, slab_items, vertical_tolerance)
        right_slab = _slab_at_point(right_point, slab_items, vertical_tolerance)
        if left_slab is not None:
            samples["left"].append(left_slab)
        if right_slab is not None:
            samples["right"].append(right_slab)
    left, left_ambiguous, left_detail = _choose_side(samples["left"])
    right, right_ambiguous, right_detail = _choose_side(samples["right"])
    return left, right, left_ambiguous or right_ambiguous, "; ".join(
        detail for detail in (left_detail, right_detail) if detail
    )


def _normalized_parameter_name(value):
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def _instance_parameter_names(element):
    names = []
    for parameter in element.Parameters:
        try:
            name = parameter.Definition.Name
            if name:
                names.append(name)
        except Exception:
            continue
    return sorted(set(names))


def _find_instance_parameter(element, name):
    parameter = element.LookupParameter(name)
    if parameter is None:
        target = _normalized_parameter_name(name)
        for candidate in element.Parameters:
            try:
                if _normalized_parameter_name(candidate.Definition.Name) == target:
                    return candidate
            except Exception:
                continue
    return parameter


def _writable_text_parameter(element, name):
    parameter = _find_instance_parameter(element, name)
    if parameter is None:
        available = [
            candidate
            for candidate in _instance_parameter_names(element)
            if "LAJE" in _normalized_parameter_name(candidate)
        ]
        detail = ", ".join(available) if available else "nenhum parametro contendo LAJE"
        raise ValueError(
            "Parametro de instancia '{}' nao encontrado. Disponiveis: {}.".format(
                name, detail
            )
        )
    if parameter.IsReadOnly:
        raise ValueError("Parametro '{}' e somente leitura.".format(name))
    if parameter.StorageType != StorageType.String:
        raise ValueError("Parametro '{}' deve ser do tipo texto.".format(name))
    return parameter


auto_beams, auto_slabs = _collect_beams_and_slabs()
beams = _as_list(_input(0)) or auto_beams
slabs = _as_list(_input(1)) or auto_slabs
clearance = float(_input(2, 5.0)) * CM_TO_FT
vertical_tolerance = float(_input(3, 150.0)) * CM_TO_FT
write_parameters = bool(_input(4, False))
slab_items = _slab_data(slabs)
report = [
    {
        "status": "RESUMO",
        "vigas_detectadas": len(beams),
        "pecas_alveolares_detectadas": len(slabs),
        "pecas_com_marca_e_geometria": len(slab_items),
        "marcas_detectadas": sorted(set(item["mark"] for item in slab_items)),
    }
]

if write_parameters:
    TransactionManager.Instance.EnsureInTransaction(doc)

try:
    for beam in beams:
        item = {
            "id_viga": _element_id_value(beam),
            "laje_marca_e": "",
            "laje_marca_d": "",
            "parametros_laje": [
                name
                for name in _instance_parameter_names(beam)
                if "LAJE" in _normalized_parameter_name(name)
            ],
            "pecas_alveolares_analisadas": len(slab_items),
            "status": "",
            "mensagem": "",
        }
        try:
            left, right, ambiguous, detail = _detect_for_beam(
                beam, slab_items, clearance, vertical_tolerance
            )
            if ambiguous:
                item["status"] = "AMBIGUO"
                item["mensagem"] = "Empate entre lajes: {}".format(detail)
            elif left is None and right is None:
                item["status"] = "SEM_LAJE"
                item["mensagem"] = "Nenhuma peca alveolar encontrada junto a viga."
            else:
                if left is None:
                    left, right = right, None
                item["laje_marca_e"] = left or ""
                item["laje_marca_d"] = right or ""
                if write_parameters:
                    left_parameter = _writable_text_parameter(beam, LEFT_PARAMETER)
                    right_parameter = _writable_text_parameter(beam, RIGHT_PARAMETER)
                    left_ok = left_parameter.Set(item["laje_marca_e"])
                    right_ok = right_parameter.Set(item["laje_marca_d"])
                    if not left_ok or not right_ok:
                        raise ValueError("A API do Revit recusou a gravacao dos parametros.")
                    item["status"] = "GRAVADO"
                else:
                    item["status"] = "PREVIA"
        except Exception as exc:
            item["status"] = "ERRO"
            item["mensagem"] = str(exc)
        report.append(item)
finally:
    if write_parameters:
        TransactionManager.Instance.TransactionTaskDone()

OUT = report
