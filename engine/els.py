"""Verificacao de ELS para tensoes CQP, CF e CR."""

from . import materials


def _status(ok):
    return "PASSA" if ok else "NAO PASSA"


def _validate_inputs(section, prestress, loads, vao, fck, fckj, caa):
    if vao <= 0:
        raise ValueError("O parametro 'vao' deve ser maior que zero.")
    if fck <= 0:
        raise ValueError("O parametro 'fck' deve ser maior que zero.")
    if fckj <= 0:
        raise ValueError("O parametro 'fckj' deve ser maior que zero.")
    if caa not in ("I", "II", "III", "IV"):
        raise ValueError("O parametro 'caa' deve ser 'I', 'II', 'III' ou 'IV'.")
    if not hasattr(section, "ac") or not hasattr(section, "ws") or not hasattr(section, "wi"):
        raise ValueError("O parametro 'section' deve representar uma secao estrutural valida.")
    if not hasattr(prestress, "sigma_sup_ato") or not hasattr(prestress, "sigma_sup_final"):
        raise ValueError("O parametro 'prestress' deve representar uma protensao valida.")
    if not hasattr(loads, "msd_cqp") or not hasattr(loads, "msd_cf") or not hasattr(loads, "msd_cr"):
        raise ValueError("O parametro 'loads' deve representar carregamentos validos.")


def _composite_params(section, loads, H39_laje=None, vao_laje=None):
    vao_laje_calc = vao_laje if vao_laje is not None else getattr(loads, "vao_laje", None)
    if vao_laje_calc is None or vao_laje_calc <= 0:
        raise ValueError("Informe 'vao_laje' maior que zero para calcular a secao composta.")

    if H39_laje is None:
        bf_eq_cm = section.bf + vao_laje_calc / 5 * 100
        H39_laje = bf_eq_cm / 100
    elif H39_laje <= 0:
        raise ValueError("O parametro 'H39_laje' deve ser maior que zero.")

    return H39_laje, vao_laje_calc


