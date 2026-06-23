"""Modelo extraido da aba Plan1 da planilha de lajes alveolares."""

from dataclasses import dataclass
from math import sqrt


NAO_PASSA = "NAO PASSA"
ITERATED_FIELDS = ("sobrecarga", "vao", "capa", "fck_capa")
EXPORT_COLUMNS = [
    "lp_type",
    "vao",
    "sobrecarga",
    "capa",
    "fck_capa",
    "peso_proprio",
    "carga_total",
    "momento_fletor",
    "forca_cortante",
    "cabos",
    "status",
]


@dataclass(frozen=True)
class LajeAlvInputs:
    """Entradas globais equivalentes as celulas L3:L6 da Plan1."""

    sobrecarga: float
    vao: float
    capa: float
    fck_capa: float
    continuidade_kgf: float = 0


@dataclass(frozen=True)
class CapacityOption:
    """Opcao de cordoalhas com momento e cortante maximos."""

    cabos: str
    momento_max: float
    cortante_max: float


@dataclass(frozen=True)
class LajeAlvSpec:
    """Dados fixos de uma familia de laje alveolar na Plan1."""

    lp_type: str
    altura_cm: float
    peso_proprio: float
    vao_max: float
    sum_bw: float
    capacities: tuple[CapacityOption, ...]
    selector: tuple[str, ...]
    lp15_selector: bool = False


@dataclass(frozen=True)
class SimpleModelResult:
    lp_type: str
    vao: float
    sobrecarga: float
    capa: float
    fck_capa: float
    peso_proprio: float
    carga_capa: float
    carga_total: float
    momento_fletor: float
    forca_cortante: float
    cabos: str
    status: str


@dataclass(frozen=True)
class ContinuityModelResult:
    lp_type: str
    vs_max: float
    xv0: float
    ms_pos_max: float
    d: float
    sum_bw: float
    x: float
    as_negativa: float
    taxa_kg_m2: float


@dataclass(frozen=True)
class ShearFillingSpec:
    """Dados da planilha de preenchimento de alveolos para cortante."""

    h_capa_cm: float
    n_alveolos: int
    b_alv_cm: float
    d_linha_cm: float
    fck_peca_mpa: float
    ac_cm2: float
    area_alv_cm2: float
    n_alveolos_concretados: int
    fck_alveolo_mpa: float
    sbw_ext_cm: float
    sbw_int_cm: float
    fpi_por_cabo_kgf: float


@dataclass(frozen=True)
class ShearFillingResult:
    lp_type: str
    cabos: str
    n_cabos_7mm: int
    n_cabos_95mm: int
    n_cabos_127mm: int
    n_alveolos_preenchidos: int
    vrd_sem_preenchimento: float
    vrd_preenchimento_fabrica: float
    vrd_preenchimento_obra: float
    vrd_preenchimento: float
    comprimento_preenchimento_m: float
    status: str


SHEAR_FILLING_SPECS = {
    "LP15": ShearFillingSpec(5, 8, 11, 3.5, 50, 1047.11, 95.03, 0, 30, 8.96, 24.4, 6327),
    "LP20": ShearFillingSpec(7, 6, 15.5, 3.5, 50, 1289.93, 188.69, 0, 30, 10.8, 17, 10640),
    "LP26,5": ShearFillingSpec(10, 5, 18.5, 3.5, 50, 1869.61, 268.8, 5, 40, 12.7, 15.6, 10640),
    "LP32": ShearFillingSpec(6, 4, 22.9, 3.5, 45, 1948, 482.47, 2, 40, 13, 16.2, 11400),
    "LP40": ShearFillingSpec(5, 4, 23, 3.5, 50, 2093, 696.12, 2, 40, 11.74, 15.9, 10640),
    "LP50": ShearFillingSpec(7, 4, 20.4, 3.5, 30, 3296.86, 738.65, 0, 30, 23, 20.4, 11400),
}


