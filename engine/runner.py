"""Orquestrador que recebe parametros e retorna resultados."""

from itertools import product

import pandas as pd

try:
    from ..data.lp_table import LP_TABLE
except ImportError:
    from data.lp_table import LP_TABLE
from .els import check_els
from .elu import check_cisalhamento, check_flexao
from .loads import Loads
from .materials import PASSIVE_BAR_AREA
from .prestress import Prestress
from .section import SectionL


try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


def _status(ok):
    return "PASSA" if ok else "NAO PASSA"


LAYER_YP = {
    "n_cord_c1": 4.1,
    "n_cord_c2": 8.1,
    "n_cord_c3": 12.1,
}
LAYER_ALLOWED_COUNTS = {
    "n_cord_c1": set(range(0, 11)),
    "n_cord_c2": set(range(0, 12)),
    "n_cord_c3": set(range(0, 11)),
}
PASSIVE_LAYER_YS = {
    "n_barras_c1": 5.0,
    "n_barras_c2": 12.0,
    "n_barras_c3": 18.0,
}
PASSIVE_LAYER_ALLOWED_COUNTS = {
    "n_barras_c1": set(range(0, 11)),
    "n_barras_c2": set(range(0, 12)),
    "n_barras_c3": set(range(0, 11)),
}
LAYER_LIMITS_BY_BW = {
    25: {"c1": 4, "c2": 5, "c3": 4},
    30: {"c1": 6, "c2": 7, "c3": 6},
    40: {"c1": 8, "c2": 9, "c3": 8},
    50: {"c1": 10, "c2": 11, "c3": 10},
}
ALLOWED_CAPAS = {5, 7, 10}
SECTION_CATALOG = {
    (60, 40),
    (65, 40),
    (72, 40),
    (77, 40),
    (70, 50),
    (75, 50),
    (82, 50),
    (87, 50),
    (80, 60),
    (85, 60),
    (92, 60),
    (97, 60),
}
HINF_VIGA_OPTIONS = {40, 50, 60}
STEEL_WEIGHT_LONGITUDINAL = 0.785
STEEL_WEIGHT_TRANSVERSE = 0.782
DEFAULT_TOP_STRAND_YP_FROM_TOP = 3.98
DEFAULT_TOP_PASSIVE_YS_FROM_TOP = 3.80


def _taxa_armadura_protendida(prestress, section) -> float:
    return prestress.asp_total * STEEL_WEIGHT_TRANSVERSE * 10**4 / section.ac


def _taxa_armadura_passiva(section, as_passiva: float, asw: float, as_passiva_superior: float = 0) -> float:
    taxa_longitudinal = (
        as_passiva + as_passiva_superior + section.h / 10
    ) * STEEL_WEIGHT_LONGITUDINAL * 10**4 / section.ac
    comprimento_estribo = (2 * (section.h + section.bw) + section.bf + section.hinf) / 100
    peso_estribos = asw * comprimento_estribo * STEEL_WEIGHT_TRANSVERSE
    taxa_transversal = peso_estribos / (section.ac / 10000)
    return taxa_longitudinal + taxa_transversal


def _resolve_section_geometry(params):
    if "h" in params:
        return {
            "h": params["h"],
            "bw": params["bw"],
            "bf": params["bf"],
            "hsup": params.get("hsup"),
            "hinf": params.get("hinf"),
            "secao": None,
        }

    hinf_viga = int(params["hinf_viga"])
    if hinf_viga not in HINF_VIGA_OPTIONS:
        raise ValueError("hinf_viga invalido. Use 40, 50 ou 60 cm.")

    lp_data = params.get("lp_table", LP_TABLE)[params["lp_type"]]
    lp_altura = lp_data["cap"]
    hsup = lp_altura + params["capa"]
    h = hsup + hinf_viga
    if (h, hinf_viga) not in SECTION_CATALOG:
        raise ValueError(
            f"Secao L{h}/{hinf_viga}x{params['bw']} nao cadastrada para "
            f"{params['lp_type']} com capa {params['capa']} cm."
        )

    return {
        "h": h,
        "bw": params["bw"],
        "bf": params["bf"],
        "hsup": hsup,
        "hinf": hinf_viga,
        "secao": f"L{h}/{hinf_viga}x{params['bw']}",
    }


