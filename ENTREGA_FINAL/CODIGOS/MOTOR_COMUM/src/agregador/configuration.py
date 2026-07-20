from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .domain import ConfigurationError


@dataclass(frozen=True)
class Config:
    path: Path
    values: dict[str, Any]

    @property
    def root(self) -> Path:
        return self.path.parent.parent.resolve()

    def value(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def nested(self, key: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        value = self.values.get(key, default or {})
        if not isinstance(value, dict):
            raise ConfigurationError(f"A chave '{key}' deve conter um objeto de configuração.")
        return value

    def resolve_path(self, setting: str) -> Path:
        raw = self.value(setting)
        if not isinstance(raw, str) or not raw.strip():
            raise ConfigurationError(f"A configuração '{setting}' é obrigatória.")
        path = Path(raw)
        return path if path.is_absolute() else (self.root / path).resolve()


def load_config(path_text: str) -> Config:
    path = Path(path_text).resolve()
    if not path.exists():
        raise ConfigurationError(f"Arquivo de configuração não encontrado: {path}")
    source = path.read_text(encoding="utf-8")
    try:
        values = json.loads(source)
    except json.JSONDecodeError as json_error:
        try:
            import yaml  # type: ignore[import-not-found]
        except ModuleNotFoundError as error:
            raise ConfigurationError(
                "Este ambiente não possui PyYAML. Use YAML compatível com JSON, como o arquivo de exemplo, "
                "ou instale as dependências do projeto. "
                f"Detalhe: {json_error.msg} (linha {json_error.lineno})."
            ) from error
        try:
            values = yaml.safe_load(source)
        except yaml.YAMLError as error:
            raise ConfigurationError(f"YAML inválido: {error}") from error
    if not isinstance(values, dict):
        raise ConfigurationError("A configuração deve ser um objeto no nível superior.")
    return Config(path=path, values=values)
