from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from .configuration import Config
from .domain import is_present, stable_id
from .standardization import StandardizedData


GROUP_COLUMNS = [
    "product", "turno", "tipo_cenario", "cenario", "scenario_id", "adversario",
    "nivel_geografico", "geografia", "segmento_tipo", "segmento", "vote_base", "metric",
]


def _common(row: pd.Series, product: str, metric: str, value: float, variance_numerator: float, vote_base: str, turno: str, tipo_cenario: str, cenario: str, adversario: str, model_b_variance_numerator: float | None = None) -> dict[str, Any]:
    payload = {
        "poll_group_id": row["poll_group_id"], "product": product, "metric": metric,
        "scenario_id": row["scenario_id"], "adversario": adversario,
        "nivel_geografico": row["nivel_geografico"], "geografia": row["geografia"],
        "segmento_tipo": row["segmento_tipo"], "segmento": row["segmento"], "vote_base": vote_base,
    }
    return {
        **payload,
        "poll_id": stable_id("poll", payload),
        "turno": turno,
        "tipo_cenario": tipo_cenario,
        "cenario": cenario,
        "data_referencia": row["data_referencia"],
        "instituto": row["instituto"],
        "tipo_pesquisa": row["tipo_pesquisa"],
        "frequencia_original": row["frequencia_original"],
        "amostra_total": row["amostra_total"],
        "amostra_segmento": row["amostra_segmento"],
        "margem_erro_pp": row["margem_erro_pp"],
        "nivel_confianca_pct": row["nivel_confianca_pct"],
        "quality_weight": row["peso_legacy"],
        "institute_status": row["situacao_instituto"],
        "raw_value_pct": value,
        "adjusted_value_pct": value,
        "variance_numerator": variance_numerator,
        "model_b_variance_numerator": variance_numerator if model_b_variance_numerator is None else model_b_variance_numerator,
        "source_file": row["source_file"],
        "source_sheet": row["source_sheet"],
        "source_row": row["source_row"],
        "raw_payload_json": row["raw_payload_json"],
    }


def _p_variance(value: float) -> float:
    proportion = value / 100
    return proportion * (1 - proportion)


def _difference_variance(value_a: float, value_b: float) -> float:
    """Variância multinomial de A − B, em escala de proporção."""
    a, b = value_a / 100, value_b / 100
    return a + b - (a - b) ** 2


def build_observations(data: StandardizedData) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for _, row in data.government.iterrows():
        for column, metric in [("otimo_bom_pct", "otimo_bom"), ("regular_pct", "regular"), ("ruim_pessimo_pct", "ruim_pessimo")]:
            if is_present(row[column]):
                value = float(row[column])
                records.append(_common(row, "Lula3", metric, value, _p_variance(value), "Nao_aplicavel", "Nao_aplicavel", "Nao_aplicavel", "Avaliacao", "Nao_aplicavel"))
        if is_present(row["otimo_bom_pct"]) and is_present(row["ruim_pessimo_pct"]):
            good, bad = float(row["otimo_bom_pct"]), float(row["ruim_pessimo_pct"])
            records.append(_common(row, "Lula3", "favorabilidade_liquida", good - bad, _p_variance(good) + _p_variance(bad), "Nao_aplicavel", "Nao_aplicavel", "Nao_aplicavel", "Avaliacao", "Nao_aplicavel", _difference_variance(good, bad)))
    for _, row in data.contests.iterrows():
        lula, opponent, others = float(row["lula_pct"]), float(row["adversario_pct"]), float(row["outros_candidatos_pct"])
        common_args = ("Confrontos",)
        if row["base_voto"] == "Totais":
            if is_present(row["brancos_nulos_indecisos_pct"]):
                no_vote = float(row["brancos_nulos_indecisos_pct"])
                records.append(_common(
                    row, *common_args, "nao_voto_totais", no_vote, _p_variance(no_vote),
                    "Totais", row["turno"], row["tipo_cenario"], row["cenario"], row["adversario"], _p_variance(no_vote),
                ))
            for metric, value, variance, model_b_variance in [
                ("lula_totais", lula, _p_variance(lula), _p_variance(lula)),
                ("adversario_totais", opponent, _p_variance(opponent), _p_variance(opponent)),
                ("margem_totais", lula - opponent, _p_variance(lula) + _p_variance(opponent), _difference_variance(lula, opponent)),
            ]:
                records.append(_common(row, *common_args, metric, value, variance, "Totais", row["turno"], row["tipo_cenario"], row["cenario"], row["adversario"], model_b_variance))
            denominator = lula + opponent if row["turno"] == "2º turno" else lula + opponent + others
            if denominator > 0:
                lula_valid, opponent_valid = lula / denominator * 100, opponent / denominator * 100
                for metric, value, variance, model_b_variance in [
                    ("lula_validos", lula_valid, _p_variance(lula_valid), _p_variance(lula_valid)),
                    ("adversario_validos", opponent_valid, _p_variance(opponent_valid), _p_variance(opponent_valid)),
                    ("margem_validos", lula_valid - opponent_valid, _p_variance(lula_valid) + _p_variance(opponent_valid), _difference_variance(lula_valid, opponent_valid)),
                ]:
                    records.append(_common(row, *common_args, metric, value, variance, "Validos_derivados", row["turno"], row["tipo_cenario"], row["cenario"], row["adversario"], model_b_variance))
        else:
            for metric, value, variance, model_b_variance in [
                ("lula_validos", lula, _p_variance(lula), _p_variance(lula)),
                ("adversario_validos", opponent, _p_variance(opponent), _p_variance(opponent)),
                ("margem_validos", lula - opponent, _p_variance(lula) + _p_variance(opponent), _difference_variance(lula, opponent)),
            ]:
                records.append(_common(row, *common_args, metric, value, variance, "Validos_publicados", row["turno"], row["tipo_cenario"], row["cenario"], row["adversario"], model_b_variance))
    return pd.DataFrame.from_records(records)


