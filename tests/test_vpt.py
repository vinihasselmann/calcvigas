import math

import pytest
from pytest import approx

from engine.vpt import (
    build_vpt_ranges,
    count_vpt_parametric,
    export_vpt_df,
    run_vpt_case,
    run_vpt_parametric,
)
from engine.vpt_model import VPT_SECTION_CATALOG


def test_run_vpt_case_matches_reference_sheet_default_case():
    result = run_vpt_case()

    assert result["status"] == "NAO PASSA"
    assert result["secao"] == "T82/40x52"
    assert result["h"] == approx(82)
    assert result["hp"] == approx(50)
    assert result["ac"] == approx(2800)

    assert result["Msd"] == approx(135.844629375)
    assert result["Vsd"] == approx(59.711925)
    assert result["VRd2"] == approx(221.72534461589223)
    assert result["Asw"] == approx(6.514602279827775)
    assert result["taxa_armadura_passiva"] == approx(112.50612935733686)
    assert result["taxa_armadura_protendida"] == approx(27.98442857142857)

    assert result["MRU"] == approx(135.75979568826094)
    assert result["MRU2"] == approx(129.1151949019369)
    assert result["MRU3"] == approx(135.75979568826094)
    assert result["MRU_MSD"] == approx(0.9993755094542244)
    assert result["dominio"] == "III"
    assert result["eps_pd"] == approx(15.9173351617241)
    assert result["eps_sd"] == approx(9.787904187563763)
    assert result["eps_cd"] == approx(3.5)
    assert result["x_final"] == approx(19.86599574710294)
    assert result["x_d"] == approx(0.26339744406613597)

    assert result["ok_flexao"] is False
    assert result["ok_cisalhamento"] is True


def test_run_vpt_case_service_stress_matches_reference_sheet_method():
    result = run_vpt_case(
        {
            "vao_viga": 8.0,
            "lp_esq": "LP26,5",
            "lp_dir": "LP26,5",
            "vao_laje_esq": 9.6,
            "vao_laje_dir": 6.6,
            "acd_esq": 300,
            "acd_dir": 300,
            "rev_esq": 200,
            "rev_dir": 200,
            "n_cord_c1": 6,
            "n_cord_c2": 3,
            "n_cord_c3": 0,
            "diam_cord_c1_mm": 12.7,
            "diam_cord_c2_mm": 12.7,
            "diam_cord_c3_mm": 15.2,
            "n_barras_c1": 2,
            "n_barras_c2": 2,
            "n_barras_c3": 0,
            "diam_barra_c1_mm": 25.0,
            "diam_barra_c2_mm": 20.0,
            "diam_barra_c3_mm": 32.0,
        }
    )

    assert result["sigma_inf_F"] == approx(-107.31142750672188)
    assert result["lim_inf_F"] == approx(-42.752077461369765)
    assert result["ok_inf_F"] is False


def test_vpt_v01_asw_and_passive_rate_match_reference_sheet():
    result = run_vpt_case(
        {
            "secao": "T65/35x30",
            "vao_viga": 8.15,
            "lp_esq": "LP20",
            "lp_dir": "LP20",
            "vao_laje_esq": 10.07,
            "vao_laje_dir": 10.07,
            "acd_esq": 300,
            "acd_dir": 300,
            "rev_esq": 200,
            "rev_dir": 200,
            "n_cord_c1": 4,
            "n_cord_c2": 4,
            "n_cord_c3": 4,
            "diam_cord_c1_mm": 12.7,
            "diam_cord_c2_mm": 12.7,
            "diam_cord_c3_mm": 12.7,
            "n_barras_c1": 2,
            "n_barras_c2": 3,
            "n_barras_c3": 0,
            "diam_barra_c1_mm": 10,
            "diam_barra_c2_mm": 10,
            "diam_barra_c3_mm": 32,
        }
    )

    assert result["Asw_calculada"] == approx(3.53117427615714)
    assert result["Asw_minima"] == approx(4.88595170987083)
    assert result["Asw"] == approx(4.88595170987083)
    assert result["taxa_armadura_passiva_longitudinal"] == approx(38.5788573148101)
    assert result["taxa_armadura_passiva_transversal"] == approx(31.5269053713315)
    assert result["taxa_armadura_passiva"] == approx(70.1057626861416)


