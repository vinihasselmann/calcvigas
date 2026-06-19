"""Verificacao de ELU para flexao e cisalhamento."""

from . import materials
from . import section as section_module


def _status(ok):
    return "PASSA" if ok else "NAO PASSA"


def _validate_common(section, vao, fck):
    if not isinstance(section, section_module.SectionL):
        raise ValueError("O parametro 'section' deve ser uma instancia de SectionL.")
    if vao <= 0:
        raise ValueError("O parametro 'vao' deve ser maior que zero.")
    if fck <= 0:
        raise ValueError("O parametro 'fck' deve ser maior que zero.")


def _compressed_block(section, area_comprimida, bf_eq):
    if area_comprimida <= 0:
        raise ValueError("A area de concreto comprimido deve ser maior que zero.")
    if bf_eq <= 0:
        raise ValueError("A largura equivalente comprimida deve ser maior que zero.")

    area_capa = bf_eq * section.capa
    if area_comprimida <= area_capa:
        return area_comprimida / bf_eq

    area_mesa = bf_eq * max(section.hsup - section.capa, 0)
    if area_comprimida <= area_capa + area_mesa:
        return (area_comprimida - area_capa) / bf_eq

    if section.bw <= 0:
        raise ValueError("A largura da alma deve ser maior que zero.")
    return (area_comprimida - area_capa - area_mesa) / section.bw


def _bf_eq_for_flexao(section, loads, H39_laje=None, vao_laje=None, fck=None, fck_capa=None):
    if H39_laje is None:
        if section.capa > 0 and fck and fck_capa:
            return (section.bf + 2) * materials.ecs(fck_capa) / materials.ecs(fck)
        return section.bf

    vao_laje = vao_laje if vao_laje is not None else getattr(loads, "vao_laje", None)
    if vao_laje is None:
        raise ValueError("Informe 'vao_laje' para calcular bf_eq com H39_laje.")
    return section.bf_eq(H39_laje, vao_laje)


def _passive_forces(passive_rebar):
    if not passive_rebar:
        return [], 0

    if "layers" in passive_rebar:
        forces = []
        total_area = 0
        for layer in passive_rebar["layers"]:
            n_barras = int(layer.get("n_barras", 0))
            diam_barra_mm = layer.get("diam_barra_mm", 12.5)
            ys = layer.get("ys")
            if n_barras < 0:
                raise ValueError("O parametro 'n_barras' nao pode ser negativo.")
            if n_barras == 0:
                continue
            if diam_barra_mm not in materials.PASSIVE_BAR_AREA:
                raise ValueError(
                    f"Diametro de barra passiva '{diam_barra_mm}' invalido. "
                    f"Use um de: {sorted(materials.PASSIVE_BAR_AREA)}."
                )
            if ys is None or ys <= 0:
                raise ValueError("Informe 'ys' maior que zero para a armadura passiva.")
            area = n_barras * materials.PASSIVE_BAR_AREA[diam_barra_mm]
            if layer.get("posicao", "inferior") == "inferior":
                total_area += area
                forces.append((area * materials.fyd() * 10, ys))
        return forces, total_area

    n_barras = int(passive_rebar.get("n_barras", 0))
    diam_barra_mm = passive_rebar.get("diam_barra_mm", 12.5)
    ys = passive_rebar.get("ys")

    if n_barras < 0:
        raise ValueError("O parametro 'n_barras' nao pode ser negativo.")
    if n_barras == 0:
        return [], 0
    if diam_barra_mm not in materials.PASSIVE_BAR_AREA:
        raise ValueError(
            f"Diametro de barra passiva '{diam_barra_mm}' invalido. "
            f"Use um de: {sorted(materials.PASSIVE_BAR_AREA)}."
        )
    if ys is None or ys <= 0:
        raise ValueError("Informe 'ys' maior que zero para a armadura passiva.")

    area = n_barras * materials.PASSIVE_BAR_AREA[diam_barra_mm]
    force = area * materials.fyd() * 10
    return [(force, ys)], area


