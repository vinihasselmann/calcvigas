"""Modelo base da planilha VIGA T Protendida."""

from dataclasses import dataclass

from .materials import STRAND_AREA


STEEL_WEIGHT_LONGITUDINAL = 0.785
STEEL_WEIGHT_TRANSVERSE = 0.782

LP_CAP = {
    "LP15": 15,
    "LP20": 20,
    "LP26,5": 27,
    "LP32": 32,
    "LP40": 40,
    "LP50": 50,
}
LP_BE = {
    "LP15": 8,
    "LP20": 10,
    "LP26,5": 14,
    "LP32": 16,
    "LP40": 20,
    "LP50": 25,
}

LP_WEIGHT = {
    "LP15": 250,
    "LP20": 290,
    "LP26,5": 370,
    "LP32": 420,
    "LP40": 490,
    "LP50": 650,
}
VPT_PASSIVE_BAR_AREA = {
    0.0: 0.0,
    10.0: 0.7853981633974483,
    12.5: 1.227184630308513,
    16.0: 2.0106192982974678,
    20.0: 3.141592653589793,
    25.0: 4.908738521234052,
    32.0: 8.042477193189871,
}


@dataclass(frozen=True)
class VptSectionSpec:
    secao: str
    bw: float
    h1: float
    h2: float
    h3: float
    hp: float


VPT_SECTION_CATALOG = {
    "T95/65x50": VptSectionSpec("T95/65x50", 50, 65, 10, 20, 95),
    "T90/65x50": VptSectionSpec("T90/65x50", 50, 65, 10, 15, 90),
    "T85/65x50": VptSectionSpec("T85/65x50", 50, 65, 10, 10, 85),
    "T95/65x40": VptSectionSpec("T95/65x40", 40, 65, 10, 20, 95),
    "T90/65x40": VptSectionSpec("T90/65x40", 40, 65, 10, 15, 90),
    "T85/65x40": VptSectionSpec("T85/65x40", 40, 65, 10, 10, 85),
    "T85/55x50": VptSectionSpec("T85/55x50", 50, 55, 10, 20, 85),
    "T80/55x50": VptSectionSpec("T80/55x50", 50, 55, 10, 15, 80),
    "T75/55x50": VptSectionSpec("T75/55x50", 50, 55, 10, 10, 75),
    "T85/55x40": VptSectionSpec("T85/55x40", 40, 55, 10, 20, 85),
    "T80/55x40": VptSectionSpec("T80/55x40", 40, 55, 10, 15, 80),
    "T75/55x40": VptSectionSpec("T75/55x40", 40, 55, 10, 10, 75),
    "T85/55x30": VptSectionSpec("T85/55x30", 30, 55, 10, 20, 85),
    "T80/55x30": VptSectionSpec("T80/55x30", 30, 55, 10, 15, 80),
    "T75/55x30": VptSectionSpec("T75/55x30", 30, 55, 10, 10, 75),
    "T75/45x50": VptSectionSpec("T75/45x50", 50, 45, 10, 20, 75),
    "T70/45x50": VptSectionSpec("T70/45x50", 50, 45, 10, 15, 70),
    "T65/45x50": VptSectionSpec("T65/45x50", 50, 45, 10, 10, 65),
    "T75/45x40": VptSectionSpec("T75/45x40", 40, 45, 10, 20, 75),
    "T70/45x40": VptSectionSpec("T70/45x40", 40, 45, 10, 15, 70),
    "T65/45x40": VptSectionSpec("T65/45x40", 40, 45, 10, 10, 65),
    "T75/45x30": VptSectionSpec("T75/45x30", 30, 45, 10, 20, 75),
    "T70/45x30": VptSectionSpec("T70/45x30", 30, 45, 10, 15, 70),
    "T65/45x30": VptSectionSpec("T65/45x30", 30, 45, 10, 10, 65),
    "T65/35x40": VptSectionSpec("T65/35x40", 40, 35, 10, 20, 65),
    "T60/35x40": VptSectionSpec("T60/35x40", 40, 35, 10, 15, 60),
    "T55/35x40": VptSectionSpec("T55/35x40", 40, 35, 10, 10, 55),
    "T65/35x30": VptSectionSpec("T65/35x30", 30, 35, 10, 20, 65),
    "T60/35x30": VptSectionSpec("T60/35x30", 30, 35, 10, 15, 60),
    "T55/35x30": VptSectionSpec("T55/35x30", 30, 35, 10, 10, 55),
    "T55/25x40": VptSectionSpec("T55/25x40", 40, 25, 10, 20, 55),
    "T50/25x40": VptSectionSpec("T50/25x40", 40, 25, 10, 15, 50),
    "T45/25x40": VptSectionSpec("T45/25x40", 40, 25, 10, 10, 45),
    "T55/25x25": VptSectionSpec("T55/25x25", 25, 25, 10, 20, 55),
    "T50/25x25": VptSectionSpec("T50/25x25", 25, 25, 10, 15, 50),
    "T45/25x25": VptSectionSpec("T45/25x25", 25, 25, 10, 10, 45),
    "T55/25x30": VptSectionSpec("T55/25x30", 30, 25, 10, 20, 55),
    "T50/25x30": VptSectionSpec("T50/25x30", 30, 25, 10, 15, 50),
    "T45/25x30": VptSectionSpec("T45/25x30", 30, 25, 10, 10, 45),
}


