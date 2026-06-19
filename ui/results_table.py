"""Tabela de resultados com status PASSA ou NAO PASSA."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from .export import export_excel, export_excel_to_path


DISPLAY_MAX_ROWS = 5000
DOWNLOAD_MAX_ROWS = 100000
INTERNAL_EXPORT_COLUMNS = ["yp_cordoalha_eq", "yp_cordoalha_total_eq"]
EXPORT_HIDDEN_COLUMNS = [
    "h",
    "hinf",
    "ys",
    "psi_tipo",
    "psi0",
    "psi1",
    "psi2",
    "sigma_sup_ato",
    "sigma_inf_ato",
    "ok_inf_ato",
    "Msd_D",
    "sigma_sup_D",
    "sigma_inf_D",
    "ok_sup_D",
    "ok_inf_D",
    "Msd_F",
    "sigma_sup_F",
    "sigma_inf_F",
    "ok_sup_F",
    "ok_inf_F",
]
REQUIRED_RATE_COLUMNS = ["taxa_armadura_passiva", "taxa_armadura_protendida"]


VISIBLE_COLUMNS = [
    "vao_viga",
    "secao",
    "h",
    "hinf",
    "hsup",
    "lp_type",
    "vao_laje",
    "acd",
    "psi1",
    "psi2",
    "n_cord_c1",
    "n_cord_c2",
    "n_cord_c3",
    "n_cord_sup",
    "n_cord",
    "diam_mm",
    "diam_cord_sup_mm",
    "yp_cord_sup",
    "n_barras",
    "n_barras_total",
    "n_barras_c1",
    "n_barras_c2",
    "n_barras_c3",
    "n_barras_sup",
    "diam_barra_mm",
    "diam_barra_c1_mm",
    "diam_barra_c2_mm",
    "diam_barra_c3_mm",
    "diam_barra_sup_mm",
    "ys",
    "ys_barra_sup",
    "As_passiva",
    "As_passiva_superior",
    "taxa_armadura_passiva",
    "taxa_armadura_protendida",
    "Msd",
    "MRU",
    "ok_flexao",
    "Vsd",
    "VRd2",
    "ok_cisalhamento",
    "ok_els",
    "status",
]


def _column_config(df: pd.DataFrame) -> dict:
    config = {}
    for col in df.columns:
        if pd.api.types.is_float_dtype(df[col]):
            config[col] = st.column_config.NumberColumn(col, format="%.2f")
        elif col == "status":
            config[col] = st.column_config.TextColumn(col)
    return config


def _filtered_df(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df

    show = st.radio(
        "Mostrar",
        ["Todas", "Somente PASSA", "Somente NAO PASSA"],
        horizontal=True,
    )
    if show == "Somente PASSA":
        filtered = filtered[filtered["status"] == "PASSA"]
    elif show == "Somente NAO PASSA":
        filtered = filtered[filtered["status"] == "NAO PASSA"]

    filter_cols = st.columns(2)
    with filter_cols[0]:
        lp_options = sorted(filtered["lp_type"].dropna().unique()) if "lp_type" in filtered else []
        selected_lp = st.multiselect("Filtrar por laje", lp_options, default=lp_options)
    with filter_cols[1]:
        diam_options = sorted(filtered["diam_mm"].dropna().unique()) if "diam_mm" in filtered else []
        selected_diam = st.multiselect("Filtrar por diametro", diam_options, default=diam_options)

    if selected_lp and "lp_type" in filtered:
        filtered = filtered[filtered["lp_type"].isin(selected_lp)]
    if selected_diam and "diam_mm" in filtered:
        filtered = filtered[filtered["diam_mm"].isin(selected_diam)]

    return filtered


def _reinforcement_totals(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    prestress_cols = [
        col
        for col in ["n_cord_c1", "n_cord_c2", "n_cord_c3", "n_cord_sup", "n_cord"]
        if col in df.columns
    ]
    passive_cols = [
        col
        for col in [
            "n_barras_c1",
            "n_barras_c2",
            "n_barras_c3",
            "n_barras_sup",
            "n_barras",
            "n_barras_passiva",
        ]
        if col in df.columns
    ]

    prestress_total = (
        df[prestress_cols].fillna(0).sum(axis=1)
        if prestress_cols
        else pd.Series(0, index=df.index)
    )
    passive_total = (
        df[passive_cols].fillna(0).sum(axis=1)
        if passive_cols
        else pd.Series(0, index=df.index)
    )
    return prestress_total, passive_total


def _drop_unreinforced_rows(df: pd.DataFrame) -> pd.DataFrame:
    prestress_total, passive_total = _reinforcement_totals(df)
    return df[(prestress_total > 0) | (passive_total > 0)].copy()


def _output_path(suffix: str) -> Path:
    output_dir = Path("data") / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = output_dir / f"resultados_vpl_{timestamp}{suffix}"
    for idx in range(1, 100):
        if not path.exists():
            return path
        path = output_dir / f"resultados_vpl_{timestamp}_{idx}{suffix}"
    raise PermissionError("Nao foi possivel criar um nome de arquivo livre em data/output.")


def _export_df(df: pd.DataFrame) -> pd.DataFrame:
    hidden_columns = INTERNAL_EXPORT_COLUMNS + EXPORT_HIDDEN_COLUMNS
    exportable = _drop_unreinforced_rows(df)
    return exportable.drop(columns=[col for col in hidden_columns if col in exportable.columns]).copy()


def _save_local_xlsx(df: pd.DataFrame) -> Path:
    path = _output_path(".xlsx")
    return export_excel_to_path(_export_df(df), path)


def render_results(df: pd.DataFrame):
    """Renderiza metricas, filtros, tabela de resultados e exportacao."""
    if df is None or df.empty:
        st.info("Nenhum resultado para exibir.")
        return

    original_total = len(df)
    df = _drop_unreinforced_rows(df)
    removed_total = original_total - len(df)
    if removed_total:
        st.warning(
            f"{removed_total:,} combinacoes sem cordoalhas e sem barras passivas foram removidas "
            "dos resultados exibidos e da exportacao. Rode o estudo novamente para recalcular a base limpa."
        )

    missing_rate_columns = [col for col in REQUIRED_RATE_COLUMNS if col not in df.columns]
    if missing_rate_columns:
        st.warning(
            "Este resultado foi gerado antes da inclusao das taxas de armadura. "
            "Rode o estudo novamente para exportar as colunas taxa_armadura_passiva e "
            "taxa_armadura_protendida."
        )

    total = len(df)
    passes = int((df["status"] == "PASSA").sum()) if "status" in df else 0
    fails = int((df["status"] == "NAO PASSA").sum()) if "status" in df else 0
    approval_rate = passes / total * 100 if total else 0

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total de combinacoes", total)
    metric_cols[1].metric("Combinacoes que PASSAM", passes)
    metric_cols[2].metric("Combinacoes que NAO PASSAM", fails)
    metric_cols[3].metric("Taxa de aprovacao", f"{approval_rate:.1f}%")

    filtered = _filtered_df(df)
    visible_cols = [col for col in VISIBLE_COLUMNS if col in filtered.columns]
    table_df = filtered[visible_cols]
    display_df = table_df.head(DISPLAY_MAX_ROWS).copy()

    if len(table_df) > DISPLAY_MAX_ROWS:
        st.info(
            f"Mostrando as primeiras {DISPLAY_MAX_ROWS:,} de {len(table_df):,} linhas filtradas. "
            "Use os filtros para reduzir a tabela ou salve o resultado completo em XLSX local."
        )

    st.dataframe(
        display_df,
        column_config=_column_config(display_df),
        height=600,
        use_container_width=True,
        hide_index=True,
    )

    if len(filtered) <= DOWNLOAD_MAX_ROWS:
        excel_bytes = export_excel(_export_df(filtered))
        st.download_button(
            "Exportar para Excel",
            data=excel_bytes,
            file_name="resultados_vpl.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning(
            f"O resultado filtrado tem {len(filtered):,} linhas. "
            "Para evitar o limite de mensagem do Streamlit, salve o XLSX completo em arquivo local."
        )
        if st.button("Salvar XLSX completo local"):
            try:
                with st.spinner("Salvando XLSX local em abas de ate 500.000 linhas..."):
                    path = _save_local_xlsx(filtered)
                st.success(f"Arquivo salvo em: {path}")
            except PermissionError as exc:
                st.error(
                    "Nao foi possivel salvar o XLSX. "
                    f"Feche arquivos abertos em data/output e tente novamente. Detalhe: {exc}"
                )
            except Exception as exc:
                st.error(
                    "O XLSX nao foi finalizado. Nenhum arquivo final foi publicado; "
                    f"tente reduzir os filtros ou rode novamente. Detalhe: {exc}"
                )
