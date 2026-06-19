"""Cria um SQLite de pre-dimensionamento a partir dos XLSX exportados pelo site."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd


VIGA_TABLE = "viga_l_resultados"
VIGA_T_TABLE = "viga_t_resultados"
LAJE_TABLE = "laje_alv_resultados"


def _read_results(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Resultados")
    if "status" in df.columns:
        df = df[df["status"] == "PASSA"].copy()
    df["origem_arquivo"] = path.name
    df["importado_em"] = datetime.now().isoformat(timespec="seconds")
    return df


def _sqlite_type(series: pd.Series) -> str:
    if pd.api.types.is_integer_dtype(series):
        return "INTEGER"
    if pd.api.types.is_float_dtype(series):
        return "REAL"
    return "TEXT"


def _create_table(conn: sqlite3.Connection, table_name: str, df: pd.DataFrame):
    columns = []
    for col in df.columns:
        columns.append(f'"{col}" {_sqlite_type(df[col])}')
    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    conn.execute(f'CREATE TABLE "{table_name}" ({", ".join(columns)})')


def _write_table(conn: sqlite3.Connection, table_name: str, df: pd.DataFrame):
    if df.empty:
        return
    _create_table(conn, table_name, df)
    df.to_sql(table_name, conn, if_exists="append", index=False)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    result = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return result is not None


def _create_indexes(conn: sqlite3.Connection):
    if _table_exists(conn, VIGA_TABLE):
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_viga_l_lookup
            ON viga_l_resultados (secao, vao_viga, lp_type, vao_laje, acd, status)
            """
        )
    if _table_exists(conn, VIGA_T_TABLE):
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_viga_t_lookup
            ON viga_t_resultados (
                secao,
                vao_viga,
                lp_esq,
                lp_dir,
                vao_laje_esq,
                vao_laje_dir,
                acd_esq,
                acd_dir,
                status
            )
            """
        )
    if _table_exists(conn, LAJE_TABLE):
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_laje_alv_lookup
            ON laje_alv_resultados (lp_type, vao, sobrecarga, capa, fck_capa, continuidade_kgf, status)
            """
        )


def _write_metadata(conn: sqlite3.Connection, sources: list[Path]):
    conn.execute("DROP TABLE IF EXISTS metadata")
    conn.execute(
        """
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    rows = [
        ("created_at", datetime.now().isoformat(timespec="seconds")),
        ("sources", ";".join(str(path) for path in sources)),
    ]
    conn.executemany("INSERT INTO metadata (key, value) VALUES (?, ?)", rows)


def build_database(
    db_path: Path,
    vigas_path: Path | None,
    lajes_path: Path | None,
    vpt_path: Path | None = None,
):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    sources = [path for path in [vigas_path, lajes_path, vpt_path] if path is not None]

    with sqlite3.connect(db_path) as conn:
        if vigas_path is not None:
            _write_table(conn, VIGA_TABLE, _read_results(vigas_path))
        if vpt_path is not None:
            _write_table(conn, VIGA_T_TABLE, _read_results(vpt_path))
        if lajes_path is not None:
            _write_table(conn, LAJE_TABLE, _read_results(lajes_path))
        _create_indexes(conn)
        _write_metadata(conn, sources)
        conn.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="Caminho do SQLite de saida.")
    parser.add_argument("--vigas", type=Path, help="XLSX exportado pela pagina VPL.")
    parser.add_argument("--vpt", type=Path, help="XLSX exportado pela pagina VPT.")
    parser.add_argument("--lajes", type=Path, help="XLSX exportado pela pagina Lajes ALV.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.vigas is None and args.lajes is None and args.vpt is None:
        raise SystemExit("Informe ao menos --vigas, --vpt ou --lajes.")
    build_database(args.db, args.vigas, args.lajes, args.vpt)
    print(f"Banco criado em: {args.db.resolve()}")


if __name__ == "__main__":
    main()
