from __future__ import annotations

from datetime import datetime
import html
import importlib.util
import json
from pathlib import Path
from shutil import move
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .configuration import Config
from .domain import Issue, safe_slug
from .ingestion import WorkbookData
from .standardization import StandardizedData


def _now() -> datetime:
    return datetime.now().astimezone()


def _model_label(config: Config) -> str:
    methodology = str(config.value("methodology_version"))
    if methodology.startswith("legacy-baseline"):
        return "Modelo_A_Baseline_Oficial"
    if methodology.startswith("model-b"):
        return "Modelo_B_Candidato_Experimental"
    return f"Modelo_{safe_slug(methodology)}"


def _run_directory(config: Config, now: datetime, publication_kind: str) -> tuple[Path, str]:
    """Escolhe um destino legível e arquiva a entrega corrente antes de substituí-la."""
    label = _model_label(config)
    timestamp = now.strftime("%Y-%m-%d_%H%M%S")
    archive_root = config.resolve_path("archive_outputs_dir")
    if publication_kind == "run":
        current = config.resolve_path("outputs_dir") / label
        if current.exists():
            archive_root.mkdir(parents=True, exist_ok=True)
            archived = archive_root / f"{label}__substituida_em_{timestamp}"
            if archived.exists():
                raise FileExistsError(f"O histórico de execução já existe: {archived}")
            move(str(current), str(archived))
        return current, label
    kind_labels = {"validate": "Validacao", "backtest": "Backtest"}
    kind_label = kind_labels.get(publication_kind, "Analise")
    return archive_root / kind_label / f"{kind_label}__{label}__{timestamp}", label


def _table(frame: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame(columns=columns or [])
    if frame.empty and columns:
        return pd.DataFrame(columns=columns)
    return frame.copy()


def _write_table(frame: pd.DataFrame, path: Path, parquet_available: bool) -> bool:
    frame.to_csv(path.with_suffix(".csv"), index=False, encoding="utf-8", date_format="%Y-%m-%d")
    if parquet_available:
        frame.to_parquet(path.with_suffix(".parquet"), index=False)
        return True
    return False


def _issues_frame(issues: list[Issue]) -> pd.DataFrame:
    return pd.DataFrame.from_records([issue.as_dict() for issue in issues], columns=[
        "severity", "sheet", "source_row", "poll_id", "field", "message", "suggestion",
    ])


def _raw_table(workbook: WorkbookData) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for sheet in [workbook.government, workbook.contests]:
        frame = sheet.frame[["source_file", "source_sheet", "source_row", "raw_payload_json"]].copy()
        parts.append(frame)
    return pd.concat(parts, ignore_index=True)


def _silver_table(observations: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "poll_group_id", "poll_id", "scenario_id", "scenario_type", "opponent", "geographic_level", "geography",
        "segment_type", "segment", "candidate_or_metric", "value_pct", "vote_base", "institute", "field_start",
        "field_end", "field_midpoint", "publication_date", "reference_date_input", "sample_size", "segment_sample_size",
        "effective_sample_size", "margin_error_pp", "confidence_level_pct", "quality_weight", "institute_status",
        "house_effect_pp", "excess_error_pp", "raw_value_pct", "adjusted_value_pct", "source_file", "source_sheet",
        "source_row",
    ]
    if observations.empty:
        return pd.DataFrame(columns=columns)
    result = pd.DataFrame({
        "poll_group_id": observations["poll_group_id"],
        "poll_id": observations["poll_id"],
        "scenario_id": observations["scenario_id"],
        "scenario_type": observations["tipo_cenario"],
        "opponent": observations["adversario"],
        "geographic_level": observations["nivel_geografico"],
        "geography": observations["geografia"],
        "segment_type": observations["segmento_tipo"],
        "segment": observations["segmento"],
        "candidate_or_metric": observations["metric"],
        "value_pct": observations["adjusted_value_pct"],
        "vote_base": observations["vote_base"],
        "institute": observations["instituto"],
        "field_start": pd.NA,
        "field_end": pd.NA,
        "field_midpoint": pd.NA,
        "publication_date": pd.NA,
        "reference_date_input": observations["data_referencia"],
        "sample_size": observations["amostra_total"],
        "segment_sample_size": observations["amostra_segmento"],
        "effective_sample_size": pd.NA,
        "margin_error_pp": observations["margem_erro_pp"],
        "confidence_level_pct": observations["nivel_confianca_pct"],
        "quality_weight": observations["quality_weight"],
        "institute_status": observations["institute_status"],
        "house_effect_pp": pd.NA,
        "excess_error_pp": pd.NA,
        "raw_value_pct": observations["raw_value_pct"],
        "adjusted_value_pct": observations["adjusted_value_pct"],
        "source_file": observations["source_file"],
        "source_sheet": observations["source_sheet"],
        "source_row": observations["source_row"],
    })
    return result[columns]


def _registry_diagnostics(registry: pd.DataFrame, observations: pd.DataFrame) -> pd.DataFrame:
    registry = registry.copy()
    if observations.empty:
        registry["observacoes_padronizadas"] = 0
        registry["ultima_data_referencia"] = pd.NaT
        return registry
    stats = observations.groupby("instituto", dropna=False).agg(
        observacoes_padronizadas=("poll_id", "count"), ultima_data_referencia=("data_referencia", "max"),
    ).reset_index()
    return registry.merge(stats, on="instituto", how="left").fillna({"observacoes_padronizadas": 0})


def _validation_html(issues: pd.DataFrame, blocked: bool) -> str:
    status = "BLOQUEADA" if blocked else "APROVADA COM ALERTAS, SE HOUVER"
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape('' if pd.isna(value) else str(value))}</td>" for value in row) + "</tr>"
        for row in issues.itertuples(index=False, name=None)
    ) or "<tr><td colspan='7'>Nenhuma ocorrência.</td></tr>"
    return f"""<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Relatório de validação</title>
<style>body{{font:14px Arial;margin:32px;color:#172033}} table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #d8dee9;padding:7px;text-align:left}} th{{background:#eef2f7}} .status{{font-weight:bold}}</style>
<h1>Relatório de validação</h1><p class='status'>Publicação Gold: {status}</p>
<table><thead><tr><th>Severidade</th><th>Aba</th><th>Linha</th><th>poll_id</th><th>Campo</th><th>Mensagem</th><th>Sugestão</th></tr></thead><tbody>{rows}</tbody></table></html>"""