@dataclass(frozen=True)
class VptGeometry:
    """Geometria da secao T conforme bloco C38:C47 da planilha."""

    bw: float = 40
    h1: float = 25
    h2: float = 10
    h3: float = 15
    hc: float = 0
    capa: float = 5
    b_capa: float = 40
    bf: float = 52

    def derived(self, lp_left_cap: float, lp_right_cap: float) -> "VptDerivedGeometry":
        h4 = abs(lp_left_cap - lp_right_cap)
        hp = self.h1 + self.h2 + self.h3 + h4 + self.hc
        h = self.h1 + self.h2 + self.h3 + max(lp_left_cap, lp_right_cap) + self.capa
        hs = min(lp_left_cap, lp_right_cap) - self.hc
        he = self.h3 + h4 if lp_left_cap < lp_right_cap else self.h3
        hd = self.h3 + h4 if lp_right_cap < lp_left_cap else self.h3
        bs1 = self.bw + 20
        bs = self.bw + 40
        return VptDerivedGeometry(
            bw=self.bw,
            h1=self.h1,
            h2=self.h2,
            h3=self.h3,
            hc=self.hc,
            h4=h4,
            hp=hp,
            h=h,
            h_v=hp,
            hs=hs,
            he=he,
            hd=hd,
            bs1=bs1,
            bs=bs,
            bf=self.bf,
            capa=self.capa,
            b_capa=self.b_capa,
        )


@dataclass(frozen=True)
class VptDerivedGeometry:
    bw: float
    h1: float
    h2: float
    h3: float
    hc: float
    h4: float
    hp: float
    h: float
    h_v: float
    hs: float
    he: float
    hd: float
    bs1: float
    bs: float
    bf: float
    capa: float
    b_capa: float


@dataclass(frozen=True)
class VptLajeSide:
    lp_type: str
    rev: float
    acd: float
    vao: float

    @property
    def pp(self) -> float:
        return LP_WEIGHT[self.lp_type]

    @property
    def cap(self) -> float:
        return LP_CAP[self.lp_type]

    @property
    def be(self) -> float:
        return LP_BE[self.lp_type]

    def capa_load(self, capa: float) -> float:
        return (capa + 1) * 25


