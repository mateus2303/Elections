from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .domain import ConfigurationError, is_present, json_value, normalized_text


GOVERNMENT_COLUMNS = [
    "data_referencia", "instituto", "tipo_pesquisa", "frequencia_original",
    "amostra_total", "margem_erro_pp", "nivel_confianca_pct", "nivel_geografico",
    "geografia", "segmento_tipo", "segmento", "amostra_segmento", "otimo_bom_pct",
    "regular_pct", "ruim_pessimo_pct",
]
CONTEST_COLUMNS = [
    "data_referencia", "instituto", "tipo_pesquisa", "frequencia_original",
    "amostra_total", "margem_erro_pp", "nivel_confianca_pct", "turno", "tipo_cenario",
    "cenario", "adversario", "nivel_geografico", "geografia", "segmento_tipo", "segmento",
    "amostra_segmento", "lula_pct", "adversario_pct", "outros_candidatos_pct",
    "brancos_nulos_indecisos_pct", "base_voto",
]
INSTITUTE_COLUMNS = ["instituto", "aliases", "peso_legacy", "situacao"]


@dataclass(frozen=True)
class LoadedSheet:
    name: str
    header_row: int
    frame: pd.DataFrame


@dataclass(frozen=True)
class WorkbookData:
    source_file: str
    source_hash_sha256: str
    government: LoadedSheet
    contests: LoadedSheet
    institutes: LoadedSheet


def _header_at(raw: pd.DataFrame, required: list[str], sheet_name: str) -> int:
    target = set(required)
    for position in range(len(raw)):
        cells = {normalized_text(value).replace(" ", "_") for value in raw.iloc[position].tolist()}
        if target.issubset(cells):
            return position
    raise ConfigurationError(
        f"Não foi localizado o cabeçalho operacional da aba '{sheet_name}'. "
        f"Campos esperados: {', '.join(required[:4])}..."
    )


def _read_sheet(path: Path, sheet_name: str, required: list[str]) -> LoadedSheet:
    try:
        raw = pd.read_excel(path, sheet_name=sheet_name, header=None, dtype=object, engine="openpyxl")
    except ValueError as error:
        raise ConfigurationError(f"Aba obrigatória ausente: '{sheet_name}'.") from error
    header_index = _header_at(raw, required, sheet_name)
    headers = [normalized_text(value).replace(" ", "_") for value in raw.iloc[header_index].tolist()]
    data = raw.iloc[header_index + 1 :].copy()
    data.columns = headers
    data["source_row"] = data.index + 1
    data = data.loc[data[required].apply(lambda row: any(is_present(value) for value in row), axis=1)].copy()
    data["source_sheet"] = sheet_name
    data["source_file"] = str(path)
    payload_columns = required.copy()
    data["raw_payload_json"] = data.apply(
        lambda row: json.dumps(
            {column: json_value(row[column]) for column in payload_columns},
            ensure_ascii=False,
            sort_keys=True,
        ),
        axis=1,
    )
    return LoadedSheet(name=sheet_name, header_row=header_index + 1, frame=data.reset_index(drop=True))


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_workbook(path: Path, sheet_names: dict[str, str]) -> WorkbookData:
    if not path.exists():
        raise ConfigurationError(f"Arquivo de entrada não encontrado: {path}")
    if path.suffix.lower() != ".xlsx":
        raise ConfigurationError("O arquivo de entrada deve ser uma planilha .xlsx.")
    return WorkbookData(
        source_file=str(path),
        source_hash_sha256=_sha256(path),
        government=_read_sheet(path, sheet_names["government"], GOVERNMENT_COLUMNS),
        contests=_read_sheet(path, sheet_names["contests"], CONTEST_COLUMNS),
        institutes=_read_sheet(path, sheet_names["institutes"], INSTITUTE_COLUMNS),
    )