LAJE_ALV_SPECS = {
    "LP15": LajeAlvSpec(
        lp_type="LP15",
        altura_cm=15,
        peso_proprio=245,
        vao_max=9.5,
        sum_bw=24.32,
        lp15_selector=True,
        selector=("7 x 9,5mm", "9 x 9,5mm"),
        capacities=(
            CapacityOption("9 x 9,5mm", 6490, 6000),
            CapacityOption("7 x 9,5mm", 5180, 5254),
            CapacityOption("5 x 9,5mm", 3760, 4509),
        ),
    ),
    "LP20": LajeAlvSpec(
        lp_type="LP20",
        altura_cm=20,
        peso_proprio=285,
        vao_max=12,
        sum_bw=22.24,
        selector=("7 x 9,5mm", "5 x 12,7mm", "7 x 12,7mm"),
        capacities=(
            CapacityOption("7 x 12,7mm", 11900, 6087),
            CapacityOption("5 x 12,7mm", 8850, 5023),
            CapacityOption("7 x 9,5mm", 6930, 4425),
            CapacityOption("5 x 9,5mm", 4960, 3837),
        ),
    ),
    "LP26,5": LajeAlvSpec(
        lp_type="LP26,5",
        altura_cm=26.5,
        peso_proprio=370,
        vao_max=15,
        sum_bw=22.56,
        selector=("6 x 12,7mm", "8 x 12,7mm", "10 x 12,7mm"),
        capacities=(
            CapacityOption("10 x 12,7mm", 21850, 7879),
            CapacityOption("8 x 12,7mm", 17950, 6900),
            CapacityOption("6 x 12,7mm", 13700, 5921),
            CapacityOption("4 x 12,7mm", 9040, 4941),
            CapacityOption("6 x 9,5mm", 7470, 4608),
            CapacityOption("4 x 9,5mm", 5040, 4066),
        ),
    ),
    "LP32": LajeAlvSpec(
        lp_type="LP32",
        altura_cm=32,
        peso_proprio=410,
        vao_max=16,
        sum_bw=22.80,
        selector=("7 x 12,7mm", "9 x 12,7mm", "11 x 12,7mm"),
        capacities=(
            CapacityOption("11 x 12,7mm", 27950, 9756),
            CapacityOption("10 x 12,7mm", 25650, 9194),
            CapacityOption("9 x 12,7mm", 23340, 8633),
            CapacityOption("8 x 12,7mm", 20970, 8071),
            CapacityOption("7 x 12,7mm", 18600, 7509),
            CapacityOption("5 x 12,7mm", 13560, 6386),
        ),
    ),
    "LP40": LajeAlvSpec(
        lp_type="LP40",
        altura_cm=40,
        peso_proprio=470,
        vao_max=17,
        sum_bw=24.64,
        selector=("11 x 12,7mm", "13 x 12,7mm", "14 x 12,7mm"),
        capacities=(
            CapacityOption("14 x 12,7mm", 44230, 12514),
            CapacityOption("13 x 12,7mm", 41340, 11915),
            CapacityOption("11 x 12,7mm", 35400, 10717),
            CapacityOption("10 x 12,7mm", 32490, 10118),
            CapacityOption("9 x 12,7mm", 29670, 9519),
            CapacityOption("8 x 12,7mm", 26580, 8920),
            CapacityOption("7 x 12,7mm", 23200, 8321),
            CapacityOption("5 x 12,7mm", 17000, 7122),
        ),
    ),
    "LP50": LajeAlvSpec(
        lp_type="LP50",
        altura_cm=50,
        peso_proprio=650,
        vao_max=17,
        sum_bw=32.64,
        selector=("11 x 12,7mm", "13 x 12,7mm", "14 x 12,7mm"),
        capacities=(
            CapacityOption("14 x 12,7mm", 55820, 14697),
            CapacityOption("13 x 12,7mm", 52430, 14078),
            CapacityOption("11 x 12,7mm", 44840, 12838),
            CapacityOption("10 x 12,7mm", 40780, 12218),
            CapacityOption("9 x 12,7mm", 37030, 11599),
            CapacityOption("8 x 12,7mm", 33270, 10979),
            CapacityOption("7 x 12,7mm", 29110, 10359),
            CapacityOption("5 x 12,7mm", 20980, 9119),
        ),
    ),
}


def carga_capa(capa: float) -> float:
    """Carga da capa conforme Plan1: ((capa + 1) / 100) * 2500."""
    return ((capa + 1) / 100) * 2500


def carga_total(spec: LajeAlvSpec, inputs: LajeAlvInputs) -> float:
    return spec.peso_proprio + inputs.sobrecarga + carga_capa(inputs.capa)


