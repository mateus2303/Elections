from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import shutil
import time
import urllib.request
import zipfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


LOGGER = logging.getLogger(__name__)
CKAN_PACKAGE_API = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id=pesquisas-eleitorais-2026"
NULLS = {"", "#NULO", "#NULO#", "#NE", "#NE#", "-1", "-3"}
DEFAULT_RESOURCES = {
    "pesquisas": {
        "name": "Pesquisas eleitorais",
        "filename": "pesquisa_eleitoral_2026.zip",
        "fallback_url": "https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/pesquisa_eleitoral_2026.zip",
        "resource_id": "769a663e-12c5-489e-a9c8-04633c2d57a3",
        "csv_prefix": "pesquisa_eleitoral_2026_",
    },
    "contratantes": {
        "name": "Pesquisas eleitorais - contratantes",
        "filename": "pesquisa_contratante_2026.zip",
        "fallback_url": "https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/pesquisa_contratante_2026.zip",
        "resource_id": "5675d403-63ce-4a39-bd00-fc110ef999a7",
        "csv_prefix": "pesquisa_contratante_2026_",
    },
    "pagantes": {
        "name": "Pesquisas eleitorais - pagantes",
        "filename": "pesquisa_pagante_2026.zip",
        "fallback_url": "https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/pesquisa_pagante_2026.zip",
        "resource_id": "32fc58de-8369-4b9f-9c97-1647f8de49cb",
        "csv_prefix": "pesquisa_pagante_2026_",
    },
}
DOCUMENT_RESOURCES = {
    "questionario": "https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/questionario_pesquisa_2026.zip",
    "territorio": "https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/bairro_municipio_2026.zip",
    "nota_fiscal": "https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/nota_fiscal_2026.zip",
}


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return None if value in NULLS else value


def _parse_dt(value: str | None) -> str | None:
    value = _clean(value)
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).isoformat(sep=" ")
        except ValueError:
            continue
    raise ValueError(f"Data inválida: {value}")


