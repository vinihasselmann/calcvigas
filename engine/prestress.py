"""Calculo da protensao por cordoalhas."""

from dataclasses import dataclass

from . import materials
from .materials import STRAND_AREA
from .section import SectionL


PRESTRESS_INITIAL_STRESS_TF_CM2 = 15.2


@dataclass(frozen=True)
class Prestress:
    """Modela as cordoalhas de protensao de uma viga pre-moldada."""

    section: SectionL
    n_cordoalhas: int
    diam_mm: float
    yp: float
    n_cordoalhas_sup: int = 0
    diam_sup_mm: float = 9.5
    yp_sup: float | None = None
    fat_pi: float = 0.95
    dpi: float = 0.20
    dps: float = 0.10
    fck: float = 50.0
    fckj: float = 35.0

    def __post_init__(self):
        self._validate_inputs()

    def _validate_inputs(self):
        if not isinstance(self.section, SectionL):
            raise ValueError("O parametro 'section' deve ser uma instancia de SectionL.")
        if self.n_cordoalhas < 0:
            raise ValueError("O parametro 'n_cordoalhas' nao pode ser negativo.")
        if self.n_cordoalhas_sup < 0:
            raise ValueError("O parametro 'n_cordoalhas_sup' nao pode ser negativo.")
        if self.n_cordoalhas > 0 and self.diam_mm not in STRAND_AREA:
            raise ValueError(
                f"Diametro nominal '{self.diam_mm}' invalido. Use um de: {sorted(STRAND_AREA)}."
            )
        if self.n_cordoalhas_sup > 0 and self.diam_sup_mm not in STRAND_AREA:
            raise ValueError(
                f"Diametro nominal superior '{self.diam_sup_mm}' invalido. "
                f"Use um de: {sorted(STRAND_AREA)}."
            )
        if self.n_cordoalhas > 0 and (self.yp <= 0 or self.yp >= self.section.h):
            raise ValueError("O parametro 'yp' deve estar entre a fibra inferior e a altura total da secao.")
        if self.n_cordoalhas_sup > 0:
            if self.yp_sup is None or self.yp_sup <= 0 or self.yp_sup >= self.section.h:
                raise ValueError(
                    "O parametro 'yp_sup' deve estar entre a fibra inferior e a altura total da secao."
                )
        if not 0 <= self.fat_pi <= 1:
            raise ValueError("O parametro 'fat_pi' deve estar entre 0 e 1.")
        if not 0 <= self.dpi < 1:
            raise ValueError("O parametro 'dpi' deve estar entre 0 e menor que 1.")
        if not 0 <= self.dps < 1:
            raise ValueError("O parametro 'dps' deve estar entre 0 e menor que 1.")
        if self.fck <= 0:
            raise ValueError("O parametro 'fck' deve ser maior que zero.")
        if self.fckj <= 0:
            raise ValueError("O parametro 'fckj' deve ser maior que zero.")

    @staticmethod
    def _validate_vao(vao):
        if vao <= 0:
            raise ValueError("O parametro 'vao' deve ser maior que zero.")

    @staticmethod
    def _validate_composite_params(H39_laje, vao_laje):
        if H39_laje is None or vao_laje is None:
            raise ValueError(
                "Informe 'H39_laje' e 'vao_laje' para calcular tensoes finais na secao composta."
            )

    @property
    def asp_total(self):
        """Area total das cordoalhas em cm2."""
        return self.asp_inferior + self.asp_superior

    @property
    def asp_inferior(self):
        """Area das cordoalhas inferiores em cm2."""
        if self.n_cordoalhas == 0:
            return 0
        return self.n_cordoalhas * STRAND_AREA[self.diam_mm]

    @property
    def asp_superior(self):
        """Area das cordoalhas superiores em cm2."""
        if self.n_cordoalhas_sup == 0:
            return 0
        return self.n_cordoalhas_sup * STRAND_AREA[self.diam_sup_mm]

    @property
    def yp_equivalente_total(self):
        """Centroide equivalente de todas as cordoalhas em cm a partir da fibra inferior."""
        if self.asp_total == 0:
            return 0
        return (
            self.asp_inferior * self.yp
            + self.asp_superior * (self.yp_sup or 0)
        ) / self.asp_total

    @property
    def fpi(self):
        """Forca de protensao inicial total em tf."""
        return self.asp_total * PRESTRESS_INITIAL_STRESS_TF_CM2 * self.fat_pi

    @property
    def fps(self):
        """Forca de protensao inicial superior em tf."""
        return self.asp_superior * PRESTRESS_INITIAL_STRESS_TF_CM2 * self.fat_pi

    @property
    def fpi_inferior(self):
        """Forca de protensao inicial inferior em tf."""
        return self.asp_inferior * PRESTRESS_INITIAL_STRESS_TF_CM2 * self.fat_pi

    def mp_ato(self, section=None):
        """Momento de protensao no ato em tfm."""
        section = section or self.section
        momento = self.fpi_inferior * (section.cg - self.yp)
        if self.asp_superior > 0:
            momento += self.fps * (section.cg - self.yp_sup)
        return momento / 100

    @property
    def fpi_tf(self):
        """Forca de protensao apos perdas iniciais em kgf."""
        return self.fpi * (1 - self.dpi) * 1000

    def mp_final(self, section=None, H39_laje=None, vao_laje=None):
        """Momento de protensao final em tfm na secao composta."""
        self._validate_composite_params(H39_laje, vao_laje)
        section = section or self.section
        cg = section.cg_f(H39_laje, vao_laje)
        pi_inf = self.fpi_inferior * (1 - self.dpi) * 1000
        pi_sup = self.fps * (1 - self.dps) * 1000
        momento = pi_inf * (cg - self.yp)
        if self.asp_superior > 0:
            yp_sup_from_top = self.yp_sup - section.h
            momento -= pi_sup * (section.hinf - cg + yp_sup_from_top)
        return momento / 1000 / 100

    def sigma_sup_ato(self, section=None, vao=None):
        """Tensao superior no ato da protensao em kgf/cm2."""
        if vao is None:
            raise ValueError("Informe 'vao' para calcular a tensao no ato da protensao.")
        self._validate_vao(vao)
        section = section or self.section
        momento_pp = section.pp_viga * vao**2 / 8
        return (
            (self.fpi + self.fps) * 1000 / section.ac
            - self.mp_ato(section) * 1000 * 100 / section.ws
            + momento_pp * 1000 * 100 / section.ws
        )

    def sigma_inf_ato(self, section=None, vao=None):
        """Tensao inferior no ato da protensao em kgf/cm2."""
        if vao is None:
            raise ValueError("Informe 'vao' para calcular a tensao no ato da protensao.")
        self._validate_vao(vao)
        section = section or self.section
        momento_pp = section.pp_viga * vao**2 / 8
        return (
            (self.fpi + self.fps) * 1000 / section.ac
            + self.mp_ato(section) * 1000 * 100 / section.wi
            - momento_pp * 1000 * 100 / section.wi
        )

    @staticmethod
    def lim_sup_ato(fckj):
        """Limite superior de compressao no ato em kgf/cm2 pela NBR 7197."""
        if fckj <= 0:
            raise ValueError("O parametro 'fckj' deve ser maior que zero.")
        return 7 * fckj * 10

    @staticmethod
    def lim_inf_ato(fckj):
        """Limite inferior de tracao no ato em kgf/cm2 pela NBR 7197."""
        if fckj <= 0:
            raise ValueError("O parametro 'fckj' deve ser maior que zero.")
        return -1.2 * materials.fctm(fckj) * 10

    def sigma_sup_final(self, section=None, msd=None, H39_laje=None, vao_laje=None):
        """Tensao superior final em kgf/cm2 na secao composta."""
        if msd is None:
            raise ValueError("Informe 'msd' para calcular a tensao final.")
        self._validate_composite_params(H39_laje, vao_laje)
        section = section or self.section
        p_final = (
            self.fpi_inferior * (1 - self.dpi) * 1000
            + self.fps * (1 - self.dps) * 1000
        )
        return (
            p_final / section.ac_f(H39_laje, vao_laje)
            - self.mp_final(section, H39_laje, vao_laje) * 1000 * 100 / section.ws_f(H39_laje, vao_laje)
            + msd * 1000 * 100 / section.ws_f(H39_laje, vao_laje)
        )

    def sigma_inf_final(self, section=None, msd=None, H39_laje=None, vao_laje=None):
        """Tensao inferior final em kgf/cm2 na secao composta."""
        if msd is None:
            raise ValueError("Informe 'msd' para calcular a tensao final.")
        self._validate_composite_params(H39_laje, vao_laje)
        section = section or self.section
        p_final = (
            self.fpi_inferior * (1 - self.dpi) * 1000
            + self.fps * (1 - self.dps) * 1000
        )
        return (
            p_final / section.ac_f(H39_laje, vao_laje)
            + self.mp_final(section, H39_laje, vao_laje) * 1000 * 100 / section.wi_f(H39_laje, vao_laje)
            - msd * 1000 * 100 / section.wi_f(H39_laje, vao_laje)
        )