@dataclass(frozen=True)
class VptConcreteSection:
    """Secao bruta da viga T, sem transformacao de aco."""

    geom: VptDerivedGeometry
    as_inferior: float = 0
    ys: float = 0
    as_superior: float = 0
    ys_superior: float = 0
    fat_i: float = 1

    @property
    def area_parts(self) -> dict[str, float]:
        g = self.geom
        return {
            "a0": g.hc * g.bw,
            "a1": g.bs1 * g.h4,
            "a2": g.bs * g.h3,
            "a3": 0.5 * (g.bw + g.bs) * g.h2,
            "a4": g.bw * g.h1,
        }

    @property
    def centroids(self) -> dict[str, float]:
        g = self.geom
        return {
            "cg0": g.h_v - 0.5 * g.hc,
            "cg1": g.h_v - g.hc - 0.5 * g.h4,
            "cg2": g.h1 + g.h2 + 0.5 * g.h3,
            "cg3": g.h1 + g.h2 * (2 * g.bs + g.bw) / (3 * (g.bs + g.bw)),
            "cg4": 0.5 * g.h1,
        }

    @property
    def ac(self) -> float:
        return sum(self.area_parts.values())

    @property
    def cg(self) -> float:
        areas = self.area_parts
        cgs = self.centroids
        steel_factor = self.fat_i - 1
        return (
            areas["a0"] * cgs["cg0"]
            + areas["a1"] * cgs["cg1"]
            + areas["a2"] * cgs["cg2"]
            + areas["a3"] * cgs["cg3"]
            + areas["a4"] * cgs["cg4"]
            + self.as_inferior * steel_factor * self.ys
            + self.as_superior * steel_factor * (self.geom.h_v + self.ys_superior)
        ) / (self.ac + steel_factor * (self.as_inferior + self.as_superior))

    @property
    def ix(self) -> float:
        g = self.geom
        areas = self.area_parts
        cgs = self.centroids
        cg = self.cg
        ix0 = g.bw * g.hc**3 + areas["a0"] * (cgs["cg0"] - cg) ** 2
        ix1 = g.bs1 * g.h4**3 / 12 + areas["a1"] * (cg - cgs["cg1"]) ** 2
        ix2 = g.bs * g.h3**3 / 12 + areas["a2"] * (cg - cgs["cg2"]) ** 2
        ix3 = (
            g.h2**3 * (g.bw**2 + 4 * g.bw * g.bs + g.bs**2) / (36 * (g.bw + g.bs))
            + areas["a3"] * (cg - cgs["cg3"]) ** 2
        )
        ix4 = g.bw * g.h1**3 / 12 + areas["a4"] * (cg - cgs["cg4"]) ** 2
        ix_steel = (
            self.as_inferior * (self.fat_i - 1) * (cg - self.ys) ** 2
            + self.as_superior * (self.fat_i - 1) * (self.geom.h_v + self.ys_superior - cg) ** 2
        )
        return ix0 + ix1 + ix2 + ix3 + ix4 + ix_steel

    @property
    def ws(self) -> float:
        return self.ix / (self.geom.h_v - self.cg)

    @property
    def wi(self) -> float:
        return self.ix / self.cg

    @property
    def pp_viga(self) -> float:
        return 2.5 * self.ac / 10000


