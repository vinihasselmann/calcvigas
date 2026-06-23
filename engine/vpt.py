"""Engine de caso unico para viga T protendida."""

from dataclasses import dataclass
from itertools import product
from math import sqrt

import pandas as pd

from .materials import fcti, fctm
from .vpt_model import (
    LP_CAP,
    VPT_SECTION_CATALOG,
    VptCompositeSection,
    VptConcreteSection,
    VptGeometry,
    VptLajeSide,
    VptPassiveLayer,
    VptPrestressLayer,
    equivalent_prestress,
    passive_area_and_ys,
    taxa_passiva_longitudinal,
    taxa_passiva_transversal,
    taxa_passiva_total,
    taxa_protendida,
)


PASSIVE_FYD_KGF_CM2 = 4347
PRESTRESS_INITIAL_STRESS = 15.2
VPT_FPYD = 1900 / 1.15 * 0.9
VPT_FPTD = 1900 / 1.15

DEFAULT_PRESTRESS_LAYERS = (
    VptPrestressLayer(n_cord=6, diam_mm=12.7),
    VptPrestressLayer(n_cord=3, diam_mm=12.7),
    VptPrestressLayer(n_cord=0, diam_mm=15.2),
)
DEFAULT_PASSIVE_BOTTOM_LAYERS = (
    VptPassiveLayer(n_barras=2, diam_mm=25.0, ys=5),
    VptPassiveLayer(n_barras=2, diam_mm=20.0, ys=12),
    VptPassiveLayer(n_barras=0, diam_mm=32.0, ys=18),
)
DEFAULT_PASSIVE_TOP_LAYER = VptPassiveLayer(n_barras=2, diam_mm=10.0, ys=-4.425)
DEFAULT_PRESTRESS_TOP_LAYER = VptPrestressLayer(n_cord=2, diam_mm=9.5)
VPT_TOP_STRAND_YP_FROM_TOP = 3.98
VPT_RESULT_COLUMNS = [
    "secao",
    "vao_viga",
    "lp_esq",
    "lp_dir",
    "vao_laje_esq",
    "vao_laje_dir",
    "acd_esq",
    "acd_dir",
    "capa",
    "fck",
    "fckj",
    "fck_capa",
    "n_cord",
    "n_cord_c1",
    "n_cord_c2",
    "n_cord_c3",
    "diam_cord_c1_mm",
    "diam_cord_c2_mm",
    "diam_cord_c3_mm",
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
    "dominio",
    "Vsd",
    "VRd2",
    "As_passiva",
    "Asw",
    "Asw_calculada",
    "Asw_minima",
    "taxa_armadura_passiva_longitudinal",
    "taxa_armadura_passiva_transversal",
    "taxa_armadura_passiva",
    "taxa_armadura_protendida",
    "ok_flexao",
    "ok_cisalhamento",
    "status",
]
VPT_PARAMETRIC_DEFAULTS = {
    "n_cord_c1": 4,
    "n_cord_c2": 0,
    "n_cord_c3": 0,
    "diam_cord_c1_mm": 12.7,
    "diam_cord_c2_mm": 12.7,
    "diam_cord_c3_mm": 15.2,
    "n_barras_c1": 2,
    "n_barras_c2": 0,
    "n_barras_c3": 0,
    "diam_barra_c1_mm": 25.0,
    "diam_barra_c2_mm": 20.0,
    "diam_barra_c3_mm": 32.0,
}
VPT_LAYER_LIMITS_BY_BW = {
    25: {"c1": 5, "c2": 4, "c3": 5},
    30: {"c1": 6, "c2": 7, "c3": 6},
    40: {"c1": 8, "c2": 9, "c3": 8},
    50: {"c1": 10, "c2": 11, "c3": 10},
}


@dataclass(frozen=True)
class VptLoadResult:
    g1: float
    g2: float
    g3: float
    qm: float
    q: float
    msd: float
    vsd: float


@dataclass(frozen=True)
class VptFlexureResult:
    mru: float
    mru2: float
    mru3: float
    ratio: float
    domain: str
    ok: bool
    x_final: float
    x_d: float
    d: float
    eps_pd: float
    eps_sd: float
    eps_cd: float
    def_ap3: float
    def_cc2: float


def _default_params() -> dict:
    return {
        "caa": "II",
        "secao": None,
        "vao_viga": 9.1,
        "fck": 50,
        "fckj": 35,
        "fck_capa": 40,
        "cob": 3,
        "bw": 40,
        "bf": 52,
        "h1": 25,
        "h2": 10,
        "h3": 15,
        "hc": 0,
        "capa": 5,
        "b_capa": 40,
        "lp_esq": "LP26,5",
        "lp_dir": "LP26,5",
        "rev_esq": 200,
        "rev_dir": 200,
        "acd_esq": 300,
        "acd_dir": 300,
        "vao_laje_esq": 9.6,
        "vao_laje_dir": 6.6,
        "eng_esq": 0,
        "eng_dir": 0,
        "h_parede": 0,
        "fat_pi": 0.95,
        "perda_imediata": 0.05672037947670973,
        "perda_final": 0.21,
    }


def _range_values(start, stop, step, decimals=2):
    if step <= 0 or stop < start:
        return []
    count = int(round((stop - start) / step))
    values = [start + idx * step for idx in range(count + 1)]
    if not values or values[-1] < stop:
        values.append(stop)
    return [round(value, decimals) for value in values]


