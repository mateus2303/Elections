from __future__ import annotations

from typing import Any

import pandas as pd

from .domain import Issue, is_present, plain_text
from .standardization import StandardizedData


REGIONS = {"Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"}
UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


def _source_row(row: pd.Series) -> int | None:
    value = row.get("source_row")
    return int(value) if is_present(value) else None


def _issue(issues: list[Issue], severity: str, sheet: str, row: pd.Series, field: str | None, message: str, suggestion: str) -> None:
    issues.append(Issue(severity, sheet, _source_row(row), None, field, message, suggestion))


def _validate_numeric(issues: list[Issue], sheet: str, frame: pd.DataFrame, fields: list[str]) -> None:
    for field in fields:
        if field not in frame:
            continue
        original = f"{field}_original"
        for _, row in frame.iterrows():
            value = row[field]
            source = row.get(original)
            if is_present(source) and not is_present(value):
                _issue(issues, "erro", sheet, row, field, f"'{field}' não é numérico.", "Informe um número ou deixe o campo vazio quando opcional.")
            if is_present(value) and field.endswith("pct") and not 0 <= float(value) <= 100:
                _issue(issues, "erro", sheet, row, field, f"'{field}' está fora do intervalo de 0 a 100.", "Corrija o percentual publicado.")
            if is_present(value) and field == "margem_erro_pp" and not 0 <= float(value) <= 20:
                _issue(issues, "erro", sheet, row, field, "A margem de erro deve estar entre 0 e 20 p.p.", "Revise a unidade e o valor informado.")
            if is_present(value) and field == "nivel_confianca_pct" and not 50 <= float(value) <= 100:
                _issue(issues, "erro", sheet, row, field, "O nível de confiança deve estar entre 50% e 100%.", "Revise o valor publicado.")
            if is_present(value) and field.startswith("amostra") and float(value) <= 0:
                _issue(issues, "erro", sheet, row, field, "A amostra preenchida deve ser maior que zero.", "Corrija ou deixe o campo vazio quando não divulgado.")


def _validate_common(issues: list[Issue], sheet: str, frame: pd.DataFrame) -> None:
    required = ["data_referencia", "instituto", "tipo_pesquisa", "frequencia_original", "nivel_geografico", "geografia", "segmento_tipo", "segmento"]
    for _, row in frame.iterrows():
        for field in required:
            if not is_present(row[field]):
                _issue(issues, "erro", sheet, row, field, f"Campo obrigatório ausente: '{field}'.", "Preencha o campo conforme a pesquisa publicada.")
        if not is_present(row["data_referencia"]):
            _issue(issues, "erro", sheet, row, "data_referencia", "Data de referência inválida ou impossível.", "Informe uma data real do Excel.")
        if row["tipo_pesquisa"] not in {"regular", "tracking"}:
            _issue(issues, "erro", sheet, row, "tipo_pesquisa", "Tipo de pesquisa inválido.", "Use 'regular' ou 'tracking'.")
        if row["frequencia_original"] not in {"pontual", "diaria", "semanal"}:
            _issue(issues, "erro", sheet, row, "frequencia_original", "Frequência original inválida.", "Use 'pontual', 'diaria' ou 'semanal'.")
        level, geography = row["nivel_geografico"], plain_text(row["geografia"])
        if level not in {"Brasil", "Regiao", "UF"}:
            _issue(issues, "erro", sheet, row, "nivel_geografico", "Nível geográfico inválido.", "Use Brasil, Regiao ou UF.")
        elif level == "Brasil" and geography != "Brasil":
            _issue(issues, "erro", sheet, row, "geografia", "Brasil deve ter geografia igual a 'Brasil'.", "Corrija a combinação nível/geografia.")
        elif level == "Regiao" and geography not in REGIONS:
            _issue(issues, "alerta", sheet, row, "geografia", "Agrupamento regional publicado fora da lista canônica de cinco regiões.", "Preserve o rótulo publicado; harmonize somente com regra metodológica aprovada.")
        elif level == "UF" and geography.upper() not in UFS:
            _issue(issues, "erro", sheet, row, "geografia", "UF inválida.", "Use uma sigla de UF válida.")
        if row["segmento_tipo"] not in {"Total", "Idade", "Sexo", "Escolaridade", "Renda", "Religiao", "Outro"}:
            _issue(issues, "erro", sheet, row, "segmento_tipo", "Tipo de segmento inválido.", "Use uma categoria prevista na aba Instrucoes.")
        if row["segmento_tipo"] == "Total" and plain_text(row["segmento"]) != "Total":
            _issue(issues, "erro", sheet, row, "segmento", "Segmento do tipo Total deve ser 'Total'.", "Corrija a combinação tipo/segmento.")
        if is_present(row.get("amostra_segmento")) and is_present(row.get("amostra_total")) and row["amostra_segmento"] > row["amostra_total"]:
            _issue(issues, "erro", sheet, row, "amostra_segmento", "A amostra do segmento é maior que a amostra total.", "Revise o valor divulgado para o recorte.")
        if not is_present(row.get("amostra_total")):
            _issue(issues, "alerta", sheet, row, "amostra_total", "Amostra ausente; será usado fallback conservador no Modelo A.", "Informe a amostra quando a fonte a publicar.")
        if row["segmento_tipo"] != "Total" and not is_present(row.get("amostra_segmento")):
            _issue(issues, "alerta", sheet, row, "amostra_segmento", "Recorte sem amostra publicada; será usado fallback conservador.", "Não copie a amostra total para o recorte.")
        if not is_present(row.get("peso_legacy")):
            _issue(issues, "alerta", sheet, row, "peso_legacy", "Instituto sem peso legado; será aplicado o prior configurado.", "Aguarde a revisão metodológica do instituto provisório.")