@dataclass(frozen=True)
class VptCompositeSection:
    """Secao composta simplificada conforme bloco C103:C117."""

    concrete: VptConcreteSection
    fck: float
    fck_capa: float

    @property
    def fat_cp(self) -> float:
        # A planilha usa Ecs.cp / Ecs; para a etapa 1 mantemos o valor de referencia via ecs.
        from .materials import ecs

        return ecs(self.fck_capa) / ecs(self.fck)

    @property
    def b_capa_eq(self) -> float:
        return self.concrete.geom.b_capa * self.fat_cp

    @property
    def bf_eq(self) -> float:
        return self.concrete.geom.bf * self.fat_cp

    @property
    def ac_f(self) -> float:
        return self.concrete.ac + self._a_cap

    @property
    def cg_f(self) -> float:
        return (self.concrete.ac * self.concrete.cg + self._a_cap * self._cg_cap) / self.ac_f

    @property
    def ix_f(self) -> float:
        return self.concrete.ix + self.concrete.ac * (self.cg_f - self.concrete.cg) ** 2 + self._ix_cap

    @property
    def ws_f(self) -> float:
        return self.ix_f / (self.concrete.geom.h - self.cg_f)

    @property
    def ws_f1(self) -> float:
        return self.ix_f / (self.concrete.geom.h_v - self.cg_f)

    @property
    def wi_f(self) -> float:
        return self.ix_f / self.cg_f

    @property
    def _a_capa(self) -> float:
        return self.b_capa_eq * self.concrete.geom.capa

    @property
    def _cg_capa(self) -> float:
        return self.concrete.geom.h - self.concrete.geom.capa / 2

    @property
    def _a_sup(self) -> float:
        return self.bf_eq * self.concrete.geom.hs

    @property
    def _cg_sup(self) -> float:
        return self.concrete.geom.h - self.concrete.geom.capa - self.concrete.geom.hs / 2

    @property
    def _a0(self) -> float:
        return self.concrete.area_parts["a0"]

    @property
    def _cg0(self) -> float:
        return self.concrete.centroids["cg0"]

    @property
    def _a_cap(self) -> float:
        return self._a_capa + self._a_sup - self._a0

    @property
    def _cg_cap(self) -> float:
        return (
            self._a_capa * self._cg_capa
            + self._a_sup * self._cg_sup
            - self._a0 * self._cg0
        ) / self._a_cap

    @property
    def _ix_cap(self) -> float:
        cg_f = self.cg_f
        g = self.concrete.geom
        ix_capa = self.b_capa_eq * g.capa**3 / 12 + self._a_capa * (self._cg_capa - cg_f) ** 2
        ix_sup = self.bf_eq * g.hs**3 / 12 + self._a_sup * (self._cg_sup - cg_f) ** 2
        ix0 = g.bw * g.hc**3 + self._a0 * (self._cg0 - cg_f) ** 2
        return ix_capa + ix_sup - ix0


@dataclass(frozen=True)
class VptPrestressLayer:
    n_cord: int
    diam_mm: float
    yp: float | None = None

    def area(self) -> float:
        if self.n_cord == 0:
            return 0
        return self.n_cord * STRAND_AREA[self.diam_mm]


@dataclass(frozen=True)
class VptPassiveLayer:
    n_barras: int
    diam_mm: float
    ys: float

    def area(self) -> float:
        if self.n_barras == 0:
            return 0
        return self.n_barras * VPT_PASSIVE_BAR_AREA[self.diam_mm]


def equivalent_prestress(layers: tuple[VptPrestressLayer, ...], cob: float) -> tuple[int, float, float]:
    resolved = []
    for idx, layer in enumerate(layers):
        yp = layer.yp if layer.yp is not None else cob + 1 + layer.diam_mm / 20 + 4 * idx
        area = layer.area()
        resolved.append((layer.n_cord, yp, area))
    total_area = sum(area for _, _, area in resolved)
    total_cords = sum(n for n, _, _ in resolved)
    yp_eq = sum(area * yp for _, yp, area in resolved) / total_area if total_area else 0
    return total_cords, yp_eq, total_area


def passive_area_and_ys(layers: tuple[VptPassiveLayer, ...]) -> tuple[float, float]:
    total_area = sum(layer.area() for layer in layers)
    ys = sum(layer.area() * layer.ys for layer in layers) / total_area if total_area else 0
    return total_area, ys


def taxa_protendida(asp_total: float, ac: float, superior_area: float = 0) -> float:
    return (asp_total + superior_area) * STEEL_WEIGHT_TRANSVERSE * 10**4 / ac


def taxa_passiva_longitudinal(as_inferior: float, as_superior: float, h: float, ac: float) -> float:
    return (as_inferior + as_superior + h / 10) * STEEL_WEIGHT_LONGITUDINAL * 10**4 / ac


def taxa_passiva_transversal(asw: float, geom: VptDerivedGeometry, ac: float) -> float:
    comprimento_estribo = (2 * (geom.h + geom.bw)) / 100
    comprimento_aba = (2 * geom.bs + geom.he + geom.hd) / 100
    peso = ((asw / 2) * comprimento_estribo + 3.35 * comprimento_aba) * STEEL_WEIGHT_TRANSVERSE
    return peso / (ac / 10000)


def taxa_passiva_total(as_inferior: float, as_superior: float, asw: float, geom: VptDerivedGeometry, ac: float) -> float:
    return taxa_passiva_longitudinal(as_inferior, as_superior, geom.h, ac) + taxa_passiva_transversal(asw, geom, ac)
