from __future__ import annotations

from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agregador.configuration import Config
from agregador.model_b import aggregate_model_b
from agregador.standardization import StandardizedData
from agregador.validation import has_blocking_errors, validate
from agregador.weighting import GROUP_COLUMNS, aggregate_model_a, build_observations


def config() -> Config:
    return Config(path=Path("config/agregador.yaml").resolve(), values={
        "sample_cap": 5000,
        "missing_sample_fallback": 600,
        "missing_segment_sample_fallback": 300,
        "unknown_institute_weight": 0.5,
        "weights": {"quality": 0.5, "recency": 0.25, "sample": 0.25},
        "windows": {"government_days": 30, "contest_days": 30},
    })


def observation(day: str, value: float, group: str, institute: str = "Teste") -> dict[str, object]:
    record: dict[str, object] = {
        "product": "Lula3", "turno": "Nao_aplicavel", "tipo_cenario": "Nao_aplicavel", "cenario": "Avaliacao",
        "scenario_id": "scenario_governo", "adversario": "Nao_aplicavel", "nivel_geografico": "Brasil",
        "geografia": "Brasil", "segmento_tipo": "Total", "segmento": "Total", "vote_base": "Nao_aplicavel",
        "metric": "otimo_bom", "data_referencia": pd.Timestamp(day), "poll_group_id": group, "poll_id": f"poll_{group}",
        "instituto": institute, "tipo_pesquisa": "regular", "frequencia_original": "pontual", "amostra_total": 5000,
        "amostra_segmento": 5000, "margem_erro_pp": None, "nivel_confianca_pct": None, "quality_weight": 1.0,
        "institute_status": "Aprovado", "raw_value_pct": value, "adjusted_value_pct": value,
        "variance_numerator": (value / 100) * (1 - value / 100), "source_file": "synthetic.xlsx",
        "source_sheet": "Lula3", "source_row": 1, "raw_payload_json": "{}",
    }
    return record


class ModelATest(unittest.TestCase):
    def test_weight_memory_reconstructs_estimate(self) -> None:
        source = pd.DataFrame([observation("2026-01-01", 40.0, "a"), observation("2026-01-11", 50.0, "b")])
        aggregates, weights = aggregate_model_a(source, config())
        latest = aggregates.sort_values("reference_date").iloc[-1]
        memory = weights.loc[weights["reference_date"] == latest["reference_date"]]
        self.assertAlmostEqual(float(memory["normalized_weight"].sum()), 1.0, places=12)
        reconstructed = float((memory["normalized_weight"] * memory["adjusted_value_pct"]).sum())
        self.assertAlmostEqual(reconstructed, float(latest["estimate_pct"]), places=12)
        self.assertGreater(float(latest["estimate_pct"]), 45.0)

    def test_totals_generate_valid_votes_without_manual_conversion(self) -> None:
        row = observation("2026-01-01", 0.0, "contest")
        row.update({
            "turno": "2º turno", "tipo_cenario": "Estimulada", "cenario": "Único", "scenario_id": "sc_test",
            "adversario": "Candidato X", "product": "Confrontos", "vote_base": "Totais", "base_voto": "Totais", "lula_pct": 45.0,
            "adversario_pct": 35.0, "outros_candidatos_pct": 0.0, "brancos_nulos_indecisos_pct": 20.0,
            "peso_legacy": 1.0, "situacao_instituto": "Aprovado",
        })
        government = pd.DataFrame()
        contests = pd.DataFrame([row])
        data = StandardizedData(government=government, contests=contests, registry=pd.DataFrame(), issues=[])
        observations = build_observations(data)
        lula_valid = observations.loc[observations["metric"] == "lula_validos", "adjusted_value_pct"].iloc[0]
        opponent_valid = observations.loc[observations["metric"] == "adversario_validos", "adjusted_value_pct"].iloc[0]
        self.assertAlmostEqual(float(lula_valid), 56.25)
        self.assertAlmostEqual(float(opponent_valid), 43.75)

    def test_blank_published_evaluation_is_alert_not_zero_or_block(self) -> None:
        government = pd.DataFrame([{
            "data_referencia": pd.Timestamp("2026-01-01"), "instituto": "Teste", "tipo_pesquisa": "regular",
            "frequencia_original": "pontual", "amostra_total": 1000, "margem_erro_pp": None,
            "nivel_confianca_pct": None, "nivel_geografico": "Brasil", "geografia": "Brasil", "segmento_tipo": "Total",
            "segmento": "Total", "amostra_segmento": 1000, "otimo_bom_pct": None, "regular_pct": 20.0,
            "ruim_pessimo_pct": 40.0, "peso_legacy": 0.8, "source_row": 5,
        }])
        data = StandardizedData(government=government, contests=pd.DataFrame(), registry=pd.DataFrame(), issues=[])
        issues = validate(data)
        self.assertFalse(has_blocking_errors(issues))
        self.assertTrue(any(issue.field == "otimo_bom_pct" and issue.severity == "alerta" for issue in issues))

    def test_model_b_caps_concentration_by_institute(self) -> None:
        candidate = Config(path=Path("config/agregador.yaml").resolve(), values={
            **config().values,
            "model_b": {
                "half_life_days": 15, "maximum_age_days": 90, "quality_prior": 0.7,
                "quality_shrinkage": 0.5, "max_institute_weight_share": 0.35,
                "uncertainty_floor_pp": 1.5, "coverage": {"min_polls": 2, "min_institutes": 3},
            },
        })
        source = pd.DataFrame([
            observation("2026-01-01", 40.0, "atlas_1", "Atlas"),
            observation("2026-01-01", 42.0, "atlas_2", "Atlas"),
            observation("2026-01-01", 50.0, "ipec_1", "Ipec"),
            observation("2026-01-01", 48.0, "datafolha_1", "Datafolha"),
        ])
        _, weights = aggregate_model_b(source, candidate)
        atlas_share = weights.loc[weights["instituto"] == "Atlas", "normalized_weight"].sum()
        self.assertLessEqual(float(atlas_share), 0.35 + 1e-12)
        self.assertLessEqual(float(weights.groupby("instituto")["normalized_weight"].sum().max()), 0.35 + 1e-12)
        self.assertTrue(bool(weights["concentration_capped"].any()))

    def test_model_b_marks_infeasible_concentration_as_insufficient(self) -> None:
        candidate = Config(path=Path("config/agregador.yaml").resolve(), values={
            **config().values,
            "model_b": {
                "half_life_days": 15, "maximum_age_days": 90, "quality_prior": 0.7,
                "quality_shrinkage": 0.5, "max_institute_weight_share": 0.35,
                "uncertainty_floor_pp": 1.5, "coverage": {"min_polls": 2, "min_institutes": 3},
            },
        })
        source = pd.DataFrame([
            observation("2026-01-01", 40.0, "atlas_1", "Atlas"),
            observation("2026-01-01", 50.0, "ipec_1", "Ipec"),
        ])
        aggregates, weights = aggregate_model_b(source, candidate)
        self.assertEqual(aggregates.iloc[-1]["evidence_status"], "evidencia_insuficiente_concentracao")
        self.assertFalse(bool(weights["concentration_cap_feasible"].all()))


if __name__ == "__main__":
    unittest.main()
