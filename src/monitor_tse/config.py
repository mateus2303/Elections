from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


_ENV = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        return _ENV.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Config:
    path: Path
    root: Path
    values: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        config_path = Path(path).expanduser().resolve()
        root = config_path.parents[1] if config_path.parent.name == "config" else config_path.parent
        load_env_file(root / ".env")
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        values = _expand(raw)
        values.setdefault("app", {})
        values["app"].setdefault("year", 2026)
        values["app"].setdefault("timezone", "America/Sao_Paulo")
        values.setdefault("paths", {})
        local_app = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local")) / "MonitorPesquisasTSE"
        values["paths"].setdefault("state_dir", str(local_app))
        values["paths"].setdefault("output_dir", str(root / "ENTREGA_FINAL" / "MONITOR_TSE"))
        values["paths"].setdefault("raw_dir", str(Path(values["paths"]["state_dir"]) / "raw"))
        values["paths"].setdefault("log_dir", str(Path(values["paths"]["state_dir"]) / "logs"))
        values.setdefault("source", {})
        values["source"].setdefault("dataset", "pesquisas-eleitorais-2026")
        values["source"].setdefault("retries", 3)
        values["source"].setdefault("timeout_seconds", 120)
        values["source"].setdefault("max_row_drop_fraction", 0.20)
        values["source"].setdefault("raw_retention_days", 0)
        values["source"].setdefault("user_agent", "MonitorPesquisasTSE/0.1 (contato a configurar)")
        values.setdefault("filters", {})
        for key in ("elections", "positions", "geographic_levels", "ufs", "municipalities", "institutes", "contractors", "publication_statuses", "tags"):
            values["filters"].setdefault(key, [])
        values["filters"].setdefault("registration_from", None)
        values["filters"].setdefault("registration_to", None)
        values.setdefault("alerts", {})
        values["alerts"].setdefault("email_enabled", False)
        values["alerts"].setdefault("daily_heartbeat", False)
        values["alerts"].setdefault("window_days", 7)
        values.setdefault("publication", {})
        values["publication"].setdefault("enabled", False)
        values.setdefault("schedule", {})
        values["schedule"].setdefault("times", ["08:00", "17:30"])
        return cls(config_path, root, values)

    def section(self, name: str) -> dict[str, Any]:
        return self.values.get(name, {})

    def path_value(self, section: str, key: str) -> Path:
        value = self.section(section).get(key)
        if value is None:
            raise ValueError(f"Configuração ausente: {section}.{key}")
        p = Path(str(value)).expanduser()
        return p if p.is_absolute() else (self.root / p).resolve()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.values.get("app", {}).get("year") != 2026:
            errors.append("O MVP atual foi preparado para o ano 2026.")
        if self.section("app").get("timezone") != "America/Sao_Paulo":
            errors.append("O fuso deve ser America/Sao_Paulo.")
        for key in ("state_dir", "output_dir", "raw_dir", "log_dir"):
            try:
                self.path_value("paths", key)
            except ValueError as exc:
                errors.append(str(exc))
        if int(self.section("source").get("retries", 0)) < 1:
            errors.append("source.retries deve ser positivo.")
        if not 0 <= float(self.section("source").get("max_row_drop_fraction", 0.20)) < 1:
            errors.append("source.max_row_drop_fraction deve estar entre 0 e 1.")
        if int(self.section("source").get("raw_retention_days", 0)) < 0:
            errors.append("source.raw_retention_days não pode ser negativo (0 preserva indefinidamente).")
        return errors
