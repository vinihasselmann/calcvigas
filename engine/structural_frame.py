"""Importacao e calculo de quadros estruturais mistos."""

from __future__ import annotations

import re
import unicodedata
from itertools import product
from pathlib import Path

import pandas as pd

from .lajes_alv import ANALYSIS_SIMPLE, run_laje_case
from .runner import LAYER_LIMITS_BY_BW, SECTION_CATALOG as VPL_SECTION_CATALOG, run_case as run_vpl_case
from .vr import optimize_vr_case
from .vpt import VPT_LAYER_LIMITS_BY_BW, run_vpt_case
from .vpt_model import VPT_SECTION_CATALOG


ELEMENT_VPL = "VPL"
ELEMENT_VPT = "VPT"
ELEMENT_VR = "VR"
ELEMENT_LAJE = "LAJE"
MAX_TAXA_CA = 200
MAX_TAXA_CP = 40
MAX_TAXA_CA_PASSIVE_ONLY = 160
VPL_SIGMA_INF_TOLERANCE = 10
MIN_MRU_MSD_RATIO = 1.10
VPT_ECONOMY_MAX_AREA_INCREASE = 1.25
VPT_ECONOMY_MAX_HP_INCREASE = 10
VPT_ECONOMY_TOTAL_REDUCTION = 0.15
VPT_ECONOMY_PRESTRESS_REDUCTION = 0.20
VPT_ECONOMY_TOTAL_TOLERANCE = 1.10
CORD_DIAM_OPTIONS = (12.7,)
VPL_PASSIVE_DIAM_OPTIONS = (10.0, 12.5, 16.0, 20.0, 25.0)
VPT_PASSIVE_DIAM_OPTIONS = (10.0, 12.5, 16.0, 20.0, 25.0, 32.0)


ALIAS_MAP = {
    "id_elemento": {"id", "id elemento", "id_elemento", "elemento", "marca", "identificador"},
    "tipo_elemento": {"tipo elemento", "tipo_elemento", "categoria", "sistema", "familia estrutural"},
    "nome_tipo": {"nome tipo", "nome_tipo", "tipo", "type", "familia", "familia e tipo", "family and type"},
    "peca_altura_pre": {
        "peca altura pre",
        "peca altura preo",
        "peca_altura_pre",
        "peca_altura_preo",
        "altura pre",
        "altura preo",
        "altura_pre",
        "altura_preo",
    },
    "peca_largura_pre": {
        "peca largura pre",
        "peca largura preo",
        "peca_largura_pre",
        "peca_largura_preo",
        "largura pre",
        "largura preo",
        "largura_pre",
        "largura_preo",
    },
    "secao": {"secao", "section", "perfil", "tipo secao"},
    "vao_viga": {
        "vao viga",
        "vao_viga",
        "vao_viga_m",
        "vao_viga_cm",
        "vao da viga",
        "comprimento viga",
        "comprimento",
    },
    "vao_laje": {"vao laje", "vao_laje", "vao_laje_m", "vao da laje"},
    "vao": {"vao", "vao_m", "comprimento laje", "vao painel"},
    "lp_type": {"tipo laje", "tipo_laje", "laje", "lp", "lp_type", "familia laje"},
    "lp_esq": {"tipo_laje_esq", "laje esquerda", "lp_esq", "lp esq"},
    "lp_dir": {"tipo_laje_dir", "laje direita", "lp_dir", "lp dir"},
    "vao_laje_esq": {"vao_laje_esq", "vao_laje_esq_m", "vao laje esquerda"},
    "vao_laje_dir": {"vao_laje_dir", "vao_laje_dir_m", "vao laje direita"},
    "acd": {"sobrecarga", "sobrecarga_kgf_m2", "acd", "acd_kgf_m2", "carga acidental", "laje sobrecarga", "laje_sobrecarga"},
    "taxa_ca": {"taxa ca", "taxa-ca", "taxa_ca"},
    "taxa_cp": {"taxa cp", "taxa-cp", "taxa_cp"},
    "laje_marca": {"laje marca", "laje_marca", "marca laje", "lajes marcas"},
    "laje_psi": {"laje psi", "laje_psi", "psi laje", "psi_laje"},
    "acd_esq": {"sobrecarga_esq", "sobrecarga_esq_kgf_m2", "acd_esq", "acd esquerda"},
    "acd_dir": {"sobrecarga_dir", "sobrecarga_dir_kgf_m2", "acd_dir", "acd direita"},
    "rev": {"revestimento", "revestimento_kgf_m2", "rev"},
    "rev_esq": {"revestimento_esq", "revestimento_esq_kgf_m2", "rev_esq"},
    "rev_dir": {"revestimento_dir", "revestimento_dir_kgf_m2", "rev_dir"},
    "capa": {"capa", "capa_cm", "capa concreto"},
    "hinf_viga": {"hinf", "hinf_viga", "hinf_viga_cm", "altura inferior"},
    "fck": {"fck", "fck_mpa", "fck viga"},
    "fckj": {"fckj", "fckj_mpa"},
    "fck_capa": {"fck_capa", "fck_capa_mpa", "fck capa"},
    "continuidade_kgf": {"continuidade", "continuidade_kgf", "momento continuidade"},
    "analise": {"analise", "modelo analise"},
    "carga_fechamento_kgf_m": {"carga fechamento", "carga_fechamento", "carga fechamento kgf m", "carga_fechamento_kgf_m", "fechamento"},
    "carga_permanente_kgf_m": {"carga permanente", "carga_permanente", "carga permanente kgf m", "carga_permanente_kgf_m", "g adicional"},
    "carga_variavel_kgf_m": {"carga variavel", "carga_variavel", "carga variavel kgf m", "carga_variavel_kgf_m", "q linear"},
    "h_parede": {"h parede", "h_parede", "altura parede", "altura_parede"},
    "esp_parede": {"esp parede", "esp_parede", "espessura parede", "espessura_parede"},
    "peso_parede_kgf_m3": {"peso parede", "peso_parede", "peso_parede_kgf_m3"},
}


