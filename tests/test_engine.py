import pytest
import pandas as pd

from engine.section import SectionL
from engine.materials import eci, fctm
from engine.loads import Loads
from engine.runner import count_parametric, run_case, run_parametric
from engine.prestress import Prestress
from engine.elu import check_flexao, check_cisalhamento
from data.lp_table import LP_TABLE
from ui.results_table import EXPORT_HIDDEN_COLUMNS, INTERNAL_EXPORT_COLUMNS, _export_df


REF_PARAMS = {
    "h": 70,
    "bw": 40,
    "bf": 15,
    "hsup": 25,
    "hinf": 45,
    "cob": 2.5,
    "capa": 5,
    "hs": 0,
    "fck": 50,
    "fckj": 35,
    "caa": "II",
    "n_cord": 6,
    "diam_mm": 12.7,
    "yp": 4.135,
    "fat_pi": 0.95,
    "dpi": 0.20,
    "dps": 0.10,
    "lp_type": "LP20",
    "vao_laje": 7.5,
    "rev": 200,
    "acd": 300,
    "vao_viga": 9.61,
}


def approx_ref(value):
    return pytest.approx(value, rel=0.02)


@pytest.fixture
def section():
    return SectionL(
        h=REF_PARAMS["h"],
        bw=REF_PARAMS["bw"],
        bf=REF_PARAMS["bf"],
        hsup=REF_PARAMS["hsup"],
        hinf=REF_PARAMS["hinf"],
        cob=REF_PARAMS["cob"],
        capa=REF_PARAMS["capa"],
        hs=REF_PARAMS["hs"],
    )


@pytest.fixture
def loads(section):
    return Loads(
        section=section,
        lp_type=REF_PARAMS["lp_type"],
        vao_laje=REF_PARAMS["vao_laje"],
        rev=REF_PARAMS["rev"],
        acd=REF_PARAMS["acd"],
        lp_table=LP_TABLE,
    )


@pytest.fixture
def prestress(section):
    return Prestress(
        section=section,
        n_cordoalhas=REF_PARAMS["n_cord"],
        diam_mm=REF_PARAMS["diam_mm"],
        yp=REF_PARAMS["yp"],
        fat_pi=REF_PARAMS["fat_pi"],
        dpi=REF_PARAMS["dpi"],
        dps=REF_PARAMS["dps"],
        fck=REF_PARAMS["fck"],
        fckj=REF_PARAMS["fckj"],
    )


def test_area_concreto(section):
    assert section.ac == approx_ref(2175)


def test_centroide(section):
    assert section.cg == approx_ref(28.53)


def test_pp_viga(section):
    assert section.pp_viga == approx_ref(0.544)


def test_sc_g1(loads):
    assert loads.sc_g1 == approx_ref(1.631)


def test_sc_g2(loads):
    assert loads.sc_g2 == approx_ref(1.313)


def test_sc_q(loads):
    assert loads.sc_q == approx_ref(1.125)


def test_msd_elu(loads):
    assert loads.msd_elu(REF_PARAMS["vao_viga"]) == approx_ref(63.87)


def test_mru(section, loads, prestress):
    flexao = check_flexao(
        section,
        prestress,
        loads,
        REF_PARAMS["vao_viga"],
        REF_PARAMS["fck"],
    )
    assert flexao["MRU"] == approx_ref(52.43)


def test_vsd(loads):
    assert loads.vsd(REF_PARAMS["vao_viga"]) == approx_ref(26.59)


def test_vrd2(section, loads):
    cisalhamento = check_cisalhamento(
        section,
        loads,
        REF_PARAMS["vao_viga"],
        REF_PARAMS["fck"],
        yp=REF_PARAMS["yp"],
    )
    assert cisalhamento["VRd2"] == approx_ref(166.95)


def test_materials_reference_smoke():
    assert eci(50) > 0
    assert fctm(50) > 0


def test_run_case_completo():
    result = run_case(REF_PARAMS)
    assert result["status"] != "ERRO", result.get("erro_msg")
    assert result["Msd"] == approx_ref(63.87)
    assert result["MRU"] == approx_ref(52.32)
    assert result["Vsd"] == approx_ref(26.59)
    assert result["VRd2"] == approx_ref(166.95)
    assert result["ok"] is False


