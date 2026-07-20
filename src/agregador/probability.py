from __future__ import annotations

from math import erf, sqrt

import pandas as pd

from .configuration import Config


def _normal_cdf(value: float) -> float:
    return 0.5 * (1 + erf(value / sqrt(2)))


def leadership_probability(aggregates: pd.DataFrame, config: Config) -> pd.DataFrame:
    columns = [
        "scenario_id", "opponent", "geographic_level", "geography", "segment_type", "segment",
        "reference_date", "probability_type", "probability_lula", "experimental_flag", "vote_base", "reason",
    ]
    if aggregates.empty or not bool(config.nested("probability").get("enabled", False)):
        return pd.DataFrame(columns=columns)
    coverage = config.nested("coverage")
    probability_config = config.nested("probability")
    floor = float(probability_config.get("uncertainty_floor_pp", 0.0))
    records: list[dict[str, object]] = []
    margin_rows = aggregates.loc[aggregates["metric"].str.startswith("margem", na=False)]
    for _, row in margin_rows.iterrows():
        reason = ""
        probability: float | None = None
        if str(row.get("evidence_status", "evidencia_suficiente")) == "evidencia_insuficiente_concentracao":
            reason = "evidencia_insuficiente_concentracao"
        elif int(row["poll_count"]) < int(coverage.get("min_polls", 1)):
            reason = "evidencia_insuficiente_pesquisas"
        elif int(row["institute_count"]) < int(coverage.get("min_institutes", 1)):
            reason = "evidencia_insuficiente_institutos"
        else:
            error = max(float(row["standard_error_pp"]), floor)
            if error <= 0:
                reason = "incerteza_indisponivel"
            else:
                probability = _normal_cdf(float(row["estimate_pct"]) / error)
        records.append({
            "scenario_id": row["scenario_id"],
            "opponent": row["adversario"],
            "geographic_level": row["nivel_geografico"],
            "geography": row["geografia"],
            "segment_type": row["segmento_tipo"],
            "segment": row["segmento"],
            "reference_date": row["reference_date"],
            "probability_type": "probabilidade_lideranca_atual",
            "probability_lula": probability,
            "experimental_flag": bool(probability_config.get("experimental", True)),
            "vote_base": row["vote_base"],
            "reason": reason,
        })
    return pd.DataFrame.from_records(records, columns=columns)
