"""Engine simplificado para viga retangular de fechamento."""

from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd

from .materials import PASSIVE_BAR_AREA, fctf, fyd


STEEL_WEIGHT_LONGITUDINAL = 0.785
STEEL_WEIGHT_TRANSVERSE = 0.782
PASSIVE_LAYER_YS = {
    "n_barras_c1": 5.0,
    "n_barras_c2": 12.0,
    "n_barras_c3": 18.0,
}
LAYER_LIMITS_BY_BW = {
    12: {"c1": 2, "c2": 2, "c3": 2},
    15: {"c1": 3, "c2": 3, "c3": 3},
    20: {"c1": 4, "c2": 4, "c3": 4},
    25: {"c1": 5, "c2": 5, "c3": 5},
    30: {"c1": 6, "c2": 6, "c3": 6},
    40: {"c1": 8, "c2": 8, "c3": 8},
}
SECTION_CATALOG = (
    (30, 12),
    (40, 15),
    (50, 15),
    (50, 20),
    (60, 20),
    (70, 20),
    (80, 25),
    (90, 25),
)
PASSIVE_DIAM_OPTIONS = (10.0, 12.5, 16.0, 20.0, 25.0)
MAX_TAXA_CA = 200
MIN_MRU_MSD_RATIO = 1.05


@dataclass(frozen=True)
class RectSection:
    h: float
    bw: float
    cob: float = 2.5

    def __post_init__(self):
        if self.h <= 0 or self.bw <= 0:
            raise ValueError("A secao retangular deve ter h e bw maiores que zero.")
        if self.cob < 0 or self.cob >= self.h:
            raise ValueError("Cobrimento invalido para a secao retangular.")

    @property
    def ac(self) -> float:
        return self.bw * self.h

    @property
    def cg(self) -> float:
        return self.h / 2

    @property
    def ix(self) -> float:
        return self.bw * self.h**3 / 12

    @property
    def wi(self) -> float:
        return self.ix / self.cg

    @property
    def ws(self) -> float:
        return self.ix / (self.h - self.cg)

    @property
    def pp_viga(self) -> float:
        return 2.5 * self.ac / 10000


@dataclass(frozen=True)
class VrLoads:
    section: RectSection
    carga_fechamento_kgf_m: float = 0
    carga_permanente_kgf_m: float = 0
    carga_variavel_kgf_m: float = 0

    @property
    def g1(self) -> float:
        return self.section.pp_viga

    @property
    def g2(self) -> float:
        return (self.carga_fechamento_kgf_m + self.carga_permanente_kgf_m) / 1000

    @property
    def q(self) -> float:
        return self.carga_variavel_kgf_m / 1000

    def p_elu(self) -> float:
        return 1.3 * self.g1 + 1.4 * self.g2 + 1.4 * self.q

    def p_els_qp(self, psi2: float = 0.3) -> float:
        return self.g1 + self.g2 + psi2 * self.q

    def msd_elu(self, vao: float) -> float:
        return self.p_elu() * vao**2 / 8

    def vsd(self, vao: float) -> float:
        return self.p_elu() * vao / 2

    def msd_qp(self, vao: float, psi2: float = 0.3) -> float:
        return self.p_els_qp(psi2) * vao**2 / 8


def _status(ok: bool) -> str:
    return "PASSA" if ok else "NAO PASSA"


def _parse_section_label(secao: str) -> tuple[float, float] | None:
    match = re.search(r"R\s*(\d+(?:[.,]\d+)?)\s*[Xx/]\s*(\d+(?:[.,]\d+)?)", str(secao or ""))
    if not match:
        return None
    h = float(match.group(1).replace(",", "."))
    bw = float(match.group(2).replace(",", "."))
    return h, bw


def _resolve_section(params: dict) -> RectSection:
    h = params.get("h")
    bw = params.get("bw")
    if (h is None or bw is None) and params.get("secao"):
        parsed = _parse_section_label(params["secao"])
        if parsed:
            h, bw = parsed
    if h is None or bw is None:
        raise ValueError("Informe h e bw, ou uma secao no formato R60x20.")
    return RectSection(h=float(h), bw=float(bw), cob=float(params.get("cob", 2.5)))


def _layer_limits(bw: float) -> dict:
    numeric = int(round(float(bw)))
    if numeric in LAYER_LIMITS_BY_BW:
        return LAYER_LIMITS_BY_BW[numeric]
    candidates = [key for key in LAYER_LIMITS_BY_BW if key <= numeric]
    if candidates:
        return LAYER_LIMITS_BY_BW[max(candidates)]
    raise ValueError(f"bw {numeric} sem limites cadastrados para camadas de Viga R.")