def test_run_case_calcula_taxas_armadura(section, loads):
    result = run_case(REF_PARAMS)
    cisalhamento = check_cisalhamento(
        section,
        loads,
        REF_PARAMS["vao_viga"],
        REF_PARAMS["fck"],
        yp=REF_PARAMS["yp"],
    )
    expected_passiva_longitudinal = (0 + REF_PARAMS["h"] / 10) * 0.785 * 10**4 / section.ac
    comprimento_estribo = (2 * (section.h + section.bw) + section.bf + section.hinf) / 100
    expected_passiva_transversal = (
        cisalhamento["Asw"] * comprimento_estribo * 0.782 / (section.ac / 10000)
    )
    expected_protendida = 6 * 0.990 * 0.782 * 10**4 / section.ac

    assert result["taxa_armadura_passiva"] == pytest.approx(
        expected_passiva_longitudinal + expected_passiva_transversal
    )
    assert result["taxa_armadura_protendida"] == pytest.approx(expected_protendida)


def test_run_case_somente_armadura_passiva_insuficiente():
    params = {
        **REF_PARAMS,
        "bf": 20,
        "n_cord_c1": 0,
        "n_cord_c2": 0,
        "n_cord_c3": 0,
        "n_barras": 6,
        "diam_barra_mm": 16.0,
    }
    result = run_case(params)
    assert result["status"] != "ERRO", result.get("erro_msg")
    assert result["ok_flexao"] is False
    assert result["ok"] is False
    assert result["MRU"] < result["Msd"]


def test_run_case_somente_armadura_passiva_suficiente():
    params = {
        **REF_PARAMS,
        "bf": 20,
        "n_cord_c1": 0,
        "n_cord_c2": 0,
        "n_cord_c3": 0,
        "n_barras": 12,
        "diam_barra_mm": 25.0,
    }
    result = run_case(params)
    assert result["status"] != "ERRO", result.get("erro_msg")
    assert result["ok_flexao"] is True
    assert result["ok"] is True
    assert result["MRU"] > result["Msd"]


def test_run_case_armadura_passiva_mais_protendida():
    params = {
        **REF_PARAMS,
        "bf": 20,
        "n_cord_c1": 6,
        "n_cord_c2": 0,
        "n_cord_c3": 0,
        "n_barras": 6,
        "diam_barra_mm": 16.0,
    }
    result = run_case(params)
    assert result["status"] != "ERRO", result.get("erro_msg")
    assert result["ok_flexao"] is True
    assert result["ok"] is True
    assert result["MRU"] > result["Msd"]


def test_camada_2_exige_camada_1_completa():
    params = {
        **REF_PARAMS,
        "bf": 20,
        "n_cord_c1": 6,
        "n_cord_c2": 3,
        "n_cord_c3": 0,
    }
    result = run_case(params)
    assert result["status"] == "ERRO"
    assert "minimo 2 barras" in result["erro_msg"]


def test_run_parametric_filtra_camadas_invalidas():
    fixed = {
        "h": 70,
        "bw": 40,
        "bf": 20,
        "cob": 2.5,
        "capa": 5,
        "hs": 0,
        "fck": 50,
        "fckj": 35,
        "caa": "II",
        "fat_pi": 0.95,
        "dpi": 0.20,
        "dps": 0.10,
        "rev": 200,
    }
    ranges = {
        "vao_viga": [9.61],
        "lp_types": ["LP20"],
        "vao_laje": [7.5],
        "acd": [300],
        "n_cord_c1": [4, 6],
        "n_cord_c2": [0, 3],
        "n_cord_c3": [0],
        "diam_mm": [12.7],
        "n_barras_c1": [2],
        "n_barras_c2": [0],
        "n_barras_c3": [0],
        "diam_barra_c1_mm": [20.0],
        "diam_barra_c2_mm": [12.5],
        "diam_barra_c3_mm": [12.5],
    }
    df = run_parametric(fixed, ranges)
    assert count_parametric(fixed, ranges) == len(df)
    assert ((df["n_cord_c1"] == 4) & (df["n_cord_c2"] == 0)).any()
    assert not ((df["n_cord_c1"] == 4) & (df["n_cord_c2"] == 3)).any()
    assert ((df["n_cord_c1"] == 6) & (df["n_cord_c2"] == 3)).any()