VPL_DEFAULTS = {
    "bw": 40,
    "bf": 20,
    "cob": 2.5,
    "capa": 5,
    "hs": 0,
    "fck": 50,
    "fckj": 35,
    "fck_capa": 40,
    "caa": "II",
    "fat_pi": 0.95,
    "dpi": 0.20,
    "dps": 0.10,
    "n_cord_c1": 6,
    "n_cord_c2": 0,
    "n_cord_c3": 0,
    "diam_mm": 12.7,
    "n_barras_c1": 2,
    "n_barras_c2": 0,
    "n_barras_c3": 0,
    "diam_barra_c1_mm": 20.0,
    "diam_barra_c2_mm": 12.5,
    "diam_barra_c3_mm": 12.5,
    "n_cord_sup": 2,
    "diam_cord_sup_mm": 9.5,
    "yp_cord_sup": -3.98,
    "n_barras_sup": 2,
    "diam_barra_sup_mm": 10.0,
    "ys_barra_sup": -3.80,
    "rev": 200,
    "psi_tipo": "Locais com predominancia de pesos/equipamentos ou concentracao de pessoas",
    "psi0": 0.7,
    "psi1": 0.6,
    "psi2": 0.4,
    "hinf_viga": 50,
}

VPT_DEFAULTS = {"capa": 5, "fck": 50, "fckj": 35, "fck_capa": 40, "rev_esq": 200, "rev_dir": 200}
LAJE_DEFAULTS = {"capa": 5, "fck_capa": 40, "continuidade_kgf": 0, "analise": ANALYSIS_SIMPLE}
PSI_BY_LAJE_CODE = {
    "0": {"psi_tipo": "Locais sem predominancia de pesos/equipamentos ou concentracao de pessoas", "psi0": 0.5, "psi1": 0.4, "psi2": 0.3},
    "1": {"psi_tipo": "Locais com predominancia de pesos/equipamentos ou concentracao de pessoas", "psi0": 0.7, "psi1": 0.6, "psi2": 0.4},
    "2": {"psi_tipo": "Bibliotecas, arquivos, oficinas e garagens", "psi0": 0.8, "psi1": 0.7, "psi2": 0.6},
}


def read_frame_table(file_or_path, filename: str | None = None) -> pd.DataFrame:
    suffix = _file_suffix(file_or_path, filename)
    try:
        if suffix in {".xlsx", ".xlsm", ".xls"}:
            return pd.read_excel(file_or_path)
        if suffix in {".txt", ".csv"}:
            return _read_delimited_text(file_or_path, sep=";")
    except pd.errors.ParserError:
        return _read_delimited_text(file_or_path, sep=";")
    if _looks_like_delimited_text(file_or_path):
        return _read_delimited_text(file_or_path, sep=";")
    raise ValueError("Use uma tabela .xlsx, .xlsm, .xls, .csv ou .txt.")


def normalize_frame_table(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    used = set()
    for column in df.columns:
        normalized = _normalize_text(column)
        canonical = CANONICAL_BY_ALIAS.get(normalized, normalized.replace(" ", "_"))
        if canonical in used:
            canonical = f"{canonical}_{len(used)}"
        renamed[column] = canonical
        used.add(canonical)
    return df.rename(columns=renamed).dropna(how="all").copy()


def run_frame_cases(df: pd.DataFrame, progress_callback=None) -> pd.DataFrame:
    normalized = normalize_frame_table(df)
    laje_lookup = _build_laje_lookup(normalized)
    results = []
    total = len(normalized)
    for idx, (_, row) in enumerate(normalized.iterrows(), start=1):
        row_data = _clean_row(row.to_dict())
        try:
            element_type = _detect_element_type(row_data)
            row_data = _resolve_laje_reference(row_data, element_type, laje_lookup)
            result = _run_typed_case(element_type, row_data)
        except Exception as exc:
            element_type = str(row_data.get("tipo_elemento", "") or "DESCONHECIDO")
            result = {"status": "ERRO", "erro_msg": str(exc)}
        results.append({"linha_origem": idx, "id_elemento": row_data.get("id_elemento"), "tipo_elemento": element_type, "nome_tipo": row_data.get("nome_tipo"), **result})
        if progress_callback is not None:
            progress_callback(idx, total)
    output = pd.DataFrame(results)
    output.attrs["fixed_params"] = {"modo": "quadro estrutural importado"}
    output.attrs["ranges"] = {"linhas_importadas": total}
    return output


def sample_frame_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ID_ELEMENTO": "LA01", "NOME_TIPO": "LP20", "PECA-Altura Pre": 20, "PECA-Largura Pre": 125, "VAO_VIGA_CM": 600, "LAJE-Sobrecarga": 800, "LAJE_Marca": ""},
            {"ID_ELEMENTO": "LA02", "NOME_TIPO": "LP20", "PECA-Altura Pre": 20, "PECA-Largura Pre": 125, "VAO_VIGA_CM": 887.5, "LAJE-Sobrecarga": 500, "LAJE_Marca": ""},
            {"ID_ELEMENTO": "V01", "NOME_TIPO": "L", "PECA-Altura Pre": 65, "PECA-Largura Pre": 40, "VAO_VIGA_CM": 652.46, "TAXA-CA": "0 kg/m3", "TAXA-CP": "0 kg/m3", "LAJE_Marca": "LA01"},
            {"ID_ELEMENTO": "V02", "NOME_TIPO": "L", "PECA-Altura Pre": 65, "PECA-Largura Pre": 40, "VAO_VIGA_CM": 652.46, "TAXA-CA": "0 kg/m3", "TAXA-CP": "0 kg/m3", "LAJE_Marca": "LA02"},
            {"ID_ELEMENTO": "V03", "NOME_TIPO": "T", "PECA-Altura Pre": 50, "PECA-Largura Pre": 25, "VAO_VIGA_CM": 792.46, "TAXA-CA": "0 kg/m3", "TAXA-CP": "0 kg/m3", "LAJE_Marca": "LA01"},
        ]
    )


def _file_suffix(file_or_path, filename: str | None) -> str:
    name = filename or getattr(file_or_path, "name", None) or str(file_or_path)
    return Path(name).suffix.lower()


def _read_delimited_text(file_or_path, sep: str) -> pd.DataFrame:
    data = _read_file_bytes(file_or_path)
    text = _decode_text_table(data)
    lines = [line.strip("\ufeff\r\n") for line in text.splitlines()]
    lines = [line for line in lines if line.strip()]
    if not lines:
        return pd.DataFrame()
    header_idx = _find_header_line(lines, sep)
    headers = [_clean_txt_cell(cell) for cell in lines[header_idx].split(sep)]
    rows = []
    for line in lines[header_idx + 1 :]:
        cells = [_clean_txt_cell(cell) for cell in line.split(sep)]
        if not any(cells):
            continue
        cells = _fit_cells_to_header(cells, len(headers))
        rows.append(cells)
    return pd.DataFrame(rows, columns=headers)


