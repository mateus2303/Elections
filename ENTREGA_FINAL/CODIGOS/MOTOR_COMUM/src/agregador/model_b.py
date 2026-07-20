from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np
import pandas as pd

from .configuration import Config
from .domain import is_present
from .weighting import GROUP_COLUMNS, _sample_used


def candidate_config(config: Config) -> Config:
    """Deriva uma configuração isolada para o Modelo B sem alterar o baseline."""
    values = deepcopy(config.values)
    settings = config.nested("model_b")
    values["methodology_version"] = settings["methodology_version"]
    values["coverage"] = deepcopy(settings["coverage"])
    probability = deepcopy(values.get("probability", {}))
    probability["experimental"] = True
    probability["uncertainty_floor_pp"] = float(settings["uncertainty_floor_pp"])
    values["probability"] = probability
    return Config(path=config.path, values=values)


def _z_value(confidence: float | None) -> float:
    if confidence is None:
        return 1.959963984540054
    nearest = min([(90, 1.6448536269514722), (95, 1.959963984540054), (99, 2.5758293035489004)], key=lambda item: abs(item[0] - confidence))
    return nearest[1]


def _effective_sample(row: pd.Series, config: Config, settings: dict[str, Any]) -> tuple[float, str]:
    declared, source = _sample_used(row, config)
    cap = float(config.value("sample_cap"))
    if row["segmento_tipo"] != "Total" or not is_present(row["margem_erro_pp"]):
        return min(declared, cap), source
    margin = float(row["margem_erro_pp"]) / 100
    if margin <= 0:
        return min(declared, cap), source
    confidence = float(row["nivel_confianca_pct"]) if is_present(row["nivel_confianca_pct"]) else float(config.value("confidence_level", 0.95)) * 100
    implied = (_z_value(confidence) ** 2 * 0.25) / (margin ** 2)
    return min(declared, implied, cap), "min_declarada_implicita_cap"


def _capped_weights(raw_weight: np.ndarray, groups: np.ndarray, maximum_share: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, bool]:
    """Aplica teto por instituto antes da normalização, preservando a soma igual a 1."""
    preliminary = raw_weight / raw_weight.sum()
    unique_groups, inverse = np.unique(groups.astype(str), return_inverse=True)
    group_weights = np.bincount(inverse, weights=preliminary, minlength=len(unique_groups))
    cap_feasible = len(unique_groups) * maximum_share >= 1 - 1e-12
    if not cap_feasible or maximum_share >= 1:
        return preliminary, preliminary, np.zeros(len(preliminary), dtype=bool), cap_feasible
    final_group_weights = np.zeros(len(unique_groups))
    available = np.ones(len(unique_groups), dtype=bool)
    remaining = 1.0
    while available.any():
        available_weights = group_weights[available]
        if available_weights.sum() <= 0:
            final_group_weights[available] = remaining / available.sum()
            break
        provisional = available_weights / available_weights.sum() * remaining
        positions = np.flatnonzero(available)
        over_cap = provisional > maximum_share + 1e-12
        if not over_cap.any():
            final_group_weights[positions] = provisional
            break
        capped_positions = positions[over_cap]
        final_group_weights[capped_positions] = maximum_share
        available[capped_positions] = False
        remaining = 1 - final_group_weights[~available].sum()
        if remaining <= 0:
            final_group_weights[available] = 0
            break
    post = np.zeros(len(preliminary))
    for group_index, weight in enumerate(group_weights):
        members = inverse == group_index
        if weight > 0:
            post[members] = preliminary[members] * final_group_weights[group_index] / weight
    capped = final_group_weights[inverse] < group_weights[inverse] - 1e-12
    return preliminary, post, capped, cap_feasible