def test_run_parametric_descarta_combinacao_sem_armadura():
    fixed = {
        "h": 70,
        "bw": 40,
        "bf": 20,
        "cob": 2.5,
        "capa": 5,
        "hs": 0,
        "fck": 50,
        "fckj": 35,
        "caa": "II",
        "fat_pi": 0.95,
        "dpi": 0.20,
        "dps": 0.10,
        "rev": 200,
    }
    ranges = {
        "vao_viga": [9.61],
        "lp_types": ["LP20"],
        "vao_laje": [7.5],
        "acd": [300],
        "n_cord_c1": [0, 2],
        "n_cord_c2": [0],
        "n_cord_c3": [0],
        "diam_mm": [12.7],
        "n_barras_c1": [0, 3],
        "n_barras_c2": [0],
        "n_barras_c3": [0],
        "diam_barra_c1_mm": [20.0],
        "diam_barra_c2_mm": [12.5],
        "diam_barra_c3_mm": [12.5],
    }
    df = run_parametric(fixed, ranges)
    sem_cordoalha = df["n_cord_c1"].fillna(0) + df["n_cord_c2"].fillna(0) + df["n_cord_c3"].fillna(0)
    sem_passiva = df["n_barras_c1"].fillna(0) + df["n_barras_c2"].fillna(0) + df["n_barras_c3"].fillna(0)

    assert count_parametric(fixed, ranges) == len(df) == 2
    assert not ((sem_cordoalha == 0) & (sem_passiva == 0)).any()
    assert "ERRO" not in set(df["status"])


def test_lp32_capa5_gera_secoes_corretas():
    fixed = {
        "bw": 40,
        "bf": 20,
        "cob": 2.5,
        "capa": 5,
        "hs": 0,
        "fck": 50,
        "fckj": 35,
        "caa": "II",
        "fat_pi": 0.95,
        "dpi": 0.20,
        "dps": 0.10,
        "rev": 200,
    }
    ranges = {
        "vao_viga": [9.61],
        "lp_types": ["LP32"],
        "hinf_viga": [40, 50, 60],
        "vao_laje": [7.5],
        "acd": [300],
        "n_cord_c1": [6],
        "n_cord_c2": [0],
        "n_cord_c3": [0],
        "diam_mm": [12.7],
        "n_barras": [0],
        "diam_barra_mm": [12.5],
    }
    df = run_parametric(fixed, ranges)
    assert set(df["secao"]) == {"L77/40x40", "L87/50x40", "L97/60x40"}
    assert set(df["h"]) == {77, 87, 97}
    assert set(df["hsup"]) == {37}


def test_armadura_passiva_em_camadas_calcula_area():
    params = {
        **REF_PARAMS,
        "bf": 20,
        "n_cord_c1": 0,
        "n_cord_c2": 0,
        "n_cord_c3": 0,
        "n_barras_c1": 3,
        "n_barras_c2": 0,
        "n_barras_c3": 0,
        "diam_barra_c1_mm": 20.0,
        "diam_barra_c2_mm": 12.5,
        "diam_barra_c3_mm": 12.5,
    }
    result = run_case(params)
    assert result["status"] != "ERRO", result.get("erro_msg")
    assert result["n_barras"] == 3
    assert result["n_barras_c1"] == 3
    assert result["As_passiva"] == pytest.approx(9.426, rel=0.01)
    assert result["ys"] == pytest.approx(5.0)


def test_run_case_inclui_armaduras_superiores_da_tabela():
    params = {
        **REF_PARAMS,
        "bf": 20,
        "n_cord_c1": 2,
        "n_cord_c2": 0,
        "n_cord_c3": 0,
        "n_cord_sup": 2,
        "diam_cord_sup_mm": 9.5,
        "yp_cord_sup": -3.98,
        "n_barras_c1": 2,
        "n_barras_c2": 0,
        "n_barras_c3": 0,
        "diam_barra_c1_mm": 20.0,
        "diam_barra_c2_mm": 12.5,
        "diam_barra_c3_mm": 12.5,
        "n_barras_sup": 2,
        "diam_barra_sup_mm": 10.0,
        "ys_barra_sup": -3.80,
    }

    result = run_case(params)

    assert result["status"] != "ERRO", result.get("erro_msg")
    assert result["yp_cordoalha_eq"] == pytest.approx(4.1)
    assert result["yp_cord_sup"] == pytest.approx(REF_PARAMS["h"] - 3.98)
    assert result["yp_cordoalha_total_eq"] == pytest.approx(26.343, rel=0.01)
    assert result["n_cord"] == 2
    assert result["n_cord_sup"] == 2
    assert result["n_barras"] == 2
    assert result["n_barras_total"] == 4
    assert result["ys"] == pytest.approx(5.0)
    assert result["ys_barra_sup"] == pytest.approx(REF_PARAMS["h"] - 3.80)
    assert result["As_passiva"] == pytest.approx(6.284, rel=0.01)
    assert result["As_passiva_superior"] == pytest.approx(1.57, rel=0.01)