def _decode_text_table(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="replace")
    sample = data[:2000]
    if sample.count(b"\x00") > len(sample) * 0.2:
        try:
            return data.decode("utf-16", errors="replace")
        except UnicodeError:
            pass
    return data.decode("utf-8-sig", errors="replace")


def _find_header_line(lines: list[str], sep: str) -> int:
    for idx, line in enumerate(lines):
        normalized = _normalize_text(line)
        if "id elemento" in normalized and "nome tipo" in normalized:
            return idx
        cells = [_normalize_text(cell) for cell in line.split(sep)]
        if "id elemento" in cells or "id_elemento" in cells:
            return idx
    return 0


def _clean_txt_cell(value: str) -> str:
    return value.strip().strip('"').strip()


def _fit_cells_to_header(cells: list[str], header_len: int) -> list[str]:
    if len(cells) < header_len:
        return cells + [""] * (header_len - len(cells))
    if len(cells) > header_len:
        return cells[: header_len - 1] + [(";".join(cells[header_len - 1 :])).strip(";")]
    return cells


def _read_file_bytes(file_or_path) -> bytes:
    if hasattr(file_or_path, "seek"):
        file_or_path.seek(0)
    data = file_or_path.getvalue() if hasattr(file_or_path, "getvalue") else Path(file_or_path).read_bytes()
    return data.encode("utf-8-sig") if isinstance(data, str) else data


def _looks_like_delimited_text(file_or_path) -> bool:
    try:
        data = _read_file_bytes(file_or_path)
    except Exception:
        return False
    sample = _decode_text_table(data[:4096])
    return ";" in sample and "ID_ELEMENTO" in sample.upper()


def _normalize_text(value) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


CANONICAL_BY_ALIAS = {_normalize_text(alias): canonical for canonical, aliases in ALIAS_MAP.items() for alias in aliases | {canonical}}


def _clean_row(row: dict) -> dict:
    return {key: value for key, value in row.items() if not _is_blank(value)}


def _is_blank(value) -> bool:
    if isinstance(value, (list, tuple, dict)):
        return False
    if isinstance(value, str) and not value.strip():
        return True
    return bool(pd.isna(value))


def _detect_element_type(row: dict) -> str:
    explicit = _normalize_text(row.get("tipo_elemento"))
    if explicit in {"vpl", "viga l", "l"}:
        return ELEMENT_VPL
    if explicit in {"vpt", "viga t", "t"}:
        return ELEMENT_VPT
    if explicit in {"vr", "viga r", "r", "retangular", "viga retangular"}:
        return ELEMENT_VR
    if explicit in {"laje", "lajes", "laje alveolar", "alveolar", "lp"}:
        return ELEMENT_LAJE
    secao = str(row.get("secao", "")).upper()
    name = str(row.get("nome_tipo", "")).upper()
    if name.startswith("LP"):
        return ELEMENT_LAJE
    if secao.startswith("T") or name == "T" or "VPT" in name:
        return ELEMENT_VPT
    if secao.startswith("R") or name == "R" or "VR" in name or "RETANGULAR" in name:
        return ELEMENT_VR
    if secao.startswith("L") or name == "L" or "VPL" in name:
        return ELEMENT_VPL
    if row.get("vao") is not None and row.get("lp_type") is not None:
        return ELEMENT_LAJE
    raise ValueError("Nao foi possivel identificar o tipo do elemento. Use tipo_elemento = VPL, VPT, VR ou LAJE.")


def _run_typed_case(element_type: str, row: dict) -> dict:
    try:
        if element_type == ELEMENT_VPL:
            return _optimize_vpl_case(_vpl_params(row))
        if element_type == ELEMENT_VPT:
            return _optimize_vpt_case(_vpt_params(row))
        if element_type == ELEMENT_VR:
            return optimize_vr_case(_vr_params(row))
        if element_type == ELEMENT_LAJE:
            return run_laje_case(_laje_params(row))
        raise ValueError(f"Tipo de elemento nao suportado: {element_type}")
    except Exception as exc:
        return {"status": "ERRO", "erro_msg": str(exc)}


def _vpl_params(row: dict) -> dict:
    params = VPL_DEFAULTS.copy()
    params.update(_take(row, "vao_viga", "vao_laje", "acd", "rev", "capa", "hinf_viga", "fck", "fckj", "fck_capa"))
    _apply_laje_psi(params, row)
    if "lp_type" in row:
        params["lp_type"] = _normalize_lp(row["lp_type"])
    elif "nome_tipo" in row and str(row["nome_tipo"]).upper().startswith("LP"):
        params["lp_type"] = _normalize_lp(row["nome_tipo"])
    if "secao" in row:
        params["secao_importada"] = row["secao"]
    if "peca_altura_pre" in row and "peca_largura_pre" in row:
        _apply_vpl_geometry_from_revit(params, row)
    _convert_lengths(params, "vao_viga", "vao_laje")
    _require(params, "vao_viga", "lp_type", "vao_laje", "acd")
    return params


def _optimize_vpl_case(base_params: dict) -> dict:
    original = _vpl_section_label(base_params)
    fallback = None
    best_structural = None
    for params, section_label in _iter_vpl_section_candidates(base_params):
        best_section = None
        for layout in _iter_vpl_layouts(params["bw"]):
            for top_layout in _iter_vpl_top_layouts(layout, params):
                candidate = {**params, **layout, **top_layout}
                result = run_vpl_case(candidate)
                if not result.get("secao"):
                    result["secao"] = section_label
                result["secao_testada"] = section_label
                if fallback is None or _fallback_score(result) < _fallback_score(fallback):
                    fallback = _copy_psi_fields(result, candidate)
                if result.get("status") == "PASSA":
                    copied = _copy_psi_fields(result, candidate)
                    if best_structural is None or _vpl_layout_score(copied) < _vpl_layout_score(best_structural):
                        best_structural = copied
                if _is_approved_vpl_solution(result):
                    accepted = _copy_psi_fields(_mark_vpl_sigma_rule_as_accepted(result), candidate)
                    if best_section is None or _vpl_layout_score(accepted) < _vpl_layout_score(best_section):
                        best_section = accepted
        if best_section is not None:
            return _with_section_recommendation(best_section, original, section_label)
    if best_structural is not None:
        marked = _mark_vpl_sigma_rule_as_accepted(best_structural)
        return _with_section_recommendation(marked, original, marked.get("secao_testada", original))
    return _with_no_solution_message(fallback, original, require_vpl_sigma=True)


