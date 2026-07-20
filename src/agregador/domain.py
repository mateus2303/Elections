from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from hashlib import sha256
import json
import math
import re
import unicodedata
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class Issue:
    severity: str
    sheet: str
    source_row: int | None
    poll_id: str | None
    field: str | None
    message: str
    suggestion: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConfigurationError(ValueError):
    """Erro em configuração que deve resultar no código de saída 2."""


def is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    try:
        return not bool(pd.isna(value))
    except (TypeError, ValueError):
        return True


def plain_text(value: Any) -> str:
    if not is_present(value):
        return ""
    return str(value).strip()


def normalized_text(value: Any) -> str:
    text = plain_text(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def json_value(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def canonical_json(payload: dict[str, Any]) -> str:
    clean = {key: json_value(value) for key, value in payload.items()}
    return json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(prefix: str, payload: dict[str, Any]) -> str:
    digest = sha256(canonical_json(payload).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def safe_slug(value: Any) -> str:
    normalized = normalized_text(value).replace(" ", "-")
    return normalized[:96] or "sem-identificador"
