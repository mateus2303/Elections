from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from urllib.error import URLError
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from monitor_tse.db import Database
from monitor_tse.excel import export_workbook, import_manual_annotations
from monitor_tse.alerts import build_digest
from monitor_tse.pipeline import _filtered
from monitor_tse.source import DEFAULT_RESOURCES, TSESource, _record_from_main


def main_row(protocol: str = "BR000012026", company: str = "Instituto Teste", allowed: str = "2026-07-25 00:00:00") -> dict[str, str]:
    return {
        "DT_GERACAO": "20/07/2026", "HH_GERACAO": "05:46:52", "AA_ELEICAO": "2026", "CD_ELEICAO": "81", "NM_ELEICAO": "Eleições Gerais 2026", "SG_UF": "BR", "SG_UE": "BR", "NM_UE": "BRASIL", "NR_PROTOCOLO_REGISTRO": protocol, "DT_REGISTRO": "2026-07-20 08:00:00", "ST_PESQUISA_PROPRIA": "S", "NR_CNPJ_EMPRESA": "12345678000199", "NM_EMPRESA": company, "NM_EMPRESA_FANTASIA": company, "DS_CARGO": "Presidente", "DT_INICIO_PESQUISA": "2026-07-18 00:00:00", "DT_FIM_PESQUISA": "2026-07-19 00:00:00", "DT_DIVULGACAO": allowed, "QT_ENTREVISTADO": "1000", "CD_CONRE": "123", "NM_ESTATISTICO_RESP": "Pessoa Técnica", "VR_PESQUISA": "10000,00", "DS_METODOLOGIA_PESQUISA": "Quantitativa", "DS_PLANO_AMOSTRAL": "95% e margem de erro 3,1 p.p.", "DS_SISTEMA_CONTROLE": "Controle", "DS_DADO_MUNICIPIO": "#NULO#",
    }


def contractor_row(protocol: str = "BR000012026") -> dict[str, str]:
    return {"DT_GERACAO": "20/07/2026", "HH_GERACAO": "05:46:51", "AA_ELEICAO": "2026", "NR_PROTOCOLO_REGISTRO": protocol, "CD_CONTRATANTE": "1", "NR_CPF_CNPJ_CONTRATANTE": "12345678000199", "NM_CONTRATANTE": "Contratante Teste", "VR_PAGO_CONTRATANTE": "10000,00", "ST_CONTRATANTE_PAGANTE": "S", "DS_ORIGEM_RECURSO": "#NULO#"}


def payer_row(protocol: str = "BR000012026") -> dict[str, str]:
    return {"DT_GERACAO": "20/07/2026", "HH_GERACAO": "05:46:50", "AA_ELEICAO": "2026", "NR_PROTOCOLO_REGISTRO": protocol, "CD_CONTRATANTE": "1", "DS_ORIGEM_RECURSO": "#NULO#", "NR_CPF_CNPJ_PAGANTE": "12345678000199", "NM_PAGANTE": "Pagante Teste"}


def normalized(rows: list[dict[str, str]]) -> list[dict]:
    source = TSESource(Path("."))
    return source._join(rows, [contractor_row(r["NR_PROTOCOLO_REGISTRO"]) for r in rows], [payer_row(r["NR_PROTOCOLO_REGISTRO"]) for r in rows])


def test_first_and_second_execution_are_idempotent(tmp_path: Path) -> None:
    db = Database(tmp_path / "monitor.sqlite3")
    db.init()
    records = normalized([main_row()])
    new, changed = db.apply_records(records, "20/07/2026 05:46:52", 1)
    assert len(new) == 1 and not changed
    new, changed = db.apply_records(records, "20/07/2026 05:46:52", 2)
    assert not new and not changed
    assert len(db.current()) == 1
    db.close()


def test_change_is_field_level_history(tmp_path: Path) -> None:
    db = Database(tmp_path / "monitor.sqlite3")
    db.init()
    db.apply_records(normalized([main_row()]), "g1", 1)
    changed_row = main_row(company="Instituto Alterado")
    _, changed = db.apply_records(normalized([changed_row]), "g2", 2)
    assert len(changed) == 1
    fields = db.conn.execute("SELECT field_path,old_value_json,new_value_json FROM research_changes").fetchall()
    assert any(row[0] == "company_name" and "Instituto Teste" in row[1] and "Instituto Alterado" in row[2] for row in fields)
    db.close()