def aggregate_model_b(observations: pd.DataFrame, config: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Modelo candidato com meia-vida, n efetivo, cap de concentração e incerteza ampliada."""
    if observations.empty:
        return pd.DataFrame(), pd.DataFrame()
    settings = config.nested("model_b")
    weights = config.nested("weights")
    sample_cap = float(config.value("sample_cap"))
    half_life = float(settings["half_life_days"])
    maximum_age = int(settings["maximum_age_days"])
    quality_prior = float(settings["quality_prior"])
    shrinkage = float(settings["quality_shrinkage"])
    maximum_share = float(settings["max_institute_weight_share"])
    floor_variance = (float(settings["uncertainty_floor_pp"]) / 100) ** 2
    z_value = 1.959963984540054
    prepared = observations.copy()
    effective = prepared.apply(lambda row: _effective_sample(row, config, settings), axis=1)
    prepared["effective_sample_size"] = [item[0] for item in effective]
    prepared["effective_sample_source"] = [item[1] for item in effective]
    raw_quality = prepared["quality_weight"].fillna(float(config.value("unknown_institute_weight"))).astype(float)
    prepared["quality_raw"] = raw_quality
    prepared["quality_component"] = quality_prior + shrinkage * (raw_quality - quality_prior)
    prepared["sample_component"] = np.minimum(prepared["effective_sample_size"], sample_cap) / sample_cap
    aggregates: list[dict[str, Any]] = []
    memories: list[dict[str, Any]] = []
    for _, curve in prepared.groupby(GROUP_COLUMNS, dropna=False, sort=False):
        curve = curve.sort_values("data_referencia").reset_index(drop=True)
        dates = curve["data_referencia"].to_numpy(dtype="datetime64[D]").astype("int64")
        reference_dates = np.unique(dates)
        quality = curve["quality_component"].to_numpy(dtype=float)
        sample_component = curve["sample_component"].to_numpy(dtype=float)
        effective_sample = curve["effective_sample_size"].to_numpy(dtype=float)
        values = curve["adjusted_value_pct"].to_numpy(dtype=float)
        variance_column = "model_b_variance_numerator" if "model_b_variance_numerator" in curve else "variance_numerator"
        covariance_variance = curve[variance_column].to_numpy(dtype=float)
        poll_groups = curve["poll_group_id"].to_numpy()
        institutes = curve["instituto"].to_numpy()
        # Toda onda publicada entra uma única vez; o teto é conservador e vale para o instituto,
        # inclusive quando ele publica uma série tracking.
        concentration_groups = np.array([f"instituto:{institute}" for institute in institutes])
        base_records = curve.to_dict(orient="records")
        group_values = {column: base_records[0][column] for column in GROUP_COLUMNS}
        metric = str(group_values["metric"])
        is_margin = metric.startswith("margem") or metric == "favorabilidade_liquida"
        lower_limit, upper_limit = (-100.0, 100.0) if is_margin else (0.0, 100.0)
        for reference_number in reference_dates:
            ages = reference_number - dates
            indexes = np.flatnonzero((ages >= 0) & (ages <= maximum_age))
            if not len(indexes):
                continue
            ages_selected = ages[indexes]
            time_component = np.power(0.5, ages_selected / half_life)
            raw_weight = (
                quality[indexes] ** float(weights["quality"])
                * time_component ** float(weights["recency"])
                * sample_component[indexes] ** float(weights["sample"])
            )
            positive = raw_weight > 0
            indexes, ages_selected, time_component, raw_weight = indexes[positive], ages_selected[positive], time_component[positive], raw_weight[positive]
            if not len(indexes):
                continue
            preliminary, normalized_weight, capped, cap_feasible = _capped_weights(raw_weight, concentration_groups[indexes], maximum_share)
            estimate = float(np.sum(normalized_weight * values[indexes]))
            sampling_variance = float(np.sum(normalized_weight ** 2 * covariance_variance[indexes] / effective_sample[indexes]))
            effective_information = float(1 / np.sum(normalized_weight ** 2))
            observed_dispersion = float(np.sum(normalized_weight * ((values[indexes] - estimate) / 100) ** 2))
            expected_dispersion = float(np.sum(normalized_weight * covariance_variance[indexes] / effective_sample[indexes]))
            heterogeneity_variance = max(0.0, observed_dispersion - expected_dispersion) / max(effective_information, 1.0)
            total_variance = sampling_variance + heterogeneity_variance + floor_variance
            standard_error_pp = float(np.sqrt(total_variance) * 100)
            poll_count = int(len(np.unique(poll_groups[indexes])))
            institute_count = int(len(np.unique(institutes[indexes])))
            coverage = settings["coverage"]
            if not cap_feasible:
                evidence_status = "evidencia_insuficiente_concentracao"
            elif poll_count < int(coverage["min_polls"]) or institute_count < int(coverage["min_institutes"]):
                evidence_status = "evidencia_insuficiente"
            else:
                evidence_status = "evidencia_suficiente"
            date = pd.Timestamp(np.datetime64(int(reference_number), "D"))
            aggregates.append({
                **group_values,
                "reference_date": date,
                "estimate_pct": estimate,
                "interval_low_pct": max(lower_limit, estimate - z_value * standard_error_pp),
                "interval_high_pct": min(upper_limit, estimate + z_value * standard_error_pp),
                "interval_type": "uncertainty_interval_model_b_experimental",
                "standard_error_pp": standard_error_pp,
                "sampling_variance": sampling_variance,
                "heterogeneity_variance": heterogeneity_variance,
                "uncertainty_floor_pp": float(settings["uncertainty_floor_pp"]),
                "poll_count": poll_count,
                "institute_count": institute_count,
                "effective_information": effective_information,
                "concentration_cap_feasible": cap_feasible,
                "evidence_status": evidence_status,
            })
            for position, age, time, raw, pre_cap, normalised, was_capped in zip(indexes, ages_selected, time_component, raw_weight, preliminary, normalized_weight, capped, strict=True):
                memory = base_records[int(position)].copy()
                memory.pop("raw_payload_json", None)
                memory.update({
                    "reference_date": date,
                    "idade_dias": int(age),
                    "time_component": float(time),
                    "raw_weight": float(raw),
                    "pre_cap_weight": float(pre_cap),
                    "normalized_weight": float(normalised),
                    "concentration_group": str(concentration_groups[int(position)]),
                    "concentration_capped": bool(was_capped),
                    "concentration_cap_feasible": cap_feasible,
                    "estimate_pct": estimate,
                    "standard_error_pp": standard_error_pp,
                    "sampling_variance": sampling_variance,
                    "heterogeneity_variance": heterogeneity_variance,
                })
                memories.append(memory)
    return pd.DataFrame.from_records(aggregates), pd.DataFrame.from_records(memories)