def _top_coordinate_from_height(section, value, default_from_top):
    distance_from_top = abs(float(value if value is not None else default_from_top))
    return section.h - distance_from_top


def _layer_limits(params: dict) -> dict:
    bw = int(params.get("bw", 40))
    if bw not in LAYER_LIMITS_BY_BW:
        raise ValueError(f"bw {bw} sem limites cadastrados para camadas.")
    return LAYER_LIMITS_BY_BW[bw]


def _validate_shared_layer_layout(params: dict):
    if not all(key in params for key in LAYER_YP):
        return
    if not all(key in params for key in PASSIVE_LAYER_YS) and any(
        key in params for key in ("n_barras", "n_barras_passiva")
    ):
        return

    limits = _layer_limits(params)
    bw = int(params.get("bw", 40))
    layer_counts = {
        "c1": (
            int(params.get("n_cord_c1", 0) or 0),
            int(params.get("n_barras_c1", 0) or 0),
        ),
        "c2": (
            int(params.get("n_cord_c2", 0) or 0),
            int(params.get("n_barras_c2", 0) or 0),
        ),
        "c3": (
            int(params.get("n_cord_c3", 0) or 0),
            int(params.get("n_barras_c3", 0) or 0),
        ),
    }

    if layer_counts["c1"][1] < 2:
        raise ValueError("CAM. 1 exige no minimo 2 barras passivas, independente da bitola.")

    for layer, (n_cord, n_barras) in layer_counts.items():
        if n_cord == 1:
            raise ValueError(f"CAM. {layer[-1]} nao permite apenas 1 cordoalha.")
        if n_barras == 1:
            raise ValueError(f"CAM. {layer[-1]} nao permite apenas 1 barra passiva.")
        total = n_cord + n_barras
        if total > limits[layer]:
            raise ValueError(
                f"CAM. {layer[-1]} excede o maximo de {limits[layer]} posicoes para bw={bw} "
                f"considerando barras + cordoalhas."
            )

    if sum(layer_counts["c2"]) > 0 and sum(layer_counts["c1"]) < limits["c1"]:
        raise ValueError(
            f"CAM. 2 so pode ser usada quando CAM. 1 estiver completa "
            f"com {limits['c1']} barras + cordoalhas para bw={bw}."
        )
    if sum(layer_counts["c3"]) > 0 and sum(layer_counts["c2"]) < limits["c2"]:
        raise ValueError(
            f"CAM. 3 so pode ser usada quando CAM. 2 estiver completa "
            f"com {limits['c2']} barras + cordoalhas para bw={bw}."
        )


