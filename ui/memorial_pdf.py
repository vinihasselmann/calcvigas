"""Geracao de memorial de calculo em PDF para o quadro estrutural."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
import math
import re
import unicodedata

import pandas as pd

from engine.materials import PASSIVE_BAR_AREA, STRAND_AREA
from engine.lajes_alv_model import LAJE_ALV_SPECS
from engine.vpt_model import VPT_PASSIVE_BAR_AREA


PAGE_W = 595
PAGE_H = 842
MARGIN = 42
LINE_H = 12


def export_memorial_pdf(df: pd.DataFrame) -> bytes:
    """Gera o memorial das vigas e lajes presentes nos resultados."""
    pdf = _Pdf()
    rows = _memorial_rows(df)
    if rows.empty:
        page = pdf.page()
        page.text(MARGIN, PAGE_H - MARGIN, "Memorial de calculo", 16, bold=True)
        page.text(MARGIN, PAGE_H - MARGIN - 24, "Nao ha elementos nos resultados filtrados.", 10)
        return pdf.render()

    for _, row in rows.iterrows():
        if _is_laje_row(row):
            _render_laje_page(pdf.page(), row)
        else:
            _render_beam_page(pdf.page(), row)
    return pdf.render()


def _memorial_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    if "tipo_elemento" in df:
        return df[df["tipo_elemento"].isin(["VPL", "VPT", "VR", "LAJE"])].copy()
    if "lp_type" in df:
        return df.copy()
    return pd.DataFrame()


def _is_laje_row(row: pd.Series) -> bool:
    return row.get("tipo_elemento") == "LAJE" or (
        not row.get("tipo_elemento") and row.get("lp_type") in LAJE_ALV_SPECS
    )


def _render_laje_page(page: "_Page", row: pd.Series):
    element_id = _first(row, "id_elemento", "lp_type") or "Laje"
    title = f"Memorial de calculo da laje - {_text(element_id)}"
    subtitle = (
        f"{_text(row.get('lp_type'))} | {_text(row.get('analise', 'sem continuidade'))} "
        f"| status {_text(row.get('status'))}"
    )
    page.text(MARGIN, PAGE_H - MARGIN, title, 15, bold=True)
    page.text(MARGIN, PAGE_H - MARGIN - 18, subtitle, 9)
    page.text(MARGIN, PAGE_H - MARGIN - 32, f"Gerado em {datetime.now():%d/%m/%Y %H:%M}", 8)

    y = PAGE_H - 92
    y = _section(page, "Dados da laje e carregamentos", _laje_load_items(row), y)
    y = _section(page, "Solicitacoes e capacidade", _laje_capacity_items(row), y)
    y = _section(page, "Continuidade e preenchimento", _laje_detail_items(row), y)

    chart_y = max(330, y - 10)
    _draw_laje_moment_chart(page, MARGIN, chart_y - 145, 240, 120, row)
    _draw_laje_shear_chart(page, MARGIN + 270, chart_y - 145, 240, 120, row)


def _laje_load_items(row: pd.Series) -> list[tuple[str, object]]:
    return [
        ("Tipo", row.get("lp_type")),
        ("Vao (m)", row.get("vao")),
        ("Capa (cm)", row.get("capa")),
        ("fck capa (MPa)", row.get("fck_capa")),
        ("Peso proprio (kgf/m2)", row.get("peso_proprio")),
        ("Sobrecarga (kgf/m2)", row.get("sobrecarga")),
        ("Carga da capa (kgf/m2)", row.get("carga_capa")),
        ("Carga total (kgf/m2)", row.get("carga_total")),
        ("Analise", row.get("analise")),
    ]


def _laje_capacity_items(row: pd.Series) -> list[tuple[str, object]]:
    option = _laje_capacity_option(row)
    return [
        ("Momento solicitante (kgf.m/m)", row.get("momento_fletor")),
        ("Momento resistente (kgf.m/m)", option.momento_max if option else None),
        ("Cortante solicitante (kgf/m)", row.get("forca_cortante")),
        ("Cortante resistente (kgf/m)", option.cortante_max if option else None),
        ("Cordoalhas", row.get("cabos")),
        ("Status", row.get("status")),
        ("LP sugerida", row.get("lp_sugerida")),
        ("Mensagem", row.get("mensagem")),
    ]


def _laje_detail_items(row: pd.Series) -> list[tuple[str, object]]:
    return [
        ("Momento continuidade (kgf.m/m)", row.get("continuidade_kgf")),
        ("Reacao maxima (kgf/m)", row.get("vs_max_continuidade")),
        ("Momento positivo max. (kgf.m/m)", row.get("ms_pos_max_continuidade")),
        ("As negativa (cm2/m)", row.get("as_negativa_continuidade")),
        ("Taxa continuidade (kg/m2)", row.get("taxa_continuidade_kg_m2")),
        ("Alveolos preenchidos", row.get("preenchimento_alveolos")),
        ("Comp. preenchimento (m)", row.get("comprimento_preenchimento_m")),
        ("VRd sem preenchimento (kgf/m)", row.get("VRd_sem_preenchimento")),
        ("VRd com preenchimento (kgf/m)", row.get("VRd_preenchimento")),
    ]


def _laje_capacity_option(row: pd.Series):
    spec = LAJE_ALV_SPECS.get(str(row.get("lp_type", "")))
    cables = row.get("cabos")
    if not spec or not cables:
        return None
    return next((option for option in spec.capacities if option.cabos == cables), None)


def _draw_laje_moment_chart(page, x, y, w, h, row):
    page.text(x, y + h + 12, "Diagrama de momento", 9, bold=True)
    _chart_box(page, x, y, w, h)
    moment = abs(_num(row.get("momento_fletor"), 0))
    points = []
    for idx in range(41):
        ratio = idx / 40
        value = 4 * ratio * (1 - ratio)
        points.append((x + ratio * w, y + h * 0.9 - value * h * 0.75))
    page.polyline(points, stroke=(0.1, 0.35, 0.8), width=1.2)
    page.text(x + 5, y + 5, f"Mmax={_fmt(moment)} kgf.m/m", 7)


def _draw_laje_shear_chart(page, x, y, w, h, row):
    page.text(x, y + h + 12, "Diagrama de cortante", 9, bold=True)
    _chart_box(page, x, y, w, h)
    shear = abs(_num(row.get("forca_cortante"), 0))
    mid = y + h / 2
    page.polyline([(x, mid + h * 0.35), (x + w, mid - h * 0.35)], stroke=(0.8, 0.2, 0.15), width=1.2)
    page.text(x + 5, y + 5, f"Vmax={_fmt(shear)} kgf/m", 7)


def _render_beam_page(page: "_Page", row: pd.Series):
    title = f"Memorial de calculo - {_text(row.get('id_elemento', 'Elemento'))}"
    subtitle = f"{_text(row.get('tipo_elemento'))} | secao {_text(row.get('secao'))} | status {_text(row.get('status'))}"
    page.text(MARGIN, PAGE_H - MARGIN, title, 15, bold=True)
    page.text(MARGIN, PAGE_H - MARGIN - 18, subtitle, 9)
    page.text(MARGIN, PAGE_H - MARGIN - 32, f"Gerado em {datetime.now():%d/%m/%Y %H:%M}", 8)

    y = PAGE_H - 92
    y = _section(page, "Dados geometricos e cargas", _geometry_and_load_items(row), y)
    y = _section(page, "Solicitacoes e verificacoes", _verification_items(row), y)
    y = _section(page, "Armaduras e taxas", _reinforcement_items(row), y)

    chart_y = max(300, y - 18)
    _draw_moment_chart(page, MARGIN, chart_y - 135, 240, 120, row)
    _draw_shear_chart(page, MARGIN + 270, chart_y - 135, 240, 120, row)
    _draw_stress_charts(page, MARGIN, chart_y - 290, 510, 130, row)


def _section(page: "_Page", title: str, items: list[tuple[str, object]], y: float) -> float:
    page.text(MARGIN, y, title, 11, bold=True)
    y -= 14
    col_w = 170
    for idx, (label, value) in enumerate(items):
        x = MARGIN + (idx % 3) * col_w
        if idx and idx % 3 == 0:
            y -= LINE_H
        page.text(x, y, f"{label}: {_fmt(value)}", 8)
    return y - 24


def _geometry_and_load_items(row: pd.Series) -> list[tuple[str, object]]:
    items = [
        ("Vao viga (m)", row.get("vao_viga")),
        ("Altura h (cm)", row.get("h")),
        ("Largura bw (cm)", row.get("bw")),
        ("Capa (cm)", row.get("capa")),
        ("Volume (m3)", row.get("volume_m3")),
        ("Peso proprio (kN)", row.get("peso_proprio")),
    ]
    if row.get("tipo_elemento") == "VPT":
        items.extend(
            [
                ("Laje esq.", row.get("lp_esq")),
                ("Vao laje esq. (m)", row.get("vao_laje_esq")),
                ("Rev. esq. (kgf/m2)", row.get("rev_esq")),
                ("ACD esq. (kgf/m2)", row.get("acd_esq")),
                ("Laje dir.", row.get("lp_dir")),
                ("Vao laje dir. (m)", row.get("vao_laje_dir")),
                ("Rev. dir. (kgf/m2)", row.get("rev_dir")),
                ("ACD dir. (kgf/m2)", row.get("acd_dir")),
            ]
        )
    else:
        items.extend(
            [
                ("Laje", row.get("lp_type")),
                ("Vao laje (m)", row.get("vao_laje")),
                ("Sobrecarga ACD", row.get("acd")),
                ("Carga fechamento (kgf/m)", row.get("carga_fechamento_kgf_m")),
                ("Carga permanente (kgf/m2)", row.get("carga_permanente_kgf_m")),
                ("Carga variavel (kgf/m)", row.get("carga_variavel_kgf_m")),
            ]
        )
    return items


def _verification_items(row: pd.Series) -> list[tuple[str, object]]:
    return [
        ("Msd (tfm)", row.get("Msd")),
        ("MRU (tfm)", row.get("MRU")),
        ("MRU/Msd", row.get("MRU_MSD")),
        ("Vsd (tf)", row.get("Vsd")),
        ("VRd2 (tf)", row.get("VRd2")),
        ("Msd-D/QP (tfm)", _first(row, "Msd_D", "Msd_QP")),
        ("Msd-F/CF (tfm)", _first(row, "Msd_F", "Msd_CF")),
        ("sigma inf", _first(row, "sigma_inf_D", "sigma_inf_qp", "sigma_inf_F")),
        ("lim inf F", row.get("lim_inf_F")),
    ]


def _reinforcement_items(row: pd.Series) -> list[tuple[str, object]]:
    items = [
        ("Cordoalhas C1", _layer_text(row, "n_cord_c1", "diam_cord_c1_mm", STRAND_AREA)),
        ("Cordoalhas C2", _layer_text(row, "n_cord_c2", "diam_cord_c2_mm", STRAND_AREA)),
        ("Cordoalhas C3", _layer_text(row, "n_cord_c3", "diam_cord_c3_mm", STRAND_AREA)),
        ("Cordoalhas sup.", _layer_text(row, "n_cord_sup", "diam_cord_sup_mm", STRAND_AREA)),
        ("Barras C1", _layer_text(row, "n_barras_c1", "diam_barra_c1_mm", _bar_area_map(row))),
        ("Barras C2", _layer_text(row, "n_barras_c2", "diam_barra_c2_mm", _bar_area_map(row))),
        ("Barras C3", _layer_text(row, "n_barras_c3", "diam_barra_c3_mm", _bar_area_map(row))),
        ("Barras sup.", _layer_text(row, "n_barras_sup", "diam_barra_sup_mm", PASSIVE_BAR_AREA)),
        ("As passiva (cm2)", row.get("As_passiva")),
        ("Asw adotada (cm2/m)", row.get("Asw")),
        ("Asw calculada (cm2/m)", row.get("Asw_calculada")),
        ("Asw minima (cm2/m)", row.get("Asw_minima")),
        ("Taxa CA longitudinal", row.get("taxa_armadura_passiva_longitudinal")),
        ("Taxa CA transversal", row.get("taxa_armadura_passiva_transversal")),
        ("Taxa passiva", row.get("taxa_armadura_passiva")),
        ("Taxa protendida", row.get("taxa_armadura_protendida")),
    ]
    return items


def _bar_area_map(row: pd.Series) -> dict:
    return VPT_PASSIVE_BAR_AREA if row.get("tipo_elemento") == "VPT" else PASSIVE_BAR_AREA


def _layer_text(row: pd.Series, n_key: str, d_key: str, area_map: dict) -> str:
    n = _num(row.get(n_key), 0)
    d = _num(row.get(d_key), 0)
    area = n * area_map.get(float(d), 0) if n and d else 0
    if not n:
        return "0"
    return f"{int(n)} x {d:g} mm | As={area:.2f} cm2"


def _draw_moment_chart(page: "_Page", x: float, y: float, w: float, h: float, row: pd.Series):
    page.text(x, y + h + 12, "Momento solicitante", 9, bold=True)
    _chart_box(page, x, y, w, h)
    m = abs(_num(row.get("Msd"), 0))
    pts = []
    for i in range(41):
        t = i / 40
        value = 4 * m * t * (1 - t)
        pts.append((x + t * w, y + h - (value / m if m else 0) * (h * 0.78) - h * 0.1))
    page.polyline(pts, stroke=(0.1, 0.35, 0.8), width=1.2)
    page.text(x + 5, y + 5, f"Msd={_fmt(m)} tfm", 7)


def _draw_shear_chart(page: "_Page", x: float, y: float, w: float, h: float, row: pd.Series):
    page.text(x, y + h + 12, "Cortante", 9, bold=True)
    _chart_box(page, x, y, w, h)
    v = abs(_num(row.get("Vsd"), 0))
    mid = y + h / 2
    pts = [(x, mid - h * 0.35), (x + w, mid + h * 0.35)]
    page.polyline(pts, stroke=(0.8, 0.2, 0.15), width=1.2)
    page.text(x + 5, y + 5, f"Vsd={_fmt(v)} tf | VRd2={_fmt(row.get('VRd2'))} tf", 7)


def _draw_stress_charts(page: "_Page", x: float, y: float, w: float, h: float, row: pd.Series):
    page.text(x, y + h + 12, "Tensoes de servico", 9, bold=True)
    gap = 18
    each_w = (w - gap) / 2
    _draw_stress_chart(
        page, x, y, each_w, h, "ELS-D / CQP",
        _first(row, "sigma_sup_D", "sigma_sup_qp"),
        _first(row, "sigma_inf_D", "sigma_inf_qp"),
        row,
    )
    _draw_stress_chart(
        page, x + each_w + gap, y, each_w, h, "ELS-F / CF",
        _first(row, "sigma_sup_F", "sigma_sup_freq", "sigma_sup_qp"),
        _first(row, "sigma_inf_F", "sigma_inf_freq", "sigma_inf_qp"),
        row,
    )


def _draw_stress_chart(
    page: "_Page",
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    sup,
    inf,
    row: pd.Series,
):
    fails = row.get("ok") is False or row.get("ok_els") is False or row.get("ok_inf_F") is False
    page.text(x, y + h - 10, title, 8, bold=True, color=(0.75, 0.08, 0.08) if fails else None)
    plot_y = y + 16
    plot_h = h - 34
    _chart_box(page, x, plot_y, w, plot_h)

    sup_available = sup is not None and not (isinstance(sup, float) and math.isnan(sup))
    sup_v = _num(sup, 0)
    inf_v = _num(inf, 0)
    lim_inf_v = _num(_first(row, "lim_inf_F", "lim_inf_D", "lim_inf_qp"), 0)

    # VPT/VR: sigma_sup nao e calculado; mostra apenas fibra inferior
    if not sup_available:
        _draw_single_fiber_chart(page, x, plot_y, w, plot_h, inf_v, lim_inf_v)
        page.text(x + 2, y + 3, f"inf={_fmt(inf_v)}  |  sup: n/d", 6)
        return

    h_viga = _num(row.get("h"), 0)
    hs = _num(row.get("hs"), 0)
    capa = _num(row.get("capa"), 0)
    h_total = h_viga + hs + capa

    # Auto-scale: sempre inclui zero, ajusta ao range real dos dados
    data_min = min(inf_v, sup_v, lim_inf_v if lim_inf_v != 0 else inf_v)
    data_max = max(inf_v, sup_v, 0)
    span = max(data_max - data_min, 20.0)
    scale_min = min(data_min - span * 0.1, 0)
    scale_max = max(data_max + span * 0.1, 0)
    _sr = scale_max - scale_min

    PAD = 4  # margem interna vertical

    def sx(value):
        return x + (value - scale_min) / _sr * w

    def sy(height_cm):
        frac = height_cm / h_total if h_total > 0 else 0
        return plot_y + PAD + frac * (plot_h - 2 * PAD)

    zero_x = sx(0)

    # Eixo zero: linha cinza com label "0" abaixo do grafico
    page.line(zero_x, plot_y, zero_x, plot_y + plot_h, stroke=(0.45, 0.45, 0.45), width=0.7)
    page.text(zero_x - 3, plot_y - 9, "0", 5)

    if h_total > 0 and h_viga > 0:
        hinf = _num(row.get("hinf"), 0)
        split_h = h_viga if hs > 0 else (hinf if 0 < hinf < h_viga else h_viga)
        sigma_at_split = inf_v + (sup_v - inf_v) * split_h / h_total

        y_bot = sy(0)
        y_spl = sy(split_h)
        y_top = sy(h_total)

        # Bloco preenchido: Viga Pre (azul claro)
        page.polygon(
            [(zero_x, y_bot), (sx(inf_v), y_bot),
             (sx(sigma_at_split), y_spl), (zero_x, y_spl)],
            fill=(0.63, 0.78, 0.94),
            stroke=(0.08, 0.28, 0.72), width=0.8,
        )
        # Bloco preenchido: In-Loco (vermelho claro)
        if split_h < h_total:
            page.polygon(
                [(zero_x, y_spl), (sx(sigma_at_split), y_spl),
                 (sx(sup_v), y_top), (zero_x, y_top)],
                fill=(0.95, 0.67, 0.63),
                stroke=(0.72, 0.08, 0.08), width=0.8,
            )

        # Separador Viga Pre / In-Loco
        page.line(x + 1, y_spl, x + w - 1, y_spl, stroke=(0.45, 0.45, 0.45), width=0.6)

        # Valor da tensao nas fibras extremas (abaixo do grafico)
        _axis_tick_label(page, sx(inf_v), plot_y, inf_v)
        _axis_tick_label(page, sx(sup_v), plot_y, sup_v)

        # Marcador do limite de tracao (fibra inf): linha vermelha no nivel da fibra inferior
        low = row.get("lim_inf_F_min")
        high = row.get("lim_inf_F_max")
        if _is_finite(low) and _is_finite(high):
            page.line(sx(_num(low)), y_bot, sx(_num(high)), y_bot,
                      stroke=(0.8, 0.08, 0.08), width=1.2)
        elif lim_inf_v != 0:
            lx = sx(lim_inf_v)
            page.line(lx - 3, y_bot, lx + 3, y_bot, stroke=(0.8, 0.08, 0.08), width=1.2)

    else:
        y_b = plot_y + PAD
        y_t = plot_y + plot_h - PAD
        page.polyline([(sx(inf_v), y_b), (sx(sup_v), y_t)], stroke=(0.08, 0.28, 0.72), width=1.0)
        _axis_tick_label(page, sx(inf_v), plot_y, inf_v)
        _axis_tick_label(page, sx(sup_v), plot_y, sup_v)

    # Texto com valores brutos abaixo do grafico (backup legivel)
    page.text(x + 2, y + 3, f"inf={_fmt(inf_v)}  sup={_fmt(sup_v)}", 6)


def _axis_tick_label(page, px, plot_y, value):
    """Tick + label numerico no eixo X (abaixo do grafico)."""
    page.line(px, plot_y, px, plot_y - 2, stroke=(0.3, 0.3, 0.3), width=0.5)
    label = _fmt_short(value)
    tw = len(label) * 3.2
    page.text(px - tw / 2, plot_y - 10, label, 5)


def _fmt_short(v) -> str:
    if v is None:
        return ""
    try:
        f = float(v)
        if f == 0:
            return "0"
        return f"{f:.0f}" if abs(f) >= 10 else f"{f:.1f}"
    except (TypeError, ValueError):
        return ""


def _draw_single_fiber_chart(page, x, plot_y, w, plot_h, inf_v, lim_inf_v):
    """Gráfico simplificado para vigas sem tensao na fibra superior (VPT/VR).
    Mostra barra horizontal representando a tensao na fibra inferior.
    """
    span = max(abs(inf_v), abs(lim_inf_v) if lim_inf_v else 20.0, 20.0)
    scale_min = -(span * 1.15)
    scale_max = span * 0.15
    _sr = scale_max - scale_min

    def sx(value):
        return x + (value - scale_min) / _sr * w

    zero_x = sx(0)
    page.line(zero_x, plot_y, zero_x, plot_y + plot_h, stroke=(0.45, 0.45, 0.45), width=0.7)
    page.text(zero_x - 3, plot_y - 9, "0", 5)

    # Barra da tensao na fibra inferior (posicionada no terco inferior do grafico)
    bar_y0 = plot_y + plot_h * 0.10
    bar_y1 = plot_y + plot_h * 0.42
    fill = (0.63, 0.78, 0.94) if inf_v <= 0 else (0.95, 0.67, 0.63)
    border = (0.08, 0.28, 0.72) if inf_v <= 0 else (0.72, 0.08, 0.08)
    page.polygon(
        [(zero_x, bar_y0), (sx(inf_v), bar_y0), (sx(inf_v), bar_y1), (zero_x, bar_y1)],
        fill=fill, stroke=border, width=0.8,
    )
    _axis_tick_label(page, sx(inf_v), plot_y, inf_v)

    if lim_inf_v != 0:
        lx = sx(lim_inf_v)
        page.line(lx, bar_y0 - 2, lx, bar_y1 + 2, stroke=(0.8, 0.08, 0.08), width=1.0)
        _axis_tick_label(page, lx, plot_y, lim_inf_v)

    page.text(x + 4, plot_y + plot_h - 12, "fibra sup.: n/d", 6)


def _chart_box(page: "_Page", x: float, y: float, w: float, h: float):
    page.rect(x, y, w, h, stroke=(0.7, 0.7, 0.7), width=0.6)
    for i in range(1, 4):
        page.line(x, y + h * i / 4, x + w, y + h * i / 4, stroke=(0.85, 0.85, 0.85), width=0.4)
        page.line(x + w * i / 4, y, x + w * i / 4, y + h, stroke=(0.85, 0.85, 0.85), width=0.4)


def _first(row: pd.Series, *keys: str):
    for key in keys:
        value = row.get(key)
        if value is not None and not pd.isna(value):
            return value
    return None


def _is_finite(value) -> bool:
    if value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _num(value, default=0.0) -> float:
    if value is None or pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fmt(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    if isinstance(value, str):
        return _text(value)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return _text(value)
    if math.isfinite(numeric):
        return f"{numeric:.3f}".rstrip("0").rstrip(".")
    return "-"


def _text(value) -> str:
    text = "" if value is None or pd.isna(value) else str(value)
    normalized = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return text.encode("latin-1", "ignore").decode("latin-1")


def _pdf_escape(text: str) -> str:
    return _text(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class _Page:
    def __init__(self):
        self.ops: list[str] = []

    def text(self, x: float, y: float, text: str, size: int = 9, bold: bool = False, color=None):
        font = "F2" if bold else "F1"
        if color and color != (0, 0, 0):
            r, g, b = color
            self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
        self.ops.append(f"BT /{font} {size} Tf {x:.2f} {y:.2f} Td ({_pdf_escape(text)}) Tj ET")
        if color and color != (0, 0, 0):
            self.ops.append("0 0 0 rg")

    def line(self, x1, y1, x2, y2, stroke=(0, 0, 0), width=1):
        self.ops.append(_stroke(stroke, width))
        self.ops.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def rect(self, x, y, w, h, stroke=(0, 0, 0), width=1):
        self.ops.append(_stroke(stroke, width))
        self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")

    def polyline(self, pts, stroke=(0, 0, 0), width=1):
        if len(pts) < 2:
            return
        self.ops.append(_stroke(stroke, width))
        first, rest = pts[0], pts[1:]
        path = [f"{first[0]:.2f} {first[1]:.2f} m"]
        path.extend(f"{x:.2f} {y:.2f} l" for x, y in rest)
        path.append("S")
        self.ops.append(" ".join(path))

    def polygon(self, pts, fill=(0.8, 0.8, 0.9), stroke=None, width=0.5):
        """Filled closed polygon; optional stroke border."""
        if len(pts) < 3:
            return
        r, g, b = fill
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
        if stroke:
            sr, sg, sb = stroke
            self.ops.append(f"{sr:.3f} {sg:.3f} {sb:.3f} RG {width:.2f} w")
        first, rest = pts[0], pts[1:]
        path = [f"{first[0]:.2f} {first[1]:.2f} m"]
        path.extend(f"{px:.2f} {py:.2f} l" for px, py in rest)
        path.append("h")
        self.ops.append(" ".join(path))
        self.ops.append("B" if stroke else "f")


def _stroke(color, width):
    r, g, b = color
    return f"{r:.3f} {g:.3f} {b:.3f} RG {width:.2f} w"


class _Pdf:
    def __init__(self):
        self.pages: list[_Page] = []

    def page(self) -> _Page:
        page = _Page()
        self.pages.append(page)
        return page

    def render(self) -> bytes:
        objects: list[bytes] = []
        n_pages = len(self.pages)
        font_regular_id = 3 + 2 * n_pages
        font_bold_id = font_regular_id + 1
        page_ids = [3 + i * 2 for i in range(n_pages)]

        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode("latin-1"))

        for idx, page in enumerate(self.pages):
            page_id = page_ids[idx]
            content_id = page_id + 1
            objects.append(
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                    f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
                    f"/Contents {content_id} 0 R >>"
                ).encode("latin-1")
            )
            stream = "\n".join(page.ops).encode("latin-1", "ignore")
            objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")

        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

        output = BytesIO()
        output.write(b"%PDF-1.4\n")
        offsets = [0]
        for obj_id, obj in enumerate(objects, start=1):
            offsets.append(output.tell())
            output.write(f"{obj_id} 0 obj\n".encode("ascii"))
            output.write(obj)
            output.write(b"\nendobj\n")
        xref = output.tell()
        output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        output.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.write(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref}\n%%EOF\n"
            ).encode("ascii")
        )
        return output.getvalue()
