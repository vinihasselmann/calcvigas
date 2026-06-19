"""Aplicativo Streamlit para calculo de quadro estrutural importado."""

from io import BytesIO

import pandas as pd
import streamlit as st

from engine.structural_frame import (
    read_frame_table,
    run_frame_cases,
    sample_frame_table,
)
from ui.export import export_excel
from ui.memorial_pdf import export_memorial_pdf


DISPLAY_MAX_ROWS = 5000
VISIBLE_FIRST_COLUMNS = [
    "linha_origem",
    "id_elemento",
    "tipo_elemento",
    "nome_tipo",
    "secao",
    "secao_original",
    "secao_sugerida",
    "mensagem",
    "laje_psi",
    "psi_tipo",
    "psi0",
    "psi1",
    "psi2",
    "lp_type",
    "lp_esq",
    "lp_dir",
    "bw",
    "vao_viga",
    "carga_fechamento_kgf_m",
    "carga_permanente_kgf_m",
    "carga_variavel_kgf_m",
    "vao_laje",
    "vao_laje_esq",
    "vao_laje_dir",
    "vao",
    "acd",
    "acd_esq",
    "acd_dir",
    "sobrecarga",
    "Msd",
    "MRU",
    "MRU_MSD",
    "Msd_D",
    "sigma_inf_D",
    "Msd_F",
    "sigma_inf_F",
    "sigma_inf_p",
    "sigma_inf_m",
    "lim_inf_F",
    "lim_inf_F_min",
    "lim_inf_F_max",
    "regra_sigma_inf_F",
    "Vsd",
    "VRd2",
    "momento_fletor",
    "forca_cortante",
    "cabos",
    "preenchimento_alveolos",
    "comprimento_preenchimento_m",
    "VRd_preenchimento",
    "lp_sugerida",
    "taxa_armadura_passiva",
    "taxa_armadura_protendida",
    "status",
    "erro_msg",
]


st.set_page_config(
    page_title="TESTESVIGAS",
    page_icon="VPL",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _template_bytes() -> bytes:
    output = BytesIO()
    sample_frame_table().to_excel(output, index=False)
    return output.getvalue()


def _column_config(df: pd.DataFrame) -> dict:
    config = {}
    for column in df.columns:
        if pd.api.types.is_float_dtype(df[column]):
            config[column] = st.column_config.NumberColumn(column, format="%.3f")
        elif column == "status":
            config[column] = st.column_config.TextColumn(column)
    return config


def _ordered_columns(df: pd.DataFrame) -> list[str]:
    first = [column for column in VISIBLE_FIRST_COLUMNS if column in df.columns]
    rest = [column for column in df.columns if column not in first]
    return first + rest


def _render_summary(df: pd.DataFrame):
    total = len(df)
    counts = df["status"].value_counts() if "status" in df else pd.Series(dtype=int)
    passes = int(counts.get("PASSA", 0))
    fails = int(counts.get("NAO PASSA", 0))
    errors = int(counts.get("ERRO", 0))
    approval_rate = passes / total * 100 if total else 0

    cols = st.columns(5)
    cols[0].metric("Elementos", total)
    cols[1].metric("PASSA", passes)
    cols[2].metric("NAO PASSA", fails)
    cols[3].metric("ERRO", errors)
    cols[4].metric("Taxa de aprovacao", f"{approval_rate:.1f}%")


def _filter_results(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df
    cols = st.columns(3)
    with cols[0]:
        status_values = sorted(df["status"].dropna().unique()) if "status" in df else []
        selected_status = st.multiselect("Status", status_values, default=status_values)
    with cols[1]:
        type_values = sorted(df["tipo_elemento"].dropna().unique()) if "tipo_elemento" in df else []
        selected_types = st.multiselect("Tipo de elemento", type_values, default=type_values)
    with cols[2]:
        lp_values = sorted(
            set(df.get("lp_type", pd.Series(dtype=object)).dropna())
            | set(df.get("lp_esq", pd.Series(dtype=object)).dropna())
            | set(df.get("lp_dir", pd.Series(dtype=object)).dropna())
        )
        selected_lps = st.multiselect("Laje", lp_values, default=lp_values)

    if selected_status and "status" in filtered:
        filtered = filtered[filtered["status"].isin(selected_status)]
    if selected_types and "tipo_elemento" in filtered:
        filtered = filtered[filtered["tipo_elemento"].isin(selected_types)]
    if selected_lps:
        lp_mask = pd.Series(False, index=filtered.index)
        has_lp = pd.Series(False, index=filtered.index)
        for column in ("lp_type", "lp_esq", "lp_dir"):
            if column in filtered:
                has_lp = has_lp | filtered[column].notna()
                lp_mask = lp_mask | filtered[column].isin(selected_lps)
        filtered = filtered[lp_mask | ~has_lp]
    return filtered


def _render_results(df: pd.DataFrame):
    _render_summary(df)
    filtered = _filter_results(df)
    ordered = _ordered_columns(filtered)
    table = filtered[ordered]
    display = table.head(DISPLAY_MAX_ROWS).copy()

    if len(table) > DISPLAY_MAX_ROWS:
        st.info(f"Mostrando as primeiras {DISPLAY_MAX_ROWS:,} de {len(table):,} linhas filtradas.")

    st.dataframe(
        display,
        column_config=_column_config(display),
        height=620,
        use_container_width=True,
        hide_index=True,
    )

    export_cols = st.columns(2)
    with export_cols[0]:
        st.download_button(
            "Exportar resultados XLSX",
            data=export_excel(filtered),
            file_name="resultados_quadro_estrutural.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with export_cols[1]:
        st.download_button(
            "Baixar memorial PDF",
            data=export_memorial_pdf(filtered),
            file_name="memorial_quadro_estrutural.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


st.title("TESTESVIGAS - Quadro Estrutural")
st.caption("Importe uma tabela unica com VPL, VPT, VR e lajes alveolares. Cada linha e calculada individualmente.")

top_cols = st.columns([1, 1])
with top_cols[0]:
    uploaded = st.file_uploader(
        "Tabela do Revit (.xlsx, .xlsm, .xls, .csv ou .txt)",
        type=["xlsx", "xlsm", "xls", "csv", "txt"],
    )
with top_cols[1]:
    st.download_button(
        "Baixar modelo de tabela",
        data=_template_bytes(),
        file_name="modelo_quadro_estrutural.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.info(
    "Use uma coluna `tipo_elemento` com VPL, VPT, VR ou LAJE. "
    "Campos ausentes de materiais, revestimento e armaduras usam os padroes atuais do app."
)

if uploaded is None:
    st.dataframe(sample_frame_table(), use_container_width=True, hide_index=True)
else:
    try:
        input_df = read_frame_table(uploaded, uploaded.name)
    except Exception as exc:
        st.error(f"Nao foi possivel ler a tabela. Detalhe: {exc}")
        st.stop()

    st.subheader("Previa da tabela importada")
    st.dataframe(input_df.head(200), use_container_width=True, hide_index=True)

    if st.button("Calcular quadro estrutural", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        progress_text = st.empty()

        def update_progress(done, total):
            progress_bar.progress(done / total if total else 1)
            progress_text.caption(f"Calculados {done:,} de {total:,} elementos")

        with st.spinner("Calculando elementos..."):
            st.session_state["df_frame_results"] = run_frame_cases(input_df, progress_callback=update_progress)
        progress_bar.progress(1.0)
        progress_text.caption("Calculo concluido")

    if "df_frame_results" in st.session_state:
        st.subheader("Resultados")
        _render_results(st.session_state["df_frame_results"])