def _latest_composition(weights: pd.DataFrame) -> pd.DataFrame:
    if weights.empty:
        return weights
    group_columns = [column for column in [
        "product", "turno", "tipo_cenario", "cenario", "scenario_id", "adversario", "nivel_geografico",
        "geografia", "segmento_tipo", "segmento", "vote_base", "metric",
    ] if column in weights]
    latest_dates = weights.groupby(group_columns, dropna=False)["reference_date"].transform("max")
    return weights.loc[weights["reference_date"] == latest_dates].copy()


def _plot_aggregates(aggregates: pd.DataFrame, directory: Path, min_points: int) -> int:
    if aggregates.empty:
        return 0
    chart_count = 0
    group_columns = [column for column in aggregates.columns if column in {
        "product", "turno", "tipo_cenario", "cenario", "scenario_id", "adversario", "nivel_geografico",
        "geografia", "segmento_tipo", "segmento", "vote_base", "metric",
    }]
    for _, curve in aggregates.groupby(group_columns, dropna=False, sort=False):
        curve = curve.sort_values("reference_date")
        if len(curve) < min_points:
            continue
        first = curve.iloc[0]
        if first["product"] == "Lula3":
            filename = f"lula3_{safe_slug(first['metric'])}__{safe_slug(first['geografia'])}__{safe_slug(first['segmento'])}.png"
            title = f"Lula III — {first['metric']} | {first['geografia']} | {first['segmento']}"
        else:
            filename = f"lula_vs_{safe_slug(first['adversario'])}__{safe_slug(first['geografia'])}__{safe_slug(first['segmento'])}__{safe_slug(first['metric'])}__{str(first['scenario_id'])[-8:]}.png"
            title = f"Lula × {first['adversario']} — {first['metric']} | {first['geografia']} | {first['segmento']}"
        figure, axis = plt.subplots(figsize=(10, 5))
        axis.plot(curve["reference_date"], curve["estimate_pct"], color="#173f5f", linewidth=2, label="Estimativa")
        interval_label = (
            "Intervalo de incerteza do Modelo B"
            if str(first.get("interval_type", "")).startswith("uncertainty_interval_model_b")
            else "Intervalo amostral legado"
        )
        axis.fill_between(curve["reference_date"], curve["interval_low_pct"], curve["interval_high_pct"], color="#20639b", alpha=0.18, label=interval_label)
        axis.axhline(0, color="#6b7280", linewidth=0.8) if str(first["metric"]).startswith("margem") or first["metric"] == "favorabilidade_liquida" else None
        axis.set_title(title)
        axis.set_ylabel("pontos percentuais")
        axis.legend(loc="best")
        axis.grid(axis="y", alpha=0.25)
        figure.autofmt_xdate()
        figure.tight_layout()
        figure.savefig(directory / filename, dpi=140)
        plt.close(figure)
        chart_count += 1
    return chart_count


