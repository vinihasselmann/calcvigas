"""Painel lateral de configuracao dos parametros."""

import numpy as np
import streamlit as st

from engine.runner import count_parametric


LP_TYPES = ["LP15", "LP20", "LP26,5", "LP32", "LP40", "LP50"]
DIAMETERS_MM = [9.5, 12.7, 15.2]
PASSIVE_DIAMETERS_MM = [8.0, 10.0, 12.5, 16.0, 20.0, 25.0]
HINF_VIGA_OPTIONS = [40, 50, 60]
FIXED_BW = 40
FIXED_BF = 20
FIXED_FAT_PI = 0.95
FIXED_DPI = 0.20
FIXED_DPS = 0.10
CAPA_OPTIONS = [5, 7, 10]
CAM1_OPTIONS = [0, 2, 4, 6, 8]
CAM2_OPTIONS = [0, 1, 3, 5, 7, 9]
CAM3_OPTIONS = [0, 2, 4, 6, 8]
PASSIVE_CAM1_OPTIONS = list(range(0, 9))
PASSIVE_CAM2_OPTIONS = list(range(0, 10))
PASSIVE_CAM3_OPTIONS = list(range(0, 9))
TOP_STRAND_COUNT_OPTIONS = list(range(0, 5))
TOP_PASSIVE_COUNT_OPTIONS = list(range(0, 5))
PSI_OPTIONS = {
    "Locais sem predominancia de pesos/equipamentos ou concentracao de pessoas": {
        "psi0": 0.5,
        "psi1": 0.4,
        "psi2": 0.3,
    },
    "Locais com predominancia de pesos/equipamentos ou concentracao de pessoas": {
        "psi0": 0.7,
        "psi1": 0.6,
        "psi2": 0.4,
    },
    "Bibliotecas, arquivos, oficinas e garagens": {
        "psi0": 0.8,
        "psi1": 0.7,
        "psi2": 0.6,
    },
}


def _range_values(start, stop, step, decimals=1):
    if step <= 0 or stop < start:
        return []
    values = np.arange(start, stop + step / 2, step)
    return np.round(values, decimals).tolist()


def _fixed_params(config):
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


def _ranges(config):
    return {
        "vao_viga": _range_values(
            config["vao_viga_min"],
            config["vao_viga_max"],
            config["vao_viga_step"],
        ),
        "lp_types": config.get("lp_types") or [],
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
        "diam_mm": config.get("diam_mm_values") or [config["diam_mm"]],
        "n_barras_c1": config.get("n_barras_c1_values", []),
        "n_barras_c2": config.get("n_barras_c2_values", []),
        "n_barras_c3": config.get("n_barras_c3_values", []),
        "diam_barra_c1_mm": config.get("diam_barra_c1_values", []),
        "diam_barra_c2_mm": config.get("diam_barra_c2_values", []),
        "diam_barra_c3_mm": config.get("diam_barra_c3_values", []),
    }