def _iter_vpl_section_candidates(base_params: dict):
    seen = set()
    current = base_params.copy()
    current_label = _vpl_section_label(current)
    if current.get("h") and current.get("bw"):
        seen.add((float(current["h"]), float(current["bw"])))
        yield current, current_label
    lp_type = base_params.get("lp_type")
    if not lp_type:
        return
    from data.lp_table import LP_TABLE

    hsup = LP_TABLE[lp_type]["cap"] + base_params.get("capa", 5)
    current_h = float(base_params.get("h") or 0)
    bw = float(base_params.get("bw", VPL_DEFAULTS["bw"]))
    for h, hinf in sorted(VPL_SECTION_CATALOG):
        if h != hsup + hinf:
            continue
        if current_h and h < current_h:
            continue
        key = (float(h), bw)
        if key in seen:
            continue
        seen.add(key)
        params = base_params.copy()
        params.update({"h": float(h), "hinf": float(hinf), "hsup": float(hsup), "bw": bw, "bf": base_params.get("bf", 20)})
        yield params, f"L{int(h)}/{int(hinf)}x{int(bw)}"


def _vpl_section_label(params: dict) -> str:
    h = params.get("h")
    hinf = params.get("hinf")
    bw = params.get("bw")
    if h and hinf and bw:
        return f"L{int(round(float(h)))}/{int(round(float(hinf)))}x{int(round(float(bw)))}"
    return str(params.get("secao") or params.get("secao_importada") or "")


def _iter_vpl_layouts(bw: float):
    limits = _limits_for_bw(bw)
    seen = set()
    for stage in (1, 2, 3):
        for d1, d2, d3 in product(VPL_PASSIVE_DIAM_OPTIONS, VPL_PASSIVE_DIAM_OPTIONS, VPL_PASSIVE_DIAM_OPTIONS):
            for n_b1 in range(2, limits["c1"] + 1):
                for n_c1 in range(0, limits["c1"] - n_b1 + 1, 2):
                    base = _reinforcement_layout(n_c1, 0, 0, n_b1, 0, 0, 12.7, d1, d2, d3)
                    if _valid_vpl_layout(base):
                        yield from _dedupe_layout(base, seen)
                    if stage == 1 or n_b1 + n_c1 < limits["c1"]:
                        continue
                    for n_b2, n_c2 in _layer_count_pairs(limits["c2"]):
                        c2 = _reinforcement_layout(n_c1, n_c2, 0, n_b1, n_b2, 0, 12.7, d1, d2, d3)
                        if _valid_vpl_layout(c2):
                            yield from _dedupe_layout(c2, seen)
                        if stage == 2 or n_b2 + n_c2 < limits["c2"]:
                            continue
                        for n_b3, n_c3 in _layer_count_pairs(limits["c3"]):
                            c3 = _reinforcement_layout(n_c1, n_c2, n_c3, n_b1, n_b2, n_b3, 12.7, d1, d2, d3)
                            if _valid_vpl_layout(c3):
                                yield from _dedupe_layout(c3, seen)


def _layer_count_pairs(limit: int, even_cords_only: bool = False):
    for total in range(1, limit + 1):
        for n_barras in range(0, total + 1):
            n_cord = total - n_barras
            if n_barras == 1 or n_cord == 1:
                continue
            if not even_cords_only or n_cord % 2 == 0:
                yield n_barras, n_cord


def _valid_vpl_layout(layout: dict) -> bool:
    n_c1 = _layout_count(layout, "n_cord_c1")
    n_c2 = _layout_count(layout, "n_cord_c2")
    n_c3 = _layout_count(layout, "n_cord_c3")
    for idx in (1, 2, 3):
        if _layout_count(layout, f"n_cord_c{idx}") == 1:
            return False
        if _layout_count(layout, f"n_barras_c{idx}") == 1:
            return False
    if n_c2 > 0 and n_c1 == 0:
        return False
    if n_c3 > 0 and (n_c1 == 0 or n_c2 == 0):
        return False
    return True


def _dedupe_layout(layout: dict, seen: set):
    key_parts = []
    for idx in (1, 2, 3):
        n_cord = _layout_count(layout, f"n_cord_c{idx}")
        n_barras = _layout_count(layout, f"n_barras_c{idx}")
        key_parts.extend(
            (
                n_cord,
                layout.get(f"diam_cord_c{idx}_mm") if n_cord else 0,
                n_barras,
                layout.get(f"diam_barra_c{idx}_mm") if n_barras else 0,
            )
        )
    key = tuple(key_parts)
    if key not in seen:
        seen.add(key)
        yield layout


def _iter_vpl_top_layouts(bottom_layout: dict, base_params: dict):
    default = {
        "n_cord_sup": base_params.get("n_cord_sup", VPL_DEFAULTS["n_cord_sup"]),
        "diam_cord_sup_mm": base_params.get("diam_cord_sup_mm", VPL_DEFAULTS["diam_cord_sup_mm"]),
        "yp_cord_sup": base_params.get("yp_cord_sup", VPL_DEFAULTS["yp_cord_sup"]),
        "n_barras_sup": base_params.get("n_barras_sup", VPL_DEFAULTS["n_barras_sup"]),
        "diam_barra_sup_mm": base_params.get("diam_barra_sup_mm", VPL_DEFAULTS["diam_barra_sup_mm"]),
        "ys_barra_sup": base_params.get("ys_barra_sup", VPL_DEFAULTS["ys_barra_sup"]),
    }
    if sum(_layout_count(bottom_layout, f"n_cord_c{idx}") for idx in (1, 2, 3)) == 0:
        yield {**default, "n_cord_sup": 0}
        return
    yield default


_LAYOUT_KEY_COLUMNS = (
    "n_cord_c1",
    "n_cord_c2",
    "n_cord_c3",
    "diam_cord_c1_mm",
    "diam_cord_c2_mm",
    "diam_cord_c3_mm",
    "n_barras_c1",
    "n_barras_c2",
    "n_barras_c3",
    "diam_barra_c1_mm",
    "diam_barra_c2_mm",
    "diam_barra_c3_mm",
)