def build_vpt_ranges(config: dict) -> dict:
    """Converte uma configuracao de UI/API em listas para iteracao VPT."""
    return {
        "vao_viga": _range_values(config["vao_viga_min"], config["vao_viga_max"], config["vao_viga_step"]),
        "vao_laje_esq": _range_values(
            config["vao_laje_esq_min"],
            config["vao_laje_esq_max"],
            config["vao_laje_esq_step"],
        ),
        "vao_laje_dir": _range_values(
            config["vao_laje_dir_min"],
            config["vao_laje_dir_max"],
            config["vao_laje_dir_step"],
        ),
        "acd_esq": _range_values(config["acd_esq_min"], config["acd_esq_max"], config["acd_esq_step"]),
        "acd_dir": _range_values(config["acd_dir_min"], config["acd_dir_max"], config["acd_dir_step"]),
        "secao": config.get("secao_values", list(VPT_SECTION_CATALOG)),
        "lp_esq": config.get("lp_esq_values", ["LP26,5"]),
        "lp_dir": config.get("lp_dir_values", ["LP26,5"]),
        "capa": config.get("capa_values", [5]),
        "fck": config.get("fck_values", [50]),
        "fckj": config.get("fckj_values", [35]),
        "fck_capa": config.get("fck_capa_values", [40]),
        "n_cord_c1": config.get("n_cord_c1_values", [4]),
        "n_cord_c2": config.get("n_cord_c2_values", [0]),
        "n_cord_c3": config.get("n_cord_c3_values", [0]),
        "diam_cord_c1_mm": config.get("diam_cord_c1_values", [12.7]),
        "diam_cord_c2_mm": config.get("diam_cord_c2_values", [12.7]),
        "diam_cord_c3_mm": config.get("diam_cord_c3_values", [15.2]),
        "n_barras_c1": config.get("n_barras_c1_values", [2]),
        "n_barras_c2": config.get("n_barras_c2_values", [0]),
        "n_barras_c3": config.get("n_barras_c3_values", [0]),
        "diam_barra_c1_mm": config.get("diam_barra_c1_values", [25.0]),
        "diam_barra_c2_mm": config.get("diam_barra_c2_values", [20.0]),
        "diam_barra_c3_mm": config.get("diam_barra_c3_values", [32.0]),
    }


def _build_layers(params: dict):
    prestress_layers = params.get("prestress_layers", DEFAULT_PRESTRESS_LAYERS)
    passive_bottom_layers = params.get("passive_bottom_layers", DEFAULT_PASSIVE_BOTTOM_LAYERS)
    passive_top_layer = params.get("passive_top_layer", DEFAULT_PASSIVE_TOP_LAYER)
    return prestress_layers, passive_bottom_layers, passive_top_layer


def _layers_from_parametric_counts(params: dict):
    prestress_layers = (
        VptPrestressLayer(
            n_cord=int(params.get("n_cord_c1", 0) or 0),
            diam_mm=float(params.get("diam_cord_c1_mm", 12.7)),
        ),
        VptPrestressLayer(
            n_cord=int(params.get("n_cord_c2", 0) or 0),
            diam_mm=float(params.get("diam_cord_c2_mm", 12.7)),
        ),
        VptPrestressLayer(
            n_cord=int(params.get("n_cord_c3", 0) or 0),
            diam_mm=float(params.get("diam_cord_c3_mm", 15.2)),
        ),
    )
    passive_bottom_layers = (
        VptPassiveLayer(
            n_barras=int(params.get("n_barras_c1", 0) or 0),
            diam_mm=float(params.get("diam_barra_c1_mm", 25.0)),
            ys=float(params.get("ys_barra_c1", 5)),
        ),
        VptPassiveLayer(
            n_barras=int(params.get("n_barras_c2", 0) or 0),
            diam_mm=float(params.get("diam_barra_c2_mm", 20.0)),
            ys=float(params.get("ys_barra_c2", 12)),
        ),
        VptPassiveLayer(
            n_barras=int(params.get("n_barras_c3", 0) or 0),
            diam_mm=float(params.get("diam_barra_c3_mm", 32.0)),
            ys=float(params.get("ys_barra_c3", 18)),
        ),
    )
    return prestress_layers, passive_bottom_layers


def _merge_parametric_layers(params: dict) -> dict:
    layer_keys = {
        "n_cord_c1",
        "n_cord_c2",
        "n_cord_c3",
        "n_barras_c1",
        "n_barras_c2",
        "n_barras_c3",
        "diam_cord_c1_mm",
        "diam_cord_c2_mm",
        "diam_cord_c3_mm",
        "diam_barra_c1_mm",
        "diam_barra_c2_mm",
        "diam_barra_c3_mm",
    }
    if not any(key in params for key in layer_keys):
        return params

    result = params.copy()
    prestress_layers, passive_bottom_layers = _layers_from_parametric_counts(result)
    result.setdefault("prestress_layers", prestress_layers)
    result.setdefault("passive_bottom_layers", passive_bottom_layers)
    return result


def _apply_default_shared_layer_counts(params: dict) -> dict:
    layer_keys = {
        "n_cord_c1",
        "n_cord_c2",
        "n_cord_c3",
        "n_barras_c1",
        "n_barras_c2",
        "n_barras_c3",
    }
    if any(key in params for key in layer_keys):
        return params

    result = params.copy()
    limits = _layer_limits(result)
    n_barras_c2_default = 2
    result.update(
        {
            "n_cord_c1": max(limits["c1"] - 2, 0),
            "n_cord_c2": max(0, min(3, limits["c2"] - n_barras_c2_default)),
            "n_cord_c3": 0,
            "n_barras_c1": 2,
            "n_barras_c2": n_barras_c2_default,
            "n_barras_c3": 0,
            "diam_cord_c1_mm": 12.7,
            "diam_cord_c2_mm": 12.7,
            "diam_cord_c3_mm": 15.2,
            "diam_barra_c1_mm": 25.0,
            "diam_barra_c2_mm": 20.0,
            "diam_barra_c3_mm": 32.0,
        }
    )
    return result


