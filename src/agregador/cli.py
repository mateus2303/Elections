from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .configuration import Config, load_config
from .domain import ConfigurationError
from .ingestion import read_workbook
from .model_b import aggregate_model_b, candidate_config
from .probability import leadership_probability
from .presentation import generate_presentation
from .publishing import publish
from .standardization import standardize
from .validation import has_blocking_errors, validate
from .weighting import aggregate_model_a, build_observations


def _pipeline(config: Config, command: str, model: str) -> tuple[Path, bool]:
    sheets = config.nested("sheets")
    required_sheets = {key: sheets[key] for key in ["government", "contests", "institutes"]}
    workbook = read_workbook(config.resolve_path("input_file"), required_sheets)
    data = standardize(workbook)
    issues = validate(data)
    blocked = has_blocking_errors(issues)
    execution_config = candidate_config(config) if model == "b" else config
    aggregate = aggregate_model_b if model == "b" else aggregate_model_a
    generate_outputs = command != "validate" and not blocked
    observations = build_observations(data) if generate_outputs else pd.DataFrame()
    aggregates, weights = aggregate(observations, execution_config) if generate_outputs else (pd.DataFrame(), pd.DataFrame())
    probabilities = leadership_probability(aggregates, execution_config) if generate_outputs else pd.DataFrame()
    extra: dict[str, pd.DataFrame] = {}
    if command == "backtest" and not blocked:
        extra["backtest_next_poll"] = _backtest(observations, execution_config, aggregate)
    run_dir = publish(
        execution_config, workbook, data, issues, observations, aggregates, weights, probabilities, blocked, extra,
        generate_charts=generate_outputs, publication_kind=command,
    )
    if command == "run" and generate_outputs:
        generate_presentation(
            execution_config,
            run_dir,
            data,
            aggregates,
            weights,
            probabilities,
            model_label="Modelo B — candidato experimental" if model == "b" else "Modelo A — baseline oficial",
        )
    return run_dir, blocked


def _backtest(observations: pd.DataFrame, config: Config, aggregate: object) -> pd.DataFrame:
    """Teste walk-forward simples: estima antes de uma nova data e compara com o ponto publicado nela."""
    if observations.empty:
        return pd.DataFrame()
    dimensions = [
        "product", "turno", "tipo_cenario", "cenario", "scenario_id", "adversario", "nivel_geografico",
        "geografia", "segmento_tipo", "segmento", "vote_base", "metric",
    ]
    results: list[dict[str, object]] = []
    for _, curve in observations.groupby(dimensions, dropna=False, sort=False):
        dates = sorted(curve["data_referencia"].dropna().unique())
        for target_date in dates[1:]:
            history = curve.loc[curve["data_referencia"] < target_date]
            estimate, _ = aggregate(history, config)
            if estimate.empty:
                continue
            predicted = estimate.sort_values("reference_date").iloc[-1]
            actuals = curve.loc[curve["data_referencia"] == target_date]
            for _, actual in actuals.iterrows():
                results.append({
                    "metric": actual["metric"], "target_date": target_date, "prediction_date": predicted["reference_date"],
                    "predicted_pct": predicted["estimate_pct"], "actual_pct": actual["adjusted_value_pct"],
                    "absolute_error_pp": abs(float(predicted["estimate_pct"]) - float(actual["adjusted_value_pct"])),
                    "poll_id": actual["poll_id"], "institute": actual["instituto"], "scenario_id": actual["scenario_id"],
                })
    return pd.DataFrame.from_records(results)


def _compare(run_a: str, run_b: str) -> Path:
    def aggregate_file(run: str) -> Path:
        root = Path(run)
        candidate = root / "tables" / "aggregates_timeseries.csv"
        if candidate.exists():
            return candidate
        if root.name == "aggregates_timeseries.csv" and root.exists():
            return root
        raise ConfigurationError(f"Não foi encontrada a tabela de agregados em: {run}")
    def canonicalize(frame: pd.DataFrame) -> pd.DataFrame:
        return frame.rename(columns={"geografia": "geography", "segmento": "segment"})
    left, right = canonicalize(pd.read_csv(aggregate_file(run_a))), canonicalize(pd.read_csv(aggregate_file(run_b)))
    keys = [key for key in ["scenario_id", "opponent", "geographic_level", "geography", "segment_type", "segment", "vote_base", "metric", "reference_date"] if key in left and key in right]
    comparison = left.merge(right, on=keys, suffixes=("_a", "_b"), how="outer")
    comparison["estimate_difference_pp"] = comparison["estimate_pct_b"] - comparison["estimate_pct_a"]
    output = Path.cwd() / "saidas" / "comparacao_modelos.csv"
    output.parent.mkdir(exist_ok=True)
    comparison.to_csv(output, index=False, encoding="utf-8")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agregador", description="Agregador auditável de pesquisas políticas")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for command in ["run", "validate", "backtest"]:
        child = subcommands.add_parser(command)
        child.add_argument("--config", required=True, help="Caminho da configuração YAML compatível com JSON.")
        child.add_argument("--model", choices=["a", "b"], default="a", help="Modelo A oficial ou Modelo B candidato experimental.")
    compare = subcommands.add_parser("compare")
    compare.add_argument("--run-a", required=True)
    compare.add_argument("--run-b", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "compare":
            print(f"Comparação gerada em: {_compare(args.run_a, args.run_b)}")
            return 0
        config = load_config(args.config)
        if args.command == "backtest" and config.value("base_config"):
            base_path = config.path.parent / str(config.value("base_config"))
            config = load_config(str(base_path))
        run_dir, blocked = _pipeline(config, args.command, args.model)
        print(f"Execução registrada em: {run_dir}")
        if blocked:
            print("Há erros bloqueantes. Foram gerados somente os artefatos de validação.")
            return 1
        return 0
    except ConfigurationError as error:
        print(f"Erro de configuração: {error}", file=sys.stderr)
        return 2
    except Exception as error:  # pragma: no cover - proteção da interface de linha de comando
        print(f"Falha inesperada: {error}", file=sys.stderr)
        return 3
