from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .domain import Issue, is_present, normalized_text, plain_text, stable_id
from .ingestion import WorkbookData


NUMERIC_COLUMNS = [
    "amostra_total", "margem_erro_pp", "nivel_confianca_pct", "amostra_segmento",
    "otimo_bom_pct", "regular_pct", "ruim_pessimo_pct", "lula_pct", "adversario_pct",
    "outros_candidatos_pct", "brancos_nulos_indecisos_pct",
]


@dataclass(frozen=True)
class StandardizedData:
    government: pd.DataFrame
    contests: pd.DataFrame
    registry: pd.DataFrame
    issues: list[Issue]


def _choice(value: Any, choices: dict[str, str]) -> str:
    key = normalized_text(value)
    return choices.get(key, plain_text(value))


def _normalise_common(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["instituto_original"] = result["instituto"]
    result["instituto"] = result["instituto"].map(plain_text)
    result["data_referencia_original"] = result["data_referencia"]
    result["data_referencia"] = pd.to_datetime(result["data_referencia"], errors="coerce").dt.normalize()
    for field in NUMERIC_COLUMNS:
        if field in result:
            result[f"{field}_original"] = result[field]
            result[field] = pd.to_numeric(result[field], errors="coerce")
    result["tipo_pesquisa"] = result["tipo_pesquisa"].map(
        lambda value: _choice(value, {"regular": "regular", "tracking": "tracking"})
    )
    result["frequencia_original"] = result["frequencia_original"].map(
        lambda value: _choice(value, {"pontual": "pontual", "diaria": "diaria", "semanal": "semanal"})
    )
    result["nivel_geografico"] = result["nivel_geografico"].map(
        lambda value: _choice(value, {"brasil": "Brasil", "regiao": "Regiao", "uf": "UF"})
    )
    result["segmento_tipo"] = result["segmento_tipo"].map(
        lambda value: _choice(
            value,
            {
                "total": "Total", "idade": "Idade", "sexo": "Sexo", "escolaridade": "Escolaridade",
                "renda": "Renda", "religiao": "Religiao", "outro": "Outro",
            },
        )
    )
    for field in ["geografia", "segmento"]:
        result[field] = result[field].map(plain_text)
    return result


def _registry(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str], list[Issue]]:
    columns = ["instituto", "aliases", "peso_legacy", "situacao", "source_row", "source_sheet", "source_file"]
    registry = frame[columns].copy()
    registry["instituto"] = registry["instituto"].map(plain_text)
    registry["peso_legacy"] = pd.to_numeric(registry["peso_legacy"], errors="coerce")
    registry["situacao"] = registry["situacao"].map(
        lambda value: _choice(value, {"aprovado": "Aprovado", "provisorio": "Provisorio", "inativo": "Inativo"})
    )
    aliases: dict[str, str] = {}
    issues: list[Issue] = []
    for _, row in registry.iterrows():
        candidates = [row["instituto"], *plain_text(row["aliases"]).split(";")]
        for candidate in candidates:
            key = normalized_text(candidate)
            if not key:
                continue
            prior = aliases.get(key)
            if prior and prior != row["instituto"]:
                issues.append(Issue(
                    "erro", "Institutos", int(row["source_row"]), None, "aliases",
                    f"O alias '{candidate}' aponta para '{prior}' e '{row['instituto']}'.",
                    "Mantenha cada alias associado a somente um instituto.",
                ))
            else:
                aliases[key] = row["instituto"]
    registry["registro_gerado"] = False
    return registry, aliases, issues


def _resolve_institutes(frame: pd.DataFrame, registry: pd.DataFrame, aliases: dict[str, str], sheet: str, issues: list[Issue]) -> tuple[pd.DataFrame, pd.DataFrame]:
    result = frame.copy()
    known = registry.set_index("instituto")["peso_legacy"].to_dict()
    status = registry.set_index("instituto")["situacao"].to_dict()
    generated: list[dict[str, Any]] = []
    resolved: list[str] = []
    for _, row in result.iterrows():
        original = plain_text(row["instituto"])
        canonical = aliases.get(normalized_text(original), original)
        resolved.append(canonical)
        if canonical and canonical not in known:
            known[canonical] = float("nan")
            status[canonical] = "Provisorio"
            generated.append({
                "instituto": canonical, "aliases": "", "peso_legacy": float("nan"), "situacao": "Provisorio",
                "source_row": None, "source_sheet": "gerado_pelo_pipeline", "source_file": "",
                "registro_gerado": True,
            })
            issues.append(Issue(
                "alerta", sheet, int(row["source_row"]), None, "instituto",
                f"Instituto '{original}' não está no cadastro; foi tratado como Provisorio.",
                "Inclua o instituto e aliases no cadastro após revisão metodológica.",
            ))
    result["instituto"] = resolved
    result["peso_legacy"] = result["instituto"].map(known)
    result["situacao_instituto"] = result["instituto"].map(status).fillna("Provisorio")
    if generated:
        registry = pd.concat([registry, pd.DataFrame(generated)], ignore_index=True)
    return result, registry.drop_duplicates(subset=["instituto"], keep="first")


def _ids(government: pd.DataFrame, contests: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    def group_id(row: pd.Series) -> str:
        return stable_id("pg", {
            "instituto": row["instituto"], "data_referencia": row["data_referencia"],
            "amostra_total": row["amostra_total"], "tipo_pesquisa": row["tipo_pesquisa"],
            "frequencia_original": row["frequencia_original"],
        })

    government = government.copy()
    contests = contests.copy()
    government["poll_group_id"] = government.apply(group_id, axis=1)
    contests["poll_group_id"] = contests.apply(group_id, axis=1)
    government["scenario_id"] = "scenario_governo"
    government["scenario_composition_id"] = "composition_governo"
    composition_columns = ["poll_group_id", "turno", "tipo_cenario", "cenario", "nivel_geografico", "geografia", "segmento_tipo", "segmento"]
    for _, indexes in contests.groupby(composition_columns, dropna=False).groups.items():
        members = sorted(contests.loc[indexes, "adversario"].map(plain_text).unique().tolist())
        composition = stable_id("comp", {"adversarios": "|".join(members)})
        contests.loc[indexes, "scenario_composition_id"] = composition
    contests["turno"] = contests["turno"].map(
        lambda value: "1º turno" if plain_text(value).startswith("1") else "2º turno" if plain_text(value).startswith("2") else plain_text(value)
    )
    contests["tipo_cenario"] = contests["tipo_cenario"].map(
        lambda value: _choice(value, {"estimulada": "Estimulada", "espontanea": "Espontânea"})
    )
    contests["base_voto"] = contests["base_voto"].map(
        lambda value: _choice(value, {"totais": "Totais", "validos": "Validos"})
    )
    contests["scenario_id"] = contests.apply(
        lambda row: stable_id("sc", {
            "turno": row["turno"], "tipo_cenario": row["tipo_cenario"], "cenario": row["cenario"],
            "composition": row["scenario_composition_id"],
        }),
        axis=1,
    )
    return government, contests


def standardize(workbook: WorkbookData) -> StandardizedData:
    issues: list[Issue] = []
    registry, aliases, registry_issues = _registry(workbook.institutes.frame)
    issues.extend(registry_issues)
    government = _normalise_common(workbook.government.frame)
    contests = _normalise_common(workbook.contests.frame)
    government, registry = _resolve_institutes(government, registry, aliases, workbook.government.name, issues)
    contests, registry = _resolve_institutes(contests, registry, aliases, workbook.contests.name, issues)
    government, contests = _ids(government, contests)
    return StandardizedData(government=government, contests=contests, registry=registry, issues=issues)