def _passive_layers(params: dict, section: RectSection) -> tuple[list[dict], float, float, float]:
    limits = _layer_limits(section.bw)
    layers = []
    as_bottom = 0.0
    weighted_y = 0.0
    for idx, key in enumerate(("n_barras_c1", "n_barras_c2", "n_barras_c3"), start=1):
        n_barras = int(params.get(key, 0) or 0)
        if n_barras < 0:
            raise ValueError(f"{key} nao pode ser negativo.")
        if n_barras > limits[f"c{idx}"]:
            raise ValueError(f"CAM. {idx} excede o limite de {limits[f'c{idx}']} barras para bw={section.bw:g}.")
        if idx > 1 and n_barras and int(params.get(f"n_barras_c{idx - 1}", 0) or 0) < limits[f"c{idx - 1}"]:
            raise ValueError(f"CAM. {idx} so pode ser usada quando CAM. {idx - 1} estiver completa.")
        diam = float(params.get(f"diam_barra_c{idx}_mm", params.get("diam_barra_mm", 12.5)))
        if diam not in PASSIVE_BAR_AREA:
            raise ValueError(f"Diametro de barra passiva '{diam}' invalido.")
        y = PASSIVE_LAYER_YS[key]
        if n_barras and y >= section.h:
            raise ValueError(f"CAM. {idx} fora da altura da secao.")
        area = n_barras * PASSIVE_BAR_AREA[diam]
        as_bottom += area
        weighted_y += area * y
        layers.append({"camada": idx, "n_barras": n_barras, "diam_barra_mm": diam, "ys": y, "area": area})

    n_sup = int(params.get("n_barras_sup", 0) or 0)
    diam_sup = float(params.get("diam_barra_sup_mm", 10.0))
    if diam_sup not in PASSIVE_BAR_AREA:
        raise ValueError(f"Diametro de barra superior '{diam_sup}' invalido.")
    as_top = n_sup * PASSIVE_BAR_AREA[diam_sup]
    ys = weighted_y / as_bottom if as_bottom else 0
    return layers, as_bottom, ys, as_top


def _mru(section: RectSection, as_bottom: float, ys: float, fck: float) -> float:
    if as_bottom <= 0 or ys <= 0:
        return 0
    force = as_bottom * fyd() * 10
    y_comp = force / (8.5 * fck / 1.4 * section.bw)
    y_comp = min(y_comp, section.h)
    lever_arm = section.h - ys - y_comp / 2
    return max(0, force * lever_arm / 100 / 1000)


def _vrd2(section: RectSection, ys: float, fck: float) -> float:
    d = section.h - (ys or section.cob)
    if d <= 0:
        return 0
    av2 = 1 - fck / 250
    return 0.27 * av2 * (fck * 10 / 1.4) * section.bw * d / 1000


def _asw_min(section: RectSection, fck: float) -> float:
    from .materials import fctm

    return 0.2 * fctm(fck) / 500 * section.bw * 100


def _taxa_passiva(section: RectSection, as_bottom: float, as_top: float, asw: float) -> float:
    taxa_long = (as_bottom + as_top + section.h / 10) * STEEL_WEIGHT_LONGITUDINAL * 10**4 / section.ac
    comprimento_estribo = 2 * (section.h + section.bw) / 100
    taxa_transv = asw * comprimento_estribo * STEEL_WEIGHT_TRANSVERSE / (section.ac / 10000)
    return taxa_long + taxa_transv