def test_vpt_v02_rejects_c3_cords_when_c2_is_not_full():
    result = run_vpt_case(
        {
            "secao": "T60/35x30",
            "vao_viga": 8.15,
            "lp_esq": "LP20",
            "lp_dir": "LP20",
            "vao_laje_esq": 10.1,
            "vao_laje_dir": 10.1,
            "acd_esq": 150,
            "acd_dir": 150,
            "rev_esq": 200,
            "rev_dir": 200,
            "psi0": 0.5,
            "psi1": 0.4,
            "psi2": 0.3,
            "n_cord_c1": 4,
            "n_cord_c2": 4,
            "n_cord_c3": 4,
            "diam_cord_c1_mm": 12.7,
            "diam_cord_c2_mm": 12.7,
            "diam_cord_c3_mm": 12.7,
            "n_barras_c1": 2,
            "n_barras_c2": 0,
            "n_barras_c3": 0,
            "diam_barra_c1_mm": 10,
            "diam_barra_c2_mm": 12.5,
            "diam_barra_c3_mm": 32,
        }
    )

    assert result["status"] == "ERRO"
    assert "CAM. 3 so pode ser usada quando CAM. 2 estiver completa" in result["erro_msg"]


def test_vpt_v02_economic_layout_completes_c2_with_seven_strands():
    result = run_vpt_case(
        {
            "secao": "T65/35x30",
            "vao_viga": 8.15,
            "lp_esq": "LP20",
            "lp_dir": "LP20",
            "vao_laje_esq": 10.1,
            "vao_laje_dir": 10.1,
            "acd_esq": 150,
            "acd_dir": 150,
            "rev_esq": 200,
            "rev_dir": 200,
            "psi0": 0.5,
            "psi1": 0.4,
            "psi2": 0.3,
            "n_cord_c1": 4,
            "n_cord_c2": 7,
            "n_cord_c3": 0,
            "diam_cord_c1_mm": 12.7,
            "diam_cord_c2_mm": 12.7,
            "diam_cord_c3_mm": 12.7,
            "n_barras_c1": 2,
            "n_barras_c2": 0,
            "n_barras_c3": 0,
            "diam_barra_c1_mm": 10,
            "diam_barra_c2_mm": 12.5,
            "diam_barra_c3_mm": 32,
        }
    )

    assert result["status"] == "PASSA"
    assert result["n_cord"] == 11
    assert result["n_barras"] == 2
    assert result["MRU_MSD"] == approx(1.17547692466184)
    assert result["taxa_armadura_passiva"] == approx(63.8358892122399)
    assert result["taxa_armadura_protendida"] == approx(31.8101694915254)


def test_run_vpt_case_accepts_v15_manual_satisfied_combination():
    result = run_vpt_case(
        {
            "secao": "T55/25x40",
            "vao_viga": 5.7,
            "lp_esq": "LP20",
            "lp_dir": "LP20",
            "vao_laje_esq": 5.1,
            "vao_laje_dir": 5.1,
            "acd_esq": 1800,
            "acd_dir": 1800,
            "rev_esq": 200,
            "rev_dir": 200,
            "n_cord_c1": 4,
            "n_cord_c2": 0,
            "n_cord_c3": 0,
            "n_barras_c1": 4,
            "n_barras_c2": 0,
            "n_barras_c3": 0,
            "diam_barra_c1_mm": 25.0,
            "diam_barra_c2_mm": 16.0,
            "diam_barra_c3_mm": 32.0,
        }
    )

    assert result["status"] == "PASSA"
    assert result["secao"] == "T55/25x40"
    assert result["MRU_MSD"] >= 1.10
    assert result["lim_inf_F"] - 10 <= result["sigma_inf_F"] <= result["lim_inf_F"] + 10


def test_run_vpt_case_reports_error_for_unknown_lp_type():
    result = run_vpt_case({"lp_esq": "LP999"})

    assert result["status"] == "ERRO"
    assert "LP999" in result["erro_msg"]


def test_run_vpt_case_rejects_invalid_layer_dependencies():
    invalid_prestress = run_vpt_case({"n_cord_c1": 4, "n_cord_c2": 3, "n_cord_c3": 0, "n_barras_c1": 2})
    invalid_passive = run_vpt_case(
        {
            "n_cord_c1": 0,
            "n_cord_c2": 0,
            "n_cord_c3": 0,
            "n_barras_c1": 2,
            "n_barras_c2": 1,
            "n_barras_c3": 0,
        }
    )
    invalid_cord_sequence = run_vpt_case(
        {
            "n_cord_c1": 0,
            "n_cord_c2": 2,
            "n_cord_c3": 0,
            "n_barras_c1": 8,
            "n_barras_c2": 7,
            "n_barras_c3": 0,
        }
    )
    invalid_cord_priority = run_vpt_case(
        {
            "n_cord_c1": 4,
            "n_cord_c2": 2,
            "n_cord_c3": 0,
            "n_barras_c1": 4,
            "n_barras_c2": 7,
            "n_barras_c3": 0,
        }
    )

    assert invalid_prestress["status"] == "ERRO"
    assert "CAM. 2" in invalid_prestress["erro_msg"]
    assert invalid_passive["status"] == "ERRO"
    assert "CAM. 2" in invalid_passive["erro_msg"]
    assert invalid_cord_sequence["status"] == "ERRO"
    assert "cordoalhas na CAM. 1" in invalid_cord_sequence["erro_msg"]
    assert invalid_cord_priority["status"] == "ERRO"
    assert "priorizar cordoalhas na CAM. 1" in invalid_cord_priority["erro_msg"]