def _reinforcement_layout(n_c1, n_c2, n_c3, n_b1, n_b2, n_b3, d_cord, d_b1, d_b2, d_b3) -> dict:
    return {
        "n_cord_c1": n_c1,
        "n_cord_c2": n_c2,
        "n_cord_c3": n_c3,
        "diam_mm": d_cord,
        "diam_cord_c1_mm": d_cord,
        "diam_cord_c2_mm": d_cord,
        "diam_cord_c3_mm": d_cord,
        "n_barras_c1": n_b1,
        "n_barras_c2": n_b2,
        "n_barras_c3": n_b3,
        "diam_barra_c1_mm": d_b1,
        "diam_barra_c2_mm": d_b2,
        "diam_barra_c3_mm": d_b3,
    }


def _limits_for_bw(bw: float) -> dict:
    numeric = int(round(float(bw)))
    if numeric in LAYER_LIMITS_BY_BW:
        return LAYER_LIMITS_BY_BW[numeric]
    if numeric in VPT_LAYER_LIMITS_BY_BW:
        return VPT_LAYER_LIMITS_BY_BW[numeric]
    raise ValueError(f"bw {numeric} sem limites cadastrados para camadas.")


def _is_approved_vpl_solution(result: dict) -> bool:
    bottom_cords = _bottom_cord_count(result)
    return (
        result.get("status") == "PASSA"
        and result.get("ok_flexao") is True
        and result.get("ok_cisalhamento") is True
        and result.get("ok_els") is True
        and _coerce_value(result.get("taxa_armadura_passiva", MAX_TAXA_CA + 1)) <= MAX_TAXA_CA
        and _coerce_value(result.get("taxa_armadura_protendida", MAX_TAXA_CP + 1)) <= MAX_TAXA_CP
        and _has_minimum_vpl_passive_only_reinforcement(result)
        and (_coerce_value(result.get("MRU_MSD", 0)) or 0) >= MIN_MRU_MSD_RATIO
        and (bottom_cords == 0 or _vpl_sigma_inf_f_within_tolerance(result))
    )


def _has_minimum_vpl_passive_only_reinforcement(result: dict) -> bool:
    if _bottom_cord_count(result) > 0:
        return True
    taxa = _coerce_value(result.get("taxa_armadura_passiva", MAX_TAXA_CA + 1))
    return taxa <= MAX_TAXA_CA_PASSIVE_ONLY


def _vpl_sigma_inf_f_ok(result: dict) -> bool:
    sigma_inf = _coerce_value(result.get("sigma_inf_D", result.get("sigma_inf_F")))
    lim_inf = _coerce_value(result.get("lim_inf_F"))
    if sigma_inf is None or lim_inf is None:
        return False
    return sigma_inf >= lim_inf - VPL_SIGMA_INF_TOLERANCE


def _vpl_sigma_inf_f_within_tolerance(result: dict) -> bool:
    return _vpl_sigma_distance(result) == 0


def _vpl_sigma_distance(result: dict) -> float:
    sigma_inf = _coerce_value(result.get("sigma_inf_D", result.get("sigma_inf_F")))
    lim_inf = _coerce_value(result.get("lim_inf_F"))
    if sigma_inf is None or lim_inf is None:
        return float("inf")
    lower = lim_inf - VPL_SIGMA_INF_TOLERANCE
    upper = lim_inf + VPL_SIGMA_INF_TOLERANCE
    if lower <= sigma_inf <= upper:
        return 0
    return min(abs(sigma_inf - lower), abs(sigma_inf - upper))


def _mark_vpl_sigma_rule_as_accepted(result: dict) -> dict:
    output = result.copy()
    lim_inf = _coerce_value(output.get("lim_inf_F"))
    if lim_inf is not None:
        output["lim_inf_F_min"] = lim_inf - VPL_SIGMA_INF_TOLERANCE
        output["lim_inf_F_max"] = lim_inf + VPL_SIGMA_INF_TOLERANCE
    output["ok_inf_F"] = True
    output["ok_inf_D"] = True
    output["ok_inf_ato"] = True
    output["ok_els"] = True
    output["ok"] = True
    output["status"] = "PASSA"
    output["regra_sigma_inf_F"] = f"sigma_inf_D dentro de lim_inf_F +/- {VPL_SIGMA_INF_TOLERANCE}"
    return output


def _bottom_cord_count(result: dict) -> int:
    return sum(_layout_count(result, f"n_cord_c{idx}") for idx in (1, 2, 3))


def _layout_count(result: dict, key: str) -> int:
    return int(_coerce_value(result.get(key)) or 0)


def _layout_stage(result: dict) -> int:
    if _layout_count(result, "n_cord_c3") + _layout_count(result, "n_barras_c3") > 0:
        return 3
    if _layout_count(result, "n_cord_c2") + _layout_count(result, "n_barras_c2") > 0:
        return 2
    return 1


def _vpl_layout_score(result: dict) -> tuple:
    n_cords = _bottom_cord_count(result)
    n_bars = sum(_layout_count(result, f"n_barras_c{idx}") for idx in (1, 2, 3))
    active_diameters = [
        _coerce_value(result.get(f"diam_barra_c{idx}_mm")) or 0
        for idx in (1, 2, 3)
        if _layout_count(result, f"n_barras_c{idx}") > 0
    ]
    passive_taxa = _coerce_value(result.get("taxa_armadura_passiva")) or float("inf")
    prestress_taxa = _coerce_value(result.get("taxa_armadura_protendida")) or float("inf")
    min_active_diameter = min(active_diameters, default=0)
    mru_distance = abs((_coerce_value(result.get("MRU_MSD")) or 0) - MIN_MRU_MSD_RATIO)
    if n_cords > 0:
        return (
            _layout_stage(result),
            n_bars,
            _vpl_sigma_distance(result),
            n_cords,
            _layout_count(result, "n_cord_c3"),
            passive_taxa,
            prestress_taxa,
            mru_distance,
            min_active_diameter,
        )
    return (
        _layout_stage(result),
        n_cords,
        _layout_count(result, "n_cord_c3"),
        n_bars,
        passive_taxa,
        prestress_taxa,
        mru_distance,
        min_active_diameter,
    )


def _fallback_score(result: dict | None) -> tuple:
    if result is None:
        return (1, float("inf"))
    return (0 if result.get("status") == "PASSA" else 1, -(_coerce_value(result.get("MRU_MSD")) or 0))


