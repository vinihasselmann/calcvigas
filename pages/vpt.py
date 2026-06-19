"""Pagina Streamlit para estudo parametrico de vigas T protendidas."""

import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from engine.vpt import (
    build_vpt_ranges,
    count_vpt_parametric,
    export_vpt_df,
    run_vpt_parametric,
)
from engine.vpt_model import LP_CAP, VPT_SECTION_CATALOG
from ui.export import export_excel, export_excel_to_path


DISPLAY_MAX_ROWS = 5000
DOWNLOAD_MAX_ROWS = 100000
LP_OPTIONS = list(LP_CAP)
SECTION_OPTIONS = list(VPT_SECTION_CATALOG)
CAPA_OPTIONS = [5, 7, 10]
FCK_OPTIONS = [35, 40, 45, 50]
FCKJ_OPTIONS = [25, 30, 35, 40]
FCK_CAPA_OPTIONS = [30, 35, 40, 45, 50]
CORD_COUNT_OPTIONS = list(range(0, 12))
BAR_COUNT_OPTIONS = list(range(0, 12))
CORD_DIAM_OPTIONS = [9.5, 12.7, 15.2]
BAR_DIAM_OPTIONS = [10.0, 12.5, 16.0, 20.0, 25.0, 32.0]

VISIBLE_COLUMNS = [
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
    "n_barras",
    "n_barras_c1",
    "n_barras_c2",
    "n_barras_c3",
    "Msd",
    "MRU",
    "MRU_MSD",
    "dominio",
    "Vsd",
    "VRd2",
    "taxa_armadura_passiva",
    "taxa_armadura_protendida",
    "status",
]


def _column_config(df: pd.DataFrame) -> dict:
    config = {}
    for col in df.columns:
        if pd.api.types.is_float_dtype(df[col]):
            config[col] = st.column_config.NumberColumn(col, format="%.3f")
        elif col == "status":
            config[col] = st.column_config.TextColumn(col)
    return config