def test_cisalhamento_vpl_v04_usa_area_biela_para_vc0():
    section = SectionL(h=85, bw=40, bf=20, hsup=32, hinf=53, cob=2.5, capa=5)
    loads = Loads(
        section=section,
        lp_type="LP26,5",
        vao_laje=8.875,
        rev=200,
        acd=1200,
        lp_table=LP_TABLE,
    )

    result = check_cisalhamento(section, loads, 9.5246, 50, yp=8.935)

    assert result["Vsd"] == pytest.approx(59.44, rel=0.01)
    assert result["VRd2"] == pytest.approx(199.6, rel=0.01)
    assert result["Asw"] == pytest.approx(9.35, rel=0.01)


def test_vpl_v04_referencia_mantem_taxa_passiva_da_planilha():
    params = {
        "h": 85,
        "bw": 40,
        "bf": 20,
        "hsup": 32,
        "hinf": 53,
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
        "rev": 200,
        "lp_type": "LP26,5",
        "vao_laje": 8.875,
        "vao_viga": 9.5246,
        "acd": 1200,
        "n_cord_c1": 4,
        "n_cord_c2": 0,
        "n_cord_c3": 6,
        "diam_mm": 12.7,
        "n_cord_sup": 2,
        "diam_cord_sup_mm": 9.5,
        "yp_cord_sup": -3.975,
        "n_barras_c1": 4,
        "n_barras_c2": 9,
        "n_barras_c3": 0,
        "diam_barra_c1_mm": 12.5,
        "diam_barra_c2_mm": 12.5,
        "diam_barra_c3_mm": 12.5,
        "n_barras_sup": 2,
        "diam_barra_sup_mm": 10.0,
        "ys_barra_sup": -3.8,
        "psi0": 0.5,
        "psi1": 0.4,
        "psi2": 0.3,
    }

    result = run_case(params)

    assert result["status"] == "PASSA"
    assert result["MRU"] == pytest.approx(164.74, rel=0.02)
    assert result["taxa_armadura_passiva"] == pytest.approx(160, rel=0.01)
    assert result["taxa_armadura_protendida"] == pytest.approx(31, rel=0.01)


def test_camada_2_passiva_exige_camada_1_completa():
    params = {
        **REF_PARAMS,
        "bf": 20,
        "n_cord_c1": 0,
        "n_cord_c2": 0,
        "n_cord_c3": 0,
        "n_barras_c1": 7,
        "n_barras_c2": 1,
        "n_barras_c3": 0,
        "diam_barra_c1_mm": 20.0,
        "diam_barra_c2_mm": 12.5,
        "diam_barra_c3_mm": 12.5,
    }
    result = run_case(params)
    assert result["status"] == "ERRO"
    assert "CAM. 2" in result["erro_msg"]


def test_export_remove_colunas_ocultas():
    kept_columns = ["vao_viga", "secao", "status"]
    columns = kept_columns + INTERNAL_EXPORT_COLUMNS + EXPORT_HIDDEN_COLUMNS
    df = pd.DataFrame([{**{column: 1 for column in columns}, "n_cord": 1, "n_barras": 0}])

    export_df = _export_df(df)

    assert list(export_df.columns) == kept_columns + ["n_cord", "n_barras"]


def test_export_remove_linhas_sem_armadura():
    df = pd.DataFrame(
        [
            {"n_cord_c1": 0, "n_cord_c2": 0, "n_cord_c3": 0, "n_barras_c1": 0, "status": "ERRO"},
            {"n_cord_c1": 2, "n_cord_c2": 0, "n_cord_c3": 0, "n_barras_c1": 0, "status": "NAO PASSA"},
            {"n_cord_c1": 0, "n_cord_c2": 0, "n_cord_c3": 0, "n_barras_c1": 3, "status": "NAO PASSA"},
        ]
    )

    export_df = _export_df(df)

    assert len(export_df) == 2
    assert not (
        (export_df[["n_cord_c1", "n_cord_c2", "n_cord_c3"]].sum(axis=1) == 0)
        & (export_df["n_barras_c1"] == 0)
    ).any()