def _vpt_params(row: dict) -> dict:
    params = VPT_DEFAULTS.copy()
    params.update(_take(row, "secao", "vao_viga", "vao_laje_esq", "vao_laje_dir", "acd_esq", "acd_dir", "rev_esq", "rev_dir", "capa", "fck", "fckj", "fck_capa"))
    _apply_laje_psi(params, row)
    if "lp_esq" in row:
        params["lp_esq"] = _normalize_lp(row["lp_esq"])
    elif "lp_type" in row:
        params["lp_esq"] = _normalize_lp(row["lp_type"])
    if "lp_dir" in row:
        params["lp_dir"] = _normalize_lp(row["lp_dir"])
    elif "lp_type" in row:
        params["lp_dir"] = _normalize_lp(row["lp_type"])
    if "secao" not in params and {"peca_altura_pre", "peca_largura_pre"}.issubset(row):
        params["secao"] = _infer_vpt_section(row)
    _convert_lengths(params, "vao_viga", "vao_laje_esq", "vao_laje_dir")
    _require(params, "secao", "vao_viga", "lp_esq", "lp_dir", "vao_laje_esq", "vao_laje_dir", "acd_esq", "acd_dir")
    return params


def _optimize_vpt_case(base_params: dict) -> dict:
    original = str(base_params.get("secao") or "")
    fallback = None
    first_approved = None
    best_economy = None
    for params, section_label in _iter_vpt_section_candidates(base_params):
        if first_approved is not None and not _should_evaluate_vpt_economy_section(first_approved, section_label):
            continue
        best_section = None
        bw = VPT_SECTION_CATALOG[section_label].bw if section_label in VPT_SECTION_CATALOG else params.get("bw", 40)
        for layout in _iter_vpt_layouts(bw):
            candidate = {**params, **layout, "secao": section_label}
            result = run_vpt_case(candidate)
            result["secao_testada"] = section_label
            if fallback is None or _vpt_score(result) < _vpt_score(fallback):
                fallback = _copy_psi_fields(result, candidate)
            if _is_approved_vpt_solution(result):
                copied = _copy_psi_fields(_mark_vpt_sigma_rule_as_accepted(result), candidate)
                if best_section is None or _vpt_score(copied) < _vpt_score(best_section):
                    best_section = copied
        if best_section is not None:
            if first_approved is None:
                first_approved = best_section
                best_economy = best_section
            elif _prefer_vpt_economy_candidate(first_approved, best_economy, best_section):
                best_economy = best_section
    if best_economy is not None:
        return _with_section_recommendation(best_economy, original, str(best_economy.get("secao_testada") or best_economy.get("secao") or ""))
    return _with_no_solution_message(fallback, original)


def _iter_vpt_section_candidates(base_params: dict):
    original = str(base_params.get("secao") or "")
    original_spec = VPT_SECTION_CATALOG.get(original)
    if original_spec is None:
        yield base_params.copy(), original
        return
    candidates = [
        spec
        for spec in VPT_SECTION_CATALOG.values()
        if spec.hp >= original_spec.hp
        and spec.bw >= original_spec.bw
    ]
    candidates.sort(key=lambda spec: (spec.hp * spec.bw, spec.hp, spec.bw, spec.secao))
    for spec in candidates:
        params = base_params.copy()
        params["secao"] = spec.secao
        yield params, spec.secao


def _iter_vpt_layouts(bw: float):
    limits = _limits_for_bw(bw)
    seen = set()
    max_c1_cords_with_min_passive = max(0, limits["c1"] - 2)
    diameter_options = tuple(reversed(VPT_PASSIVE_DIAM_OPTIONS))
    for d_b1, d_b2, d_b3 in product(diameter_options, diameter_options, diameter_options):
        for n_b1 in range(2, limits["c1"] + 1):
            for n_c1 in range(0, limits["c1"] - n_b1 + 1):
                if n_c1 % 2:
                    continue
                base = _reinforcement_layout(n_c1, 0, 0, n_b1, 0, 0, 12.7, d_b1, d_b2, d_b3)
                yield from _dedupe_layout(base, seen)
                if n_b1 + n_c1 < limits["c1"]:
                    continue
                for n_b2, n_c2 in _layer_count_pairs(limits["c2"], even_cords_only=True):
                    if n_c2 > 0 and n_c1 == 0:
                        continue
                    if n_c2 > 0 and n_c1 < max_c1_cords_with_min_passive:
                        continue
                    c2 = _reinforcement_layout(n_c1, n_c2, 0, n_b1, n_b2, 0, 12.7, d_b1, d_b2, d_b3)
                    yield from _dedupe_layout(c2, seen)
                    if n_b2 + n_c2 < limits["c2"]:
                        continue
                    for n_b3, n_c3 in _layer_count_pairs(limits["c3"], even_cords_only=True):
                        if n_c3 > 0 and n_c2 == 0:
                            continue
                        c3 = _reinforcement_layout(n_c1, n_c2, n_c3, n_b1, n_b2, n_b3, 12.7, d_b1, d_b2, d_b3)
                        yield from _dedupe_layout(c3, seen)


def _is_approved_vpt_solution(result: dict) -> bool:
    return (
        result.get("status") == "PASSA"
        and result.get("ok_flexao") is True
        and result.get("ok_cisalhamento") is True
        and _coerce_value(result.get("taxa_armadura_passiva", MAX_TAXA_CA + 1)) <= MAX_TAXA_CA
        and _coerce_value(result.get("taxa_armadura_protendida", MAX_TAXA_CP + 1)) <= MAX_TAXA_CP
        and (_coerce_value(result.get("MRU_MSD", 0)) or 0) >= MIN_MRU_MSD_RATIO
        and _vpt_sigma_inf_f_within_tolerance(result)
    )


def _should_evaluate_vpt_economy_section(reference: dict, section_label: str) -> bool:
    return section_label in _vpt_economy_section_labels(reference)


def _vpt_economy_section_labels(reference: dict) -> set[str]:
    ref_spec = VPT_SECTION_CATALOG.get(str(reference.get("secao_testada") or reference.get("secao") or ""))
    if ref_spec is None:
        return set()
    ref_area = ref_spec.hp * ref_spec.bw
    candidates = [
        spec
        for spec in VPT_SECTION_CATALOG.values()
        if spec.bw == ref_spec.bw
        and spec.h1 > ref_spec.h1
        and spec.hp <= ref_spec.hp + VPT_ECONOMY_MAX_HP_INCREASE
        and spec.hp * spec.bw <= ref_area * VPT_ECONOMY_MAX_AREA_INCREASE
    ]
    if not candidates:
        return set()
    max_h1 = max(spec.h1 for spec in candidates)
    best_h1_family = [spec for spec in candidates if spec.h1 == max_h1]
    target = min(best_h1_family, key=lambda spec: (spec.hp * spec.bw, spec.hp, spec.secao))
    return {target.secao}


