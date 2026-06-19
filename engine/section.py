"""Geometria da secao transversal tipo L."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionL:
    """Representa uma secao transversal de viga pre-moldada em formato L."""

    h: float
    bw: float
    bf: float
    cob: float
    capa: float
    hsup: float = None
    hinf: float = None
    hs: float = 0

    def __post_init__(self):
        self._derive_internal_geometry()
        self._validate_geometry()

    def _derive_internal_geometry(self):
        if self.hsup is None and self.hinf is None:
            hsup = min(25, self.h - 1)
            object.__setattr__(self, "hsup", hsup)
            object.__setattr__(self, "hinf", self.h - hsup)
        elif self.hsup is None:
            object.__setattr__(self, "hsup", self.h - self.hinf)
        elif self.hinf is None:
            object.__setattr__(self, "hinf", self.h - self.hsup)

    def _validate_geometry(self):
        positive_fields = {
            "h": self.h,
            "bw": self.bw,
            "bf": self.bf,
            "hsup": self.hsup,
            "hinf": self.hinf,
            "cob": self.cob,
        }
        non_negative_fields = {"capa": self.capa, "hs": self.hs}

        for name, value in positive_fields.items():
            if value <= 0:
                raise ValueError(f"O parametro geometrico '{name}' deve ser maior que zero.")

        for name, value in non_negative_fields.items():
            if value < 0:
                raise ValueError(f"O parametro geometrico '{name}' nao pode ser negativo.")

        if self.hinf + self.hsup > self.h:
            raise ValueError("Geometria inconsistente: hinf + hsup nao pode ser maior que h.")

        if self.cob >= self.h:
            raise ValueError("Geometria inconsistente: cob deve ser menor que h.")

    @staticmethod
    def _validate_laje_params(H39_laje, vao_laje):
        if H39_laje <= 0:
            raise ValueError("O parametro 'H39_laje' deve ser maior que zero.")
        if vao_laje <= 0:
            raise ValueError("O parametro 'vao_laje' deve ser maior que zero.")

    @property
    def ac(self):
        """Area de concreto da viga em cm2."""
        return self.bw * self.hinf + self.bf * self.hsup

    @property
    def cg(self):
        """Centroide da viga em cm, medido a partir da fibra inferior."""
        return (
            self.bw * self.hinf * (self.hinf / 2)
            + self.bf * self.hsup * (self.hinf + self.hsup / 2)
        ) / self.ac

    @property
    def ix(self):
        """Momento de inercia bruto da viga em cm4, sem capa e sem armadura."""
        cg = self.cg
        return (
            self.bw * self.hinf**3 / 12
            + self.bw * self.hinf * (cg - self.hinf / 2) ** 2
            + self.bf * self.hsup**3 / 12
            + self.bf * self.hsup * (self.hinf + self.hsup / 2 - cg) ** 2
        )

    @property
    def ws(self):
        """Modulo resistente superior bruto em cm3."""
        return self.ix / (self.h - self.cg)

    @property
    def wi(self):
        """Modulo resistente inferior bruto em cm3."""
        return self.ix / self.cg

    def bf_eq(self, H39_laje, vao_laje):
        """Largura efetiva simplificada da mesa equivalente em cm."""
        self._validate_laje_params(H39_laje, vao_laje)
        largura_colaborante_cm = vao_laje / 5 * 100
        return min(self.bf + 2 * (largura_colaborante_cm / 2), H39_laje * 100)

    def ac_f(self, H39_laje, vao_laje):
        """Area composta simplificada em cm2, seguindo a planilha VPL."""
        bf_eq = self.bf_eq(H39_laje, vao_laje)
        return self.ac + self.hs * bf_eq

    def cg_f(self, H39_laje, vao_laje):
        """Centroide composto em cm, medido a partir da fibra inferior."""
        bf_eq = self.bf_eq(H39_laje, vao_laje)
        area_hs = bf_eq * self.hs
        momento_viga = self.ac * self.cg
        momento_hs = area_hs * (self.h + self.hs / 2)
        return (momento_viga + momento_hs) / self.ac_f(H39_laje, vao_laje)

    def ix_f(self, H39_laje, vao_laje):
        """Momento de inercia composto em cm4 por Steiner, incluindo capa e enchimento."""
        bf_eq = self.bf_eq(H39_laje, vao_laje)
        cg_f = self.cg_f(H39_laje, vao_laje)
        area_hs = bf_eq * self.hs
        y_hs = self.h + self.hs / 2

        ix_viga = self.ix + self.ac * (cg_f - self.cg) ** 2
        ix_hs = bf_eq * self.hs**3 / 12 + area_hs * (y_hs - cg_f) ** 2

        return ix_viga + ix_hs

    def ws_f(self, H39_laje, vao_laje):
        """Modulo resistente superior composto em cm3."""
        altura_total = self.h + self.hs + self.capa
        return self.ix_f(H39_laje, vao_laje) / (altura_total - self.cg_f(H39_laje, vao_laje))

    def wi_f(self, H39_laje, vao_laje):
        """Modulo resistente inferior composto em cm3."""
        return self.ix_f(H39_laje, vao_laje) / self.cg_f(H39_laje, vao_laje)

    @property
    def pp_viga(self):
        """Peso proprio da viga em tf/m, adotando peso especifico de 2.5 tf/m3."""
        return 2.5 * self.ac / 10000
