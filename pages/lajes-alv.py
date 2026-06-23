"""Pagina Streamlit para estudo parametrico de lajes alveolares."""

import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from engine.lajes_alv import (
    ANALYSIS_CONTINUITY,
    ANALYSIS_SIMPLE,
    build_laje_ranges,
    count_laje_parametric,
    export_laje_df,
    run_laje_parametric,
)
from engine.lajes_alv_model import LAJE_ALV_SPECS
from ui.export import export_excel, export_excel_to_path
from ui.memorial_pdf import export_memorial_pdf
from ui.theme import apply_brand_theme


apply_brand_theme()


DISPLAY_MAX_ROWS = 5000
DOWNLOAD_MAX_ROWS = 100000
MEMORIAL_MAX_ROWS = 500
LAJE_TYPES = list(LAJE_ALV_SPECS)
CAPA_OPTIONS = [5, 7, 10]
FCK_CAPA_OPTIONS = [30, 35, 40, 45, 50]
ANALYSIS_OPTIONS = [ANALYSIS_SIMPLE, ANALYSIS_CONTINUITY]

VISIBLE_COLUMNS = [
    "analise",
    "continuidade_kgf",
    "lp_type",
    "vao",
    "sobrecarga",
    "capa",
    "fck_capa",
    "peso_proprio",
    "carga_capa",
    "carga_total",
    "momento_fletor",
    "forca_cortante",
    "cabos",
    "vs_max_continuidade",
    "ms_pos_max_continuidade",
    "as_negativa_continuidade",
    "taxa_continuidade_kg_m2",
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


def _render_sidebar() -> dict:
    st.sidebar.title("Configuracao")

    with st.sidebar.expander("Faixas do Estudo", expanded=True):
        sobrecarga_min = st.number_input("Sobrecarga minima (kgf/m2)", value=150, step=50)
        sobrecarga_max = st.number_input("Sobrecarga maxima (kgf/m2)", value=1000, step=50)
        sobrecarga_step = st.number_input("Passo da sobrecarga (kgf/m2)", value=50, step=50)

        vao_min = st.number_input("Vao minimo (m)", value=3.0, step=0.1)
        vao_max = st.number_input("Vao maximo (m)", value=17.0, step=0.1)
        vao_step = st.number_input("Passo do vao (m)", value=0.5, step=0.1)

        continuidade_min = st.number_input("Continuidade minima (kgf)", value=0, step=100)
        continuidade_max = st.number_input("Continuidade maxima (kgf)", value=0, step=100)
        continuidade_step = st.number_input("Passo da continuidade (kgf)", value=100, step=100)

    with st.sidebar.expander("Materiais e Geometria", expanded=True):
        capa_values = st.multiselect("Capa (cm)", CAPA_OPTIONS, default=[5])
        fck_capa_values = st.multiselect("fck capa (MPa)", FCK_CAPA_OPTIONS, default=[40])

    with st.sidebar.expander("Lajes e Analise", expanded=True):
        lp_types = st.multiselect("Tipos de laje alveolar", LAJE_TYPES, default=LAJE_TYPES)
        analysis_types = st.multiselect(
            "Modelo de analise",
            ANALYSIS_OPTIONS,
            default=ANALYSIS_OPTIONS,
        )

    config = {
        "sobrecarga_min": sobrecarga_min,
        "sobrecarga_max": sobrecarga_max,
        "sobrecarga_step": sobrecarga_step,
        "vao_min": vao_min,
        "vao_max": vao_max,
        "vao_step": vao_step,
        "continuidade_min": continuidade_min,
        "continuidade_max": continuidade_max,
        "continuidade_step": continuidade_step,
        "capa_values": capa_values,
        "fck_capa_values": fck_capa_values,
        "lp_types": lp_types,
        "analysis_types": analysis_types,
    }
    ranges = build_laje_ranges(config)
    total = count_laje_parametric(ranges)
    st.sidebar.metric("Total de combinacoes", f"{total:,}".replace(",", "."))
    config["ranges"] = ranges
    config["total_combinacoes"] = total
    return config


def _filtered_df(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df

    show = st.radio(
        "Mostrar",
        ["Todas", "Somente PASSA", "Somente NAO PASSA", "Somente ERRO"],
        horizontal=True,
    )
    if show == "Somente PASSA":
        filtered = filtered[filtered["status"] == "PASSA"]
    elif show == "Somente NAO PASSA":
        filtered = filtered[filtered["status"] == "NAO PASSA"]
    elif show == "Somente ERRO":
        filtered = filtered[filtered["status"] == "ERRO"]

    filter_cols = st.columns(3)
    with filter_cols[0]:
        lp_options = sorted(filtered["lp_type"].dropna().unique()) if "lp_type" in filtered else []
        selected_lp = st.multiselect("Filtrar por laje", lp_options, default=lp_options)
    with filter_cols[1]:
        analysis_options = sorted(filtered["analise"].dropna().unique()) if "analise" in filtered else []
        selected_analysis = st.multiselect(
            "Filtrar por analise",
            analysis_options,
            default=analysis_options,
        )
    with filter_cols[2]:
        cable_options = sorted(filtered["cabos"].dropna().unique()) if "cabos" in filtered else []
        selected_cables = st.multiselect("Filtrar por cabos", cable_options, default=cable_options)

    if selected_lp and "lp_type" in filtered:
        filtered = filtered[filtered["lp_type"].isin(selected_lp)]
    if selected_analysis and "analise" in filtered:
        filtered = filtered[filtered["analise"].isin(selected_analysis)]
    if selected_cables and "cabos" in filtered:
        filtered = filtered[filtered["cabos"].isin(selected_cables)]

    return filtered


def _output_path(suffix: str) -> Path:
    output_dir = Path("data") / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = output_dir / f"resultados_lajes_alv_{timestamp}{suffix}"
    for idx in range(1, 100):
        if not path.exists():
            return path
        path = output_dir / f"resultados_lajes_alv_{timestamp}_{idx}{suffix}"
    raise PermissionError("Nao foi possivel criar um nome de arquivo livre em data/output.")


def _export_df(df: pd.DataFrame) -> pd.DataFrame:
    return export_laje_df(df)


def _save_local_xlsx(df: pd.DataFrame) -> Path:
    path = _output_path(".xlsx")
    return export_excel_to_path(_export_df(df), path)


def _render_results(df: pd.DataFrame):
    if df is None or df.empty:
        st.info("Nenhum resultado para exibir.")
        return

    total = len(df)
    passes = int((df["status"] == "PASSA").sum()) if "status" in df else 0
    fails = int((df["status"] == "NAO PASSA").sum()) if "status" in df else 0
    errors = int((df["status"] == "ERRO").sum()) if "status" in df else 0
    approval_rate = passes / total * 100 if total else 0

    metric_cols = st.columns(5)
    metric_cols[0].metric("Total", total)
    metric_cols[1].metric("PASSA", passes)
    metric_cols[2].metric("NAO PASSA", fails)
    metric_cols[3].metric("ERRO", errors)
    metric_cols[4].metric("Taxa de aprovacao", f"{approval_rate:.1f}%")

    filtered = _filtered_df(df)
    visible_cols = [col for col in VISIBLE_COLUMNS if col in filtered.columns]
    table_df = filtered[visible_cols]
    display_df = table_df.head(DISPLAY_MAX_ROWS).copy()

    if len(table_df) > DISPLAY_MAX_ROWS:
        st.info(
            f"Mostrando as primeiras {DISPLAY_MAX_ROWS:,} de {len(table_df):,} linhas filtradas. "
            "Use os filtros para reduzir a tabela."
        )

    st.dataframe(
        display_df,
        column_config=_column_config(display_df),
        height=600,
        use_container_width=True,
        hide_index=True,
    )

    export_data = _export_df(filtered)
    if len(export_data) <= DOWNLOAD_MAX_ROWS:
        excel_bytes = export_excel(export_data)
        st.download_button(
            "Exportar para Excel",
            data=excel_bytes,
            file_name="resultados_lajes_alv.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning(
            f"O resultado filtrado tem {len(export_data):,} linhas. "
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

    if len(filtered) <= MEMORIAL_MAX_ROWS:
        st.download_button(
            "Baixar memorial de lajes PDF",
            data=export_memorial_pdf(filtered),
            file_name="memorial_lajes_alveolares.pdf",
            mime="application/pdf",
        )
    else:
        st.info(
            f"Para gerar o memorial PDF, reduza o resultado filtrado para ate "
            f"{MEMORIAL_MAX_ROWS} lajes."
        )


st.title("Lajes ALV - Estudo Parametrico de Lajes Alveolares")
st.caption("Itera sobrecarga, vao, capa, fck da capa e continuidade para lajes biapoiadas simples.")

config = _render_sidebar()
ranges = config["ranges"]
n_total = config["total_combinacoes"]

if n_total > 50_000:
    st.warning(
        f"{n_total:,} combinacoes - isso pode demorar varios minutos. "
        "Reduza os intervalos ou selecoes."
    )

run_button = st.button("Rodar Estudo Parametrico", type="primary", use_container_width=True)

if run_button:
    if n_total == 0:
        st.error("Nenhuma combinacao para calcular. Revise os intervalos e selecoes.")
    else:
        progress_bar = st.progress(0)
        progress_text = st.empty()

        def update_progress(done, total):
            progress = done / total if total else 1
            progress_bar.progress(progress)
            progress_text.caption(f"Calculadas {done:,} de {total:,} combinacoes")

        start = time.perf_counter()
        with st.spinner(f"Calculando {n_total:,} combinacoes..."):
            df = run_laje_parametric(ranges, progress_callback=update_progress)
        elapsed = time.perf_counter() - start

        st.session_state["df_lajes_alv_results"] = df
        progress_bar.progress(1.0)
        progress_text.caption(f"Calculadas {len(df):,} de {len(df):,} combinacoes")

        passes = int((df["status"] == "PASSA").sum()) if "status" in df else 0
        taxa = passes / len(df) * 100 if len(df) else 0
        st.success(f"Concluido em {elapsed:.1f}s - {passes} combinacoes PASSAM ({taxa:.1f}%)")

if "df_lajes_alv_results" in st.session_state:
    _render_results(st.session_state["df_lajes_alv_results"])

st.markdown("---")
st.caption("Base: planilha LAJE 00 - LP00 SC000 LMAX=00,00M | Aba Plan1")