def _passive_rebar(params, section=None):
    if all(key in params for key in PASSIVE_LAYER_YS):
        _validate_shared_layer_layout(params)
        n_c1 = int(params.get("n_barras_c1", 0))
        n_c2 = int(params.get("n_barras_c2", 0))
        n_c3 = int(params.get("n_barras_c3", 0))
        counts = {
            "n_barras_c1": n_c1,
            "n_barras_c2": n_c2,
            "n_barras_c3": n_c3,
        }
        for key, value in counts.items():
            if value not in PASSIVE_LAYER_ALLOWED_COUNTS[key]:
                allowed = sorted(PASSIVE_LAYER_ALLOWED_COUNTS[key])
                raise ValueError(f"Quantidade invalida para {key}: {value}. Use um de {allowed}.")

        layers = []
        for idx, key in enumerate(("n_barras_c1", "n_barras_c2", "n_barras_c3"), start=1):
            diam_key = f"diam_barra_c{idx}_mm"
            layers.append(
                {
                    "camada": idx,
                    "n_barras": counts[key],
                    "diam_barra_mm": params.get(diam_key, params.get("diam_barra_mm", 12.5)),
                    "ys": PASSIVE_LAYER_YS[key],
                    "posicao": "inferior",
                }
            )

        n_barras_sup = int(params.get("n_barras_sup", 0) or 0)
        diam_barra_sup_mm = params.get("diam_barra_sup_mm", 10.0)
        ys_barra_sup_ref = params.get("ys_barra_sup", -DEFAULT_TOP_PASSIVE_YS_FROM_TOP)
        ys_barra_sup = (
            _top_coordinate_from_height(section, ys_barra_sup_ref, DEFAULT_TOP_PASSIVE_YS_FROM_TOP)
            if section is not None
            else abs(float(ys_barra_sup_ref))
        )
        if n_barras_sup < 0:
            raise ValueError("O parametro 'n_barras_sup' nao pode ser negativo.")
        if n_barras_sup > 0:
            layers.append(
                {
                    "camada": "sup",
                    "n_barras": n_barras_sup,
                    "diam_barra_mm": diam_barra_sup_mm,
                    "ys": ys_barra_sup,
                    "posicao": "superior",
                }
            )

        total_barras = n_c1 + n_c2 + n_c3
        total_barras_geral = total_barras + n_barras_sup
        as_superior = 0
        if n_barras_sup > 0:
            as_superior = n_barras_sup * PASSIVE_BAR_AREA[diam_barra_sup_mm]
        return {
            "layers": layers,
            "n_barras": total_barras,
            "n_barras_total": total_barras_geral,
            "n_barras_c1": n_c1,
            "n_barras_c2": n_c2,
            "n_barras_c3": n_c3,
            "n_barras_sup": n_barras_sup,
            "diam_barra_c1_mm": layers[0]["diam_barra_mm"],
            "diam_barra_c2_mm": layers[1]["diam_barra_mm"],
            "diam_barra_c3_mm": layers[2]["diam_barra_mm"],
            "diam_barra_sup_mm": diam_barra_sup_mm,
            "ys_barra_sup": ys_barra_sup,
            "As_passiva_superior": as_superior,
            "ys": (
                sum(
                    layer["n_barras"] * layer["ys"]
                    for layer in layers
                    if layer.get("posicao") == "inferior"
                ) / total_barras
                if total_barras
                else 0
            ),
        }

    n_barras = int(params.get("n_barras", params.get("n_barras_passiva", 0)) or 0)
    diam_barra_mm = params.get("diam_barra_mm", 12.5)
    ys = params.get("ys", params.get("ys_passiva", params.get("cob", 2.5) + 1.0 + diam_barra_mm / 20))
    return {
        "n_barras": n_barras,
        "n_barras_total": n_barras,
        "n_barras_c1": None,
        "n_barras_c2": None,
        "n_barras_c3": None,
        "n_barras_sup": 0,
        "diam_barra_mm": diam_barra_mm,
        "diam_barra_sup_mm": None,
        "ys_barra_sup": None,
        "As_passiva_superior": 0,
        "ys": ys,
    }


def _prestress_layout(params, passive_rebar=None):
    if all(key in params for key in LAYER_YP):
        _validate_shared_layer_layout(params)
        n_c1 = int(params.get("n_cord_c1", 0))
        n_c2 = int(params.get("n_cord_c2", 0))
        n_c3 = int(params.get("n_cord_c3", 0))
        counts = {
            "n_cord_c1": n_c1,
            "n_cord_c2": n_c2,
            "n_cord_c3": n_c3,
        }
        for key, value in counts.items():
            if value not in LAYER_ALLOWED_COUNTS[key]:
                allowed = sorted(LAYER_ALLOWED_COUNTS[key])
                raise ValueError(f"Quantidade invalida para {key}: {value}. Use um de {allowed}.")

        n_sup = int(params.get("n_cord_sup", 0) or 0)
        n_total = n_c1 + n_c2 + n_c3
        if n_total + n_sup <= 0:
            if passive_rebar and passive_rebar["n_barras_total"] > 0:
                return 0, passive_rebar["ys"], n_c1, n_c2, n_c3
            raise ValueError("Informe ao menos uma cordoalha ou armadura passiva inferior.")

        yp = (
            (
                n_c1 * LAYER_YP["n_cord_c1"]
                + n_c2 * LAYER_YP["n_cord_c2"]
                + n_c3 * LAYER_YP["n_cord_c3"]
            ) / n_total
            if n_total
            else passive_rebar["ys"]
        )
        return n_total, yp, n_c1, n_c2, n_c3

    n_cord = int(params.get("n_cord", 0))
    if n_cord <= 0:
        if passive_rebar and passive_rebar["n_barras_total"] > 0:
            return 0, passive_rebar["ys"], None, None, None
        raise ValueError("Informe ao menos uma cordoalha ou armadura passiva inferior.")
    return n_cord, params["yp"], None, None, None