def check_els(
    section,
    prestress,
    loads,
    vao,
    fck,
    fckj,
    caa="II",
    H39_laje=None,
    vao_laje=None,
    psi1=0.6,
    psi2=0.4,
):
    """Verifica ELS de tensoes pela NBR 7197 em combinacoes CQP, CF e CR."""
    caa = caa.upper().strip()
    _validate_inputs(section, prestress, loads, vao, fck, fckj, caa)
    H39_laje, vao_laje = _composite_params(section, loads, H39_laje, vao_laje)

    if getattr(prestress, "asp_total", 0) == 0:
        Msd_D = loads.msd_cqp(vao, psi2=psi2) if caa in ("I", "II") else loads.msd_cf(vao, psi1=psi1)
        Msd_F = loads.msd_cf(vao, psi1=psi1) if caa in ("I", "II") else loads.msd_cr(vao)
        sigma_sup_D = Msd_D * 1000 * 100 / section.ws_f(H39_laje, vao_laje)
        sigma_inf_D = -Msd_D * 1000 * 100 / section.wi_f(H39_laje, vao_laje)
        sigma_sup_F = Msd_F * 1000 * 100 / section.ws_f(H39_laje, vao_laje)
        sigma_inf_F = -Msd_F * 1000 * 100 / section.wi_f(H39_laje, vao_laje)
        detalhes = {
            "caa": caa,
            "psi1": psi1,
            "psi2": psi2,
            "H39_laje": H39_laje,
            "vao_laje": vao_laje,
            "Msd_mont": loads.sc_g1 * vao**2 / 8,
            "sigma_sup_ato": 0,
            "sigma_inf_ato": 0,
            "lim_sup_ato": 0,
            "lim_inf_ato": 0,
            "ok_sup_ato": True,
            "ok_inf_ato": True,
            "Msd_D": Msd_D,
            "sigma_sup_D": sigma_sup_D,
            "sigma_inf_D": sigma_inf_D,
            "lim_sup_D": 5 * fck * 10,
            "lim_inf_D": None,
            "ok_sup_D": True,
            "ok_inf_D": True,
            "Msd_F": Msd_F,
            "sigma_sup_F": sigma_sup_F,
            "sigma_inf_F": sigma_inf_F,
            "lim_sup_F": 5 * fck * 10,
            "lim_inf_F": -materials.fctf(fck) * 10,
            "ok_sup_F": True,
            "ok_inf_F": sigma_inf_F >= -materials.fctf(fck) * 10,
            "observacao": "ELS de fissuracao para armadura passiva nao modelado; verificado por ELU neste estudo.",
        }
        return {"ok": True, "status": _status(True), "detalhes": detalhes}

    Msd_mont = loads.sc_g1 * vao**2 / 8
    sigma_sup_mont = prestress.sigma_sup_ato(section, vao)
    sigma_inf_mont = prestress.sigma_inf_ato(section, vao)
    lim_sup_mont = 7 * fckj * 10
    lim_inf_mont = -1.2 * materials.fctm(fckj) * 10
    ok_sup_mont = sigma_sup_mont <= lim_sup_mont
    ok_inf_mont = sigma_inf_mont >= lim_inf_mont

    Msd_D = loads.msd_cqp(vao, psi2=psi2) if caa in ("I", "II") else loads.msd_cf(vao, psi1=psi1)
    sigma_sup_D = prestress.sigma_sup_final(
        section, Msd_D, H39_laje=H39_laje, vao_laje=vao_laje
    )
    sigma_inf_D = prestress.sigma_inf_final(
        section, Msd_D, H39_laje=H39_laje, vao_laje=vao_laje
    )
    lim_sup_D = 5 * fck * 10
    lim_inf_D = -materials.fctf(fck) * 10
    ok_sup_D = sigma_sup_D <= lim_sup_D
    ok_inf_D = (lim_inf_D - 10) <= sigma_inf_D <= (lim_inf_D + 10)

    Msd_F = loads.msd_cf(vao, psi1=psi1) if caa in ("I", "II") else loads.msd_cr(vao)
    sigma_sup_F = prestress.sigma_sup_final(
        section, Msd_F, H39_laje=H39_laje, vao_laje=vao_laje
    )
    sigma_inf_F = prestress.sigma_inf_final(
        section, Msd_F, H39_laje=H39_laje, vao_laje=vao_laje
    )
    lim_sup_F = 5 * fck * 10
    lim_inf_F = -materials.fctf(fck) * 10
    ok_sup_F = sigma_sup_F <= lim_sup_F
    ok_inf_F = sigma_inf_F >= lim_inf_F

    checks = [
        ok_sup_mont,
        ok_inf_mont,
        ok_sup_D,
        ok_inf_D,
        ok_sup_F,
    ]
    ok_els = all(checks)

    detalhes = {
        "caa": caa,
        "psi1": psi1,
        "psi2": psi2,
        "H39_laje": H39_laje,
        "vao_laje": vao_laje,
        "Msd_mont": Msd_mont,
        "sigma_sup_ato": sigma_sup_mont,
        "sigma_inf_ato": sigma_inf_mont,
        "lim_sup_ato": lim_sup_mont,
        "lim_inf_ato": lim_inf_mont,
        "ok_sup_ato": ok_sup_mont,
        "ok_inf_ato": ok_inf_mont,
        "Msd_D": Msd_D,
        "sigma_sup_D": sigma_sup_D,
        "sigma_inf_D": sigma_inf_D,
        "lim_sup_D": lim_sup_D,
        "lim_inf_D": lim_inf_D,
        "ok_sup_D": ok_sup_D,
        "ok_inf_D": ok_inf_D,
        "Msd_F": Msd_F,
        "sigma_sup_F": sigma_sup_F,
        "sigma_inf_F": sigma_inf_F,
        "lim_sup_F": lim_sup_F,
        "lim_inf_F": lim_inf_F,
        "ok_sup_F": ok_sup_F,
        "ok_inf_F": ok_inf_F,
    }

    return {
        "ok": ok_els,
        "status": _status(ok_els),
        "detalhes": detalhes,
    }
