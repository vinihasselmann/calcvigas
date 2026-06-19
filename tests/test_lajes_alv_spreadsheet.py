from pathlib import Path

import pytest
from openpyxl import load_workbook

from engine.lajes_alv_model import LAJE_ALV_SPECS, LajeAlvInputs, run_simple_model


SPREADSHEET_PATH = Path(__file__).resolve().parents[1] / "data" / "laje_alv_base.xlsx"
DEFAULT_INPUTS = LajeAlvInputs(sobrecarga=500, vao=12.5, capa=5, fck_capa=40)
PLAN1_RESULT_ROWS = {
    "LP15": 3,
    "LP20": 4,
    "LP26,5": 5,
    "LP32": 6,
    "LP40": 7,
    "LP50": 8,
}
PLAN1_MAX_SPAN_ROWS = {
    "LP15": 45,
    "LP20": 46,
    "LP26,5": 47,
    "LP32": 48,
    "LP40": 49,
    "LP50": 50,
}
PLAN1_CAPACITY_BLOCKS = {
    "LP15": ("B", "C", "D", range(13, 16)),
    "LP20": ("B", "C", "D", range(21, 25)),
    "LP26,5": ("F", "G", "H", range(13, 19)),
    "LP32": ("F", "G", "H", range(24, 30)),
    "LP40": ("J", "K", "L", range(13, 21)),
    "LP50": ("J", "K", "L", range(25, 33)),
}


@pytest.fixture(scope="module")
def plan1_values():
    wb = load_workbook(SPREADSHEET_PATH, data_only=True, read_only=True)
    return wb["Plan1"]


def test_spreadsheet_fixture_is_available():
    assert SPREADSHEET_PATH.exists()


@pytest.mark.parametrize("lp_type", PLAN1_RESULT_ROWS)
def test_simple_model_matches_cached_plan1_results(plan1_values, lp_type):
    row = PLAN1_RESULT_ROWS[lp_type]
    result = run_simple_model(LAJE_ALV_SPECS[lp_type], DEFAULT_INPUTS)

    assert result.peso_proprio == pytest.approx(plan1_values[f"C{row}"].value)
    assert result.sobrecarga == pytest.approx(plan1_values[f"D{row}"].value)
    assert result.carga_capa == pytest.approx(plan1_values[f"E{row}"].value)
    assert result.carga_total == pytest.approx(plan1_values[f"F{row}"].value)
    assert result.vao == pytest.approx(plan1_values[f"G{row}"].value)
    assert result.momento_fletor == pytest.approx(plan1_values[f"H{row}"].value)
    assert result.forca_cortante == pytest.approx(plan1_values[f"I{row}"].value)
    assert result.cabos == str(plan1_values[f"J{row}"].value).replace("NÃO", "NAO")


@pytest.mark.parametrize("lp_type", PLAN1_MAX_SPAN_ROWS)
def test_catalog_max_spans_match_plan1(plan1_values, lp_type):
    row = PLAN1_MAX_SPAN_ROWS[lp_type]
    assert LAJE_ALV_SPECS[lp_type].vao_max == pytest.approx(plan1_values[f"C{row}"].value)


@pytest.mark.parametrize("lp_type", PLAN1_CAPACITY_BLOCKS)
def test_catalog_capacities_match_plan1_blocks(plan1_values, lp_type):
    cable_col, moment_col, shear_col, rows = PLAN1_CAPACITY_BLOCKS[lp_type]
    spreadsheet_options = [
        (
            plan1_values[f"{cable_col}{row}"].value,
            plan1_values[f"{moment_col}{row}"].value,
            plan1_values[f"{shear_col}{row}"].value,
        )
        for row in rows
        if plan1_values[f"{cable_col}{row}"].value is not None
    ]
    model_options = [
        (option.cabos, option.momento_max, option.cortante_max)
        for option in LAJE_ALV_SPECS[lp_type].capacities
    ]

    assert model_options == spreadsheet_options
