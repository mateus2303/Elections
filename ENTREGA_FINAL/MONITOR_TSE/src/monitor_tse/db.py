from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS runs (
  run_id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  source_generation TEXT,
  row_count INTEGER,
  new_count INTEGER DEFAULT 0,
  changed_count INTEGER DEFAULT 0,
  error_count INTEGER DEFAULT 0,
  message TEXT
);
CREATE TABLE IF NOT EXISTS source_snapshots (
  snapshot_id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES runs(run_id),
  resource_name TEXT NOT NULL,
  resource_id TEXT,
  url TEXT NOT NULL,
  source_generated_at TEXT,
  sha256 TEXT NOT NULL,
  bytes INTEGER NOT NULL,
  raw_path TEXT,
  schema_hash TEXT,
  row_count INTEGER,
  status TEXT NOT NULL,
  UNIQUE(run_id, resource_name)
);
CREATE TABLE IF NOT EXISTS researches (
  protocol TEXT PRIMARY KEY,
  current_version INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  business_hash TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  last_checked_at TEXT NOT NULL,
  last_changed_at TEXT,
  missing_streak INTEGER NOT NULL DEFAULT 0,
  availability_status TEXT NOT NULL DEFAULT 'ativa',
  publication_status TEXT NOT NULL,
  manual_notes TEXT,
  manual_tags TEXT,
  manual_priority INTEGER
);
CREATE TABLE IF NOT EXISTS research_versions (
  version_id INTEGER PRIMARY KEY,
  protocol TEXT NOT NULL REFERENCES researches(protocol),
  version_number INTEGER NOT NULL,
  observed_at TEXT NOT NULL,
  business_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  source_generation TEXT,
  UNIQUE(protocol, version_number)
);
CREATE TABLE IF NOT EXISTS research_changes (
  change_id INTEGER PRIMARY KEY,
  protocol TEXT NOT NULL REFERENCES researches(protocol),
  version_id INTEGER NOT NULL REFERENCES research_versions(version_id),
  detected_at TEXT NOT NULL,
  change_type TEXT NOT NULL,
  field_path TEXT NOT NULL,
  old_value_json TEXT,
  new_value_json TEXT,
  source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contractors_current (
  protocol TEXT NOT NULL REFERENCES researches(protocol),
  contractor_code TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  PRIMARY KEY(protocol, contractor_code)
);
CREATE TABLE IF NOT EXISTS payers_current (
  protocol TEXT NOT NULL REFERENCES researches(protocol),
  contractor_code TEXT NOT NULL,
  party_key TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  PRIMARY KEY(protocol, contractor_code, party_key)
);
CREATE TABLE IF NOT EXISTS document_references (
  protocol TEXT NOT NULL REFERENCES researches(protocol),
  document_kind TEXT NOT NULL,
  resource_url TEXT NOT NULL,
  reference_status TEXT NOT NULL,
  PRIMARY KEY(protocol, document_kind)
);
CREATE TABLE IF NOT EXISTS manual_annotations (
  protocol TEXT PRIMARY KEY REFERENCES researches(protocol),
  notes TEXT,
  tags TEXT,
  priority INTEGER,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
  alert_id INTEGER PRIMARY KEY,
  run_id INTEGER REFERENCES runs(run_id),
  channel TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  sent_at TEXT,
  error_message TEXT
);
CREATE TABLE IF NOT EXISTS failures (
  failure_id INTEGER PRIMARY KEY,
  run_id INTEGER REFERENCES runs(run_id),
  stage TEXT NOT NULL,
  error_code TEXT NOT NULL,
  message TEXT NOT NULL,
  details_json TEXT,
  created_at TEXT NOT NULL,
  transient INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS publication_checks (
  check_id INTEGER PRIMARY KEY,
  protocol TEXT NOT NULL REFERENCES researches(protocol),
  checked_at TEXT NOT NULL,
  adapter TEXT NOT NULL,
  status TEXT NOT NULL,
  evidence_json TEXT
);
CREATE TABLE IF NOT EXISTS publication_records (
  publication_id INTEGER PRIMARY KEY,
  protocol TEXT NOT NULL REFERENCES researches(protocol),
  status TEXT NOT NULL,
  source_url TEXT,
  title TEXT,
  published_at TEXT,
  found_at TEXT,
  confidence REAL,
  evidence_json TEXT,
  needs_review INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_researches_publication ON researches(publication_status);
CREATE INDEX IF NOT EXISTS idx_changes_detected ON research_changes(detected_at);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")

    def close(self) -> None:
        self.conn.close()

    def init(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def begin_run(self) -> int:
        cur = self.conn.execute("INSERT INTO runs(started_at,status) VALUES (?, 'running')", (now_iso(),))
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_run(self, run_id: int, status: str, **metrics: Any) -> None:
        fields = ["finished_at=?", "status=?"]
        values: list[Any] = [now_iso(), status]
        for key in ("source_generation", "row_count", "new_count", "changed_count", "error_count", "message"):
            if key in metrics:
                fields.append(f"{key}=?")
                values.append(metrics[key])
        values.append(run_id)
        self.conn.execute(f"UPDATE runs SET {', '.join(fields)} WHERE run_id=?", values)
        self.conn.commit()

    def record_failure(self, run_id: int | None, stage: str, code: str, message: str, details: Any = None, transient: bool = False) -> None:
        self.conn.execute("INSERT INTO failures(run_id,stage,error_code,message,details_json,created_at,transient) VALUES(?,?,?,?,?,?,?)", (run_id, stage, code, message, _json(details) if details is not None else None, now_iso(), int(transient)))
        self.conn.commit()

    def save_snapshot(self, run_id: int, item: dict[str, Any]) -> None:
        self.conn.execute("INSERT OR REPLACE INTO source_snapshots(run_id,resource_name,resource_id,url,source_generated_at,sha256,bytes,raw_path,schema_hash,row_count,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (run_id, item["resource_name"], item.get("resource_id"), item["url"], item.get("source_generated_at"), item["sha256"], item["bytes"], item.get("raw_path"), item.get("schema_hash"), item.get("row_count"), item.get("status", "valid")))
        self.conn.commit()

    def current(self) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM researches").fetchall()
        return {r["protocol"]: dict(r) for r in rows}

    def annotations(self) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM manual_annotations").fetchall()
        return {r["protocol"]: dict(r) for r in rows}

    def upsert_annotation(self, protocol: str, notes: str | None, tags: str | None, priority: int | None) -> None:
        self.conn.execute("INSERT INTO manual_annotations(protocol,notes,tags,priority,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(protocol) DO UPDATE SET notes=excluded.notes,tags=excluded.tags,priority=excluded.priority,updated_at=excluded.updated_at", (protocol, notes, tags, priority, now_iso()))
        self.conn.execute("UPDATE researches SET manual_notes=?,manual_tags=?,manual_priority=? WHERE protocol=?", (notes, tags, priority, protocol))
        self.conn.commit()

    def apply_records(self, records: list[dict[str, Any]], source_generation: str, run_id: int, raw_source: str = "TSE Dados Abertos") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        old = self.current()
        now = now_iso()
        new_items: list[dict[str, Any]] = []
        changed_items: list[dict[str, Any]] = []
        seen: set[str] = set()
        with self.conn:
            for record in records:
                protocol = record["protocol"]
                seen.add(protocol)
                payload = dict(record)
                payload.pop("business_hash", None)
                digest = canonical_hash(payload)
                existing = old.get(protocol)
                publication_status = record.get("publication_status", "informacao_indisponivel")
                if existing is None:
                    self.conn.execute("INSERT INTO researches(protocol,current_version,payload_json,business_hash,first_seen_at,last_seen_at,last_checked_at,last_changed_at,missing_streak,availability_status,publication_status) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (protocol, 1, _json(payload), digest, now, now, now, now, 0, "ativa", publication_status))
                    self.conn.execute("INSERT INTO research_versions(protocol,version_number,observed_at,business_hash,payload_json,source_generation) VALUES(?,?,?,?,?,?)", (protocol, 1, now, digest, _json(payload), source_generation))
                    version_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    self._write_related(protocol, payload)
                    self._write_documents(protocol, payload)
                    new_items.append(payload)
                else:
                    current_payload = json.loads(existing["payload_json"])
                    version = int(existing["current_version"])
                    if existing["business_hash"] != digest:
                        version += 1
                        self.conn.execute("INSERT INTO research_versions(protocol,version_number,observed_at,business_hash,payload_json,source_generation) VALUES(?,?,?,?,?,?)", (protocol, version, now, digest, _json(payload), source_generation))
                        version_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        for field, old_value, new_value in _diff(current_payload, payload):
                            self.conn.execute("INSERT INTO research_changes(protocol,version_id,detected_at,change_type,field_path,old_value_json,new_value_json,source) VALUES(?,?,?,?,?,?,?,?)", (protocol, version_id, now, "alterado", field, _json(old_value), _json(new_value), raw_source))
                        self.conn.execute("UPDATE researches SET current_version=?,payload_json=?,business_hash=?,last_seen_at=?,last_checked_at=?,last_changed_at=?,missing_streak=0,availability_status='ativa',publication_status=? WHERE protocol=?", (version, _json(payload), digest, now, now, now, publication_status, protocol))
                        self._write_related(protocol, payload)
                        self._write_documents(protocol, payload)
                        changed_items.append(payload)
                    else:
                        self.conn.execute("UPDATE researches SET last_seen_at=?,last_checked_at=?,missing_streak=0,availability_status='ativa',publication_status=? WHERE protocol=?", (now, now, publication_status, protocol))
            for protocol, row in old.items():
                if protocol in seen:
                    continue
                streak = int(row.get("missing_streak") or 0) + 1
                status = "possivelmente_indisponivel" if streak < 3 else "ausente_persistente"
                self.conn.execute("UPDATE researches SET last_checked_at=?,missing_streak=?,availability_status=? WHERE protocol=?", (now, streak, status, protocol))
        return new_items, changed_items

    def _write_related(self, protocol: str, payload: dict[str, Any]) -> None:
        self.conn.execute("DELETE FROM contractors_current WHERE protocol=?", (protocol,))
        self.conn.execute("DELETE FROM payers_current WHERE protocol=?", (protocol,))
        for item in payload.get("contractors", []):
            code = str(item.get("contractor_code") or "sem_codigo")
            self.conn.execute("INSERT INTO contractors_current(protocol,contractor_code,payload_json) VALUES(?,?,?)", (protocol, code, _json(item)))
        for item in payload.get("payers", []):
            code = str(item.get("contractor_code") or "sem_codigo")
            key = canonical_hash(item)
            self.conn.execute("INSERT INTO payers_current(protocol,contractor_code,party_key,payload_json) VALUES(?,?,?,?)", (protocol, code, key, _json(item)))

    def _write_documents(self, protocol: str, payload: dict[str, Any]) -> None:
        self.conn.execute("DELETE FROM document_references WHERE protocol=?", (protocol,))
        for kind, url in payload.get("document_references", {}).items():
            self.conn.execute("INSERT INTO document_references(protocol,document_kind,resource_url,reference_status) VALUES(?,?,?,?)", (protocol, kind, url, "pacote_oficial"))

    def create_alert(self, run_id: int, channel: str, subject: str, body: str, key: str) -> bool:
        cur = self.conn.execute("INSERT OR IGNORE INTO alerts(run_id,channel,subject,body,idempotency_key,status,created_at) VALUES(?,?,?,?,?,?,?)", (run_id, channel, subject, body, key, "pending", now_iso()))
        self.conn.commit()
        return cur.rowcount == 1

    def mark_alert(self, key: str, status: str, error: str | None = None) -> None:
        self.conn.execute("UPDATE alerts SET status=?,sent_at=?,error_message=? WHERE idempotency_key=?", (status, now_iso() if status == "sent" else None, error, key))
        self.conn.commit()

    def pending_alerts(self, run_id: int) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM alerts WHERE run_id=? AND status='pending' ORDER BY alert_id", (run_id,)).fetchall()

    def close(self) -> None:  # type: ignore[override]
        self.conn.close()


def _diff(old: Any, new: Any, prefix: str = "") -> Iterable[tuple[str, Any, Any]]:
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(set(old) | set(new)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in old or key not in new:
                yield path, old.get(key), new.get(key)
            else:
                yield from _diff(old[key], new[key], path)
    elif old != new:
        yield prefix, old, new