def _prefer_vpt_economy_candidate(reference: dict, current: dict | None, candidate: dict) -> bool:
    if not _is_vpt_economy_candidate(reference, candidate):
        return False
    if current is None or current is reference:
        return True
    return _vpt_economy_score(candidate) < _vpt_economy_score(current)


def _is_vpt_economy_candidate(reference: dict, candidate: dict) -> bool:
    ref_total = _vpt_total_taxa(reference)
    candidate_total = _vpt_total_taxa(candidate)
    ref_prestress = _coerce_value(reference.get("taxa_armadura_protendida")) or float("inf")
    candidate_prestress = _coerce_value(candidate.get("taxa_armadura_protendida")) or float("inf")
    if not all(value < float("inf") for value in (ref_total, candidate_total, ref_prestress, candidate_prestress)):
        return False
    total_gain = candidate_total <= ref_total * (1 - VPT_ECONOMY_TOTAL_REDUCTION)
    prestress_gain = (
        candidate_prestress <= ref_prestress * (1 - VPT_ECONOMY_PRESTRESS_REDUCTION)
        and candidate_total <= ref_total * VPT_ECONOMY_TOTAL_TOLERANCE
    )
    return total_gain or prestress_gain


def _vpt_total_taxa(result: dict) -> float:
    passive = _coerce_value(result.get("taxa_armadura_passiva"))
    prestress = _coerce_value(result.get("taxa_armadura_protendida"))
    if passive is None or prestress is None:
        return float("inf")
    return passive + prestress


def _vpt_economy_score(result: dict) -> tuple:
    spec = VPT_SECTION_CATALOG.get(str(result.get("secao_testada") or result.get("secao") or ""))
    area = spec.hp * spec.bw if spec else float("inf")
    prestress = _coerce_value(result.get("taxa_armadura_protendida")) or float("inf")
    total = _vpt_total_taxa(result)
    passive = _coerce_value(result.get("taxa_armadura_passiva")) or float("inf")
    ratio = _coerce_value(result.get("MRU_MSD")) or 0
    return (prestress, total, passive, area, abs(ratio - MIN_MRU_MSD_RATIO))


def _vpt_sigma_inf_f_ok(result: dict) -> bool:
    return _vpt_sigma_inf_f_within_tolerance(result)


def _vpt_sigma_inf_f_within_tolerance(result: dict) -> bool:
    return _vpt_sigma_distance(result) == 0


def _vpt_sigma_distance(result: dict) -> float:
    sigma_inf = _coerce_value(result.get("sigma_inf_F"))
    lim_inf = _coerce_value(result.get("lim_inf_F"))
    if sigma_inf is None or lim_inf is None:
        return float("inf")
    lower = lim_inf - VPL_SIGMA_INF_TOLERANCE
    upper = lim_inf + VPL_SIGMA_INF_TOLERANCE
    if lower <= sigma_inf <= upper:
        return 0
    return min(abs(sigma_inf - lower), abs(sigma_inf - upper))


def _mark_vpt_sigma_rule_as_accepted(result: dict) -> dict:
    output = result.copy()
    lim_inf = _coerce_value(output.get("lim_inf_F"))
    if lim_inf is not None:
        output["lim_inf_F_min"] = lim_inf - VPL_SIGMA_INF_TOLERANCE
        output["lim_inf_F_max"] = lim_inf + VPL_SIGMA_INF_TOLERANCE
    output["ok_inf_F"] = True
    output["ok"] = True
    output["status"] = "PASSA"
    output["regra_sigma_inf_F"] = f"sigma_inf_F dentro de lim_inf_F +/- {VPL_SIGMA_INF_TOLERANCE}"
    return output


def _vpt_score(result: dict | None) -> tuple:
    if result is None:
        return (1, float("inf"))
    n_cords = sum(_layout_count(result, f"n_cord_c{idx}") for idx in (1, 2, 3))
    n_bars = sum(_layout_count(result, f"n_barras_c{idx}") for idx in (1, 2, 3))
    h = _coerce_value(result.get("h")) or float("inf")
    ratio = _coerce_value(result.get("MRU_MSD")) or 0
    return (
        0 if result.get("status") == "PASSA" else 1,
        h,
        _coerce_value(result.get("taxa_armadura_passiva")) or float("inf"),
        _coerce_value(result.get("taxa_armadura_protendida")) or float("inf"),
        n_cords + n_bars,
        _vpt_sigma_distance(result),
        max(0, MIN_MRU_MSD_RATIO - ratio),
        abs(ratio - MIN_MRU_MSD_RATIO),
    )


def _vr_params(row: dict) -> dict:
    params = {"cob": 2.5, "fck": 30, "n_barras_sup": 2, "diam_barra_sup_mm": 10.0}
    params.update(_take(row, "secao", "vao_viga", "fck", "carga_fechamento_kgf_m", "carga_permanente_kgf_m", "carga_variavel_kgf_m", "n_barras_c1", "n_barras_c2", "n_barras_c3", "diam_barra_c1_mm", "diam_barra_c2_mm", "diam_barra_c3_mm", "n_barras_sup", "diam_barra_sup_mm"))
    if "peca_altura_pre" in row:
        params["h"] = _coerce_value(row["peca_altura_pre"])
    if "peca_largura_pre" in row:
        params["bw"] = _coerce_value(row["peca_largura_pre"])
    if "h_parede" in row:
        h_parede = float(_coerce_value(row["h_parede"]) or 0)
        esp = float(_coerce_value(row.get("esp_parede", 0.15)) or 0.15)
        peso = float(_coerce_value(row.get("peso_parede_kgf_m3", 1200)) or 1200)
        params.setdefault("carga_fechamento_kgf_m", h_parede * esp * peso)
    _convert_lengths(params, "vao_viga")
    _require(params, "vao_viga")
    return params


def _laje_params(row: dict) -> dict:
    params = LAJE_DEFAULTS.copy()
    params["auto_ajuste"] = True
    params.update(_take(row, "vao", "acd", "capa", "fck_capa", "continuidade_kgf", "analise"))
    if "vao" not in params and "vao_viga" in row:
        params["vao"] = _coerce_value(row["vao_viga"])
    if "lp_type" in row:
        params["lp_type"] = _normalize_lp(row["lp_type"])
    elif "nome_tipo" in row:
        params["lp_type"] = _normalize_lp(row["nome_tipo"])
    params["sobrecarga"] = params.pop("acd", params.get("sobrecarga"))
    _convert_lengths(params, "vao")
    _require(params, "lp_type", "vao", "sobrecarga")
    return params