def _parse_decimal(value: str | None) -> int | None:
    value = _clean(value)
    if value is None:
        return None
    try:
        return int((Decimal(value.replace(".", "").replace(",", ".")) * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Valor monetário inválido: {value}") from exc


def _parse_int(value: str | None) -> int | None:
    value = _clean(value)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Número inválido: {value}") from exc


def _level(uf: str | None, ue: str | None) -> str:
    uf = (uf or "").upper()
    ue = (ue or "").upper()
    if uf == "BR":
        return "nacional"
    if ue == uf or (uf == "DF" and ue == "DF"):
        return "estadual"
    if ue.isdigit():
        return "municipal"
    return "indisponivel"


def _read_csv(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    with zf.open(name) as stream:
        text = io.TextIOWrapper(stream, encoding="iso-8859-1", newline="")
        try:
            return list(csv.DictReader(text, delimiter=";", quotechar='"', strict=True))
        finally:
            text.detach()


def _source_generation(rows: list[dict[str, str]]) -> str:
    values = {(row.get("DT_GERACAO"), row.get("HH_GERACAO")) for row in rows if row.get("DT_GERACAO")}
    if not values:
        raise ValueError("Arquivo sem DT_GERACAO")
    if len({v[0] for v in values}) != 1:
        raise ValueError("DT_GERACAO inconsistente dentro do arquivo")
    date_value = next(iter(values))[0]
    return f"{date_value} {max((v[1] or '') for v in values)}"


def _validate_columns(rows: list[dict[str, str]], required: set[str], label: str) -> str:
    if not rows:
        raise ValueError(f"Arquivo {label} vazio")
    columns = set(rows[0])
    missing = required - columns
    if missing:
        raise ValueError(f"Colunas críticas ausentes em {label}: {sorted(missing)}")
    return hashlib.sha256("|".join(sorted(columns)).encode()).hexdigest()


def _record_from_main(row: dict[str, str], documents: dict[str, str]) -> dict[str, Any]:
    protocol = _clean(row.get("NR_PROTOCOLO_REGISTRO"))
    if not protocol:
        raise ValueError("Pesquisa sem NR_PROTOCOLO_REGISTRO")
    positions_raw = _clean(row.get("DS_CARGO"))
    positions = [p.strip() for p in positions_raw.split(",")] if positions_raw else []
    publication_date = _parse_dt(row.get("DT_DIVULGACAO"))
    today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    pub_day = datetime.fromisoformat(publication_date).date() if publication_date else None
    if pub_day and pub_day > today:
        publication_status = "aguardando_data_permitida"
    elif pub_day:
        publication_status = "verificacao_externa_nao_configurada"
    else:
        publication_status = "informacao_indisponivel"
    return {
        "protocol": protocol,
        "election_year": _parse_int(row.get("AA_ELEICAO")),
        "election_code": _clean(row.get("CD_ELEICAO")),
        "election_name": _clean(row.get("NM_ELEICAO")),
        "source_generation_date": _clean(row.get("DT_GERACAO")),
        "source_generation_time": _clean(row.get("HH_GERACAO")),
        "registered_at": _parse_dt(row.get("DT_REGISTRO")),
        "publication_allowed_at": publication_date,
        "uf": _clean(row.get("SG_UF")),
        "electoral_unit_code": _clean(row.get("SG_UE")),
        "electoral_unit_name": _clean(row.get("NM_UE")),
        "geographic_level": _level(_clean(row.get("SG_UF")), _clean(row.get("SG_UE"))),
        "positions_raw": positions_raw,
        "positions": positions,
        "company_name": _clean(row.get("NM_EMPRESA")),
        "company_trade_name": _clean(row.get("NM_EMPRESA_FANTASIA")),
        "company_cnpj": _clean(row.get("NR_CNPJ_EMPRESA")),
        "own_research": _clean(row.get("ST_PESQUISA_PROPRIA")),
        "sample_size": _parse_int(row.get("QT_ENTREVISTADO")),
        "field_start": _parse_dt(row.get("DT_INICIO_PESQUISA")),
        "field_end": _parse_dt(row.get("DT_FIM_PESQUISA")),
        "methodology": _clean(row.get("DS_METODOLOGIA_PESQUISA")),
        "sample_plan": _clean(row.get("DS_PLANO_AMOSTRAL")),
        "control_system": _clean(row.get("DS_SISTEMA_CONTROLE")),
        "municipality_detail": _clean(row.get("DS_DADO_MUNICIPIO")),
        "statistician_registration": _clean(row.get("CD_CONRE")),
        "statistician_name": _clean(row.get("NM_ESTATISTICO_RESP")),
        "research_value_cents": _parse_decimal(row.get("VR_PESQUISA")),
        "source_reference": "https://pesqele-divulgacao.tse.jus.br/",
        "publication_status": publication_status,
        "actual_publication_at": None,
        "publication_source": None,
        "notes": None,
        "document_references": documents,
        "contractors": [],
        "payers": [],
    }


def _party_document(value: str | None) -> tuple[str | None, str | None]:
    value = _clean(value)
    if value is None:
        return None, None
    digits = re.sub(r"\D", "", value)
    if len(digits) == 14:
        return digits, "CNPJ"
    if len(digits) == 11:
        return f"***.***.***-**", "CPF_mascarado"
    return value, "outro"


class TSESource:
    def __init__(self, raw_dir: Path, retries: int = 3, timeout: int = 120, user_agent: str = "MonitorPesquisasTSE/0.1"):
        self.raw_dir = raw_dir
        self.retries = retries
        self.timeout = timeout
        self.user_agent = user_agent

    def discover_resources(self) -> dict[str, dict[str, Any]]:
        """Descobre os URLs publicados no CKAN e mantém URLs CDN como contingência.

        O catálogo é consultado antes dos downloads para absorver mudanças de URL
        ou de identificador de recurso. Se o catálogo estiver indisponível, os
        endereços oficiais previamente validados continuam sendo usados.
        """
        resources = {key: dict(spec) for key, spec in DEFAULT_RESOURCES.items()}
        try:
            request = urllib.request.Request(CKAN_PACKAGE_API, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(request, timeout=min(self.timeout, 60)) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not payload.get("success"):
                raise ValueError("API CKAN retornou success=false")
            catalog = payload.get("result", {}).get("resources", [])
            by_name = {str(item.get("name", "")).strip().casefold(): item for item in catalog}
            aliases = {
                "pesquisas": ("pesquisas eleitorais", "pesquisa eleitoral"),
                "contratantes": ("pesquisas eleitorais - contratantes", "contratantes"),
                "pagantes": ("pesquisas eleitorais - pagantes", "pagantes"),
            }
            found = 0
            for key, names in aliases.items():
                item = next((by_name[name] for name in names if name in by_name), None)
                if item and item.get("url"):
                    resources[key]["url"] = item["url"]
                    resources[key]["resource_id"] = item.get("id") or resources[key]["resource_id"]
                    found += 1
            if found != len(resources):
                LOGGER.warning("Catálogo CKAN encontrado, mas apenas %s/%s recursos tabulares foram identificados; mantendo contingências.", found, len(resources))
            else:
                LOGGER.info("URLs dos recursos TSE descobertos pelo catálogo CKAN")
        except Exception as exc:
            LOGGER.warning("Não foi possível consultar o catálogo CKAN; usando URLs CDN validados: %s", exc)
        return resources

    def fetch(self, run_id: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        staging = self.raw_dir / datetime.now().strftime("%Y-%m-%d") / datetime.now().strftime("%H%M%S")
        staging.mkdir(parents=True, exist_ok=True)
        zips: dict[str, tuple[dict[str, Any], Path]] = {}
        resources = self.discover_resources()
        for key, spec in resources.items():
            url = spec.get("url") or spec["fallback_url"]
            zips[key] = (spec, self._download(url, staging / spec["filename"]))
        main_rows = self._read_resource(zips["pesquisas"], "pesquisas")
        contractor_rows = self._read_resource(zips["contratantes"], "contratantes")
        payer_rows = self._read_resource(zips["pagantes"], "pagantes")
        if len(main_rows["rows"]) < 1:
            raise ValueError("Fonte principal sem registros")
        main_generation = main_rows["generation"]
        records = self._join(main_rows["rows"], contractor_rows["rows"], payer_rows["rows"])
        for record in records:
            record["document_references"] = dict(DOCUMENT_RESOURCES)
        snapshots = {key: meta for key, (spec, meta) in zips.items()}
        return records, {"source_generation": main_generation, "snapshots": snapshots, "staging": str(staging), "row_count": len(records)}

    def prune_raw(self, retention_days: int) -> int:
        """Remove snapshots antigos somente quando a retenção foi explicitamente configurada."""
        if retention_days <= 0 or not self.raw_dir.exists():
            return 0
        cutoff = time.time() - retention_days * 86400
        removed = 0
        root = self.raw_dir.resolve()
        for day_dir in list(root.iterdir()):
            if not day_dir.is_dir():
                continue
            for run_dir in list(day_dir.iterdir()):
                if not run_dir.is_dir() or run_dir.resolve().parent != day_dir.resolve():
                    continue
                if run_dir.stat().st_mtime < cutoff:
                    shutil.rmtree(run_dir)
                    removed += 1
            if not any(day_dir.iterdir()):
                day_dir.rmdir()
        return removed

    def _download(self, url: str, target: Path) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data = response.read()
                    headers = response.headers
                if not data.startswith(b"PK"):
                    raise ValueError(f"Resposta não é ZIP: {url}")
                target.write_bytes(data)
                digest = hashlib.sha256(data).hexdigest()
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    bad = zf.testzip()
                    if bad:
                        raise ValueError(f"ZIP corrompido no arquivo interno {bad}")
                return {"url": url, "sha256": digest, "bytes": len(data), "raw_path": str(target), "etag": headers.get("ETag"), "last_modified": headers.get("Last-Modified")}
            except Exception as exc:  # pragma: no cover - coberto por testes de falha
                last_error = exc
                if attempt + 1 < self.retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"Falha no download após {self.retries} tentativas: {url}: {last_error}") from last_error

    def _read_resource(self, pair: tuple[dict[str, Any], dict[str, Any]], label: str) -> dict[str, Any]:
        spec, meta = pair
        with zipfile.ZipFile(meta["raw_path"]) as zf:
            names = zf.namelist()
            candidates = [n for n in names if n.lower().endswith("_brasil.csv") and n.lower().startswith(spec["csv_prefix"].lower())]
            if len(candidates) != 1:
                raise ValueError(f"ZIP {label} não contém exatamente um CSV BRASIL: {candidates}")
            rows = _read_csv(zf, candidates[0])
            required_by_label = {
                "pesquisas": {"NR_PROTOCOLO_REGISTRO", "DT_GERACAO", "HH_GERACAO", "DT_REGISTRO", "DT_DIVULGACAO", "SG_UF", "SG_UE"},
                "contratantes": {"NR_PROTOCOLO_REGISTRO", "CD_CONTRATANTE", "DT_GERACAO"},
                "pagantes": {"NR_PROTOCOLO_REGISTRO", "CD_CONTRATANTE", "DT_GERACAO"},
            }
            meta["schema_hash"] = _validate_columns(rows, required_by_label[label], label)
            meta["row_count"] = len(rows)
            meta["source_generated_at"] = _source_generation(rows)
            return {"rows": rows, "generation": meta["source_generated_at"]}

    def _join(self, main_rows: list[dict[str, str]], contractor_rows: list[dict[str, str]], payer_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
        if not main_rows:
            raise ValueError("Fonte principal sem registros")
        by_protocol: dict[str, dict[str, Any]] = {}
        for row in main_rows:
            protocol = _clean(row.get("NR_PROTOCOLO_REGISTRO"))
            if not protocol or protocol in by_protocol:
                raise ValueError(f"Protocolo ausente ou duplicado na fonte principal: {protocol}")
            by_protocol[protocol] = _record_from_main(row, {})
        for row in contractor_rows:
            protocol = _clean(row.get("NR_PROTOCOLO_REGISTRO"))
            if protocol not in by_protocol:
                raise ValueError(f"Contratante sem pesquisa correspondente: {protocol}")
            doc, doc_type = _party_document(row.get("NR_CPF_CNPJ_CONTRATANTE"))
            by_protocol[protocol]["contractors"].append({
                "contractor_code": _clean(row.get("CD_CONTRATANTE")),
                "document": doc,
                "document_type": doc_type,
                "name": _clean(row.get("NM_CONTRATANTE")),
                "amount_cents": _parse_decimal(row.get("VR_PAGO_CONTRATANTE")),
                "same_as_payer": _clean(row.get("ST_CONTRATANTE_PAGANTE")),
                "resource_origin": _clean(row.get("DS_ORIGEM_RECURSO")),
            })
        for row in payer_rows:
            protocol = _clean(row.get("NR_PROTOCOLO_REGISTRO"))
            if protocol not in by_protocol:
                raise ValueError(f"Pagante sem pesquisa correspondente: {protocol}")
            doc, doc_type = _party_document(row.get("NR_CPF_CNPJ_PAGANTE"))
            by_protocol[protocol]["payers"].append({
                "contractor_code": _clean(row.get("CD_CONTRATANTE")),
                "document": doc,
                "document_type": doc_type,
                "name": _clean(row.get("NM_PAGANTE")),
                "resource_origin": _clean(row.get("DS_ORIGEM_RECURSO")),
            })
        return list(by_protocol.values())