def _render_sidebar() -> dict:
    st.sidebar.title("Configuracao")

    with st.sidebar.expander("Faixas do Estudo", expanded=True):
        secao_values = st.multiselect("Secoes VPT", SECTION_OPTIONS, default=SECTION_OPTIONS)

        vao_viga_min = st.number_input("Vao minimo da viga (m)", value=8.0, step=0.1)
        vao_viga_max = st.number_input("Vao maximo da viga (m)", value=10.0, step=0.1)
        vao_viga_step = st.number_input("Passo do vao da viga (m)", value=0.5, step=0.1)

        acd_esq_min = st.number_input("ACD esq. minima (kgf/m2)", value=300, step=50)
        acd_esq_max = st.number_input("ACD esq. maxima (kgf/m2)", value=300, step=50)
        acd_esq_step = st.number_input("Passo ACD esq. (kgf/m2)", value=50, step=50)

        acd_dir_min = st.number_input("ACD dir. minima (kgf/m2)", value=300, step=50)
        acd_dir_max = st.number_input("ACD dir. maxima (kgf/m2)", value=300, step=50)
        acd_dir_step = st.number_input("Passo ACD dir. (kgf/m2)", value=50, step=50)

    with st.sidebar.expander("Lajes Apoiadas", expanded=True):
        lp_esq_values = st.multiselect("Laje esquerda", LP_OPTIONS, default=["LP26,5"])
        lp_dir_values = st.multiselect("Laje direita", LP_OPTIONS, default=["LP26,5"])

        vao_laje_esq_min = st.number_input("Vao laje esq. minimo (m)", value=9.6, step=0.1)
        vao_laje_esq_max = st.number_input("Vao laje esq. maximo (m)", value=9.6, step=0.1)
        vao_laje_esq_step = st.number_input("Passo vao laje esq. (m)", value=0.5, step=0.1)

        vao_laje_dir_min = st.number_input("Vao laje dir. minimo (m)", value=6.6, step=0.1)
        vao_laje_dir_max = st.number_input("Vao laje dir. maximo (m)", value=6.6, step=0.1)
        vao_laje_dir_step = st.number_input("Passo vao laje dir. (m)", value=0.5, step=0.1)

    with st.sidebar.expander("Materiais", expanded=True):
        capa_values = st.multiselect("Capa (cm)", CAPA_OPTIONS, default=[5])
        fck_values = st.multiselect("fck viga (MPa)", FCK_OPTIONS, default=[50])
        fckj_values = st.multiselect("fckj (MPa)", FCKJ_OPTIONS, default=[35])
        fck_capa_values = st.multiselect("fck capa (MPa)", FCK_CAPA_OPTIONS, default=[40])

    with st.sidebar.expander("Cordoalhas", expanded=True):
        n_cord_c1_values = st.multiselect("N cordoalhas cam. 1", CORD_COUNT_OPTIONS, default=[4])
        n_cord_c2_values = st.multiselect("N cordoalhas cam. 2", CORD_COUNT_OPTIONS, default=[0])
        n_cord_c3_values = st.multiselect("N cordoalhas cam. 3", CORD_COUNT_OPTIONS, default=[0])
        diam_cord_c1_values = st.multiselect("Diam. cord. cam. 1 (mm)", CORD_DIAM_OPTIONS, default=[12.7])
        diam_cord_c2_values = st.multiselect("Diam. cord. cam. 2 (mm)", CORD_DIAM_OPTIONS, default=[12.7])
        diam_cord_c3_values = st.multiselect("Diam. cord. cam. 3 (mm)", CORD_DIAM_OPTIONS, default=[15.2])

    with st.sidebar.expander("Armadura Passiva", expanded=True):
        n_barras_c1_values = st.multiselect("N barras cam. 1", BAR_COUNT_OPTIONS, default=[2])
        n_barras_c2_values = st.multiselect("N barras cam. 2", BAR_COUNT_OPTIONS, default=[0])
        n_barras_c3_values = st.multiselect("N barras cam. 3", BAR_COUNT_OPTIONS, default=[0])
        diam_barra_c1_values = st.multiselect("Diam. barra cam. 1 (mm)", BAR_DIAM_OPTIONS, default=[25.0])
        diam_barra_c2_values = st.multiselect("Diam. barra cam. 2 (mm)", BAR_DIAM_OPTIONS, default=[20.0])
        diam_barra_c3_values = st.multiselect("Diam. barra cam. 3 (mm)", BAR_DIAM_OPTIONS, default=[32.0])

    config = {
        "vao_viga_min": vao_viga_min,
        "vao_viga_max": vao_viga_max,
        "vao_viga_step": vao_viga_step,
        "vao_laje_esq_min": vao_laje_esq_min,
        "vao_laje_esq_max": vao_laje_esq_max,
        "vao_laje_esq_step": vao_laje_esq_step,
        "vao_laje_dir_min": vao_laje_dir_min,
        "vao_laje_dir_max": vao_laje_dir_max,
        "vao_laje_dir_step": vao_laje_dir_step,
        "acd_esq_min": acd_esq_min,
        "acd_esq_max": acd_esq_max,
        "acd_esq_step": acd_esq_step,
        "acd_dir_min": acd_dir_min,
        "acd_dir_max": acd_dir_max,
        "acd_dir_step": acd_dir_step,
        "secao_values": secao_values,
        "lp_esq_values": lp_esq_values,
        "lp_dir_values": lp_dir_values,
        "capa_values": capa_values,
        "fck_values": fck_values,
        "fckj_values": fckj_values,
        "fck_capa_values": fck_capa_values,
        "n_cord_c1_values": n_cord_c1_values,
        "n_cord_c2_values": n_cord_c2_values,
        "n_cord_c3_values": n_cord_c3_values,
        "diam_cord_c1_values": diam_cord_c1_values,
        "diam_cord_c2_values": diam_cord_c2_values,
        "diam_cord_c3_values": diam_cord_c3_values,
        "n_barras_c1_values": n_barras_c1_values,
        "n_barras_c2_values": n_barras_c2_values,
        "n_barras_c3_values": n_barras_c3_values,
        "diam_barra_c1_values": diam_barra_c1_values,
        "diam_barra_c2_values": diam_barra_c2_values,
        "diam_barra_c3_values": diam_barra_c3_values,
    }
    ranges = build_vpt_ranges(config)
    total = count_vpt_parametric({}, ranges)
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

    cols = st.columns(3)
    with cols[0]:
        secao_options = sorted(filtered["secao"].dropna().unique()) if "secao" in filtered else []
        selected_secao = st.multiselect("Filtrar por secao", secao_options, default=secao_options)
    with cols[1]:
        lp_options = sorted(set(filtered["lp_esq"].dropna()) | set(filtered["lp_dir"].dropna())) if not filtered.empty else []
        selected_lp = st.multiselect("Filtrar por laje", lp_options, default=lp_options)
    with cols[2]:
        dominio_options = sorted(filtered["dominio"].dropna().unique()) if "dominio" in filtered else []
        selected_dominio = st.multiselect("Filtrar por dominio", dominio_options, default=dominio_options)

    if selected_secao:
        filtered = filtered[filtered["secao"].isin(selected_secao)]
    if selected_lp:
        filtered = filtered[filtered["lp_esq"].isin(selected_lp) | filtered["lp_dir"].isin(selected_lp)]
    if selected_dominio:
        filtered = filtered[filtered["dominio"].isin(selected_dominio)]
    return filtered


