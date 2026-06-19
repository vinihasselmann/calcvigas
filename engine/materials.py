"""Propriedades do concreto e do aco."""

from math import log


STRAND_AREA = {9.5: 0.555, 12.7: 0.990, 15.2: 1.400}
PASSIVE_BAR_AREA = {
    6.3: 0.312,
    8.0: 0.503,
    10.0: 0.785,
    12.5: 1.227,
    16.0: 2.011,
    20.0: 3.142,
    25.0: 4.909,
}


def eci(fck):
    """Calcula Eci pela NBR 6118: 5600*fck^0.5 ate C50 e 21500*((fck/10)+1.25)^(1/3) de C50 a C90."""
    if fck <= 50:
        return 5600 * fck**0.5
    return 21500 * ((fck / 10) + 1.25) ** (1 / 3)


def ecs(fck):
    """Calcula Ecs pela NBR 6118: Ecs = Eci*(0.8 + 0.2*fck/80)."""
    return eci(fck) * (0.8 + 0.2 * fck / 80)


def fctm(fck):
    """Calcula fctm pela NBR 6118: 0.3*fck^(2/3) ate C50 e 2.12*ln(1 + fck/10) acima de C50."""
    if fck <= 50:
        return 0.3 * fck ** (2 / 3)
    return 2.12 * log(1 + fck / 10)


def fcti(fck):
    """Calcula fctk inferior pela NBR 6118: fcti = 0.7*fctm."""
    return 0.7 * fctm(fck)


def fcts(fck):
    """Calcula fctk superior pela NBR 6118: fcts = 1.3*fctm."""
    return 1.3 * fctm(fck)


def fctf(fck):
    """Calcula resistencia a tracao na flexao pela NBR 6118: fctf = 1.5*fctm/fck^0.1."""
    return 1.5 * fctm(fck) / fck**0.1


def fptd(fpu=1900, gamma_p=1.15):
    """Calcula fptd para cordoalha CP-190 RB pela NBR 7197: fptd = fpu/gamma_p*0.9."""
    return fpu / gamma_p * 0.9


def fpyd(fpu=1900, gamma_p=1.15):
    """Calcula fpyd para cordoalha CP-190 RB pela NBR 7197: fpyd = fpu/gamma_p*0.9*0.9."""
    return fpu / gamma_p * 0.9 * 0.9


def fyd(fyk=500, gamma_s=1.15):
    """Calcula fyd para aco passivo CA-50 pela NBR 6118: fyd = fyk/gamma_s."""
    return fyk / gamma_s