def _section_bw(params: dict) -> float:
    section = VPT_SECTION_CATALOG.get(params.get("secao"))
    return section.bw if section else params.get("bw", 40)


def _layer_limits(params: dict) -> dict:
    bw = int(_section_bw(params))
    if bw not in VPT_LAYER_LIMITS_BY_BW:
        raise ValueError(f"bw {bw} sem limites cadastrados para camadas VPT.")
    return VPT_LAYER_LIMITS_BY_BW[bw]


def _validate_layer_dependencies(params: dict):
    n_cord_c1 = int(params.get("n_cord_c1", VPT_PARAMETRIC_DEFAULTS["n_cord_c1"]) or 0)
    n_cord_c2 = int(params.get("n_cord_c2", VPT_PARAMETRIC_DEFAULTS["n_cord_c2"]) or 0)
    n_cord_c3 = int(params.get("n_cord_c3", VPT_PARAMETRIC_DEFAULTS["n_cord_c3"]) or 0)
    n_barras_c1 = int(params.get("n_barras_c1", VPT_PARAMETRIC_DEFAULTS["n_barras_c1"]) or 0)
    n_barras_c2 = int(params.get("n_barras_c2", VPT_PARAMETRIC_DEFAULTS["n_barras_c2"]) or 0)
    n_barras_c3 = int(params.get("n_barras_c3", VPT_PARAMETRIC_DEFAULTS["n_barras_c3"]) or 0)
    limits = _layer_limits(params)
    bw = int(_section_bw(params))

    if n_barras_c1 < 2:
        raise ValueError("CAM. 1 exige no minimo 2 barras passivas, independente da bitola.")
    for layer, n_cord, n_barras in (
        ("1", n_cord_c1, n_barras_c1),
        ("2", n_cord_c2, n_barras_c2),
        ("3", n_cord_c3, n_barras_c3),
    ):
        if n_cord == 1:
            raise ValueError(f"CAM. {layer} nao permite apenas 1 cordoalha.")
        if n_barras == 1:
            raise ValueError(f"CAM. {layer} nao permite apenas 1 barra passiva.")
    if n_cord_c2 > 0 and n_cord_c1 == 0:
        raise ValueError("CAM. 2 com cordoalhas exige cordoalhas na CAM. 1.")
    max_c1_cords_with_min_passive = max(0, limits["c1"] - 2)
    if n_cord_c2 > 0 and n_cord_c1 < max_c1_cords_with_min_passive:
        raise ValueError(
            "CAM. 2 com cordoalhas exige priorizar cordoalhas na CAM. 1, "
            f"mantendo 2 barras passivas minimas."
        )
    if n_cord_c3 > 0 and n_cord_c2 == 0:
        raise ValueError("CAM. 3 com cordoalhas exige cordoalhas na CAM. 2.")

    layer_counts = {
        "c1": n_cord_c1 + n_barras_c1,
        "c2": n_cord_c2 + n_barras_c2,
        "c3": n_cord_c3 + n_barras_c3,
    }
    for layer, total in layer_counts.items():
        if total > limits[layer]:
            raise ValueError(
                f"CAM. {layer[-1]} excede o maximo de {limits[layer]} posicoes para bw={bw} "
                f"considerando barras + cordoalhas."
            )

    if layer_counts["c2"] > 0 and layer_counts["c1"] < limits["c1"]:
        raise ValueError(
            f"CAM. 2 so pode ser usada quando CAM. 1 estiver completa "
            f"com {limits['c1']} barras + cordoalhas para bw={bw}."
        )
    if layer_counts["c3"] > 0 and layer_counts["c2"] < limits["c2"]:
        raise ValueError(
            f"CAM. 3 so pode ser usada quando CAM. 2 estiver completa "
            f"com {limits['c2']} barras + cordoalhas para bw={bw}."
        )


def _has_valid_reinforcement_layout(params: dict) -> bool:
    total_cords = sum(int(params.get(key, 0) or 0) for key in ("n_cord_c1", "n_cord_c2", "n_cord_c3"))
    total_bars = sum(int(params.get(key, 0) or 0) for key in ("n_barras_c1", "n_barras_c2", "n_barras_c3"))
    if total_cords <= 0 and total_bars <= 0:
        return False
    try:
        _validate_layer_dependencies(params)
    except ValueError:
        return False
    return True


