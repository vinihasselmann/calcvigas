import sqlite3
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

import pandas as pd

from tools.import_exports_to_sqlite import build_database


def _write_results_xlsx(path, rows):
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name="Resultados", index=False)


def test_build_database_imports_vpt_pass_rows_and_creates_lookup_index():
    output_dir = Path("data") / "output" / "pytest_sqlite"
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = uuid4().hex
    vpt_path = output_dir / f"resultados_vpt_sqlite_test_{suffix}.xlsx"
    db_path = output_dir / f"precast_design_sqlite_test_{suffix}.db"
    try:
        _write_results_xlsx(
            vpt_path,
            [
                {
                    "secao": "T82/40x52",
                    "vao_viga": 9.1,
                    "lp_esq": "LP26,5",
                    "lp_dir": "LP26,5",
                    "vao_laje_esq": 9.6,
                    "vao_laje_dir": 6.6,
                    "acd_esq": 300,
                    "acd_dir": 300,
                    "taxa_armadura_passiva": 120.0,
                    "taxa_armadura_protendida": 25.0,
                    "status": "PASSA",
                },
                {
                    "secao": "T82/40x52",
                    "vao_viga": 10.0,
                    "lp_esq": "LP26,5",
                    "lp_dir": "LP26,5",
                    "vao_laje_esq": 9.6,
                    "vao_laje_dir": 6.6,
                    "acd_esq": 300,
                    "acd_dir": 300,
                    "taxa_armadura_passiva": 130.0,
                    "taxa_armadura_protendida": 30.0,
                    "status": "NAO PASSA",
                },
            ],
        )

        build_database(db_path, vigas_path=None, lajes_path=None, vpt_path=vpt_path)

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute("SELECT secao, vao_viga, status FROM viga_t_resultados").fetchall()
            indexes = conn.execute("PRAGMA index_list(viga_t_resultados)").fetchall()
            sources = conn.execute("SELECT value FROM metadata WHERE key = 'sources'").fetchone()[0]

        assert rows == [("T82/40x52", 9.1, "PASSA")]
        assert any(index[1] == "idx_viga_t_lookup" for index in indexes)
        assert vpt_path.name in sources
    finally:
        for path in (vpt_path, db_path):
            with suppress(PermissionError, FileNotFoundError):
                path.unlink()