def render_sidebar() -> dict:
    """Renderiza a sidebar do Streamlit e retorna os parametros selecionados."""
    st.sidebar.title("Configuracao")
    total_metric = st.sidebar.empty()

    with st.sidebar.expander("Secao Transversal da Viga", expanded=True):
        bw = FIXED_BW
        bf = FIXED_BF
        st.caption(f"bw fixo = {bw} cm")
        st.caption(f"bf fixo = {bf} cm")
        hinf_viga_values = st.multiselect(
            "Familias de secao L - hinf (cm)",
            HINF_VIGA_OPTIONS,
            default=HINF_VIGA_OPTIONS,
        )
        st.caption("h e calculado por LP + capa + hinf, respeitando a tabela de secoes cadastradas.")
        cob = st.slider("Cobrimento cob (cm)", 2.0, 5.0, 2.5, step=0.5)

    with st.sidebar.expander("Material e Protensao", expanded=True):
        fck_options = [35, 40, 45, 50, 55, 60]
        fckj_options = [25, 30, 35, 40, 45]
        fck = st.selectbox("fck (MPa)", fck_options, index=fck_options.index(50))
        fckj = st.selectbox("fckj (MPa)", fckj_options, index=fckj_options.index(35))
        caa = st.radio("CAA", ["I", "II", "III", "IV"], index=1, horizontal=True)
        diam_mm = st.radio("Diametro nominal (mm)", DIAMETERS_MM, index=1, horizontal=True)
        fat_pi = FIXED_FAT_PI
        dpi = FIXED_DPI
        dps = FIXED_DPS
        st.caption(f"Fator de protensao inicial fixo = {fat_pi:.2f}")
        st.caption(f"dpi fixo = {dpi:.2f}")
        st.caption(f"dps fixo = {dps:.2f}")

    with st.sidebar.expander("Faixas do Estudo Parametrico", expanded=True):
        st.warning("Cada combinacao adicional multiplica o tempo de calculo")
        vao_viga_min = st.number_input("Vao da viga minimo (m)", value=3.0, step=0.1)
        vao_viga_max = st.number_input("Vao da viga maximo (m)", value=12.5, step=0.1)
        vao_viga_step = st.number_input("Passo do vao da viga (m)", value=0.5, step=0.1)

        vao_laje_min = st.number_input("Vao da laje minimo (m)", value=3.0, step=0.1)
        vao_laje_max = st.number_input("Vao da laje maximo (m)", value=12.0, step=0.1)
        vao_laje_step = st.number_input("Passo do vao da laje (m)", value=0.5, step=0.1)

        acd_min = st.number_input("Sobrecarga minima ACD (kgf/m2)", value=150, step=50)
        acd_max = st.number_input("Sobrecarga maxima ACD (kgf/m2)", value=3800, step=100)
        acd_step = st.number_input("Passo da sobrecarga ACD (kgf/m2)", value=100, step=50)
        psi_tipo = st.selectbox(
            "Tipo de ocupacao para psi0, psi1 e psi2",
            list(PSI_OPTIONS),
            index=1,
        )
        psi_values = PSI_OPTIONS[psi_tipo]
        st.caption(
            f"psi0 = {psi_values['psi0']:.1f} | "
            f"psi1 = {psi_values['psi1']:.1f} | "
            f"psi2 = {psi_values['psi2']:.1f}"
        )

        st.caption("CAM. 1: yp = 4,1 cm | maximo 8 cordoalhas pares")
        st.caption("CAM. 2: yp = 8,1 cm | maximo 9 cordoalhas impares")
        st.caption("CAM. 3: yp = 12,1 cm | maximo 8 cordoalhas pares")
        n_cord_c1_values = st.multiselect("CAM. 1 - N.C.", CAM1_OPTIONS, default=[4, 6, 8])
        n_cord_c2_values = st.multiselect("CAM. 2 - N.C.", CAM2_OPTIONS, default=[0])
        n_cord_c3_values = st.multiselect("CAM. 3 - N.C.", CAM3_OPTIONS, default=[0])

        st.caption("Barras passivas inferiores: CAM. 1 ys = 5,0 cm | CAM. 2 ys = 12,0 cm | CAM. 3 ys = 18,0 cm")
        st.caption("CAM. 2 passiva exige CAM. 1 completa com 8 barras; CAM. 3 exige CAM. 2 completa com 9 barras.")
        n_barras_c1_values = st.multiselect("Passiva CAM. 1 - N.B.", PASSIVE_CAM1_OPTIONS, default=[0, 3])
        diam_barra_c1_values = st.multiselect(
            "Passiva CAM. 1 - diametro (mm)",
            PASSIVE_DIAMETERS_MM,
            default=[20.0],
        )
        n_barras_c2_values = st.multiselect("Passiva CAM. 2 - N.B.", PASSIVE_CAM2_OPTIONS, default=[0])
        diam_barra_c2_values = st.multiselect(
            "Passiva CAM. 2 - diametro (mm)",
            PASSIVE_DIAMETERS_MM,
            default=[12.5],
        )
        n_barras_c3_values = st.multiselect("Passiva CAM. 3 - N.B.", PASSIVE_CAM3_OPTIONS, default=[0])
        diam_barra_c3_values = st.multiselect(
            "Passiva CAM. 3 - diametro (mm)",
            PASSIVE_DIAMETERS_MM,
            default=[12.5],
        )
        lp_types = st.multiselect(
            "Tipos de laje pre-moldada",
            LP_TYPES,
            default=["LP20", "LP26,5", "LP32"],
        )
        diam_mm_values = st.multiselect(
            "Diametros no estudo parametrico (mm)",
            DIAMETERS_MM,
            default=[diam_mm],
        )

        st.caption("Armadura superior: valores informados como distancia a partir da face superior.")
        n_cord_sup = st.selectbox("Superior - N.C.", TOP_STRAND_COUNT_OPTIONS, index=2)
        diam_cord_sup_mm = st.selectbox(
            "Superior - diametro cordoalha (mm)",
            DIAMETERS_MM,
            index=DIAMETERS_MM.index(9.5),
        )
        yp_cord_sup = -st.number_input("Superior - Yp cordoalha (cm)", value=3.98, step=0.01)
        n_barras_sup = st.selectbox("Superior - N.B.", TOP_PASSIVE_COUNT_OPTIONS, index=2)
        diam_barra_sup_mm = st.selectbox(
            "Superior - diametro barra (mm)",
            PASSIVE_DIAMETERS_MM,
            index=PASSIVE_DIAMETERS_MM.index(10.0),
        )
        ys_barra_sup = -st.number_input("Superior - Ys barra (cm)", value=3.80, step=0.01)

    with st.sidebar.expander("Cargas Fixas", expanded=True):
        rev = st.number_input("Revestimento (kgf/m2)", value=200, step=50)
        capa = st.selectbox("Capa de concreto moldada no local (cm)", CAPA_OPTIONS, index=0)
        st.caption("yp das cordoalhas e calculado automaticamente pelas camadas selecionadas.")

    config = {
        "bw": bw,
        "bf": bf,
        "hinf_viga_values": hinf_viga_values,
        "cob": cob,
        "fck": fck,
        "fckj": fckj,
        "caa": caa,
        "diam_mm": diam_mm,
        "diam_mm_values": diam_mm_values,
        "fat_pi": fat_pi,
        "dpi": dpi,
        "dps": dps,
        "n_cord_sup": n_cord_sup,
        "diam_cord_sup_mm": diam_cord_sup_mm,
        "yp_cord_sup": yp_cord_sup,
        "n_barras_sup": n_barras_sup,
        "diam_barra_sup_mm": diam_barra_sup_mm,
        "ys_barra_sup": ys_barra_sup,
        "vao_viga_min": vao_viga_min,
        "vao_viga_max": vao_viga_max,
        "vao_viga_step": vao_viga_step,
        "vao_laje_min": vao_laje_min,
        "vao_laje_max": vao_laje_max,
        "vao_laje_step": vao_laje_step,
        "acd_min": acd_min,
        "acd_max": acd_max,
        "acd_step": acd_step,
        "psi_tipo": psi_tipo,
        "psi0": psi_values["psi0"],
        "psi1": psi_values["psi1"],
        "psi2": psi_values["psi2"],
        "n_cord_c1_values": n_cord_c1_values,
        "n_cord_c2_values": n_cord_c2_values,
        "n_cord_c3_values": n_cord_c3_values,
        "n_barras_c1_values": n_barras_c1_values,
        "n_barras_c2_values": n_barras_c2_values,
        "n_barras_c3_values": n_barras_c3_values,
        "diam_barra_c1_values": diam_barra_c1_values,
        "diam_barra_c2_values": diam_barra_c2_values,
        "diam_barra_c3_values": diam_barra_c3_values,
        "lp_types": lp_types,
        "rev": rev,
        "capa": capa,
    }

    total_combinacoes = count_parametric(_fixed_params(config), _ranges(config))
    total_metric.metric("Total de combinacoes", f"{total_combinacoes:,}".replace(",", "."))
    config["total_combinacoes"] = total_combinacoes
    return config