def _build_sections(params: dict):
    left = VptLajeSide(
        lp_type=params["lp_esq"],
        rev=params["rev_esq"],
        acd=params["acd_esq"],
        vao=params["vao_laje_esq"],
    )
    right = VptLajeSide(
        lp_type=params["lp_dir"],
        rev=params["rev_dir"],
        acd=params["acd_dir"],
        vao=params["vao_laje_dir"],
    )
    section = VPT_SECTION_CATALOG.get(params.get("secao"))
    bw = section.bw if section else params["bw"]
    h1 = section.h1 if section else params["h1"]
    h2 = section.h2 if section else params["h2"]
    h3 = section.h3 if section else params["h3"]
    bf = params.get("bf")
    if section:
        bf = bw + 40 - left.be - right.be
    geom = VptGeometry(
        bw=bw,
        bf=bf,
        h1=h1,
        h2=h2,
        h3=h3,
        hc=params["hc"],
        capa=params["capa"],
        b_capa=params["b_capa"],
    ).derived(left.cap, right.cap)
    _, passive_bottom_layers, passive_top_layer = _build_layers(params)
    as_bottom, ys = passive_area_and_ys(passive_bottom_layers)
    n_cord_top = int(params.get("n_cord_top", DEFAULT_PRESTRESS_TOP_LAYER.n_cord))
    diam_cord_top_mm = float(params.get("diam_cord_top_mm", DEFAULT_PRESTRESS_TOP_LAYER.diam_mm))
    asp_top = VptPrestressLayer(n_cord=n_cord_top, diam_mm=diam_cord_top_mm).area()
    as_top_passive = passive_top_layer.area()
    as_top_total = as_top_passive + asp_top
    if as_top_total > 0:
        ys_top = (as_top_passive * passive_top_layer.ys + asp_top * (-VPT_TOP_STRAND_YP_FROM_TOP)) / as_top_total
    else:
        ys_top = passive_top_layer.ys
    concrete = VptConcreteSection(
        geom,
        as_inferior=as_bottom,
        ys=ys,
        as_superior=as_top_total,
        ys_superior=ys_top,
        fat_i=params.get("fat_i", 5.303300858899107),
    )
    composite = VptCompositeSection(concrete, fck=params["fck"], fck_capa=params["fck_capa"])
    return left, right, geom, concrete, composite


def _loads(params: dict, concrete: VptConcreteSection, geom) -> VptLoadResult:
    left = VptLajeSide(params["lp_esq"], params["rev_esq"], params["acd_esq"], params["vao_laje_esq"])
    right = VptLajeSide(params["lp_dir"], params["rev_dir"], params["acd_dir"], params["vao_laje_dir"])
    vao = params["vao_viga"]
    bf_m = geom.bf / 100
    h_parede = params.get("h_parede", 0)
    parede = 1200 * 0.2 * h_parede / 1000

    g1 = (left.pp * left.vao + right.pp * right.vao) / 2000 + concrete.pp_viga
    g2 = (
        (left.capa_load(params["capa"]) * left.vao + right.capa_load(params["capa"]) * right.vao)
        / 2000
        + (geom.bf * (params["capa"] + geom.hs) - concrete.area_parts["a0"]) * 2.5 / 10000
    )
    g3 = (
        params["rev_esq"] * 0.5 * (params["vao_laje_esq"] + bf_m)
        + params["rev_dir"] * 0.5 * (params["vao_laje_dir"] + bf_m)
    ) / 1000 + parede
    qm = params.get("qm", 0)
    q = (
        params["acd_esq"] * params["vao_laje_esq"]
        + params["acd_dir"] * params["vao_laje_dir"]
    ) / 2000 + bf_m * (params["acd_esq"] + params["acd_dir"]) / 2000

    eng_esq = params.get("eng_esq", 0)
    eng_dir = params.get("eng_dir", 0)
    m_esq = 0 if eng_esq == 0 else eng_esq * 1.4 * (g3 + q) * vao**2 / (8 if eng_dir == 0 else 12)
    m_dir = 0 if eng_dir == 0 else eng_dir * 1.4 * (g3 + q) * vao**2 / (8 if eng_esq == 0 else 12)
    total_load = 1.3 * g1 + 1.4 * g2 + 1.4 * g3 + 1.4 * q
    msd = total_load * vao**2 / 8 if not m_esq and not m_dir else total_load * vao**2 / 8 - max(m_esq, m_dir)
    vsd = total_load * vao / 2
    return VptLoadResult(g1=g1, g2=g2, g3=g3, qm=qm, q=q, msd=msd, vsd=vsd)


def _vrd2(params: dict, geom, composite: VptCompositeSection, yp: float) -> float:
    fck = params["fck"]
    av2 = 1 - fck / 250
    return 0.27 * av2 * (
        (fck * 10 / 1.3) * (geom.bw * geom.h_v - geom.bw * yp) / 1000
        + (params["fck_capa"] * 10 / 1.4) * (composite.bf_eq * geom.hs) / 1000
    )


def _asw_min(params: dict, geom) -> float:
    return 0.2 * fctm(params["fck"]) / 500 * geom.bw * 100


def _asw_required(params: dict, geom, concrete, composite, loads, yp: float) -> float:
    """Calcula Asw solicitada conforme o bloco de cisalhamento da planilha VPT."""
    fcti_kgf_cm2 = fcti(params["fck"]) * 10
    vc0 = 0.6 * (
        (fcti_kgf_cm2 / 1.3) * (concrete.ac - geom.bw * yp)
        + (fcti_kgf_cm2 / 1.4) * ((geom.hs + geom.capa) * composite.bf_eq)
    ) / 1000
    vsw = max(0.0, loads.vsd - vc0)
    effective_depth = geom.h - yp
    if effective_depth <= 0:
        raise ValueError("Altura util invalida para calcular Asw: h - yp deve ser maior que zero.")
    return vsw * 100 / (0.9 * effective_depth * 5 / 1.15) if vsw > 0 else 0.0


def _compressed_depth_from_area(acc: float, geom, concrete: VptConcreteSection, composite: VptCompositeSection) -> float:
    a_capa = composite._a_capa
    a_sup = composite._a_sup
    a1 = concrete.area_parts["a1"]
    a2 = concrete.area_parts["a2"]
    a3 = concrete.area_parts["a3"]
    fat_a = (geom.bs - geom.bw) / geom.h2

    if acc <= a_capa:
        return acc / composite.b_capa_eq
    if acc <= a_capa + a_sup:
        return geom.capa + (acc - a_capa) / composite.bf_eq
    if acc <= a_capa + a_sup + a1:
        return geom.capa + geom.hs + (acc - a_capa - a_sup) / geom.bs1
    if acc <= a_capa + a_sup + a1 + a2:
        return geom.capa + geom.hs + geom.h4 + (acc - a_capa - a_sup - a1) / geom.bs
    if acc <= a_capa + a_sup + a1 + a2 + a3:
        partial = acc - a_capa - a_sup - a1 - a2
        return geom.capa + geom.hs + geom.h4 + geom.h3 + (-geom.bs + sqrt(geom.bs**2 - 2 * fat_a * partial)) / -fat_a
    return geom.capa + geom.hs + geom.h4 + geom.h3 + geom.h2 + (acc - a_capa - a_sup - a1 - a2 - a3) / geom.bw