def momento_fletor(spec: LajeAlvSpec, inputs: LajeAlvInputs) -> float:
    return carga_total(spec, inputs) * inputs.vao**2 / 8


def forca_cortante(spec: LajeAlvSpec, inputs: LajeAlvInputs) -> float:
    return carga_total(spec, inputs) * inputs.vao / 2


def _capacity_by_cables(spec: LajeAlvSpec) -> dict[str, CapacityOption]:
    return {option.cabos: option for option in spec.capacities}


def _option_passes_demand(
    option: CapacityOption,
    spec: LajeAlvSpec,
    vao: float,
    momento: float,
    cortante: float,
    check_span: bool = True,
) -> bool:
    return (
        option.momento_max >= momento
        and option.cortante_max >= cortante
        and (not check_span or spec.vao_max >= vao)
    )


def select_simple_cables(spec: LajeAlvSpec, inputs: LajeAlvInputs) -> str:
    """Replica a logica da coluna J para laje biapoiada simples."""
    options = _capacity_by_cables(spec)
    moment = momento_fletor(spec, inputs)
    shear = forca_cortante(spec, inputs)

    for cable_name in spec.selector:
        if _option_passes_demand(
            options[cable_name],
            spec,
            inputs.vao,
            moment,
            shear,
        ):
            return cable_name
    return NAO_PASSA


def select_cables_by_demands(
    spec: LajeAlvSpec,
    vao: float,
    momento: float,
    cortante: float,
    check_span: bool = True,
) -> str:
    """Seleciona cordoalhas usando demandas ja calculadas, como N/P da continuidade."""
    options = _capacity_by_cables(spec)
    for cable_name in spec.selector:
        if _option_passes_demand(options[cable_name], spec, vao, momento, cortante, check_span):
            return cable_name
    return NAO_PASSA


def _parse_cable_counts(cabos: str) -> tuple[int, int, int]:
    if not cabos or cabos == NAO_PASSA:
        return (0, 0, 0)
    amount_text, _, diameter_text = cabos.partition("x")
    try:
        amount = int(amount_text.strip())
    except ValueError:
        return (0, 0, 0)
    diameter = diameter_text.replace(",", ".")
    if "7" in diameter and "12.7" not in diameter and "12,7" not in diameter:
        return (amount, 0, 0)
    if "9.5" in diameter or "9,5" in diameter:
        return (0, amount, 0)
    if "12.7" in diameter or "12,7" in diameter:
        return (0, 0, amount)
    return (0, 0, 0)


def _shear_capacity(
    spec: LajeAlvSpec,
    filling: ShearFillingSpec,
    cabos: str,
    inputs: LajeAlvInputs,
    filled: bool,
    post_release: bool,
) -> float:
    n7, n95, n127 = _parse_cable_counts(cabos)
    steel_area = n7 * 0.385 + n95 * 0.548 + n127 * 0.987
    cable_count = n7 + n95 + n127
    h_capa = inputs.capa if inputs.capa is not None else filling.h_capa_cm
    fck_alveolo = inputs.fck_capa if inputs.fck_capa is not None else filling.fck_alveolo_mpa
    d = spec.altura_cm + h_capa - filling.d_linha_cm
    k = 1.6 - d / 100
    fctm = 0.3 * filling.fck_peca_mpa ** (2 / 3)
    fctd = (0.7 * fctm / 1.4) * 10

    n_filled = filling.n_alveolos_concretados if filled else 0
    ac = filling.ac_cm2 + n_filled * filling.area_alv_cm2
    ec = 0.85 * 5600 * sqrt(fck_alveolo)
    ep = 0.85 * 5600 * sqrt(filling.fck_peca_mpa)
    sbw = filling.sbw_ext_cm + filling.sbw_int_cm
    if filled:
        sbw += 0.5 * n_filled * filling.b_alv_cm * (ec / ep)

    rho = steel_area / (sbw * d) if sbw and d else 0
    np = 0.8 * filling.fpi_por_cabo_kgf * cable_count
    scp1 = np / filling.ac_cm2 if filling.ac_cm2 else 0
    scp2 = np / ac if ac else 0
    vc = 0.25 * fctd * k * (1.2 + 40 * rho) * sbw * d
    vp_source_scp = scp1 if post_release else scp2
    vp_source_sbw = filling.sbw_ext_cm + filling.sbw_int_cm if post_release else sbw
    vp = 0.15 * vp_source_scp * vp_source_sbw * d
    return (vc + vp) / 1.25 / 1.4