def run_case(params: dict) -> dict:
    """Executa uma combinacao de parametros e retorna resultados estruturados."""
    try:
        if params["capa"] not in ALLOWED_CAPAS:
            raise ValueError("Capa de concreto invalida. Use 5, 7 ou 10 cm.")

        geom = _resolve_section_geometry(params)
        section = SectionL(
            h=geom["h"],
            bw=geom["bw"],
            bf=geom["bf"],
            cob=params["cob"],
            capa=params["capa"],
            hsup=geom["hsup"],
            hinf=geom["hinf"],
            hs=params.get("hs", 0),
        )

        loads = Loads(
            section=section,
            lp_type=params["lp_type"],
            vao_laje=params["vao_laje"],
            rev=params.get("rev", 200),
            acd=params["acd"],
            lp_table=params.get("lp_table", LP_TABLE),
        )

        passive_rebar = _passive_rebar(params, section)
        n_cord, yp, n_c1, n_c2, n_c3 = _prestress_layout(params, passive_rebar)
        n_cord_sup = int(params.get("n_cord_sup", 0) or 0)
        yp_cord_sup_ref = params.get("yp_cord_sup", -DEFAULT_TOP_STRAND_YP_FROM_TOP)
        yp_cord_sup = _top_coordinate_from_height(
            section,
            yp_cord_sup_ref,
            DEFAULT_TOP_STRAND_YP_FROM_TOP,
        )

        prestress = Prestress(
            section=section,
            n_cordoalhas=n_cord,
            diam_mm=params.get("diam_mm", 12.7),
            yp=yp,
            n_cordoalhas_sup=n_cord_sup,
            diam_sup_mm=params.get("diam_cord_sup_mm", 9.5),
            yp_sup=yp_cord_sup,
            fat_pi=params.get("fat_pi", 0.95),
            dpi=params.get("dpi", 0.20),
            dps=params.get("dps", 0.10),
            fck=params["fck"],
            fckj=params["fckj"],
        )

        vao = params["vao_viga"]
        H39_laje = params.get("H39_laje")
        vao_laje = params["vao_laje"]

        flexao = check_flexao(
            section,
            prestress,
            loads,
            vao,
            params["fck"],
            H39_laje=H39_laje,
            vao_laje=vao_laje,
            passive_rebar=passive_rebar,
            fck_capa=params.get("fck_capa", 40),
        )
        cisalhamento = check_cisalhamento(
            section,
            loads,
            vao,
            params["fck"],
            yp=prestress.yp,
        )
        els = check_els(
            section,
            prestress,
            loads,
            vao,
            params["fck"],
            params["fckj"],
            caa=params.get("caa", "II"),
            H39_laje=H39_laje,
            vao_laje=vao_laje,
            psi1=params.get("psi1", 0.6),
            psi2=params.get("psi2", 0.4),
        )
        detalhes_els = els["detalhes"]
        _H39 = detalhes_els["H39_laje"]
        _vl = detalhes_els["vao_laje"]

        ok = flexao["ok"] and cisalhamento["ok"] and els["ok"]
        taxa_armadura_passiva = _taxa_armadura_passiva(
            section,
            flexao["As_passiva"],
            cisalhamento["Asw"],
            passive_rebar["As_passiva_superior"],
        )
        taxa_armadura_protendida = _taxa_armadura_protendida(prestress, section)
        volume_m3 = float(params["volume"]) if params.get("volume") else (section.ac / 10000) * vao
        peso_proprio_kn = 25 * volume_m3
        return {
            "secao": geom["secao"],
            "h": section.h,
            "bw": section.bw,
            "capa": params["capa"],
            "hs": params.get("hs", 0),
            "hinf": section.hinf,
            "hsup": section.hsup,
            "vao_viga": vao,
            "lp_type": params["lp_type"],
            "vao_laje": vao_laje,
            "acd": params["acd"],
            "volume_m3": round(volume_m3, 4),
            "peso_proprio": peso_proprio_kn,
            "carga_permanente_kgf_m": params.get("rev", 200),
            "n_cord": n_cord,
            "n_cord_c1": n_c1,
            "n_cord_c2": n_c2,
            "n_cord_c3": n_c3,
            "n_cord_sup": n_cord_sup,
            "yp_cordoalha_eq": yp,
            "yp_cordoalha_total_eq": prestress.yp_equivalente_total,
            "yp_cord_sup": yp_cord_sup,
            "diam_mm": params.get("diam_mm", 12.7),
            "diam_cord_c1_mm": params.get("diam_mm", 12.7),
            "diam_cord_c2_mm": params.get("diam_mm", 12.7),
            "diam_cord_c3_mm": params.get("diam_mm", 12.7),
            "diam_cord_sup_mm": params.get("diam_cord_sup_mm", 9.5),
            "n_barras": passive_rebar["n_barras"],
            "n_barras_total": passive_rebar["n_barras_total"],
            "n_barras_c1": passive_rebar["n_barras_c1"],
            "n_barras_c2": passive_rebar["n_barras_c2"],
            "n_barras_c3": passive_rebar["n_barras_c3"],
            "n_barras_sup": passive_rebar["n_barras_sup"],
            "diam_barra_mm": passive_rebar.get("diam_barra_mm"),
            "diam_barra_c1_mm": passive_rebar.get("diam_barra_c1_mm"),
            "diam_barra_c2_mm": passive_rebar.get("diam_barra_c2_mm"),
            "diam_barra_c3_mm": passive_rebar.get("diam_barra_c3_mm"),
            "diam_barra_sup_mm": passive_rebar.get("diam_barra_sup_mm"),
            "ys": passive_rebar["ys"],
            "ys_barra_sup": passive_rebar["ys_barra_sup"],
            "psi_tipo": params.get("psi_tipo"),
            "psi0": params.get("psi0", 0.7),
            "psi1": params.get("psi1", 0.6),
            "psi2": params.get("psi2", 0.4),
            "Msd": flexao["Msd"],
            "MRU": flexao["MRU"],
            "MRU_MSD": flexao["MRU"] / flexao["Msd"] if flexao["Msd"] else 0,
            "As_passiva": flexao["As_passiva"],
            "As_passiva_superior": passive_rebar["As_passiva_superior"],
            "taxa_armadura_passiva": taxa_armadura_passiva,
            "taxa_armadura_protendida": taxa_armadura_protendida,
            "ok_flexao": flexao["ok"],
            "Vsd": cisalhamento["Vsd"],
            "VRd2": cisalhamento["VRd2"],
            "ok_cisalhamento": cisalhamento["ok"],
            "ok_els": els["ok"],
            "sigma_sup_ato": detalhes_els["sigma_sup_ato"],
            "sigma_inf_ato": detalhes_els["sigma_inf_ato"],
            "lim_sup_ato": detalhes_els["lim_sup_ato"],
            "lim_inf_ato": detalhes_els["lim_inf_ato"],
            "ok_sup_ato": detalhes_els["ok_sup_ato"],
            "ok_inf_ato": detalhes_els["ok_inf_ato"],
            "Msd_mont": detalhes_els["Msd_mont"],
            "cg_f": section.cg_f(_H39, _vl),
            "ix_f": section.ix_f(_H39, _vl),
            "Msd_D": detalhes_els["Msd_D"],
            "sigma_sup_D": detalhes_els["sigma_sup_D"],
            "sigma_inf_D": detalhes_els["sigma_inf_D"],
            "lim_sup_D": detalhes_els["lim_sup_D"],
            "lim_inf_D": detalhes_els["lim_inf_D"],
            "ok_sup_D": detalhes_els["ok_sup_D"],
            "ok_inf_D": detalhes_els["ok_inf_D"],
            "Msd_F": detalhes_els["Msd_F"],
            "sigma_sup_F": detalhes_els["sigma_sup_F"],
            "sigma_inf_F": detalhes_els["sigma_inf_F"],
            "lim_sup_F": detalhes_els["lim_sup_F"],
            "lim_inf_F": detalhes_els["lim_inf_F"],
            "ok_sup_F": detalhes_els["ok_sup_F"],
            "ok_inf_F": detalhes_els["ok_inf_F"],
            "status": _status(ok),
            "ok": ok,
        }
    except Exception as exc:
        return {
            "secao": params.get("secao"),
            "h": params.get("h"),
            "bw": params.get("bw"),
            "capa": params.get("capa"),
            "hinf": params.get("hinf", params.get("hinf_viga")),
            "hsup": params.get("hsup"),
            "vao_viga": params.get("vao_viga"),
            "lp_type": params.get("lp_type"),
            "vao_laje": params.get("vao_laje"),
            "acd": params.get("acd"),
            "n_cord": params.get("n_cord"),
            "n_cord_c1": params.get("n_cord_c1"),
            "n_cord_c2": params.get("n_cord_c2"),
            "n_cord_c3": params.get("n_cord_c3"),
            "n_cord_sup": params.get("n_cord_sup"),
            "diam_cord_sup_mm": params.get("diam_cord_sup_mm"),
            "diam_mm": params.get("diam_mm"),
            "n_barras": params.get("n_barras", params.get("n_barras_passiva")),
            "n_barras_c1": params.get("n_barras_c1"),
            "n_barras_c2": params.get("n_barras_c2"),
            "n_barras_c3": params.get("n_barras_c3"),
            "n_barras_sup": params.get("n_barras_sup"),
            "diam_barra_mm": params.get("diam_barra_mm"),
            "diam_barra_sup_mm": params.get("diam_barra_sup_mm"),
            "status": "ERRO",
            "erro_msg": str(exc),
            "ok": False,
        }


