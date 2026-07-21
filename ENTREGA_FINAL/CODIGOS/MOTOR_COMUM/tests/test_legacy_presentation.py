from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agregador.configuration import Config
from agregador.legacy_presentation import (
    _legacy_second_round_input,
    _valid_votes,
    _weekly_tracking_from_daily,
    generate_legacy_model_a,
)
from agregador.standardization import StandardizedData


def config() -> Config:
    return Config(path=Path("config/agregador.yaml").resolve(), values={
        "sample_cap": 5000,
        "missing_sample_fallback": 600,
        "missing_segment_sample_fallback": 300,
        "unknown_institute_weight": 0.5,
        "weights": {"quality": 0.5, "recency": 0.25, "sample": 0.25},
    })


def common(day: str, institute: str, sample: int = 2000) -> dict[str, object]:
    return {
        "data_referencia": pd.Timestamp(day), "instituto": institute, "amostra_total": sample,
        "amostra_segmento": sample, "peso_legacy": 1.0, "nivel_geografico": "Brasil",
        "geografia": "Brasil", "segmento_tipo": "Total", "segmento": "Total",
        "tipo_pesquisa": "regular", "frequencia_original": "pontual",
    }


class LegacyPresentationTest(unittest.TestCase):
    def test_daily_tracking_becomes_one_complete_week_and_then_valid_votes(self) -> None:
        base = {
            **common("2025-12-08", "Atlas", 1800),
            "turno": "2 turno", "tipo_cenario": "Estimulada", "cenario": "Unico", "scenario_id": "sc_unico",
            "adversario": "Flavio", "base_voto": "Totais", "tipo_pesquisa": "tracking",
            "frequencia_original": "diaria", "outros_candidatos_pct": 0.0,
        }
        daily_rows = []
        for offset in range(7):
            daily_rows.append({
                **base, "data_referencia": pd.Timestamp("2025-12-08") + pd.Timedelta(days=offset),
                "lula_pct": 50.0 + offset, "adversario_pct": 40.0 - offset,
                "brancos_nulos_indecisos_pct": 10.0,
            })
        partial = {
            **base, "data_referencia": pd.Timestamp("2025-12-07"), "lula_pct": 90.0,
            "adversario_pct": 5.0, "brancos_nulos_indecisos_pct": 5.0,
        }
        weekly = {
            **base, "data_referencia": pd.Timestamp("2025-12-21"), "lula_pct": 48.0,
            "adversario_pct": 44.0, "brancos_nulos_indecisos_pct": 8.0, "frequencia_original": "semanal",
        }
        daily = pd.DataFrame([partial, *daily_rows])
        reconstructed = _weekly_tracking_from_daily(daily)
        self.assertEqual(len(reconstructed), 1)
        self.assertEqual(reconstructed.iloc[0]["data_referencia"], pd.Timestamp("2025-12-14"))
        self.assertAlmostEqual(float(reconstructed.iloc[0]["lula_pct"]), 53.0)
        self.assertAlmostEqual(float(reconstructed.iloc[0]["adversario_pct"]), 37.0)

        prepared = _legacy_second_round_input(pd.concat([daily, pd.DataFrame([weekly])], ignore_index=True))
        self.assertEqual(len(prepared), 2)
        valid = _valid_votes(prepared)
        self.assertTrue(((valid["lula_validos_pct"] + valid["adversario_validos_pct"]) - 100).abs().lt(1e-12).all())

    def test_generates_only_the_three_legacy_products(self) -> None:
        government_rows = []
        contest_rows = []
        for day, institute, good, regular, bad, lula, flavio in [
            ("2026-01-01", "Instituto A", 40.0, 25.0, 30.0, 49.0, 43.0),
            ("2026-01-11", "Instituto B", 44.0, 24.0, 28.0, 51.0, 41.0),
        ]:
            government_rows.append({
                **common(day, institute), "otimo_bom_pct": good, "regular_pct": regular, "ruim_pessimo_pct": bad,
            })
            contest_rows.append({
                **common(day, institute), "turno": "2º turno", "tipo_cenario": "Estimulada", "base_voto": "Totais",
                "adversario": "Flávio Bolsonaro", "lula_pct": lula, "adversario_pct": flavio,
            })
        data = StandardizedData(
            government=pd.DataFrame(government_rows), contests=pd.DataFrame(contest_rows),
            registry=pd.DataFrame(), issues=[],
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            files = generate_legacy_model_a(config(), output, data)
            self.assertEqual(len(files), 6)
            self.assertEqual({item.name for item in output.iterdir()}, {item.name for item in files})
            with pd.ExcelFile(output / "01_Avaliacao_do_Governo.xlsx") as government_book:
                self.assertEqual(government_book.sheet_names, ["Suavizados", "IC_Baixo", "IC_Alto"])
            with pd.ExcelFile(output / "02_Avaliacao_Liquida_do_Governo.xlsx") as net_book:
                self.assertEqual(net_book.sheet_names, ["Serie_Janela_15d", "Serie_Janela_30d"])
            with pd.ExcelFile(output / "03_Segundo_Turno_Lula_vs_Flavio.xlsx") as contest_book:
                self.assertEqual(contest_book.sheet_names, ["Suavizados", "IC_Baixo", "IC_Alto"])


if __name__ == "__main__":
    unittest.main()