def test_duplicate_protocol_is_rejected() -> None:
    source = TSESource(Path("."))
    with pytest.raises(ValueError, match="duplicado"):
        source._join([main_row(), main_row()], [contractor_row()], [payer_row()])


def test_invalid_date_is_rejected() -> None:
    row = main_row()
    row["DT_DIVULGACAO"] = "31/99/2026"
    with pytest.raises(ValueError, match="Data inválida"):
        _record_from_main(row, {})


def test_manual_observations_survive_excel_regeneration(tmp_path: Path) -> None:
    db = Database(tmp_path / "monitor.sqlite3")
    db.init()
    db.apply_records(normalized([main_row()]), "g1", 1)
    db.upsert_annotation("BR000012026", "Verificar publicação", "prioritario", 1)
    record = json.loads(db.current()["BR000012026"]["payload_json"])
    current = [record]
    current[0].update({"first_seen_at": "2026-07-20 10:00:00", "last_checked_at": "2026-07-20 10:00:00", "publication_status": "aguardando_data_permitida", "business_hash": db.current()["BR000012026"]["business_hash"], "availability_status": "ativa", "manual_notes": "Verificar publicação", "manual_tags": "prioritario", "manual_priority": 1})
    output = tmp_path / "monitor.xlsx"
    export_workbook(output, current, db.annotations(), {"source_generation": "g1", "window_days": 7}, [], [], [])
    assert import_manual_annotations(output) == [{"protocol": "BR000012026", "notes": "Verificar publicação", "tags": "prioritario", "priority": 1}]
    db.close()


def test_alert_event_is_deduplicated(tmp_path: Path) -> None:
    db = Database(tmp_path / "monitor.sqlite3")
    db.init()
    run_id = db.begin_run()
    assert db.create_alert(run_id, "email", "Assunto", "Corpo", "new:BR000012026")
    assert not db.create_alert(run_id, "email", "Assunto", "Corpo", "new:BR000012026")
    db.close()


def test_empty_or_incomplete_source_does_not_replace_state(tmp_path: Path) -> None:
    db = Database(tmp_path / "monitor.sqlite3")
    db.init()
    db.apply_records(normalized([main_row()]), "g1", 1)
    with pytest.raises(ValueError):
        TSESource(tmp_path)._join([], [], [])
    assert "BR000012026" in db.current()
    db.close()


def test_configurable_registration_period_filter() -> None:
    records = normalized([main_row()])
    assert _filtered(records, {"registration_from": "2026-07-21"}) == []
    assert len(_filtered(records, {"registration_to": "2026-07-20"})) == 1


def test_download_failure_uses_limited_retries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = 0

    def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise URLError("sem internet")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(RuntimeError, match="Falha no download"):
        TSESource(tmp_path, retries=2, timeout=1)._download("https://exemplo.invalid/a.zip", tmp_path / "a.zip")
    assert calls == 2


def test_invalid_zip_is_rejected(tmp_path: Path) -> None:
    invalid = tmp_path / "invalido.zip"
    invalid.write_bytes(b"PK\x03\x04arquivo incompleto")
    source = TSESource(tmp_path)
    with pytest.raises(zipfile.BadZipFile):
        source._read_resource((DEFAULT_RESOURCES["pesquisas"], {"raw_path": str(invalid)}), "pesquisas")


def test_schema_change_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "esquema.zip"
    content = "DT_GERACAO;HH_GERACAO\n20/07/2026;05:46:52\n".encode("iso-8859-1")
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("pesquisa_eleitoral_2026_BRASIL.csv", content)
    source = TSESource(tmp_path)
    with pytest.raises(ValueError, match="Colunas cr.ticas ausentes"):
        source._read_resource((DEFAULT_RESOURCES["pesquisas"], {"raw_path": str(archive)}), "pesquisas")


def test_digest_includes_upcoming_allowed_date_in_idempotency_keys() -> None:
    record = normalized([main_row(allowed="2026-07-25 00:00:00")])[0]
    _, body, keys = build_digest([], [], [record], 1, 7)
    assert "Próximos 7 dias" in body
    assert any(key.startswith("allowed:BR000012026:2026-07-25") for key in keys)