def _output_path(suffix: str) -> Path:
    output_dir = Path("data") / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = output_dir / f"resultados_vpt_{timestamp}{suffix}"
    for idx in range(1, 100):
        if not path.exists():
            return path
        path = output_dir / f"resultados_vpt_{timestamp}_{idx}{suffix}"
    raise PermissionError("Nao foi possivel criar um nome de arquivo livre em data/output.")


def _save_local_xlsx(df: pd.DataFrame) -> Path:
    return export_excel_to_path(export_vpt_df(df), _output_path(".xlsx"))


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
        st.info(f"Mostrando as primeiras {DISPLAY_MAX_ROWS:,} de {len(table_df):,} linhas filtradas.")

    st.dataframe(
        display_df,
        column_config=_column_config(display_df),
        height=600,
        use_container_width=True,
        hide_index=True,
    )

    export_data = export_vpt_df(filtered)
    if len(export_data) <= DOWNLOAD_MAX_ROWS:
        st.download_button(
            "Exportar para Excel",
            data=export_excel(export_data),
            file_name="resultados_vpt.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning(
            f"O resultado filtrado tem {len(export_data):,} linhas. "
            "Use o salvamento local para gerar o XLSX completo."
        )
        if st.button("Salvar XLSX completo local"):
            try:
                with st.spinner("Salvando XLSX local..."):
                    path = _save_local_xlsx(filtered)
                st.success(f"Arquivo salvo em: {path}")
            except Exception as exc:
                st.error(f"Nao foi possivel salvar o XLSX. Detalhe: {exc}")


st.title("VPT - Estudo Parametrico de Vigas T Protendidas")
st.caption("Itera geometria carregada por lajes, cordoalhas e barras conforme a planilha VIGA 00 - VPT 00X00.")

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
            df = run_vpt_parametric({}, ranges, progress_callback=update_progress)
        elapsed = time.perf_counter() - start

        st.session_state["df_vpt_results"] = df
        progress_bar.progress(1.0)
        progress_text.caption(f"Calculadas {len(df):,} de {len(df):,} combinacoes")

        passes = int((df["status"] == "PASSA").sum()) if "status" in df else 0
        taxa = passes / len(df) * 100 if len(df) else 0
        st.success(f"Concluido em {elapsed:.1f}s - {passes} combinacoes PASSAM ({taxa:.1f}%)")

if "df_vpt_results" in st.session_state:
    _render_results(st.session_state["df_vpt_results"])

st.markdown("---")
st.caption("Base: planilha VIGA 00 - VPT 00X00 | Aba Viga T Protendida")