def test_run_vpt_case_uses_parametric_layer_counts_when_valid():
    result = run_vpt_case(
        {
            "n_cord_c1": 6,
            "n_cord_c2": 3,
            "n_cord_c3": 0,
            "n_barras_c1": 2,
            "n_barras_c2": 0,
            "n_barras_c3": 0,
        }
    )

    assert result["status"] != "ERRO", result.get("erro_msg")
    assert result["n_cord_c1"] == 6
    assert result["n_cord_c2"] == 3
    assert result["n_cord"] == 9
    assert result["n_barras_c1"] == 2
    assert result["n_barras_c2"] == 0


def test_run_vpt_case_rejects_layer_counts_above_bw_limit():
    result = run_vpt_case({"secao": "T55/25x25", "n_cord_c1": 5, "n_cord_c2": 0, "n_cord_c3": 0})

    assert result["status"] == "ERRO"
    assert "CAM. 1 excede o maximo de 5 posicoes para bw=25" in result["erro_msg"]


def test_run_vpt_case_accepts_layer_counts_at_bw50_limit():
    result = run_vpt_case(
        {
            "secao": "T95/65x50",
            "n_cord_c1": 8,
            "n_cord_c2": 11,
            "n_cord_c3": 10,
            "n_barras_c1": 2,
            "n_barras_c2": 0,
            "n_barras_c3": 0,
        }
    )

    assert result["status"] != "ERRO", result.get("erro_msg")
    assert result["n_cord_c1"] == 8
    assert result["n_cord_c2"] == 11
    assert result["n_cord_c3"] == 10
    assert result["n_barras_c1"] == 2
    assert result["n_barras_c2"] == 0
    assert result["n_barras_c3"] == 0


def test_build_vpt_ranges_from_config():
    ranges = build_vpt_ranges(
        {
            "vao_viga_min": 8,
            "vao_viga_max": 9,
            "vao_viga_step": 0.5,
            "vao_laje_esq_min": 6,
            "vao_laje_esq_max": 7,
            "vao_laje_esq_step": 0.5,
            "vao_laje_dir_min": 5,
            "vao_laje_dir_max": 5.5,
            "vao_laje_dir_step": 0.5,
            "acd_esq_min": 300,
            "acd_esq_max": 400,
            "acd_esq_step": 100,
            "acd_dir_min": 300,
            "acd_dir_max": 500,
            "acd_dir_step": 100,
            "lp_esq_values": ["LP20", "LP26,5"],
            "lp_dir_values": ["LP26,5"],
            "capa_values": [5],
            "fck_values": [50],
            "fckj_values": [35],
            "fck_capa_values": [40],
        }
    )

    assert ranges["vao_viga"] == [8, 8.5, 9]
    assert ranges["vao_laje_esq"] == [6, 6.5, 7]
    assert ranges["vao_laje_dir"] == [5, 5.5]
    assert ranges["acd_esq"] == [300, 400]
    assert ranges["acd_dir"] == [300, 400, 500]
    assert ranges["lp_esq"] == ["LP20", "LP26,5"]
    assert ranges["lp_dir"] == ["LP26,5"]


def test_run_vpt_parametric_discards_cases_without_bottom_reinforcement():
    ranges = {
        "vao_viga": [9.1],
        "vao_laje_esq": [9.6],
        "vao_laje_dir": [6.6],
        "acd_esq": [300],
        "acd_dir": [300],
        "lp_esq": ["LP26,5"],
        "lp_dir": ["LP26,5"],
        "capa": [5],
        "fck": [50],
        "fckj": [35],
        "fck_capa": [40],
        "n_cord_c1": [0, 6],
        "n_cord_c2": [0],
        "n_cord_c3": [0],
        "n_barras_c1": [0, 2],
        "n_barras_c2": [0],
        "n_barras_c3": [0],
    }

    df = run_vpt_parametric({}, ranges)

    assert count_vpt_parametric({}, ranges) == len(df) == 2
    assert "ERRO" not in set(df["status"])
    assert not (
        (df[["n_cord_c1", "n_cord_c2", "n_cord_c3"]].sum(axis=1) == 0)
        & (df[["n_barras_c1", "n_barras_c2", "n_barras_c3"]].sum(axis=1) == 0)
    ).any()
    assert {"PASSA", "NAO PASSA"}.issuperset(set(df["status"]))
    assert list(df.columns[:6]) == [
        "secao",
        "vao_viga",
        "lp_esq",
        "lp_dir",
        "vao_laje_esq",
        "vao_laje_dir",
    ]