def _plot_probabilities(probabilities: pd.DataFrame, directory: Path, min_points: int) -> int:
    if probabilities.empty:
        return 0
    count = 0
    usable = probabilities.dropna(subset=["probability_lula"])
    for keys, curve in usable.groupby(["scenario_id", "opponent", "geography", "segment", "vote_base"], dropna=False, sort=False):
        if len(curve) < min_points:
            continue
        scenario_id, opponent, geography, segment, vote_base = keys
        curve = curve.sort_values("reference_date")
        figure, axis = plt.subplots(figsize=(10, 5))
        axis.plot(curve["reference_date"], curve["probability_lula"] * 100, color="#8c2d04", linewidth=2)
        axis.axhline(50, color="#6b7280", linewidth=0.8)
        axis.set_ylim(0, 100)
        axis.set_ylabel("probabilidade experimental (%)")
        axis.set_title(f"Liderança atual: Lula × {opponent} | {geography} | {segment} | {vote_base}")
        axis.grid(axis="y", alpha=0.25)
        figure.autofmt_xdate()
        figure.tight_layout()
        figure.savefig(directory / f"prob_lideranca__{safe_slug(opponent)}__{safe_slug(geography)}__{safe_slug(segment)}__{safe_slug(vote_base)}__{str(scenario_id)[-8:]}.png", dpi=140)
        plt.close(figure)
        count += 1
    return count


def publish(
    config: Config,
    workbook: WorkbookData,
    data: StandardizedData,
    issues: list[Issue],
    observations: pd.DataFrame,
    aggregates: pd.DataFrame,
    weights: pd.DataFrame,
    probabilities: pd.DataFrame,
    blocked: bool,
    extra_tables: dict[str, pd.DataFrame] | None = None,
    generate_charts: bool = True,
    publication_kind: str = "run",
) -> Path:
    now = _now()
    run_dir, model_label = _run_directory(config, now, publication_kind)
    run_id = f"{safe_slug(model_label)}_{now.strftime('%Y%m%dT%H%M%S%z')}"
    charts_dir, tables_dir, reports_dir = run_dir / "graficos_diagnostico", run_dir / "tables", run_dir / "reports"
    for directory in [charts_dir, tables_dir, reports_dir]:
        directory.mkdir(parents=True, exist_ok=False)
    parquet_available = importlib.util.find_spec("pyarrow") is not None or importlib.util.find_spec("fastparquet") is not None
    issues_frame = _issues_frame(issues)
    raw = _raw_table(workbook)
    silver = _silver_table(observations)
    registry = _registry_diagnostics(data.registry, observations)
    aggregates = _table(aggregates)
    probabilities = _table(probabilities)
    weights = _table(weights)
    for frame in [raw, silver, registry, aggregates, probabilities, weights]:
        frame.insert(0, "run_id", run_id)
        frame.insert(1, "methodology_version", config.value("methodology_version"))
    if not aggregates.empty:
        aggregates.rename(columns={
            "nivel_geografico": "geographic_level", "adversario": "opponent", "segmento_tipo": "segment_type",
            "geografia": "geography", "segmento": "segment",
        }, inplace=True)
    if not probabilities.empty:
        probabilities.rename(columns={"geographic_level": "geographic_level"}, inplace=True)
    table_map = {
        "polls_raw": raw,
        "polls_standardized": silver,
        "poll_weights": weights,
        "aggregates_timeseries": aggregates,
        "win_probability_timeseries": probabilities,
        "institutes_registry": registry,
        "institutes_diagnostics": registry,
        "validation_issues": issues_frame,
        "run_log": pd.DataFrame([{
            "run_id": run_id, "started_at": now.isoformat(), "methodology_version": config.value("methodology_version"),
            "input_file": workbook.source_file, "input_hash_sha256": workbook.source_hash_sha256, "blocked": blocked,
            "errors": int((issues_frame["severity"] == "erro").sum()) if not issues_frame.empty else 0,
            "alerts": int((issues_frame["severity"] == "alerta").sum()) if not issues_frame.empty else 0,
            "parquet_available": parquet_available,
        }]),
    }
    if extra_tables:
        table_map.update(extra_tables)
    for name, frame in table_map.items():
        _write_table(_table(frame), tables_dir / name, parquet_available)
    reports_dir.joinpath("validation_report.html").write_text(_validation_html(issues_frame, blocked), encoding="utf-8")
    snapshot: dict[str, Any] = {
        "run_id": run_id,
        "created_at": now.isoformat(),
        "methodology_version": config.value("methodology_version"),
        "input_file": workbook.source_file,
        "input_hash_sha256": workbook.source_hash_sha256,
        "header_rows": {
            "Lula3": workbook.government.header_row,
            "Confrontos": workbook.contests.header_row,
            "Institutos": workbook.institutes.header_row,
        },
        "config": config.values,
        "parquet_available": parquet_available,
        "probability_notice": "Experimental: a incerteza total ainda não foi homologada." if bool(config.nested("probability").get("experimental", True)) else "Não experimental.",
    }
    reports_dir.joinpath("methodology_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    latest = _latest_composition(weights)
    latest.to_html(reports_dir / "latest_composition.html", index=False, escape=True)
    if not blocked and generate_charts:
        charting = config.nested("charting", {"min_points": 20})
        min_points = int(charting.get("min_points", 20))
        _plot_aggregates(aggregates.rename(columns={
            "geographic_level": "nivel_geografico", "opponent": "adversario", "segment_type": "segmento_tipo",
            "geography": "geografia", "segment": "segmento",
        }), charts_dir, min_points)
        _plot_probabilities(probabilities, charts_dir, min_points)
    return run_dir