def _validate_duplicates(issues: list[Issue], sheet: str, frame: pd.DataFrame, fields: list[str]) -> None:
    if not fields or frame.empty:
        return
    repeated = frame.duplicated(subset=fields, keep=False)
    for _, row in frame.loc[repeated].iterrows():
        _issue(issues, "erro", sheet, row, None, "Duplicata exata inequívoca.", "Mantenha apenas a linha publicada uma vez.")


def validate(data: StandardizedData) -> list[Issue]:
    issues = list(data.issues)
    government, contests = data.government, data.contests
    _validate_common(issues, "Lula3", government)
    _validate_common(issues, "Confrontos", contests)
    _validate_numeric(issues, "Lula3", government, [
        "amostra_total", "amostra_segmento", "margem_erro_pp", "nivel_confianca_pct", "otimo_bom_pct", "regular_pct", "ruim_pessimo_pct",
    ])
    _validate_numeric(issues, "Confrontos", contests, [
        "amostra_total", "amostra_segmento", "margem_erro_pp", "nivel_confianca_pct", "lula_pct", "adversario_pct", "outros_candidatos_pct", "brancos_nulos_indecisos_pct",
    ])
    for _, row in government.iterrows():
        if not is_present(row["otimo_bom_pct"]):
            _issue(issues, "alerta", "Lula3", row, "otimo_bom_pct", "Célula publicada em branco foi preservada como nula e não entrará nessa métrica.", "Não substitua branco publicado por zero.")
        if not is_present(row["ruim_pessimo_pct"]):
            _issue(issues, "erro", "Lula3", row, "ruim_pessimo_pct", "Ruim/Péssimo é obrigatório para a escala de avaliação.", "Preencha o percentual publicado.")
        if not is_present(row["regular_pct"]):
            _issue(issues, "alerta", "Lula3", row, "regular_pct", "Regular não foi publicado; a série será omitida apenas para esta linha.", "Preserve como vazio quando a fonte não divulgar.")
    for _, row in contests.iterrows():
        for field in ["turno", "tipo_cenario", "cenario", "adversario", "lula_pct", "adversario_pct", "outros_candidatos_pct", "base_voto"]:
            if not is_present(row[field]):
                _issue(issues, "erro", "Confrontos", row, field, f"Campo obrigatório ausente: '{field}'.", "Preencha a célula publicada.")
        if row["turno"] not in {"1º turno", "2º turno"}:
            _issue(issues, "erro", "Confrontos", row, "turno", "Turno inválido.", "Use '1º turno' ou '2º turno'.")
        if row["tipo_cenario"] not in {"Estimulada", "Espontânea"}:
            _issue(issues, "erro", "Confrontos", row, "tipo_cenario", "Tipo de cenário inválido.", "Use 'Estimulada' ou 'Espontânea'.")
        if row["base_voto"] not in {"Totais", "Validos"}:
            _issue(issues, "erro", "Confrontos", row, "base_voto", "Base de voto inválida.", "Use 'Totais' ou 'Validos'.")
        values = [row[name] for name in ["lula_pct", "adversario_pct", "outros_candidatos_pct", "brancos_nulos_indecisos_pct"] if is_present(row[name])]
        if values and not 98 <= sum(values) <= 102:
            _issue(issues, "alerta", "Confrontos", row, None, "A soma das categorias publicadas está fora de 98%–102%.", "Revise a transcrição, sem criar residual para forçar 100%.")
        if row["base_voto"] == "Totais" and row["turno"] == "2º turno" and is_present(row["lula_pct"]) and is_present(row["adversario_pct"]) and row["lula_pct"] + row["adversario_pct"] == 0:
            _issue(issues, "erro", "Confrontos", row, None, "Soma zero na conversão para votos válidos.", "Corrija Lula e adversário antes da conversão.")
    _validate_duplicates(issues, "Lula3", government, [column for column in government.columns if not column.endswith("_original") and column not in {"source_row", "source_sheet", "source_file", "raw_payload_json", "poll_group_id", "scenario_id", "scenario_composition_id"}])
    _validate_duplicates(issues, "Confrontos", contests, [column for column in contests.columns if not column.endswith("_original") and column not in {"source_row", "source_sheet", "source_file", "raw_payload_json", "poll_group_id", "scenario_id", "scenario_composition_id"}])
    return issues


def has_blocking_errors(issues: list[Issue]) -> bool:
    return any(issue.severity == "erro" for issue in issues)