def _mru_from_compression_area(
    acc: float,
    y: float,
    ys_eq: float,
    params: dict,
    geom,
    concrete: VptConcreteSection,
    composite: VptCompositeSection,
    fixed_mr_ys: float | None = None,
) -> float:
    stress_cap = 8.5 * params["fck"] / 1.4
    stress_web = 8.5 * params["fck"] / 1.3
    a_capa = composite._a_capa
    a_sup = composite._a_sup
    a1 = concrete.area_parts["a1"]
    a2 = concrete.area_parts["a2"]
    a3 = concrete.area_parts["a3"]
    cg_capa = geom.h - geom.capa / 2
    cg_sup = geom.h - geom.capa - geom.hs / 2
    cg = concrete.centroids
    mr_ys = ys_eq if fixed_mr_ys is None else fixed_mr_ys

    mr1 = a_capa * stress_cap * (cg_capa - mr_ys)
    mr2 = a_sup * stress_cap * (cg_sup - mr_ys)
    mr3 = a1 * stress_web * (cg["cg1"] - mr_ys)
    mr4 = a2 * stress_web * (cg["cg2"] - mr_ys)
    mr5 = a3 * stress_web * (cg["cg3"] - mr_ys)

    if y <= geom.capa:
        return acc * stress_cap * (geom.h - ys_eq - y / 2)
    if y <= geom.capa + geom.hs:
        return mr1 + (acc - a_capa) * stress_cap * (geom.h - ys_eq - geom.capa - (y - geom.capa) / 2)
    if y <= geom.capa + geom.hs + geom.h4:
        return mr1 + mr2 + (acc - a_capa - a_sup) * stress_web * (
            geom.h_v - ys_eq - (y - geom.capa - geom.hs) / 2
        )
    if y <= geom.capa + geom.hs + geom.h4 + geom.h3:
        return mr1 + mr2 + mr3 + (acc - a_capa - a_sup - a1) * stress_web * (
            geom.h_v - ys_eq - geom.h4 - (y - geom.capa - geom.hs - geom.h4) / 2
        )
    if y <= geom.capa + geom.hs + geom.h4 + geom.h3 + geom.h2:
        return mr1 + mr2 + mr3 + mr4 + (acc - a_capa - a_sup - a1 - a2) * stress_web * (
            geom.h_v - ys_eq - geom.h4 - geom.h3 - (y - geom.capa - geom.hs - geom.h4 - geom.h3) / 2
        )
    return mr1 + mr2 + mr3 + mr4 + mr5 + (acc - a_capa - a_sup - a1 - a2 - a3) * stress_web * (
        geom.h1 - ys_eq - (y - geom.capa - geom.hs - geom.h4 - geom.h3 - geom.h2) / 2
    )


def _flexure(
    params: dict,
    geom,
    concrete: VptConcreteSection,
    composite: VptCompositeSection,
    loads: VptLoadResult,
    yp: float,
    asp: float,
    as_bottom: float,
    ys: float,
) -> VptFlexureResult:
    rt_ap3 = asp * VPT_FPYD * 10
    rt_as = as_bottom * PASSIVE_FYD_KGF_CM2
    ys3 = (rt_ap3 * yp + rt_as * ys) / (rt_ap3 + rt_as)
    acc3 = (rt_ap3 + rt_as) / (8.5 * params["fck"] / 1.4)
    y3 = _compressed_depth_from_area(acc3, geom, concrete, composite)
    x3 = y3 / 0.8
    def_ap3 = 3.5 * (geom.h - x3 - ys3) / x3
    mru3 = _mru_from_compression_area(acc3, y3, ys3, params, geom, concrete, composite) / 100 / 1000

    fpi = asp * PRESTRESS_INITIAL_STRESS * params["fat_pi"]
    eps_pdi = 0.9 * fpi * (1 - params["perda_imediata"]) / (asp * 2) if asp else 0
    eps_pd2 = eps_pdi + 10
    spd2 = VPT_FPYD + (VPT_FPTD - VPT_FPYD) * eps_pdi / 25
    rt_ap2 = spd2 * asp * 10
    ys2 = (rt_ap2 * yp + rt_as * ys) / (rt_ap2 + rt_as)
    acc2 = (rt_ap2 + rt_as) / (8.5 * params["fck"] / 1.3)
    y2 = _compressed_depth_from_area(acc2, geom, concrete, composite)
    x2 = y2 / 0.8
    def_cc2 = 10 * x2 / (geom.h - ys2 - x2)
    mru2 = _mru_from_compression_area(acc2, y2, ys2, params, geom, concrete, composite, fixed_mr_ys=ys3) / 100 / 1000

    if def_ap3 <= 10:
        mru = mru3
        domain = "III"
        x_final = x3
        eps_pd = def_ap3 + eps_pdi
        eps_sd = def_ap3
        eps_cd = 3.5
    elif def_cc2 <= 3.5:
        mru = mru2
        domain = "II"
        x_final = x2
        eps_pd = eps_pd2
        eps_sd = 10
        eps_cd = def_cc2
    else:
        mru = mru3
        domain = "IV"
        x_final = x3
        eps_pd = float("nan")
        eps_sd = float("nan")
        eps_cd = float("nan")

    d = geom.h - ys3
    ratio = mru / loads.msd if loads.msd else 0
    return VptFlexureResult(
        mru=mru,
        mru2=mru2,
        mru3=mru3,
        ratio=ratio,
        domain=domain,
        ok=mru >= loads.msd,
        x_final=x_final,
        x_d=x_final / d if d else 0,
        d=d,
        eps_pd=eps_pd,
        eps_sd=eps_sd,
        eps_cd=eps_cd,
        def_ap3=def_ap3,
        def_cc2=def_cc2,
    )