def _iter_combinations(fixed_params: dict, ranges: dict):
    section_items = _valid_section_items(fixed_params, ranges)
    reinforcement_pairs = _valid_reinforcement_pairs(fixed_params, ranges)

    keys = ("vao_viga", "vao_laje", "acd", "diam_mm")
    values = (
        ranges["vao_viga"],
        ranges["vao_laje"],
        ranges["acd"],
        ranges.get("diam_mm", [fixed_params.get("diam_mm", 12.7)]),
    )

    for combo in product(*values):
        base_params = fixed_params.copy()
        base_params.update(dict(zip(keys, combo)))
        for section_item, reinforcement_pair in product(
            section_items,
            reinforcement_pairs,
        ):
            prestress_item, passive_item = reinforcement_pair
            params = base_params.copy()
            params.update(section_item)
            params.update(prestress_item)
            params.update(passive_item)
            yield params


def _valid_section_items(fixed_params: dict, ranges: dict) -> list[dict]:
    if "hinf_viga" not in ranges:
        return [{"lp_type": lp_type} for lp_type in ranges["lp_types"]]

    items = []
    for lp_type, hinf_viga in product(ranges["lp_types"], ranges["hinf_viga"]):
        params = fixed_params.copy()
        params.update({"lp_type": lp_type, "hinf_viga": hinf_viga})
        try:
            _resolve_section_geometry(params)
        except (KeyError, ValueError):
            continue
        items.append({"lp_type": lp_type, "hinf_viga": hinf_viga})
    return items


