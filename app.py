"""Aplicativo Streamlit para calculo de quadro estrutural importado."""

import base64
import hashlib
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from engine.structural_frame import (
    normalize_floor_table,
    read_frame_table,
    run_frame_cases,
    sample_beam_table,
    sample_floor_table,
)
from ui.export import export_excel
from ui.memorial_pdf import export_memorial_pdf
from ui.theme import apply_brand_theme


DISPLAY_MAX_ROWS = 5000
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "cassol_precalc_logo.png"
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

apply_brand_theme()


def _template_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    df.to_excel(output, index=False)
    return output.getvalue()


def _image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _upload_fingerprint(uploaded) -> tuple[str, int, str]:
    content = uploaded.getvalue()
    return uploaded.name, len(content), hashlib.sha256(content).hexdigest()


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


hero_cols = st.columns([0.95, 1.15], gap="large")
with hero_cols[0]:
    st.markdown(
        f'<img class="cassol-home-logo" src="{_image_data_uri(LOGO_PATH)}" alt="Cassol PreCalc">',
        unsafe_allow_html=True,
    )
with hero_cols[1]:
    st.markdown(
        '<p class="cassol-home-copy">Importe a tabela de vigas e, separadamente, a tabela de pisos '
        "estruturais. Cada elemento e calculado individualmente.</p>",
        unsafe_allow_html=True,
    )
    beams_uploaded = st.file_uploader(
        "Tabela de vigas do Revit (.xlsx, .xlsm, .xls, .csv ou .txt)",
        type=["xlsx", "xlsm", "xls", "csv", "txt"],
        key="beams_table_upload",
    )
    st.download_button(
        "Baixar modelo de vigas",
        data=_template_bytes(sample_beam_table()),
        file_name="modelo_vigas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    floors_uploaded = st.file_uploader(
        "Tabela de pisos do Revit (.xlsx, .xlsm, .xls, .csv ou .txt)",
        type=["xlsx", "xlsm", "xls", "csv", "txt"],
        key="floors_table_upload",
    )
    st.download_button(
        "Baixar modelo de pisos",
        data=_template_bytes(sample_floor_table()),
        file_name="modelo_pisos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.info(
    "A tabela de vigas deve conter VPL, VPT e VR, sem linhas de lajes. A tabela de pisos deve conter "
    "`Marca de tipo`, `Modelo`, `LAJE-Sobrecarga`, `LAJE-Vão` e `LAJE_Psi`. Nas vigas, use "
    "`LAJE_Marca_E` e `LAJE_Marca_D`."
)

upload_signature = (
    (_upload_fingerprint(beams_uploaded), _upload_fingerprint(floors_uploaded))
    if beams_uploaded is not None and floors_uploaded is not None
    else None
)
if st.session_state.get("frame_upload_signature") != upload_signature:
    st.session_state.pop("df_frame_results", None)
    st.session_state["frame_upload_signature"] = upload_signature

if beams_uploaded is None and floors_uploaded is None:
    preview_cols = st.columns(2)
    with preview_cols[0]:
        st.caption("Exemplo — vigas")
        st.dataframe(sample_beam_table(), use_container_width=True, hide_index=True)
    with preview_cols[1]:
        st.caption("Exemplo — pisos")
        st.dataframe(sample_floor_table(), use_container_width=True, hide_index=True)
elif beams_uploaded is None or floors_uploaded is None:
    missing = "tabela de vigas" if beams_uploaded is None else "tabela de pisos"
    st.warning(f"Envie tambem a {missing} para liberar o calculo.")
else:
    try:
        beams_df = read_frame_table(beams_uploaded, beams_uploaded.name)
        floors_df = read_frame_table(floors_uploaded, floors_uploaded.name)
        normalize_floor_table(floors_df)
    except Exception as exc:
        st.error(f"Nao foi possivel ler uma das tabelas. Detalhe: {exc}")
        st.stop()

    st.subheader("Previa das tabelas importadas")
    preview_cols = st.columns(2)
    with preview_cols[0]:
        st.caption(f"Vigas — {len(beams_df):,} linhas")
        st.dataframe(beams_df.head(200), use_container_width=True, hide_index=True)
    with preview_cols[1]:
        st.caption(f"Pisos — {len(floors_df):,} linhas")
        st.dataframe(floors_df.head(200), use_container_width=True, hide_index=True)

    if st.button("Calcular quadro estrutural", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        progress_text = st.empty()

        def update_progress(done, total):
            progress_bar.progress(done / total if total else 1)
            progress_text.caption(f"Calculados {done:,} de {total:,} elementos")

        try:
            with st.spinner("Calculando elementos..."):
                st.session_state["df_frame_results"] = run_frame_cases(
                    beams_df,
                    progress_callback=update_progress,
                    floor_df=floors_df,
                )
        except Exception as exc:
            st.session_state.pop("df_frame_results", None)
            st.error(f"Nao foi possivel calcular a tabela. Detalhe: {exc}")
            st.stop()
        progress_bar.progress(1.0)
        progress_text.caption("Calculo concluido")

    if "df_frame_results" in st.session_state:
        st.subheader("Resultados")
        _render_results(st.session_state["df_frame_results"])
