"""Orquestrador parametrico para lajes alveolares."""

from itertools import product

import pandas as pd

from .lajes_alv_model import (
    EXPORT_COLUMNS,
    ITERATED_FIELDS,
    LAJE_ALV_SPECS,
    LajeAlvInputs,
    NAO_PASSA,
    run_continuity_model,
    run_shear_filling_model,
    run_simple_model,
    select_cables_by_demands,
)


ANALYSIS_SIMPLE = "sem continuidade"
ANALYSIS_CONTINUITY = "com continuidade"
ANALYSIS_FILLING = "com preenchimento"
ANALYSIS_CONTINUITY_FILLING = "com continuidade + preenchimento"
ANALYSIS_TYPES = (ANALYSIS_SIMPLE, ANALYSIS_CONTINUITY)
NEXT_LP_TYPE = {
    "LP15": "LP20",
    "LP20": "LP26,5",
    "LP26,5": "LP32",
    "LP32": "LP40",
    "LP40": "LP50",
}


RESULT_COLUMNS = [
    "analise",
    "continuidade_kgf",
    *EXPORT_COLUMNS,
    "carga_capa",
    "vs_max_continuidade",
    "xv0_continuidade",
    "ms_pos_max_continuidade",
    "as_negativa_continuidade",
    "taxa_continuidade_kg_m2",
    "preenchimento_alveolos",
    "comprimento_preenchimento_m",
    "VRd_sem_preenchimento",
    "VRd_preenchimento",
    "lp_sugerida",
    "mensagem",
]
LAJE_EXPORT_COLUMNS = [
    "lp_type",
    "analise",
    "continuidade_kgf",
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
    "preenchimento_alveolos",
    "comprimento_preenchimento_m",
    "VRd_preenchimento",
    "lp_sugerida",
    "mensagem",
]


def _range_values(start, stop, step, decimals=2):
    if step <= 0 or stop < start:
        return []
    count = int(round((stop - start) / step))
    values = [start + idx * step for idx in range(count + 1)]
    if not values or values[-1] < stop:
        values.append(stop)
    return [round(value, decimals) for value in values]


def _normalize_laje_types(value):
    selected = value or list(LAJE_ALV_SPECS)
    return [item for item in selected if item in LAJE_ALV_SPECS]


def _normalize_analysis_types(value):
    selected = value or list(ANALYSIS_TYPES)
    return [item for item in selected if item in ANALYSIS_TYPES]


def _empty_auto_fields() -> dict:
    return {
        "preenchimento_alveolos": 0,
        "comprimento_preenchimento_m": None,
        "VRd_sem_preenchimento": None,
        "VRd_preenchimento": None,
        "lp_sugerida": None,
        "mensagem": None,
    }


def build_laje_ranges(config: dict) -> dict:
    """Converte configuracao de UI/API em listas de valores para iteracao."""
    return {
        "sobrecarga": _range_values(
            config["sobrecarga_min"],
            config["sobrecarga_max"],
            config["sobrecarga_step"],
        ),
        "vao": _range_values(config["vao_min"], config["vao_max"], config["vao_step"]),
        "capa": config.get("capa_values", []),
        "fck_capa": config.get("fck_capa_values", []),
        "continuidade_kgf": _range_values(
            config.get("continuidade_min", 0),
            config.get("continuidade_max", 0),
            config.get("continuidade_step", 1),
        ),
        "lp_types": _normalize_laje_types(config.get("lp_types")),
        "analysis_types": _normalize_analysis_types(config.get("analysis_types")),
    }