def _valid_prestress_items(fixed_params: dict, ranges: dict) -> list[dict]:
    if "n_cord" in ranges:
        return [{"n_cord": n_cord} for n_cord in ranges["n_cord"]]

    c1_values = ranges.get("n_cord_c1", [fixed_params.get("n_cord_c1", 0)])
    c2_values = ranges.get("n_cord_c2", [fixed_params.get("n_cord_c2", 0)])
    c3_values = ranges.get("n_cord_c3", [fixed_params.get("n_cord_c3", 0)])
    items = []
    for n_c1, n_c2, n_c3 in product(c1_values, c2_values, c3_values):
        if n_c1 not in LAYER_ALLOWED_COUNTS["n_cord_c1"]:
            continue
        if n_c2 not in LAYER_ALLOWED_COUNTS["n_cord_c2"]:
            continue
        if n_c3 not in LAYER_ALLOWED_COUNTS["n_cord_c3"]:
            continue
        items.append({"n_cord_c1": n_c1, "n_cord_c2": n_c2, "n_cord_c3": n_c3})
    return items


def _valid_passive_items(fixed_params: dict, ranges: dict) -> list[dict]:
    if "n_barras_c1" in ranges:
        c1_values = ranges.get("n_barras_c1", [fixed_params.get("n_barras_c1", 0)])
        c2_values = ranges.get("n_barras_c2", [fixed_params.get("n_barras_c2", 0)])
        c3_values = ranges.get("n_barras_c3", [fixed_params.get("n_barras_c3", 0)])
        diam_c1_values = ranges.get("diam_barra_c1_mm", [fixed_params.get("diam_barra_c1_mm", 12.5)])
        diam_c2_values = ranges.get("diam_barra_c2_mm", [fixed_params.get("diam_barra_c2_mm", 12.5)])
        diam_c3_values = ranges.get("diam_barra_c3_mm", [fixed_params.get("diam_barra_c3_mm", 12.5)])
        items = []
        for n_c1, n_c2, n_c3, d_c1, d_c2, d_c3 in product(
            c1_values,
            c2_values,
            c3_values,
            diam_c1_values,
            diam_c2_values,
            diam_c3_values,
        ):
            if n_c1 not in PASSIVE_LAYER_ALLOWED_COUNTS["n_barras_c1"]:
                continue
            if n_c2 not in PASSIVE_LAYER_ALLOWED_COUNTS["n_barras_c2"]:
                continue
            if n_c3 not in PASSIVE_LAYER_ALLOWED_COUNTS["n_barras_c3"]:
                continue
            items.append(
                {
                    "n_barras_c1": n_c1,
                    "n_barras_c2": n_c2,
                    "n_barras_c3": n_c3,
                    "diam_barra_c1_mm": d_c1,
                    "diam_barra_c2_mm": d_c2,
                    "diam_barra_c3_mm": d_c3,
                }
            )
        return items

    items = [{}]
    if "n_barras" in ranges:
        items = [{"n_barras": n_barras} for n_barras in ranges["n_barras"]]
    if "diam_barra_mm" in ranges:
        items = [
            {**item, "diam_barra_mm": diam_barra_mm}
            for item, diam_barra_mm in product(items, ranges["diam_barra_mm"])
        ]
    return items