def _service_stresses(params: dict, geom, concrete: VptConcreteSection, composite: VptCompositeSection, loads, yp, asp):
    """Calcula tensoes inferiores em etapas conforme a planilha VPT."""
    vao = params["vao_viga"]
    psi1 = params.get("psi1", 0.6)
    psi2 = params.get("psi2", 0.4)
    loss_factor = 1 - params.get("perda_final", 0.21)

    n_cord_top = int(params.get("n_cord_top", DEFAULT_PRESTRESS_TOP_LAYER.n_cord))
    diam_cord_top_mm = float(params.get("diam_cord_top_mm", DEFAULT_PRESTRESS_TOP_LAYER.diam_mm))
    asp_top = VptPrestressLayer(n_cord=n_cord_top, diam_mm=diam_cord_top_mm).area()
    yp_top = -(params["cob"] + 1 + diam_cord_top_mm / 20)

    p_inf = asp * PRESTRESS_INITIAL_STRESS * params.get("fat_pi", 0.95) * loss_factor * 1000
    p_sup = asp_top * PRESTRESS_INITIAL_STRESS * params.get("fat_ps", params.get("fat_pi", 0.95)) * loss_factor * 1000
    mpf = p_inf * (concrete.cg - yp) - p_sup * (geom.h_v - concrete.cg + yp_top)
    sigma_inf_p = (p_inf + p_sup) / concrete.ac + mpf / concrete.wi

    m_pre_composite = (loads.g1 + loads.g2 + loads.qm) * vao**2 / 8 * 1000 * 100
    sigma_inf_g1 = -m_pre_composite / concrete.wi

    moments = {
        "qp": (loads.g1 + loads.g2 + loads.g3 + psi2 * loads.q) * vao**2 / 8 * 1000 * 100,
        "freq": (loads.g1 + loads.g2 + loads.g3 + psi1 * loads.q) * vao**2 / 8 * 1000 * 100,
        "rare": (loads.g1 + loads.g2 + loads.g3 + loads.q) * vao**2 / 8 * 1000 * 100,
    }
    sigma_after = {key: -(moment - m_pre_composite) / composite.wi_f for key, moment in moments.items()}

    # Tensoes na fibra superior (informativo, nao verificado pelo criterio de ELS desta norma)
    sigma_sup_p = (p_inf + p_sup) / concrete.ac - mpf / concrete.ws
    sigma_sup_g1 = m_pre_composite / concrete.ws
    sigma_sup_after = {key: (moment - m_pre_composite) / composite.ws_f for key, moment in moments.items()}

    caa = str(params.get("caa", "II")).upper()
    selected_key = "qp" if caa in {"I", "II"} else "freq"
    sigma_inf = sigma_inf_p + sigma_inf_g1 + sigma_after[selected_key]

    return {
        "Msd_QP": moments["qp"] / 1000 / 100,
        "Msd_CF": moments["freq"] / 1000 / 100,
        "Msd_CR": moments["rare"] / 1000 / 100,
        "sigma_inf_p": sigma_inf_p,
        "sigma_inf_g1": sigma_inf_g1,
        "sigma_inf_qp": sigma_inf_p + sigma_inf_g1 + sigma_after["qp"],
        "sigma_inf_freq": sigma_inf_p + sigma_inf_g1 + sigma_after["freq"],
        "sigma_inf_rare": sigma_inf_p + sigma_inf_g1 + sigma_after["rare"],
        "sigma_inf_F": sigma_inf,
        "lim_inf_F": -fcti(params["fck"]) * 1.5 * 10,
        "service_key": selected_key,
        "sigma_sup_qp": sigma_sup_p + sigma_sup_g1 + sigma_sup_after["qp"],
        "sigma_sup_freq": sigma_sup_p + sigma_sup_g1 + sigma_sup_after["freq"],
    }


