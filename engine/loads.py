"""Cargas permanentes e variaveis."""

from dataclasses import dataclass

from .section import SectionL


@dataclass(frozen=True)
class Loads:
    """Calcula cargas distribuidas e solicitacoes simplificadas da viga."""

    section: SectionL
    lp_type: str
    vao_laje: float
    acd: float
    lp_table: dict
    rev: float = 200

    def __post_init__(self):
        self._validate_inputs()

    def _validate_inputs(self):
        if not isinstance(self.section, SectionL):
            raise ValueError("O parametro 'section' deve ser uma instancia de SectionL.")
        if self.lp_type not in self.lp_table:
            raise ValueError(f"Tipo de laje '{self.lp_type}' nao encontrado em lp_table.")
        if self.vao_laje <= 0:
            raise ValueError("O parametro 'vao_laje' deve ser maior que zero.")
        if self.rev < 0:
            raise ValueError("O parametro 'rev' nao pode ser negativo.")
        if self.acd < 0:
            raise ValueError("O parametro 'acd' nao pode ser negativo.")

        lp_data = self.lp_table[self.lp_type]
        for key in ("pp", "cap"):
            if key not in lp_data:
                raise ValueError(f"O tipo de laje '{self.lp_type}' deve conter o campo '{key}'.")
            if lp_data[key] < 0:
                raise ValueError(f"O campo '{key}' da laje '{self.lp_type}' nao pode ser negativo.")

    @staticmethod
    def _validate_vao(vao):
        if vao <= 0:
            raise ValueError("O parametro 'vao' deve ser maior que zero.")

    @property
    def lp_data(self):
        """Dados da laje selecionada."""
        return self.lp_table[self.lp_type]

    @property
    def sc_g1(self):
        """Carga permanente fase 1 em tf/m: viga + laje."""
        return self.lp_data["pp"] * self.vao_laje / 2000 + self.section.pp_viga

    @property
    def sc_g2(self):
        """Carga permanente fase 2 em tf/m: revestimento + parcela simplificada da capa."""
        # A planilha de referencia considera tambem o peso da capa moldada no local
        # com peso especifico aproximado de 25 kgf/m2 por cm de espessura.
        peso_capa = self.section.capa * 25
        return (self.lp_data["cap"] + self.rev + peso_capa) * self.vao_laje / 2000

    @property
    def sc_q(self):
        """Sobrecarga variavel em tf/m."""
        return self.acd * self.vao_laje / 2000

    def p_elu(self, gamma_g1=1.3, gamma_g2=1.4, gamma_q=1.4):
        """Carga distribuida total de ELU em tf/m."""
        return gamma_g1 * self.sc_g1 + gamma_g2 * self.sc_g2 + gamma_q * self.sc_q

    def p_els_cqp(self, psi2=0.4):
        """Carga distribuida da combinacao quase permanente em tf/m."""
        return self.sc_g1 + self.sc_g2 + psi2 * self.sc_q

    def p_els_cf(self, psi1=0.6):
        """Carga distribuida da combinacao frequente em tf/m."""
        return self.sc_g1 + self.sc_g2 + psi1 * self.sc_q

    def p_els_cr(self):
        """Carga distribuida da combinacao rara em tf/m."""
        return self.sc_g1 + self.sc_g2 + self.sc_q

    def msd_elu(self, vao):
        """Momento fletor maximo de ELU em tfm para viga biapoiada."""
        self._validate_vao(vao)
        return self.p_elu() * vao**2 / 8

    def msd_cqp(self, vao, psi2=0.4):
        """Momento fletor maximo quase permanente em tfm para viga biapoiada."""
        self._validate_vao(vao)
        return self.p_els_cqp(psi2=psi2) * vao**2 / 8

    def msd_cf(self, vao, psi1=0.6):
        """Momento fletor maximo frequente em tfm para viga biapoiada."""
        self._validate_vao(vao)
        return self.p_els_cf(psi1=psi1) * vao**2 / 8

    def msd_cr(self, vao):
        """Momento fletor maximo raro em tfm para viga biapoiada."""
        self._validate_vao(vao)
        return self.p_els_cr() * vao**2 / 8

    def vsd(self, vao):
        """Forca cortante maxima de ELU em tf para viga biapoiada."""
        self._validate_vao(vao)
        return self.p_elu() * vao / 2

    def summary(self, vao=None):
        """Retorna os principais valores calculados em um dicionario."""
        data = {
            "lp_type": self.lp_type,
            "vao_laje": self.vao_laje,
            "sc_g1": self.sc_g1,
            "sc_g2": self.sc_g2,
            "sc_q": self.sc_q,
            "p_elu": self.p_elu(),
            "p_els_cqp": self.p_els_cqp(),
            "p_els_cf": self.p_els_cf(),
            "p_els_cr": self.p_els_cr(),
        }

        if vao is not None:
            data.update(
                {
                    "vao": vao,
                    "msd_elu": self.msd_elu(vao),
                    "msd_cqp": self.msd_cqp(vao),
                    "msd_cf": self.msd_cf(vao),
                    "msd_cr": self.msd_cr(vao),
                    "vsd": self.vsd(vao),
                }
            )

        return data