def _total_prestress_count(params: dict) -> int:
    n_sup = int(params.get("n_cord_sup", 0) or 0)
    if all(key in params for key in LAYER_YP):
        return sum(int(params.get(key, 0) or 0) for key in LAYER_YP) + n_sup
    return int(params.get("n_cord", 0) or 0) + n_sup


def _total_passive_count(params: dict) -> int:
    n_sup = int(params.get("n_barras_sup", 0) or 0)
    if all(key in params for key in PASSIVE_LAYER_YS):
        return sum(int(params.get(key, 0) or 0) for key in PASSIVE_LAYER_YS) + n_sup
    return int(params.get("n_barras", params.get("n_barras_passiva", 0)) or 0) + n_sup


def _valid_reinforcement_pairs(fixed_params: dict, ranges: dict) -> list[tuple[dict, dict]]:
    prestress_items = _valid_prestress_items(fixed_params, ranges)
    passive_items = _valid_passive_items(fixed_params, ranges)
    items = []

    for prestress_item, passive_item in product(prestress_items, passive_items):
        params = fixed_params.copy()
        params.update(prestress_item)
        params.update(passive_item)
        if _total_prestress_count(params) <= 0 and _total_passive_count(params) <= 0:
            continue
        try:
            _validate_shared_layer_layout(params)
        except ValueError:
            continue
        items.append((prestress_item, passive_item))

    return items


def run_parametric(fixed_params: dict, ranges: dict, progress_callback=None) -> pd.DataFrame:
    """Executa estudo parametrico por produto cartesiano e retorna DataFrame."""
    total = count_parametric(fixed_params, ranges)
    combinations = _iter_combinations(fixed_params, ranges)
    iterator = (
        tqdm(combinations, desc="Calculando casos", total=total)
        if tqdm and progress_callback is None
        else combinations
    )

    if tqdm is None and progress_callback is None:
        print(f"Calculando {total} casos...")

    results = []
    for idx, params in enumerate(iterator, start=1):
        results.append(run_case(params))
        if progress_callback is not None:
            progress_callback(idx, total)

    df = pd.DataFrame(results)
    df.attrs["fixed_params"] = fixed_params.copy()
    df.attrs["ranges"] = ranges.copy()
    return df


def count_parametric(fixed_params: dict, ranges: dict) -> int:
    """Conta as combinacoes reais apos filtros de secao e camadas."""
    section_items = _valid_section_items(fixed_params, ranges)
    reinforcement_pairs = _valid_reinforcement_pairs(fixed_params, ranges)
    return (
        len(ranges["vao_viga"])
        * len(ranges["vao_laje"])
        * len(ranges["acd"])
        * len(ranges.get("diam_mm", [fixed_params.get("diam_mm", 12.7)]))
        * len(section_items)
        * len(reinforcement_pairs)
    )
