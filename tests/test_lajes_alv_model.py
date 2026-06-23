import pytest

from engine.lajes_alv_model import (
    EXPORT_COLUMNS,
    ITERATED_FIELDS,
    LAJE_ALV_SPECS,
    LajeAlvInputs,
    carga_capa,
    run_continuity_model,
    run_shear_filling_model,
    run_simple_model,
)


DEFAULT_INPUTS = LajeAlvInputs(sobrecarga=500, vao=12.5, capa=5, fck_capa=40)


def test_plan1_inputs_and_export_contract():
    assert ITERATED_FIELDS == ("sobrecarga", "vao", "capa", "fck_capa")
    assert EXPORT_COLUMNS == [
        "lp_type",
        "vao",
        "sobrecarga",
        "capa",
        "fck_capa",
        "peso_proprio",
        "carga_total",
        "momento_fletor",
        "forca_cortante",
        "cabos",
        "status",
    ]


def test_plan1_laje_specs_catalog():
    assert set(LAJE_ALV_SPECS) == {"LP15", "LP20", "LP26,5", "LP32", "LP40", "LP50"}
    assert LAJE_ALV_SPECS["LP15"].peso_proprio == 245
    assert LAJE_ALV_SPECS["LP50"].peso_proprio == 650
    assert LAJE_ALV_SPECS["LP20"].vao_max == 12
    assert LAJE_ALV_SPECS["LP32"].capacities[0].cabos == "11 x 12,7mm"


def test_carga_capa_matches_plan1_formula():
    assert carga_capa(5) == 150
    assert carga_capa(7) == 200


def test_lp15_checks_span_and_both_capacity_limits():
    spec = LAJE_ALV_SPECS["LP15"]

    beyond_catalog = run_simple_model(
        spec, LajeAlvInputs(sobrecarga=0, vao=9.6, capa=5, fck_capa=40)
    )
    excessive_shear = run_simple_model(
        spec, LajeAlvInputs(sobrecarga=12000, vao=1, capa=5, fck_capa=40)
    )

    assert beyond_catalog.status == "NAO PASSA"
    assert excessive_shear.status == "NAO PASSA"


def test_shear_filling_model_matches_lp265_spreadsheet_values():
    inputs = LajeAlvInputs(sobrecarga=3000, vao=5.8, capa=10, fck_capa=40)
    result = run_shear_filling_model(
        LAJE_ALV_SPECS["LP26,5"],
        inputs,
        "10 x 12,7mm",
        cortante=16080.5,
    )

    assert result.vrd_sem_preenchimento == pytest.approx(9241.964658917828)
    assert result.vrd_preenchimento_fabrica == pytest.approx(16867.62070609401)
    assert result.vrd_preenchimento_obra == pytest.approx(15292.524019449002)
    assert result.vrd_preenchimento == pytest.approx(15292.524019449002)
    assert result.comprimento_preenchimento_m == pytest.approx(1.3832795926207704)


@pytest.mark.parametrize(
    ("lp_type", "carga_total", "momento", "cortante", "cabos", "status"),
    [
        ("LP15", 895, 17480.46875, 5593.75, "NAO PASSA", "NAO PASSA"),
        ("LP20", 935, 18261.71875, 5843.75, "NAO PASSA", "NAO PASSA"),
        ("LP26,5", 1020, 19921.875, 6375, "10 x 12,7mm", "PASSA"),
        ("LP32", 1060, 20703.125, 6625, "9 x 12,7mm", "PASSA"),
        ("LP40", 1120, 21875, 7000, "11 x 12,7mm", "PASSA"),
        ("LP50", 1300, 25390.625, 8125, "11 x 12,7mm", "PASSA"),
    ],
)
def test_simple_model_matches_plan1_default_case(lp_type, carga_total, momento, cortante, cabos, status):
    result = run_simple_model(LAJE_ALV_SPECS[lp_type], DEFAULT_INPUTS)

    assert result.carga_total == pytest.approx(carga_total)
    assert result.momento_fletor == pytest.approx(momento)
    assert result.forca_cortante == pytest.approx(cortante)
    assert result.cabos == cabos
    assert result.status == status


@pytest.mark.parametrize(
    ("lp_type", "vs_max", "xv0", "ms_pos_max", "d", "sum_bw"),
    [
        ("LP15", 5593.75, 6.25, 17480.46875, 17, 24.32),
        ("LP20", 5843.75, 6.25, 18261.71875, 22, 22.24),
        ("LP26,5", 6375, 6.25, 19921.875, 28.5, 22.56),
        ("LP32", 6625, 6.25, 20703.125, 34, 22.8),
        ("LP40", 7000, 6.25, 21875, 42, 24.64),
        ("LP50", 8125, 6.25, 25390.625, 52, 32.64),
    ],
)
def test_continuity_model_matches_plan1_default_case(lp_type, vs_max, xv0, ms_pos_max, d, sum_bw):
    result = run_continuity_model(LAJE_ALV_SPECS[lp_type], DEFAULT_INPUTS)

    assert result.vs_max == pytest.approx(vs_max)
    assert result.xv0 == pytest.approx(xv0)
    assert result.ms_pos_max == pytest.approx(ms_pos_max)
    assert result.d == pytest.approx(d)
    assert result.sum_bw == pytest.approx(sum_bw)
    assert result.x == pytest.approx(0)
    assert result.as_negativa == pytest.approx(0)
    assert result.taxa_kg_m2 == pytest.approx(0)