def run_laje_case(params: dict) -> dict:
    """Executa uma combinacao de laje alveolar e retorna resultado tabular."""
    try:
        lp_type = params["lp_type"]
        analysis_type = params.get("analise", ANALYSIS_SIMPLE)
        spec = LAJE_ALV_SPECS[lp_type]
        inputs = LajeAlvInputs(
            sobrecarga=params["sobrecarga"],
            vao=params["vao"],
            capa=params["capa"],
            fck_capa=params["fck_capa"],
            continuidade_kgf=params.get("continuidade_kgf", 0),
        )
        simple = run_simple_model(spec, inputs)
        continuity = (
            run_continuity_model(spec, inputs)
            if analysis_type == ANALYSIS_CONTINUITY
            else None
        )
        display_analysis = (
            ANALYSIS_SIMPLE
            if inputs.continuidade_kgf == 0
            else analysis_type
        )
        cabos = simple.cabos
        status = simple.status
        momento = simple.momento_fletor
        cortante = simple.forca_cortante
        if continuity is not None and inputs.continuidade_kgf > 0:
            momento = continuity.ms_pos_max
            cortante = continuity.vs_max
            cabos = select_cables_by_demands(spec, inputs.vao, momento, cortante, check_span=False)
            status = "PASSA" if cabos != "NAO PASSA" else "NAO PASSA"

        result = {
            "analise": display_analysis,
            "continuidade_kgf": inputs.continuidade_kgf if analysis_type == ANALYSIS_CONTINUITY else 0,
            "lp_type": simple.lp_type,
            "vao": simple.vao,
            "sobrecarga": simple.sobrecarga,
            "capa": simple.capa,
            "fck_capa": simple.fck_capa,
            "peso_proprio": simple.peso_proprio,
            "carga_total": simple.carga_total,
            "momento_fletor": momento,
            "forca_cortante": cortante,
            "cabos": cabos,
            "status": status,
            "carga_capa": simple.carga_capa,
            "vs_max_continuidade": None,
            "xv0_continuidade": None,
            "ms_pos_max_continuidade": None,
            "as_negativa_continuidade": None,
            "taxa_continuidade_kg_m2": None,
            **_empty_auto_fields(),
        }
        if continuity is not None:
            result.update(
                {
                    "vs_max_continuidade": continuity.vs_max,
                    "xv0_continuidade": continuity.xv0,
                    "ms_pos_max_continuidade": continuity.ms_pos_max,
                    "as_negativa_continuidade": continuity.as_negativa,
                    "taxa_continuidade_kg_m2": continuity.taxa_kg_m2,
                }
            )
        if params.get("auto_ajuste") and result["status"] != "PASSA":
            return _auto_adjust_failed_laje(params, result, spec, inputs)
        return result
    except Exception as exc:
        return {
            "analise": params.get("analise"),
            "continuidade_kgf": params.get("continuidade_kgf"),
            "lp_type": params.get("lp_type"),
            "vao": params.get("vao"),
            "sobrecarga": params.get("sobrecarga"),
            "capa": params.get("capa"),
            "fck_capa": params.get("fck_capa"),
            "peso_proprio": None,
            "carga_total": None,
            "momento_fletor": None,
            "forca_cortante": None,
            "cabos": None,
            "status": "ERRO",
            "erro_msg": str(exc),
            **_empty_auto_fields(),
        }


def _auto_adjust_failed_laje(
    params: dict,
    initial: dict,
    spec,
    inputs: LajeAlvInputs,
) -> dict:
    if spec.lp_type != "LP26,5":
        return _with_lp_suggestion(initial, spec.lp_type)

    for continuidade in range(100, 5001, 100):
        adjusted_inputs = LajeAlvInputs(
            sobrecarga=inputs.sobrecarga,
            vao=inputs.vao,
            capa=inputs.capa,
            fck_capa=inputs.fck_capa,
            continuidade_kgf=continuidade,
        )
        continuity = run_continuity_model(spec, adjusted_inputs)
        cabos = select_cables_by_demands(
            spec,
            adjusted_inputs.vao,
            continuity.ms_pos_max,
            continuity.vs_max,
            check_span=False,
        )
        result = _with_continuity_result(initial, adjusted_inputs, continuity, cabos)
        if result["status"] == "PASSA":
            result["mensagem"] = f"Aprovada automaticamente com continuidade de {continuidade} kgf."
            return result

    filled = _try_filling(initial, spec, inputs, initial["momento_fletor"], initial["forca_cortante"])
    if filled["status"] == "PASSA":
        return filled

    for continuidade in range(100, 5001, 100):
        adjusted_inputs = LajeAlvInputs(
            sobrecarga=inputs.sobrecarga,
            vao=inputs.vao,
            capa=inputs.capa,
            fck_capa=inputs.fck_capa,
            continuidade_kgf=continuidade,
        )
        continuity = run_continuity_model(spec, adjusted_inputs)
        base = _with_continuity_result(initial, adjusted_inputs, continuity, NAO_PASSA)
        filled = _try_filling(base, spec, adjusted_inputs, continuity.ms_pos_max, continuity.vs_max)
        if filled["status"] == "PASSA":
            filled["analise"] = ANALYSIS_CONTINUITY_FILLING
            filled["continuidade_kgf"] = continuidade
            filled.update(
                {
                    "vs_max_continuidade": continuity.vs_max,
                    "xv0_continuidade": continuity.xv0,
                    "ms_pos_max_continuidade": continuity.ms_pos_max,
                    "as_negativa_continuidade": continuity.as_negativa,
                    "taxa_continuidade_kg_m2": continuity.taxa_kg_m2,
                }
            )
            return filled

    return _with_lp_suggestion(initial, spec.lp_type)