def run_vr_case(params: dict | None = None) -> dict:
    params = {
        "h": 50,
        "bw": 20,
        "cob": 2.5,
        "fck": 30,
        "vao_viga": 5,
        "carga_fechamento_kgf_m": 0,
        "carga_permanente_kgf_m": 0,
        "carga_variavel_kgf_m": 0,
        "psi2": 0.3,
        "n_barras_c1": 2,
        "n_barras_c2": 0,
        "n_barras_c3": 0,
        "diam_barra_c1_mm": 12.5,
        "diam_barra_c2_mm": 12.5,
        "diam_barra_c3_mm": 12.5,
        "n_barras_sup": 2,
        "diam_barra_sup_mm": 10.0,
        **(params or {}),
    }
    try:
        section = _resolve_section(params)
        vao = float(params["vao_viga"])
        if vao <= 0:
            raise ValueError("vao_viga deve ser maior que zero.")
        loads = VrLoads(
            section=section,
            carga_fechamento_kgf_m=float(params.get("carga_fechamento_kgf_m", 0) or 0),
            carga_permanente_kgf_m=float(params.get("carga_permanente_kgf_m", 0) or 0),
            carga_variavel_kgf_m=float(params.get("carga_variavel_kgf_m", 0) or 0),
        )
        layers, as_bottom, ys, as_top = _passive_layers(params, section)
        mru = _mru(section, as_bottom, ys, float(params["fck"]))
        msd = loads.msd_elu(vao)
        vsd = loads.vsd(vao)
        vrd2 = _vrd2(section, ys, float(params["fck"]))
        asw = max(float(params.get("asw", 0) or 0), _asw_min(section, float(params["fck"])))
        taxa = _taxa_passiva(section, as_bottom, as_top, asw)
        msd_qp = loads.msd_qp(vao, float(params.get("psi2", 0.3)))
        sigma_inf_qp = -msd_qp * 1000 * 100 / section.wi
        sigma_sup_qp = msd_qp * 1000 * 100 / section.ws
        lim_inf_qp = -fctf(float(params["fck"])) * 10
        ok_flexao = mru >= msd and (mru / msd if msd else 0) >= MIN_MRU_MSD_RATIO
        ok_cisalhamento = vrd2 >= vsd
        ok_els = sigma_inf_qp >= lim_inf_qp
        ok_taxa = taxa <= MAX_TAXA_CA
        ok = ok_flexao and ok_cisalhamento and ok_els and ok_taxa
        volume_m3 = float(params["volume"]) if params.get("volume") else (section.ac / 10000) * vao
        peso_proprio_kn = 25 * volume_m3
        return {
            "secao": f"R{int(round(section.h))}x{int(round(section.bw))}",
            "h": section.h,
            "bw": section.bw,
            "vao_viga": vao,
            "volume_m3": round(volume_m3, 4),
            "peso_proprio": peso_proprio_kn,
            "carga_fechamento_kgf_m": loads.carga_fechamento_kgf_m if loads.carga_fechamento_kgf_m else None,
            "carga_permanente_kgf_m": loads.carga_permanente_kgf_m if loads.carga_permanente_kgf_m else None,
            "carga_variavel_kgf_m": loads.carga_variavel_kgf_m if loads.carga_variavel_kgf_m else None,
            "fck": float(params["fck"]),
            "ac": section.ac,
            "cg": section.cg,
            "ix": section.ix,
            "n_barras": sum(layer["n_barras"] for layer in layers),
            "n_barras_c1": layers[0]["n_barras"],
            "n_barras_c2": layers[1]["n_barras"],
            "n_barras_c3": layers[2]["n_barras"],
            "n_barras_sup": int(params.get("n_barras_sup", 0) or 0),
            "diam_barra_c1_mm": layers[0]["diam_barra_mm"],
            "diam_barra_c2_mm": layers[1]["diam_barra_mm"],
            "diam_barra_c3_mm": layers[2]["diam_barra_mm"],
            "diam_barra_sup_mm": float(params.get("diam_barra_sup_mm", 10.0)),
            "As_passiva": as_bottom,
            "As_passiva_superior": as_top,
            "ys": ys,
            "Msd": msd,
            "MRU": mru,
            "MRU_MSD": mru / msd if msd else 0,
            "Vsd": vsd,
            "VRd2": vrd2,
            "Asw": asw,
            "taxa_armadura_passiva": taxa,
            "Msd_QP": msd_qp,
            "sigma_inf_qp": sigma_inf_qp,
            "sigma_sup_qp": sigma_sup_qp,
            "lim_inf_qp": lim_inf_qp,
            "ok_flexao": ok_flexao,
            "ok_cisalhamento": ok_cisalhamento,
            "ok_els": ok_els,
            "ok_taxa": ok_taxa,
            "status": _status(ok),
            "ok": ok,
        }
    except Exception as exc:
        return {
            "secao": params.get("secao"),
            "h": params.get("h"),
            "bw": params.get("bw"),
            "vao_viga": params.get("vao_viga"),
            "status": "ERRO",
            "erro_msg": str(exc),
            "ok": False,
        }