def test_run_vpt_parametric_filters_invalid_layer_dependencies():
    ranges = {
        "vao_viga": [9.1],
        "vao_laje_esq": [9.6],
        "vao_laje_dir": [6.6],
        "acd_esq": [300],
        "acd_dir": [300],
        "lp_esq": ["LP26,5"],
        "lp_dir": ["LP26,5"],
        "capa": [5],
        "fck": [50],
        "fckj": [35],
        "fck_capa": [40],
        "n_cord_c1": [4, 6],
        "n_cord_c2": [0, 3],
        "n_cord_c3": [0],
        "n_barras_c1": [2],
        "n_barras_c2": [0],
        "n_barras_c3": [0],
    }

    df = run_vpt_parametric({}, ranges)

    assert count_vpt_parametric({}, ranges) == len(df) == 3
    assert ((df["n_cord_c1"] == 4) & (df["n_cord_c2"] == 0)).any()
    assert ((df["n_cord_c1"] == 6) & (df["n_cord_c2"] == 0)).any()
    assert ((df["n_cord_c1"] == 6) & (df["n_cord_c2"] == 3)).any()
    assert not ((df["n_cord_c1"] == 4) & (df["n_cord_c2"] == 3)).any()
    assert "ERRO" not in set(df["status"])


def test_run_vpt_parametric_filters_layer_counts_by_section_bw():
    ranges = {
        "secao": ["T55/25x25", "T95/65x50"],
        "vao_viga": [9.1],
        "vao_laje_esq": [9.6],
        "vao_laje_dir": [6.6],
        "acd_esq": [300],
        "acd_dir": [300],
        "lp_esq": ["LP26,5"],
        "lp_dir": ["LP26,5"],
        "capa": [5],
        "fck": [50],
        "fckj": [35],
        "fck_capa": [40],
        "n_cord_c1": [5],
        "n_cord_c2": [0],
        "n_cord_c3": [0],
        "n_barras_c1": [2],
        "n_barras_c2": [0],
        "n_barras_c3": [0],
    }

    df = run_vpt_parametric({}, ranges)

    assert count_vpt_parametric({}, ranges) == len(df) == 1
    assert df.iloc[0]["secao"] == "T95/65x50"
    assert df.iloc[0]["n_cord_c1"] == 5


def test_run_vpt_parametric_uses_section_catalog():
    ranges = {
        "secao": ["T95/65x50"],
        "vao_viga": [9.1],
        "vao_laje_esq": [9.6],
        "vao_laje_dir": [6.6],
        "acd_esq": [300],
        "acd_dir": [300],
        "lp_esq": ["LP26,5"],
        "lp_dir": ["LP26,5"],
        "capa": [5],
        "fck": [50],
        "fckj": [35],
        "fck_capa": [40],
    }

    df = run_vpt_parametric({}, ranges)
    row = df.iloc[0]

    assert len(df) == 1
    assert row["secao"] == "T95/65x50"
    assert row["hp"] == 95
    assert row["h"] == 127
    assert row["As_passiva"] > 0


@pytest.mark.parametrize("secao", VPT_SECTION_CATALOG.keys())
def test_run_vpt_case_accepts_every_catalog_section(secao):
    result = run_vpt_case({"secao": secao})

    assert result["status"] != "ERRO", result.get("erro_msg")
    assert result["secao"] == secao
    for field in (
        "h",
        "hp",
        "ac",
        "Msd",
        "MRU",
        "Vsd",
        "VRd2",
        "taxa_armadura_passiva",
        "taxa_armadura_protendida",
    ):
        assert isinstance(result[field], int | float)
        assert math.isfinite(result[field])


def test_export_vpt_df_orders_suggested_columns():
    ranges = {
        "vao_viga": [9.1],
        "vao_laje_esq": [9.6],
        "vao_laje_dir": [6.6],
        "acd_esq": [300],
        "acd_dir": [300],
        "lp_esq": ["LP26,5"],
        "lp_dir": ["LP26,5"],
        "capa": [5],
        "fck": [50],
        "fckj": [35],
        "fck_capa": [40],
    }
    df = run_vpt_parametric({}, ranges)

    export_df = export_vpt_df(df)

    assert list(export_df.columns[:12]) == [
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
    ]