def _sample_used(row: pd.Series, config: Config) -> tuple[float, str]:
    total = row["amostra_total"] if is_present(row["amostra_total"]) else None
    segment = row["amostra_segmento"] if is_present(row["amostra_segmento"]) else None
    if row["segmento_tipo"] == "Total":
        if segment is not None:
            return float(segment), "amostra_segmento"
        if total is not None:
            return float(total), "amostra_total"
        return float(config.value("missing_sample_fallback")), "fallback_amostra_ausente"
    if segment is not None:
        return float(segment), "amostra_segmento"
    fallback = float(config.value("missing_segment_sample_fallback"))
    if total is not None:
        return min(float(total), fallback), "fallback_recorte_sem_amostra"
    return fallback, "fallback_recorte_sem_amostra"


def _window_for(row: pd.Series, config: Config) -> int:
    windows = config.nested("windows")
    return int(windows["government_days"] if row["product"] == "Lula3" else windows["contest_days"])


def aggregate_model_a(observations: pd.DataFrame, config: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    if observations.empty:
        return pd.DataFrame(), pd.DataFrame()
    weight_config = config.nested("weights")
    sample_cap = float(config.value("sample_cap"))
    z_value = 1.959963984540054
    prepared = observations.copy()
    samples = prepared.apply(lambda row: _sample_used(row, config), axis=1)
    prepared["sample_used"] = [item[0] for item in samples]
    prepared["sample_source"] = [item[1] for item in samples]
    prepared["quality_component"] = prepared["quality_weight"].fillna(float(config.value("unknown_institute_weight"))).astype(float)
    prepared["sample_component"] = np.minimum(prepared["sample_used"], sample_cap) / sample_cap
    aggregates: list[dict[str, Any]] = []
    memories: list[dict[str, Any]] = []
    for _, curve in prepared.groupby(GROUP_COLUMNS, dropna=False, sort=False):
        curve = curve.sort_values("data_referencia").reset_index(drop=True)
        window = _window_for(curve.iloc[0], config)
        dates = curve["data_referencia"].to_numpy(dtype="datetime64[D]").astype("int64")
        reference_dates = np.unique(dates)
        quality = curve["quality_component"].to_numpy(dtype=float)
        sample_component = curve["sample_component"].to_numpy(dtype=float)
        sample_used = curve["sample_used"].to_numpy(dtype=float)
        values = curve["adjusted_value_pct"].to_numpy(dtype=float)
        variance_numerator = curve["variance_numerator"].to_numpy(dtype=float)
        poll_groups = curve["poll_group_id"].to_numpy()
        institutes = curve["instituto"].to_numpy()
        base_records = curve.to_dict(orient="records")
        group_values = {column: base_records[0][column] for column in GROUP_COLUMNS}
        metric = str(group_values["metric"])
        is_margin = metric.startswith("margem") or metric == "favorabilidade_liquida"
        lower_limit, upper_limit = (-100.0, 100.0) if is_margin else (0.0, 100.0)
        interval_type = "sampling_interval_legacy" if not metric.startswith("margem") else "sampling_interval_legacy_approx"
        for reference_number in reference_dates:
            ages = reference_number - dates
            indexes = np.flatnonzero((ages >= 0) & (ages <= window))
            if not len(indexes):
                continue
            ages_selected = ages[indexes]
            time_component = np.maximum(0, 1 - ages_selected / window)
            raw_weight = (
                quality[indexes] ** float(weight_config["quality"])
                * time_component ** float(weight_config["recency"])
                * sample_component[indexes] ** float(weight_config["sample"])
            )
            positive = raw_weight > 0
            indexes = indexes[positive]
            raw_weight = raw_weight[positive]
            time_component = time_component[positive]
            ages_selected = ages_selected[positive]
            if not len(indexes):
                continue
            normalized_weight = raw_weight / raw_weight.sum()
            estimate = float(np.sum(normalized_weight * values[indexes]))
            variance = float(np.sum(normalized_weight ** 2 * variance_numerator[indexes] / sample_used[indexes]))
            standard_error_pp = float(np.sqrt(max(variance, 0)) * 100)
            date = pd.Timestamp(np.datetime64(int(reference_number), "D"))
            aggregates.append({
                **group_values,
                "reference_date": date,
                "estimate_pct": estimate,
                "interval_low_pct": max(lower_limit, estimate - z_value * standard_error_pp),
                "interval_high_pct": min(upper_limit, estimate + z_value * standard_error_pp),
                "interval_type": interval_type,
                "standard_error_pp": standard_error_pp,
                "poll_count": int(len(np.unique(poll_groups[indexes]))),
                "institute_count": int(len(np.unique(institutes[indexes]))),
                "effective_information": float(1 / np.sum(normalized_weight ** 2)),
            })
            for position, age, time, weight, normalised in zip(indexes, ages_selected, time_component, raw_weight, normalized_weight, strict=True):
                memory = base_records[int(position)].copy()
                # O payload bruto já está em Bronze; repeti-lo por ponto calculado tornaria a memória de pesos desnecessariamente grande.
                memory.pop("raw_payload_json", None)
                memory.update({
                    "reference_date": date,
                    "idade_dias": int(age),
                    "time_component": float(time),
                    "raw_weight": float(weight),
                    "normalized_weight": float(normalised),
                    "estimate_pct": estimate,
                    "standard_error_pp": standard_error_pp,
                })
                memories.append(memory)
    return pd.DataFrame.from_records(aggregates), pd.DataFrame.from_records(memories)