def optimize_vr_case(base_params: dict) -> dict:
    original = _section_label(base_params)
    fallback = None
    original_fallback = None
    for section_params in _iter_section_candidates(base_params):
        section_label = _section_label(section_params)
        best = None
        for layout in _iter_passive_layouts(section_params["bw"]):
            result = run_vr_case({**section_params, **layout})
            if fallback is None or _candidate_score(result) < _candidate_score(fallback):
                fallback = result
            if section_label == original and (
                original_fallback is None
                or _candidate_score(result) < _candidate_score(original_fallback)
            ):
                original_fallback = result
            if result.get("ok"):
                if best is None or _candidate_score(result) < _candidate_score(best):
                    best = result
        if best is not None:
            return _with_recommendation(best, original)
    # Uma alternativa reprovada nao e uma recomendacao. Quando nenhuma
    # candidata passa, preserva a geometria importada no resultado/memorial.
    return _with_recommendation(
        original_fallback or fallback or run_vr_case(base_params), original
    )


def _section_label(params: dict) -> str:
    try:
        section = _resolve_section(params)
    except Exception:
        return str(params.get("secao") or "")
    return f"R{int(round(section.h))}x{int(round(section.bw))}"


def _iter_section_candidates(base_params: dict):
    current = _resolve_section(base_params)
    yielded = set()
    candidates = sorted({(current.h, current.bw), *SECTION_CATALOG}, key=lambda item: (item[0] * item[1], item[0], item[1]))
    for h, bw in candidates:
        key = (h, bw)
        if key in yielded:
            continue
        yielded.add(key)
        params = base_params.copy()
        params.update({"h": h, "bw": bw})
        yield params


def _iter_passive_layouts(bw: float):
    limits = _layer_limits(bw)
    for stage in (1, 2, 3):
        for d1 in PASSIVE_DIAM_OPTIONS:
            for n1 in range(2, limits["c1"] + 1):
                base = {
                    "n_barras_c1": n1,
                    "n_barras_c2": 0,
                    "n_barras_c3": 0,
                    "diam_barra_c1_mm": d1,
                    "diam_barra_c2_mm": 12.5,
                    "diam_barra_c3_mm": 12.5,
                }
                if stage == 1:
                    yield base
                    continue
                for d2 in PASSIVE_DIAM_OPTIONS:
                    for n2 in range(1, limits["c2"] + 1):
                        c2 = {**base, "n_barras_c1": limits["c1"], "n_barras_c2": n2, "diam_barra_c2_mm": d2}
                        if stage == 2:
                            yield c2
                            continue
                        for d3 in PASSIVE_DIAM_OPTIONS:
                            for n3 in range(1, limits["c3"] + 1):
                                yield {**c2, "n_barras_c2": limits["c2"], "n_barras_c3": n3, "diam_barra_c3_mm": d3}


def _candidate_score(result: dict) -> tuple:
    if result is None:
        return (1, float("inf"))
    ok_rank = 0 if result.get("ok") else 1
    n_bars = int(result.get("n_barras", 0) or 0)
    taxa = result.get("taxa_armadura_passiva", float("inf")) or float("inf")
    ratio_gap = abs((result.get("MRU_MSD", 0) or 0) - MIN_MRU_MSD_RATIO)
    h = result.get("h", float("inf")) or float("inf")
    return (ok_rank, h, n_bars, taxa, ratio_gap)


def _with_recommendation(result: dict, original: str) -> dict:
    output = result.copy()
    selected = output.get("secao") or ""
    output["secao_original"] = original
    output["secao_sugerida"] = selected if selected and selected != original else ""
    if selected and selected != original:
        original_dims = _parse_section_label(original)
        selected_dims = _parse_section_label(selected)
        smaller = original_dims and selected_dims and selected_dims[0] * selected_dims[1] < original_dims[0] * original_dims[1]
        output["mensagem"] = f"{'reduzir' if smaller else 'aumentar'} seção para {selected}"
    else:
        output["mensagem"] = ""
    return output


def export_vr_df(df: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "secao",
        "vao_viga",
        "carga_fechamento_kgf_m",
        "carga_permanente_kgf_m",
        "carga_variavel_kgf_m",
        "fck",
        "h",
        "bw",
        "n_barras",
        "n_barras_c1",
        "n_barras_c2",
        "n_barras_c3",
        "diam_barra_c1_mm",
        "diam_barra_c2_mm",
        "diam_barra_c3_mm",
        "Msd",
        "MRU",
        "MRU_MSD",
        "Vsd",
        "VRd2",
        "taxa_armadura_passiva",
        "sigma_inf_qp",
        "lim_inf_qp",
        "status",
    ]
    ordered = [column for column in preferred if column in df.columns]
    extra = [column for column in df.columns if column not in ordered]
    return df[ordered + extra].copy()