def run_vpt_case(params: dict | None = None) -> dict:
    """Executa um caso unico de viga T protendida.

    Calcula geometria, cargas ELU, flexao, cisalhamento e taxas.
    """
    merged = _default_params()
    if params:
        merged.update(params)
    merged = _apply_default_shared_layer_counts(merged)
    merged = _merge_parametric_layers(merged)

    try:
        _validate_layer_dependencies(merged)
        _, _, geom, concrete, composite = _build_sections(merged)
        prestress_layers, passive_bottom_layers, passive_top_layer = _build_layers(merged)
        n_cord, yp, asp = equivalent_prestress(prestress_layers, cob=merged["cob"])
        as_bottom, ys = passive_area_and_ys(passive_bottom_layers)
        if n_cord <= 0 and as_bottom <= 0:
            raise ValueError("Informe ao menos uma cordoalha ou armadura passiva inferior.")
        as_top = passive_top_layer.area()
        n_cord_top = int(merged.get("n_cord_top", DEFAULT_PRESTRESS_TOP_LAYER.n_cord))
        diam_cord_top_mm = float(merged.get("diam_cord_top_mm", DEFAULT_PRESTRESS_TOP_LAYER.diam_mm))
        asp_top = VptPrestressLayer(n_cord=n_cord_top, diam_mm=diam_cord_top_mm).area()
        loads = _loads(merged, concrete, geom)
        flexure = _flexure(merged, geom, concrete, composite, loads, yp, asp, as_bottom, ys)
        vrd2 = _vrd2(merged, geom, composite, yp)
        asw_calculada = _asw_required(merged, geom, concrete, composite, loads, yp)
        asw_minima = _asw_min(merged, geom)
        asw = max(float(merged.get("asw", 0) or 0), asw_calculada, asw_minima)
        taxa_longitudinal = taxa_passiva_longitudinal(
            as_bottom, as_top, geom.h, concrete.ac
        )
        taxa_transversal = taxa_passiva_transversal(asw, geom, concrete.ac)
        taxa_passiva = taxa_passiva_total(as_bottom, as_top, asw, geom, concrete.ac)
        taxa_cp = taxa_protendida(asp, concrete.ac, superior_area=asp_top)
        ok_cisalhamento = vrd2 >= loads.vsd

        service = _service_stresses(merged, geom, concrete, composite, loads, yp, asp)
        ok_inf_F = service["sigma_inf_F"] >= service["lim_inf_F"]

        ok = ok_cisalhamento and flexure.ok and ok_inf_F

        _vao_vpt = merged["vao_viga"]
        volume_m3 = float(merged["volume"]) if merged.get("volume") else (concrete.ac / 10000) * _vao_vpt
        return {
            "secao": merged.get("secao") or f"T{geom.h:.0f}/{geom.bw:.0f}x{geom.bf:.0f}",
            "vao_viga": _vao_vpt,
            "lp_esq": merged["lp_esq"],
            "lp_dir": merged["lp_dir"],
            "vao_laje_esq": merged["vao_laje_esq"],
            "vao_laje_dir": merged["vao_laje_dir"],
            "acd_esq": merged["acd_esq"],
            "acd_dir": merged["acd_dir"],
            "capa": merged["capa"],
            "fck": merged["fck"],
            "fckj": merged["fckj"],
            "fck_capa": merged["fck_capa"],
            "volume_m3": round(volume_m3, 4),
            "peso_proprio": 25 * volume_m3,
            "h": geom.h,
            "hp": geom.hp,
            "hs": geom.hs,
            "ac": concrete.ac,
            "cg": concrete.cg,
            "ix": concrete.ix,
            "ac_f": composite.ac_f,
            "cg_f": composite.cg_f,
            "ix_f": composite.ix_f,
            "n_cord": n_cord,
            "n_cord_c1": prestress_layers[0].n_cord,
            "n_cord_c2": prestress_layers[1].n_cord,
            "n_cord_c3": prestress_layers[2].n_cord,
            "diam_cord_c1_mm": prestress_layers[0].diam_mm,
            "diam_cord_c2_mm": prestress_layers[1].diam_mm,
            "diam_cord_c3_mm": prestress_layers[2].diam_mm,
            "yp": yp,
            "asp": asp,
            "n_barras": sum(layer.n_barras for layer in passive_bottom_layers),
            "n_barras_c1": passive_bottom_layers[0].n_barras,
            "n_barras_c2": passive_bottom_layers[1].n_barras,
            "n_barras_c3": passive_bottom_layers[2].n_barras,
            "diam_barra_c1_mm": passive_bottom_layers[0].diam_mm,
            "diam_barra_c2_mm": passive_bottom_layers[1].diam_mm,
            "diam_barra_c3_mm": passive_bottom_layers[2].diam_mm,
            "As_passiva": as_bottom,
            "ys": ys,
            "Msd": loads.msd,
            "MRU": flexure.mru,
            "MRU2": flexure.mru2,
            "MRU3": flexure.mru3,
            "MRU_MSD": flexure.ratio,
            "dominio": flexure.domain,
            "x_final": flexure.x_final,
            "x_d": flexure.x_d,
            "d": flexure.d,
            "eps_pd": flexure.eps_pd,
            "eps_sd": flexure.eps_sd,
            "eps_cd": flexure.eps_cd,
            "def_ap3": flexure.def_ap3,
            "def_cc2": flexure.def_cc2,
            "Vsd": loads.vsd,
            "VRd2": vrd2,
            "Asw": asw,
            "Asw_calculada": asw_calculada,
            "Asw_minima": asw_minima,
            "taxa_armadura_passiva_longitudinal": taxa_longitudinal,
            "taxa_armadura_passiva_transversal": taxa_transversal,
            "taxa_armadura_passiva": taxa_passiva,
            "taxa_armadura_protendida": taxa_cp,
            "ok_cisalhamento": ok_cisalhamento,
            "ok_flexao": flexure.ok,
            "Msd_QP": service["Msd_QP"],
            "Msd_CF": service["Msd_CF"],
            "Msd_CR": service["Msd_CR"],
            "sigma_inf_F": service["sigma_inf_F"],
            "sigma_inf_p": service["sigma_inf_p"],
            "sigma_inf_g1": service["sigma_inf_g1"],
            "sigma_inf_qp": service["sigma_inf_qp"],
            "sigma_inf_freq": service["sigma_inf_freq"],
            "sigma_inf_rare": service["sigma_inf_rare"],
            "sigma_sup_qp": service["sigma_sup_qp"],
            "sigma_sup_freq": service["sigma_sup_freq"],
            "lim_inf_F": service["lim_inf_F"],
            "ok_inf_F": ok_inf_F,
            "status": "PASSA" if ok else "NAO PASSA",
        }
    except Exception as exc:
        return {
            "status": "ERRO",
            "erro_msg": str(exc),
        }