def run_shear_filling_model(
    spec: LajeAlvSpec,
    inputs: LajeAlvInputs,
    cabos: str,
    cortante: float,
) -> ShearFillingResult:
    """Replica a planilha de cortante para preenchimento de alveolos."""
    filling = SHEAR_FILLING_SPECS[spec.lp_type]
    no_fill = _shear_capacity(spec, filling, cabos, inputs, filled=False, post_release=True)
    before_release = _shear_capacity(spec, filling, cabos, inputs, filled=True, post_release=False)
    after_release = _shear_capacity(spec, filling, cabos, inputs, filled=True, post_release=True)
    filled_capacity = min(before_release, after_release)
    status = "PASSA" if cortante <= filled_capacity else NAO_PASSA
    length = 0
    if cortante > no_fill and cortante > 0:
        length = inputs.vao / 2 * (1 - no_fill / cortante) + 0.15
        length = max(0, min(inputs.vao / 2, length))
    n7, n95, n127 = _parse_cable_counts(cabos)
    return ShearFillingResult(
        lp_type=spec.lp_type,
        cabos=cabos,
        n_cabos_7mm=n7,
        n_cabos_95mm=n95,
        n_cabos_127mm=n127,
        n_alveolos_preenchidos=filling.n_alveolos_concretados,
        vrd_sem_preenchimento=no_fill,
        vrd_preenchimento_fabrica=before_release,
        vrd_preenchimento_obra=after_release,
        vrd_preenchimento=filled_capacity,
        comprimento_preenchimento_m=length,
        status=status,
    )


def run_simple_model(spec: LajeAlvSpec, inputs: LajeAlvInputs) -> SimpleModelResult:
    cabos = select_simple_cables(spec, inputs)
    return SimpleModelResult(
        lp_type=spec.lp_type,
        vao=inputs.vao,
        sobrecarga=inputs.sobrecarga,
        capa=inputs.capa,
        fck_capa=inputs.fck_capa,
        peso_proprio=spec.peso_proprio,
        carga_capa=carga_capa(inputs.capa),
        carga_total=carga_total(spec, inputs),
        momento_fletor=momento_fletor(spec, inputs),
        forca_cortante=forca_cortante(spec, inputs),
        cabos=cabos,
        status="PASSA" if cabos != NAO_PASSA else NAO_PASSA,
    )


def run_continuity_model(spec: LajeAlvSpec, inputs: LajeAlvInputs) -> ContinuityModelResult:
    """Replica as colunas N:R e T:V da area '1 CONTINUIDADE'."""
    permanent_load = spec.peso_proprio + carga_capa(inputs.capa)
    total = carga_total(spec, inputs)
    vs_max = (
        permanent_load * inputs.vao / 2
        + (0.5 * inputs.sobrecarga * inputs.vao**2 + inputs.continuidade_kgf) / inputs.vao
    )
    xv0 = vs_max / total if total else 0
    ms_pos_max = vs_max * xv0 - 0.5 * total * xv0**2 - inputs.continuidade_kgf
    d = spec.altura_cm + inputs.capa - 3

    radicand = 1
    if inputs.continuidade_kgf:
        denominator = 0.425 * (10 * inputs.fck_capa / 1.4) * spec.sum_bw * d**2
        radicand = 1 - (1.4 * inputs.continuidade_kgf * 100) / denominator
    x = 0 if radicand < 0 else 1.25 * d * (1 - sqrt(radicand))
    as_negativa = 0.68 * (10 * inputs.fck_capa / 1.4) * spec.sum_bw * x / (10 * 500 / 1.15)
    taxa = as_negativa * 0.8 * (inputs.vao / 4) / inputs.vao if inputs.vao else 0

    return ContinuityModelResult(
        lp_type=spec.lp_type,
        vs_max=vs_max,
        xv0=xv0,
        ms_pos_max=ms_pos_max,
        d=d,
        sum_bw=spec.sum_bw,
        x=x,
        as_negativa=as_negativa,
        taxa_kg_m2=taxa,
    )
