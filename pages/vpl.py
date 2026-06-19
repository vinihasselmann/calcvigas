"""Pagina Streamlit do estudo VPL."""

import time

import numpy as np
import streamlit as st

from engine.runner import run_parametric
from ui.results_table import render_results
from ui.sidebar import render_sidebar
from ui.theme import apply_brand_theme


apply_brand_theme()


def _range_values(start, stop, step, decimals=1):
    if step <= 0 or stop < start:
        return []
    values = np.arange(start, stop + step / 2, step)
    return np.round(values, decimals).tolist()


def _build_fixed_params(config):
    return {
        "bw": config["bw"],
        "bf": config["bf"],
        "cob": config["cob"],
        "capa": config["capa"],
        "hs": config.get("hs", 0),
        "fck": config["fck"],
        "fckj": config["fckj"],
        "caa": config["caa"],
        "fat_pi": config["fat_pi"],
        "dpi": config["dpi"],
        "dps": config["dps"],
        "n_cord_sup": config["n_cord_sup"],
        "diam_cord_sup_mm": config["diam_cord_sup_mm"],
        "yp_cord_sup": config["yp_cord_sup"],
        "n_barras_sup": config["n_barras_sup"],
        "diam_barra_sup_mm": config["diam_barra_sup_mm"],
        "ys_barra_sup": config["ys_barra_sup"],
        "rev": config["rev"],
        "psi_tipo": config["psi_tipo"],
        "psi0": config["psi0"],
        "psi1": config["psi1"],
        "psi2": config["psi2"],
    }


def _build_ranges(config):
    diam_values = config.get("diam_mm_values") or [config["diam_mm"]]
    lp_types = config.get("lp_types") or []

    return {
        "vao_viga": _range_values(
            config["vao_viga_min"],
            config["vao_viga_max"],
            config["vao_viga_step"],
        ),
        "lp_types": lp_types,
        "vao_laje": _range_values(
            config["vao_laje_min"],
            config["vao_laje_max"],
            config["vao_laje_step"],
        ),
        "acd": _range_values(config["acd_min"], config["acd_max"], config["acd_step"]),
        "hinf_viga": config.get("hinf_viga_values", []),
        "n_cord_c1": config.get("n_cord_c1_values", []),
        "n_cord_c2": config.get("n_cord_c2_values", []),
        "n_cord_c3": config.get("n_cord_c3_values", []),
        "diam_mm": diam_values,
        "n_barras_c1": config.get("n_barras_c1_values", []),
        "n_barras_c2": config.get("n_barras_c2_values", []),
        "n_barras_c3": config.get("n_barras_c3_values", []),
        "diam_barra_c1_mm": config.get("diam_barra_c1_values", []),
        "diam_barra_c2_mm": config.get("diam_barra_c2_values", []),
        "diam_barra_c3_mm": config.get("diam_barra_c3_values", []),
    }


st.title("VPL - Dimensionamento Parametrico de Vigas Pre-Moldadas Tipo L")
st.caption("Verifica ELU (flexao e cisalhamento) e ELS (tensoes) conforme NBR 6118 / NBR 7197")

config = render_sidebar()
ranges = _build_ranges(config)
fixed_params = _build_fixed_params(config)
n_total = config.get("total_combinacoes", 0)

if n_total > 50_000:
    st.warning(
        f"{n_total:,} combinacoes - isso pode demorar varios minutos. "
        "Reduza os intervalos ou aumente o step."
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
            df = run_parametric(fixed_params, ranges, progress_callback=update_progress)
        elapsed = time.perf_counter() - start

        st.session_state["df_results"] = df
        progress_bar.progress(1.0)
        progress_text.caption(f"Calculadas {len(df):,} de {len(df):,} combinacoes")

        n_pass = int((df["status"] == "PASSA").sum()) if "status" in df else 0
        taxa = n_pass / len(df) * 100 if len(df) else 0
        st.success(f"Concluido em {elapsed:.1f}s - {n_pass} combinacoes PASSAM ({taxa:.1f}%)")

if "df_results" in st.session_state:
    render_results(st.session_state["df_results"])

st.markdown("---")
st.caption("Engine: NBR 6118:2023 + NBR 7197:2019 | Desenvolvido para estudo parametrico de vigas VPL")
st.info("Para rodar localmente: `pip install -r requirements.txt` -> `streamlit run app.py`")