def _iter_vpt_combinations(fixed_params: dict, ranges: dict):
    defaults = {**_default_params(), **VPT_PARAMETRIC_DEFAULTS}
    base_keys = (
        "secao",
        "vao_viga",
        "lp_esq",
        "lp_dir",
        "vao_laje_esq",
        "vao_laje_dir",
        "acd_esq",
        "acd_dir",
        "capa",
        "fck",
        "fckj",
        "fck_capa",
    )
    base_values = tuple(ranges.get(key, [fixed_params.get(key, defaults.get(key))]) for key in base_keys)

    prestress_keys = (
        "n_cord_c1",
        "n_cord_c2",
        "n_cord_c3",
        "diam_cord_c1_mm",
        "diam_cord_c2_mm",
        "diam_cord_c3_mm",
    )
    passive_keys = (
        "n_barras_c1",
        "n_barras_c2",
        "n_barras_c3",
        "diam_barra_c1_mm",
        "diam_barra_c2_mm",
        "diam_barra_c3_mm",
    )
    prestress_values = tuple(ranges.get(key, [fixed_params.get(key, defaults.get(key))]) for key in prestress_keys)
    passive_values = tuple(ranges.get(key, [fixed_params.get(key, defaults.get(key))]) for key in passive_keys)

    for base_combo, prestress_combo, passive_combo in product(
        product(*base_values),
        product(*prestress_values),
        product(*passive_values),
    ):
        params = fixed_params.copy()
        params.update(dict(zip(base_keys, base_combo)))
        params.update(dict(zip(prestress_keys, prestress_combo)))
        params.update(dict(zip(passive_keys, passive_combo)))

        if not _has_valid_reinforcement_layout(params):
            continue

        prestress_layers, passive_bottom_layers = _layers_from_parametric_counts(params)
        params["prestress_layers"] = prestress_layers
        params["passive_bottom_layers"] = passive_bottom_layers
        yield params


def _values_for_keys(fixed_params: dict, ranges: dict, keys: tuple[str, ...], defaults: dict) -> tuple:
    return tuple(ranges.get(key, [fixed_params.get(key, defaults.get(key))]) for key in keys)


def _count_nonzero_reinforcement(fixed_params: dict, ranges: dict, defaults: dict, base_params: dict) -> int:
    prestress_keys = ("n_cord_c1", "n_cord_c2", "n_cord_c3")
    passive_keys = ("n_barras_c1", "n_barras_c2", "n_barras_c3")
    prestress_count_keys = (
        "n_cord_c1",
        "n_cord_c2",
        "n_cord_c3",
        "diam_cord_c1_mm",
        "diam_cord_c2_mm",
        "diam_cord_c3_mm",
    )
    passive_count_keys = (
        "n_barras_c1",
        "n_barras_c2",
        "n_barras_c3",
        "diam_barra_c1_mm",
        "diam_barra_c2_mm",
        "diam_barra_c3_mm",
    )
    count = 0
    prestress_values = _values_for_keys(fixed_params, ranges, prestress_count_keys, defaults)
    passive_values = _values_for_keys(fixed_params, ranges, passive_count_keys, defaults)
    for prestress_combo, passive_combo in product(product(*prestress_values), product(*passive_values)):
        prestress = dict(zip(prestress_count_keys, prestress_combo))
        passive = dict(zip(passive_count_keys, passive_combo))
        if _has_valid_reinforcement_layout({**base_params, **prestress, **passive}):
            count += 1
    return count


def count_vpt_parametric(fixed_params: dict, ranges: dict) -> int:
    """Conta as combinacoes reais da VPT, descartando casos sem armadura inferior."""
    defaults = {**_default_params(), **VPT_PARAMETRIC_DEFAULTS}
    base_keys = (
        "secao",
        "vao_viga",
        "lp_esq",
        "lp_dir",
        "vao_laje_esq",
        "vao_laje_dir",
        "acd_esq",
        "acd_dir",
        "capa",
        "fck",
        "fckj",
        "fck_capa",
    )
    total = 0
    base_values = _values_for_keys(fixed_params, ranges, base_keys, defaults)
    for base_combo in product(*base_values):
        base_params = fixed_params.copy()
        base_params.update(dict(zip(base_keys, base_combo)))
        total += _count_nonzero_reinforcement(fixed_params, ranges, defaults, base_params)
    return total


def run_vpt_parametric(fixed_params: dict, ranges: dict, progress_callback=None) -> pd.DataFrame:
    """Executa estudo parametrico de viga T protendida."""
    total = count_vpt_parametric(fixed_params, ranges)
    results = []
    for idx, params in enumerate(_iter_vpt_combinations(fixed_params, ranges), start=1):
        results.append(run_vpt_case(params))
        if progress_callback is not None:
            progress_callback(idx, total)

    df = pd.DataFrame(results)
    if not df.empty:
        ordered = [column for column in VPT_RESULT_COLUMNS if column in df.columns]
        extra = [column for column in df.columns if column not in ordered]
        df = df[ordered + extra]
    df.attrs["fixed_params"] = fixed_params.copy()
    df.attrs["ranges"] = ranges.copy()
    return df


def export_vpt_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena as colunas principais da VPT para exportacao."""
    ordered = [column for column in VPT_RESULT_COLUMNS if column in df.columns]
    extra = [column for column in df.columns if column not in ordered]
    result = df[ordered + extra].copy()
    result.attrs.update(df.attrs)
    return result
