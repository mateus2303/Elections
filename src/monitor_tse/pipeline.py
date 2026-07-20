from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from filelock import FileLock, Timeout

from .alerts import build_digest, send_pending
from .config import Config
from .db import Database
from .excel import export_workbook, import_manual_annotations
from .source import TSESource


LOGGER = logging.getLogger("monitor_tse")


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "monitor_tse.log"
    if any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(path) for h in LOGGER.handlers):
        return
    handler = logging.handlers.RotatingFileHandler(path, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)


def _current_records(db: Database) -> list[dict[str, Any]]:
    rows = db.conn.execute("SELECT * FROM researches ORDER BY protocol").fetchall()
    output = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        payload.update({
            "first_seen_at": row["first_seen_at"],
            "last_seen_at": row["last_seen_at"],
            "last_checked_at": row["last_checked_at"],
            "last_changed_at": row["last_changed_at"],
            "missing_streak": row["missing_streak"],
            "availability_status": row["availability_status"],
            "publication_status": row["publication_status"],
            "manual_notes": row["manual_notes"],
            "manual_tags": row["manual_tags"],
            "manual_priority": row["manual_priority"],
            "business_hash": row["business_hash"],
        })
        output.append(payload)
    return output


def _filtered(records: list[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
    def contains(values: list[str], value: str | None) -> bool:
        if not values:
            return True
        value = (value or "").casefold()
        return any(str(x).casefold() in value or value in str(x).casefold() for x in values)

    output = []
    registration_from = str(filters.get("registration_from") or "")[:10]
    registration_to = str(filters.get("registration_to") or "")[:10]
    for record in records:
        if filters.get("elections") and not contains(filters["elections"], record.get("election_name")):
            continue
        if filters.get("positions") and not any(contains(filters["positions"], p) for p in record.get("positions", [])):
            continue
        if filters.get("geographic_levels") and record.get("geographic_level") not in filters["geographic_levels"]:
            continue
        if filters.get("ufs") and str(record.get("uf")) not in {str(x).upper() for x in filters["ufs"]}:
            continue
        if filters.get("municipalities") and not contains(filters["municipalities"], record.get("electoral_unit_name")):
            continue
        if filters.get("institutes") and not contains(filters["institutes"], record.get("company_name")) and not contains(filters["institutes"], record.get("company_trade_name")):
            continue
        if filters.get("contractors") and not any(contains(filters["contractors"], x.get("name")) for x in record.get("contractors", [])):
            continue
        if filters.get("publication_statuses") and record.get("publication_status") not in filters["publication_statuses"]:
            continue
        if filters.get("tags") and not any(tag.strip() in set(str(record.get("manual_tags") or "").split(",")) for tag in filters["tags"]):
            continue
        registered = str(record.get("registered_at") or "")[:10]
        if registration_from and (not registered or registered < registration_from):
            continue
        if registration_to and (not registered or registered > registration_to):
            continue
        output.append(record)
    return output


def _changes(db: Database) -> list[dict[str, Any]]:
    rows = db.conn.execute("SELECT protocol,detected_at,change_type,field_path,old_value_json,new_value_json,source FROM research_changes ORDER BY detected_at DESC LIMIT 1000").fetchall()
    return [{"protocol": r["protocol"], "detected_at": r["detected_at"], "change_type": r["change_type"], "field_path": r["field_path"], "old_value": json.loads(r["old_value_json"]) if r["old_value_json"] else None, "new_value": json.loads(r["new_value_json"]) if r["new_value_json"] else None, "source": r["source"]} for r in rows]


def _runs(db: Database) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs = [dict(r) for r in db.conn.execute("SELECT * FROM runs ORDER BY run_id DESC LIMIT 100").fetchall()]
    errors = [dict(r) for r in db.conn.execute("SELECT * FROM failures ORDER BY failure_id DESC LIMIT 200").fetchall()]
    return runs, errors


def run_once(config: Config) -> int:
    errors = config.validate()
    if errors:
        raise ValueError("; ".join(errors))
    paths = config.section("paths")
    state_dir = config.path_value("paths", "state_dir")
    raw_dir = config.path_value("paths", "raw_dir")
    output_path = config.path_value("paths", "output_dir") / "monitor_pesquisas_tse.xlsx"
    log_dir = config.path_value("paths", "log_dir")
    setup_logging(log_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    db = Database(state_dir / "monitor_tse.sqlite3")
    db.init()
    lock = FileLock(str(state_dir / "monitor_tse.lock"))
    try:
        lock.acquire(timeout=1)
    except Timeout:
        LOGGER.warning("Execução ignorada: outra instância possui o lock")
        db.close()
        return 10
    run_id = db.begin_run()
    LOGGER.info("Início da execução %s", run_id)
    try:
        try:
            for item in import_manual_annotations(output_path):
                if item["protocol"] in db.current():
                    db.upsert_annotation(item["protocol"], item.get("notes"), item.get("tags"), item.get("priority"))
        except Exception as exc:
            db.record_failure(run_id, "manual_annotations", "ANNOTATION_READ", str(exc))
            db.finish_run(run_id, "failed", error_count=1, message=str(exc))
            return 4
        source_cfg = config.section("source")
        source = TSESource(raw_dir, int(source_cfg["retries"]), int(source_cfg["timeout_seconds"]), str(source_cfg["user_agent"]))
        before_count = len(db.current())
        records, source_meta = source.fetch(run_id)
        drop_fraction = float(source_cfg.get("max_row_drop_fraction", 0.20))
        if before_count and len(records) < int(before_count * (1 - drop_fraction)):
            raise ValueError(f"Redução de registros acima do limite: antes={before_count}, agora={len(records)}")
        for key, meta in source_meta["snapshots"].items():
            meta = dict(meta)
            meta["resource_name"] = key
            db.save_snapshot(run_id, meta)
        new_records, changed_records = db.apply_records(records, source_meta["source_generation"], run_id)
        current = _current_records(db)
        filtered_new = _filtered(new_records, config.section("filters"))
        filtered_changed = _filtered(changed_records, config.section("filters"))
        local_today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        allowed = []
        for record in _filtered(current, config.section("filters")):
            if record.get("publication_allowed_at"):
                try:
                    allowed.append((record, datetime.fromisoformat(record["publication_allowed_at"]).date()))
                except ValueError:
                    pass
        metrics = {
            "last_execution": datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(sep=" "),
            "source_generation": source_meta["source_generation"],
            "new_count": len(filtered_new),
            "changed_count": len(filtered_changed),
            "error_count": 0,
            "today_count": sum(day == local_today for _, day in allowed),
            "tomorrow_count": sum(day == local_today.fromordinal(local_today.toordinal() + 1) for _, day in allowed),
            "next_7_count": sum(local_today <= day <= local_today.fromordinal(local_today.toordinal() + 7) for _, day in allowed),
            "new_records": filtered_new,
            "window_days": int(config.section("alerts").get("window_days", 7)),
        }
        db.finish_run(run_id, "success", source_generation=source_meta["source_generation"], row_count=len(records), new_count=len(new_records), changed_count=len(changed_records), error_count=0)
        annotations = db.annotations()
        runs, failures = _runs(db)
        export_workbook(output_path, current, annotations, metrics, _changes(db), runs, failures)
        alert_cfg = config.section("alerts")
        alert_new = [] if before_count == 0 else filtered_new
        has_calendar_events = bool(metrics["today_count"] or metrics["tomorrow_count"] or metrics["next_7_count"])
        if alert_cfg.get("email_enabled") and (alert_new or filtered_changed or has_calendar_events or alert_cfg.get("daily_heartbeat")):
            subject, body, keys = build_digest(alert_new, filtered_changed, _filtered(current, config.section("filters")), run_id, int(alert_cfg.get("window_days", 7)))
            digest_day = datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
            key = f"digest:{digest_day}:{','.join(sorted(keys)) or 'heartbeat'}"
            if db.create_alert(run_id, "email", subject, body, key):
                sent, send_errors = send_pending(db)
                if send_errors:
                    message = "; ".join(send_errors)
                    db.record_failure(run_id, "email", "SMTP", message, transient=True)
                    db.finish_run(run_id, "failed", error_count=1, message=message)
                    LOGGER.error("Falha de e-mail: %s", send_errors)
                    return 5
                LOGGER.info("Alertas enviados: %s", sent)
        retention_days = int(source_cfg.get("raw_retention_days", 0))
        if retention_days > 0:
            LOGGER.info("Snapshots brutos removidos pela retenção: %s", source.prune_raw(retention_days))
        LOGGER.info("Execução %s concluída: %s novos, %s alterados", run_id, len(new_records), len(changed_records))
        return 0
    except Exception as exc:
        LOGGER.exception("Falha na execução %s", run_id)
        db.record_failure(run_id, "pipeline", "RUN_FAILED", str(exc), transient=True)
        db.finish_run(run_id, "failed", error_count=1, message=str(exc))
        return 3
    finally:
        lock.release()
        db.close()