def _with_continuity_result(
    initial: dict,
    inputs: LajeAlvInputs,
    continuity,
    cabos: str,
) -> dict:
    result = initial.copy()
    result.update(
        {
            "analise": ANALYSIS_CONTINUITY,
            "continuidade_kgf": inputs.continuidade_kgf,
            "momento_fletor": continuity.ms_pos_max,
            "forca_cortante": continuity.vs_max,
            "cabos": cabos,
            "status": "PASSA" if cabos != NAO_PASSA else NAO_PASSA,
            "vs_max_continuidade": continuity.vs_max,
            "xv0_continuidade": continuity.xv0,
            "ms_pos_max_continuidade": continuity.ms_pos_max,
            "as_negativa_continuidade": continuity.as_negativa,
            "taxa_continuidade_kg_m2": continuity.taxa_kg_m2,
        }
    )
    return result


def _try_filling(
    base: dict,
    spec,
    inputs: LajeAlvInputs,
    momento: float,
    cortante: float,
) -> dict:
    cabos = select_cables_by_demands(spec, inputs.vao, momento, 0, check_span=True)
    if cabos == NAO_PASSA:
        return base
    filling = run_shear_filling_model(spec, inputs, cabos, cortante)
    result = base.copy()
    result.update(
        {
            "analise": ANALYSIS_FILLING,
            "cabos": cabos,
            "preenchimento_alveolos": filling.n_alveolos_preenchidos,
            "comprimento_preenchimento_m": filling.comprimento_preenchimento_m,
            "VRd_sem_preenchimento": filling.vrd_sem_preenchimento,
            "VRd_preenchimento": filling.vrd_preenchimento,
            "status": filling.status,
            "mensagem": (
                f"Aprovada automaticamente com preenchimento de "
                f"{filling.n_alveolos_preenchidos} alveolos."
                if filling.status == "PASSA"
                else base.get("mensagem")
            ),
        }
    )
    return result


def _with_lp_suggestion(result: dict, lp_type: str) -> dict:
    suggested = NEXT_LP_TYPE.get(lp_type)
    output = result.copy()
    output["lp_sugerida"] = suggested
    if suggested:
        output["mensagem"] = f"Nao passou com ajustes automaticos. Sugere aumentar a laje para {suggested}."
    return output


def _iter_laje_combinations(ranges: dict):
    base_keys = (*ITERATED_FIELDS, "lp_type")
    values = (
        ranges["sobrecarga"],
        ranges["vao"],
        ranges["capa"],
        ranges["fck_capa"],
        _normalize_laje_types(ranges.get("lp_types")),
    )
    analysis_types = _normalize_analysis_types(ranges.get("analysis_types"))
    continuity_values = ranges.get("continuidade_kgf") or [0]

    for combo in product(*values):
        base_params = dict(zip(base_keys, combo))
        if ANALYSIS_SIMPLE in analysis_types and (
            ANALYSIS_CONTINUITY not in analysis_types or 0 not in continuity_values
        ):
            yield {**base_params, "analise": ANALYSIS_SIMPLE, "continuidade_kgf": 0}
        if ANALYSIS_CONTINUITY in analysis_types:
            for continuidade_kgf in continuity_values:
                yield {
                    **base_params,
                    "analise": ANALYSIS_CONTINUITY,
                    "continuidade_kgf": continuidade_kgf,
                }


def count_laje_parametric(ranges: dict) -> int:
    """Conta as combinacoes de lajes alveolares."""
    analysis_types = _normalize_analysis_types(ranges.get("analysis_types"))
    continuity_values = ranges.get("continuidade_kgf") or [0]
    analysis_multiplier = 0
    if ANALYSIS_SIMPLE in analysis_types and (
        ANALYSIS_CONTINUITY not in analysis_types or 0 not in continuity_values
    ):
        analysis_multiplier += 1
    if ANALYSIS_CONTINUITY in analysis_types:
        analysis_multiplier += len(continuity_values)

    return (
        len(ranges["sobrecarga"])
        * len(ranges["vao"])
        * len(ranges["capa"])
        * len(ranges["fck_capa"])
        * len(_normalize_laje_types(ranges.get("lp_types")))
        * analysis_multiplier
    )


def run_laje_parametric(ranges: dict, progress_callback=None) -> pd.DataFrame:
    """Executa o estudo parametrico de lajes alveolares."""
    total = count_laje_parametric(ranges)
    results = []
    for idx, params in enumerate(_iter_laje_combinations(ranges), start=1):
        results.append(run_laje_case(params))
        if progress_callback is not None:
            progress_callback(idx, total)

    df = pd.DataFrame(results)
    if not df.empty:
        ordered = [col for col in RESULT_COLUMNS if col in df.columns]
        extra = [col for col in df.columns if col not in ordered]
        df = df[ordered + extra]
    df.attrs["ranges"] = ranges.copy()
    return df


def export_laje_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena as colunas principais para exportacao de lajes alveolares."""
    ordered = [col for col in LAJE_EXPORT_COLUMNS if col in df.columns]
    extra = [col for col in df.columns if col not in ordered]
    result = df[ordered + extra].copy()
    result.attrs.update(df.attrs)
    return result