def _take(row: dict, *keys: str) -> dict:
    return {key: _coerce_value(row[key]) for key in keys if key in row}


def _coerce_value(value):
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if re.match(r"^\s*-?\d", stripped):
            number = re.search(r"-?\d+(?:[.,]\d+)?", stripped)
            if number:
                return float(number.group(0).replace(",", "."))
        return stripped
    return value.item() if hasattr(value, "item") else value


def _build_laje_lookup(df: pd.DataFrame) -> dict[str, dict]:
    lookup = {}
    for _, row in df.iterrows():
        data = _clean_row(row.to_dict())
        try:
            if _detect_element_type(data) != ELEMENT_LAJE:
                continue
        except ValueError:
            continue
        element_id = data.get("id_elemento")
        if not element_id:
            continue
        lookup[str(element_id).strip().upper()] = {
            "lp_type": _normalize_lp(data.get("lp_type") or data.get("nome_tipo")),
            "vao": _length_to_m(data.get("vao_viga") or data.get("vao")),
            "acd": _coerce_value(data.get("acd")),
        }
    return lookup


def _resolve_laje_reference(row: dict, element_type: str, lookup: dict[str, dict]) -> dict:
    if element_type in {ELEMENT_LAJE, ELEMENT_VR} or not row.get("laje_marca"):
        return row
    marks = _split_marks(row["laje_marca"])
    if not marks:
        return row
    lajes = []
    for mark in marks:
        key = mark.strip().upper()
        if key not in lookup:
            raise ValueError(f"LAJE_Marca '{mark}' nao encontrada nas linhas de laje.")
        lajes.append(lookup[key])
    result = row.copy()
    first = lajes[0]
    result.setdefault("lp_type", first["lp_type"])
    result.setdefault("vao_laje", first["vao"])
    result.setdefault("acd", first["acd"])
    if element_type == ELEMENT_VPT:
        second = lajes[1] if len(lajes) > 1 else first
        result.setdefault("lp_esq", first["lp_type"])
        result.setdefault("vao_laje_esq", first["vao"])
        result.setdefault("acd_esq", first["acd"])
        result.setdefault("lp_dir", second["lp_type"])
        result.setdefault("vao_laje_dir", second["vao"])
        result.setdefault("acd_dir", second["acd"])
    return result


def _split_marks(value) -> list[str]:
    return [item for item in re.split(r"[,;/+ ]+", str(value).strip()) if item]


def _apply_vpl_geometry_from_revit(params: dict, row: dict):
    height = _coerce_value(row["peca_altura_pre"])
    width = _coerce_value(row["peca_largura_pre"])
    if height:
        params["h"] = float(height)
    if width:
        params["bw"] = float(width)
    lp_type = params.get("lp_type")
    if params.get("h") and lp_type:
        from data.lp_table import LP_TABLE

        hsup = LP_TABLE[lp_type]["cap"] + params.get("capa", 5)
        params["hsup"] = hsup
        params["hinf"] = params["h"] - hsup
        params["bf"] = params.get("bf", 20)


def _infer_vpt_section(row: dict) -> str:
    height = int(round(float(_coerce_value(row["peca_altura_pre"]))))
    width = int(round(float(_coerce_value(row["peca_largura_pre"]))))
    if height >= 50:
        width = max(30, width)
    candidates = [spec for spec in VPT_SECTION_CATALOG.values() if int(spec.hp) == height and int(spec.bw) == width]
    if candidates:
        return min(candidates, key=lambda s: s.h1).secao
    return f"T{height}/25x{width}"


def _length_to_m(value) -> float | None:
    if value is None:
        return None
    numeric = _coerce_value(value)
    if numeric is None:
        return None
    numeric = float(numeric)
    return numeric / 100 if numeric > 100 else numeric


def _convert_lengths(params: dict, *keys: str):
    for key in keys:
        if key in params:
            params[key] = _length_to_m(params[key])


def _normalize_lp(value) -> str:
    text = str(value).upper().replace(" ", "").replace(".", ",")
    text = text.replace("LP26,50", "LP26,5")
    return text


def _require(params: dict, *keys: str):
    missing = [key for key in keys if params.get(key) is None]
    if missing:
        raise ValueError(f"Campos obrigatorios ausentes: {', '.join(missing)}")


def _apply_laje_psi(params: dict, row: dict):
    if "laje_psi" not in row:
        return
    code = str(row["laje_psi"]).strip().upper()
    if not code:
        return
    if code not in PSI_BY_LAJE_CODE:
        raise ValueError("LAJE_psi invalido. Use 0, 1 ou 2.")
    params["laje_psi"] = code
    params.update(PSI_BY_LAJE_CODE[code])


def _copy_psi_fields(result: dict, params: dict) -> dict:
    output = result.copy()
    for key in (
        "laje_psi",
        "psi_tipo",
        "psi0",
        "psi1",
        "psi2",
        "rev",
        "rev_esq",
        "rev_dir",
        "carga_fechamento_kgf_m",
        "carga_permanente_kgf_m",
        "carga_variavel_kgf_m",
    ):
        if key in params:
            output[key] = params[key]
    return output


def _with_section_recommendation(result: dict, original: str, selected: str) -> dict:
    output = result.copy()
    output["secao_original"] = original
    output["secao_sugerida"] = selected if selected and selected != original else ""
    output["mensagem"] = f"aumentar seção para {selected}" if selected and selected != original else ""
    return output


def _with_no_solution_message(result: dict | None, original: str, require_vpl_sigma: bool = False) -> dict:
    output = (result or {"status": "NAO PASSA"}).copy()
    output["status"] = output.get("status") if output.get("status") == "ERRO" else "NAO PASSA"
    output["secao_original"] = original
    output["secao_sugerida"] = ""
    criteria = f"taxa CA <= {MAX_TAXA_CA} e taxa CP <= {MAX_TAXA_CP}"
    if require_vpl_sigma:
        criteria += f", e sigma_inf_D >= lim_inf_F - {VPL_SIGMA_INF_TOLERANCE}"
    output["mensagem"] = f"Nenhuma secao cadastrada passou com {criteria}."
    return output