def _mru_from_forces(section, forces, fck, bf_eq):
    total_force = sum(force for force, _ in forces)
    if total_force <= 0:
        return 0, 0

    area_comprimida = total_force / (8.5 * fck / 1.3)
    y = _compressed_block(section, area_comprimida, bf_eq)
    h_eq = section.h
    mru = sum(force * (h_eq - y_pos - y / 2) / 100 / 1000 for force, y_pos in forces)
    return mru, y


def check_flexao(
    section,
    prestress,
    loads,
    vao,
    fck,
    H39_laje=None,
    vao_laje=None,
    passive_rebar=None,
    fck_capa=None,
):
    """Verifica ELU de flexao pela NBR 6118 em modelo simplificado de dominios 2 e 3."""
    _validate_common(section, vao, fck)

    Msd = loads.msd_elu(vao)
    bf_eq = _bf_eq_for_flexao(
        section,
        loads,
        H39_laje,
        vao_laje,
        fck=fck,
        fck_capa=fck_capa,
    )
    passive_forces, as_passiva = _passive_forces(passive_rebar)

    asp_inferior = getattr(prestress, "asp_inferior", prestress.asp_total)
    Rt_ap = asp_inferior * materials.fptd() * 10
    forces3 = []
    if Rt_ap > 0:
        forces3.append((Rt_ap, prestress.yp))
    forces3.extend(passive_forces)
    MRU3, y3 = _mru_from_forces(section, forces3, fck, bf_eq)

    epsilon_pdi = 5.2
    spd2 = materials.fpyd() + (materials.fptd() - materials.fpyd()) * epsilon_pdi / 25
    Rt_ap2 = spd2 * asp_inferior * 10
    forces2 = []
    if Rt_ap2 > 0:
        forces2.append((Rt_ap2, prestress.yp))
    forces2.extend(passive_forces)
    MRU2, y2 = _mru_from_forces(section, forces2, fck, bf_eq)

    if MRU3 >= MRU2:
        MRU = MRU3
        dominio = 3
        y_comp = y3
    else:
        MRU = MRU2
        dominio = 2
        y_comp = y2

    ok = MRU >= Msd
    return {
        "Msd": Msd,
        "MRU": MRU,
        "dominio": dominio,
        "y_comp": y_comp,
        "As_passiva": as_passiva,
        "ok": ok,
        "status": _status(ok),
    }


def check_cisalhamento(section, loads, vao, fck, yp=None):
    """Verifica ELU de cisalhamento pela NBR 6118 em modelo simplificado."""
    _validate_common(section, vao, fck)
    if yp is not None and (yp < 0 or yp >= section.h):
        raise ValueError("O parametro 'yp' deve estar entre zero e a altura total da secao.")

    Vsd = loads.vsd(vao)
    av2 = 1 - fck / 250

    altura_alma_util = section.hinf if yp is None else max(section.hinf - yp, 0)
    area_biela = section.bf * section.hsup + section.bw * altura_alma_util
    VRd2 = 0.27 * av2 * (fck * 10 / 1.3) * area_biela / 1000

    Vc0 = 0.6 * (materials.fcti(fck) * 10 / 1.3) * area_biela / 1000
    Vsw = max(0, Vsd - Vc0)

    prestress_yp = yp if yp is not None else section.cob
    d = section.h - prestress_yp
    if d <= 0:
        raise ValueError("Altura util invalida para cisalhamento: h - yp deve ser maior que zero.")

    Asw = Vsw * 100 / (0.9 * d * 5 / 1.15) if Vsw > 0 else 0
    Asw_min = 0.2 * materials.fctm(fck) / 500 * section.bw * 100
    Asw_final = max(Asw, Asw_min)
    ok_biela = VRd2 >= Vsd

    return {
        "Vsd": Vsd,
        "VRd2": VRd2,
        "Vc0": Vc0,
        "Vsw": Vsw,
        "Asw": Asw_final,
        "ok_biela": ok_biela,
        "ok": ok_biela,
        "status": _status(ok_biela),
    }
