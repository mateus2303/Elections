#!/usr/bin/env python3
"""Atualiza a Base_nova_limpa.xlsx com as ondas semanais do Atlas.

Uso normal, a partir de qualquer pasta:
    python ATUALIZAR_ATLAS.PY

O script procura a Base_nova_limpa.xlsx e a pasta "Atlas tracking" ao lado da
pasta CODIGOS. Os arquivos do Atlas são identificados pelo radical fixo: o
trecho variável com data/hora do download é ignorado. Ele aceita --dry-run
para apenas conferir o que seria incluído.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import unicodedata
from copy import copy
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable

try:
    from openpyxl import load_workbook
    from openpyxl.utils.cell import range_boundaries
except ImportError as exc:  # pragma: no cover - mensagem para o operador
    raise SystemExit(
        "Este script precisa da biblioteca openpyxl. Instale com: "
        "python -m pip install openpyxl"
    ) from exc


class ErroAtlas(RuntimeError):
    """Erro bloqueante que deixa a base original intacta."""


COLUNAS_LULA3 = [
    "data_referencia", "instituto", "tipo_pesquisa", "frequencia_original",
    "amostra_total", "margem_erro_pp", "nivel_confianca_pct", "nivel_geografico",
    "geografia", "segmento_tipo", "segmento", "amostra_segmento", "otimo_bom_pct",
    "regular_pct", "ruim_pessimo_pct",
]

COLUNAS_CONFRONTOS = [
    "data_referencia", "instituto", "tipo_pesquisa", "frequencia_original",
    "amostra_total", "margem_erro_pp", "nivel_confianca_pct", "turno", "tipo_cenario",
    "cenario", "adversario", "nivel_geografico", "geografia", "segmento_tipo", "segmento",
    "amostra_segmento", "lula_pct", "adversario_pct", "outros_candidatos_pct",
    "brancos_nulos_indecisos_pct", "base_voto",
]

RADICAIS_ESPERADOS = {
    "governo": "government_evaluation",
    "primeiro_turno": "1st_round_-_with_flavio",
    "flavio": "2nd_round_lula_vs_flavio_bolsonaro",
    "renan": "2nd_round_lula_vs_renan_santos",
    "zema": "2nd_round_lula_vs_romeu_zema",
    "caiado": "2nd_round_lula_vs_ronaldo_caiado",
}

ADVERSARIOS_SEGUNDO_TURNO = {
    "flavio": "Flávio",
    "renan": "Renan Santos",
    "zema": "Romeu Zema",
    "caiado": "Ronaldo Caiado",
}

NAO_VOTO_1T = {
    "voto branco / nulo", "branco/nulo", "brancos/nulos", "nao sei", "ns/nr",
    "branco/nulo/nao sei", "brancos/nulos/nao sei",
}
OUTROS_CANDIDATOS_1T = {"outros", "outros candidatos", "demais candidatos"}
NAO_VOTO_2T = {"branco/nulo/nao sei", "brancos/nulos/nao sei", "branco/nulo", "nao sei"}


@dataclass(frozen=True)
class FonteAtlas:
    caminho: Path
    datas: tuple[date, ...]
    linhas: dict[str, tuple[float | None, ...]]
    rotulos: dict[str, str]


@dataclass
class PlanoAtualizacao:
    fontes: dict[str, FonteAtlas]
    lula3: list[dict[str, Any]]
    confrontos: list[dict[str, Any]]
    ignoradas: int


def normalizar(valor: Any) -> str:
    texto = "" if valor is None else str(valor)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    return " ".join(texto.casefold().strip().split())


def data_real(valor: Any, contexto: str) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        texto = valor.strip()
        for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(texto[:10], formato).date()
            except ValueError:
                pass
    raise ErroAtlas(f"Data inválida em {contexto}: {valor!r}.")


def numero(valor: Any, contexto: str) -> float | None:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if isinstance(valor, bool):
        raise ErroAtlas(f"Percentual inválido em {contexto}: {valor!r}.")
    try:
        resultado = float(str(valor).replace(",", ".")) if isinstance(valor, str) else float(valor)
    except (TypeError, ValueError) as exc:
        raise ErroAtlas(f"Percentual inválido em {contexto}: {valor!r}.") from exc
    if not 0 <= resultado <= 100:
        raise ErroAtlas(f"Percentual fora de 0–100 em {contexto}: {resultado}.")
    return resultado


def soma_publicada(valores: Iterable[float | None]) -> float:
    return round(sum(valor for valor in valores if valor is not None), 10)


def conferir_soma(total: float, contexto: str) -> None:
    if not 99.5 <= total <= 100.5:
        raise ErroAtlas(
            f"A soma publicada em {contexto} é {total:.1f}%, fora da tolerância de arredondamento."
        )


def hash_sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def timestamp_nome(caminho: Path) -> datetime:
    correspondencia = re.search(r"-(\d{12})\.xlsx$", caminho.name, re.IGNORECASE)
    if not correspondencia:
        return datetime.min
    try:
        return datetime.strptime(correspondencia.group(1), "%d%m%Y%H%M")
    except ValueError:
        return datetime.min


def ler_fonte(caminho: Path) -> FonteAtlas:
    try:
        workbook = load_workbook(caminho, read_only=True, data_only=True)
    except Exception as exc:
        raise ErroAtlas(f"Não foi possível abrir a fonte {caminho.name}: {exc}") from exc
    try:
        if not workbook.sheetnames:
            raise ErroAtlas(f"A fonte {caminho.name} não possui abas.")
        planilha = workbook[workbook.sheetnames[0]]
        cabecalho = [celula.value for celula in planilha[1]]
        if len(cabecalho) < 2:
            raise ErroAtlas(f"A fonte {caminho.name} não possui datas na primeira linha.")
        datas = tuple(data_real(valor, f"{caminho.name}, coluna {indice + 2}") for indice, valor in enumerate(cabecalho[1:]))
        if len(set(datas)) != len(datas) or tuple(sorted(datas)) != datas:
            raise ErroAtlas(f"As datas de {caminho.name} devem ser únicas e crescentes.")

        linhas: dict[str, tuple[float | None, ...]] = {}
        rotulos: dict[str, str] = {}
        for indice_linha, linha in enumerate(planilha.iter_rows(min_row=2, values_only=True), start=2):
            rotulo = linha[0]
            valores = linha[1:len(datas) + 1]
            if rotulo is None and not any(valor is not None for valor in valores):
                continue
            if rotulo is None:
                raise ErroAtlas(f"Rótulo ausente em {caminho.name}, linha {indice_linha}.")
            chave = normalizar(rotulo)
            if chave in linhas:
                raise ErroAtlas(f"Rótulo duplicado em {caminho.name}: {rotulo!r}.")
            linhas[chave] = tuple(
                numero(valor, f"{caminho.name}, linha {indice_linha}, data {datas[indice].isoformat()}")
                for indice, valor in enumerate(valores)
            )
            rotulos[chave] = str(rotulo).strip()
        if not linhas:
            raise ErroAtlas(f"A fonte {caminho.name} não possui linhas de dados.")
        return FonteAtlas(caminho=caminho, datas=datas, linhas=linhas, rotulos=rotulos)
    finally:
        workbook.close()


def localizar_fontes(pasta: Path) -> dict[str, FonteAtlas]:
    if not pasta.is_dir():
        raise ErroAtlas(f"Pasta de fontes não encontrada: {pasta}")
    resultado: dict[str, FonteAtlas] = {}
    for nome, radical in RADICAIS_ESPERADOS.items():
        candidatas = sorted(
            caminho for caminho in pasta.iterdir()
            if caminho.is_file()
            and caminho.suffix.casefold() == ".xlsx"
            and caminho.stem.casefold().startswith(radical.casefold())
        )
        if not candidatas:
            raise ErroAtlas(f"Arquivo Atlas ausente: esperado radical {radical!r} em {pasta}.")
        lidas = [ler_fonte(caminho) for caminho in candidatas]
        resultado[nome] = max(
            lidas,
            key=lambda fonte: (fonte.datas[-1], timestamp_nome(fonte.caminho), fonte.caminho.stat().st_mtime),
        )
    return resultado


def valor_linha(fonte: FonteAtlas, aliases: Iterable[str], contexto: str) -> tuple[float | None, ...]:
    for alias in aliases:
        chave = normalizar(alias)
        if chave in fonte.linhas:
            return fonte.linhas[chave]
    raise ErroAtlas(f"Rótulo obrigatório ausente em {fonte.caminho.name}: {contexto}.")


def linhas_governo(fonte: FonteAtlas) -> list[dict[str, Any]]:
    otimo = valor_linha(fonte, ["Ótimo / Bom", "Ótimo/Bom"], "Ótimo / Bom")
    regular = valor_linha(fonte, ["Regular"], "Regular")
    ruim = valor_linha(fonte, ["Ruim / Péssimo", "Ruim/Péssimo"], "Ruim / Péssimo")
    resultado = []
    for indice, data_referencia in enumerate(fonte.datas):
        valores = (otimo[indice], regular[indice], ruim[indice])
        if any(valor is None for valor in valores):
            raise ErroAtlas(f"Avaliação incompleta em {fonte.caminho.name}, data {data_referencia.isoformat()}.")
        conferir_soma(soma_publicada(valores), f"avaliação do governo em {data_referencia.isoformat()}")
        resultado.append({
            "data_referencia": data_referencia, "instituto": "Atlas", "tipo_pesquisa": "tracking",
            "frequencia_original": "semanal", "amostra_total": None, "margem_erro_pp": None,
            "nivel_confianca_pct": None, "nivel_geografico": "Brasil", "geografia": "Brasil",
            "segmento_tipo": "Total", "segmento": "Total", "amostra_segmento": None,
            "otimo_bom_pct": otimo[indice], "regular_pct": regular[indice], "ruim_pessimo_pct": ruim[indice],
        })
    return resultado


def rotulo_canonico_primeiro_turno(rotulo: str) -> str:
    if normalizar(rotulo) == "flavio bolsonaro":
        return "Flávio"
    return rotulo.strip()


def linhas_primeiro_turno(fonte: FonteAtlas) -> list[dict[str, Any]]:
    lula = valor_linha(fonte, ["Lula"], "Lula")
    nao_voto = [valores for chave, valores in fonte.linhas.items() if chave in NAO_VOTO_1T]
    outros_publicados = [valores for chave, valores in fonte.linhas.items() if chave in OUTROS_CANDIDATOS_1T]
    if not nao_voto:
        raise ErroAtlas(f"Não foram encontradas categorias de não voto em {fonte.caminho.name}.")
    candidaturas = {
        chave: valores for chave, valores in fonte.linhas.items()
        if chave not in NAO_VOTO_1T | OUTROS_CANDIDATOS_1T | {"lula"}
    }
    if not candidaturas:
        raise ErroAtlas(f"Nenhuma candidatura foi encontrada em {fonte.caminho.name}.")

    resultado = []
    for indice, data_referencia in enumerate(fonte.datas):
        if lula[indice] is None:
            raise ErroAtlas(f"Lula está em branco no primeiro turno de {data_referencia.isoformat()}.")
        candidatos_publicados = {
            chave: valores[indice] for chave, valores in candidaturas.items() if valores[indice] is not None
        }
        if not candidatos_publicados:
            raise ErroAtlas(f"Nenhum adversário publicado no primeiro turno de {data_referencia.isoformat()}.")
        nao_voto_pct = soma_publicada(valores[indice] for valores in nao_voto)
        outros_fixos_pct = soma_publicada(valores[indice] for valores in outros_publicados)
        conferir_soma(
            soma_publicada([lula[indice], *candidatos_publicados.values(), nao_voto_pct, outros_fixos_pct]),
            f"primeiro turno em {data_referencia.isoformat()}",
        )
        for chave, adversario_pct in candidatos_publicados.items():
            outros_pct = outros_fixos_pct + soma_publicada(
                valor for outro, valor in candidatos_publicados.items() if outro != chave
            )
            resultado.append({
                "data_referencia": data_referencia, "instituto": "Atlas", "tipo_pesquisa": "tracking",
                "frequencia_original": "semanal", "amostra_total": None, "margem_erro_pp": None,
                "nivel_confianca_pct": None, "turno": "1º turno", "tipo_cenario": "Estimulada",
                "cenario": "Com Flávio", "adversario": rotulo_canonico_primeiro_turno(fonte.rotulos[chave]),
                "nivel_geografico": "Brasil", "geografia": "Brasil", "segmento_tipo": "Total",
                "segmento": "Total", "amostra_segmento": None, "lula_pct": lula[indice],
                "adversario_pct": adversario_pct, "outros_candidatos_pct": outros_pct,
                "brancos_nulos_indecisos_pct": nao_voto_pct, "base_voto": "Totais",
            })
    return resultado


def linhas_segundo_turno(fonte: FonteAtlas, adversario: str) -> list[dict[str, Any]]:
    lula = valor_linha(fonte, ["Lula"], "Lula")
    adversario_valores = valor_linha(fonte, [adversario, f"{adversario} Bolsonaro"], adversario)
    nao_voto = valor_linha(fonte, NAO_VOTO_2T, "Branco/Nulo/Não sei")
    resultado = []
    for indice, data_referencia in enumerate(fonte.datas):
        valores = (lula[indice], adversario_valores[indice], nao_voto[indice])
        if any(valor is None for valor in valores):
            raise ErroAtlas(f"Segundo turno incompleto em {fonte.caminho.name}, data {data_referencia.isoformat()}.")
        conferir_soma(soma_publicada(valores), f"Lula × {adversario} em {data_referencia.isoformat()}")
        resultado.append({
            "data_referencia": data_referencia, "instituto": "Atlas", "tipo_pesquisa": "tracking",
            "frequencia_original": "semanal", "amostra_total": None, "margem_erro_pp": None,
            "nivel_confianca_pct": None, "turno": "2º turno", "tipo_cenario": "Estimulada",
            "cenario": "Único", "adversario": adversario, "nivel_geografico": "Brasil",
            "geografia": "Brasil", "segmento_tipo": "Total", "segmento": "Total",
            "amostra_segmento": None, "lula_pct": lula[indice], "adversario_pct": adversario_valores[indice],
            "outros_candidatos_pct": 0.0, "brancos_nulos_indecisos_pct": nao_voto[indice],
            "base_voto": "Totais",
        })
    return resultado


def cabeçalhos(planilha: Any, esperadas: list[str], nome: str) -> tuple[list[str], int, int]:
    if name := next((celula.coordinate for linha in planilha.iter_rows() for celula in linha if celula.data_type == "f"), None):
        raise ErroAtlas(f"Aba {nome} contém fórmula em {name}; o atualizador só aceita tabela de dados sem fórmulas.")
    tabela = next(iter(planilha.tables.values()), None)
    if tabela is None:
        raise ErroAtlas(f"Aba {nome} não contém tabela do Excel.")
    min_coluna, min_linha, max_coluna, max_linha = range_boundaries(tabela.ref)
    if min_linha != 4 or min_coluna != 1:
        raise ErroAtlas(f"Tabela da aba {nome} não começa em A4: {tabela.ref}.")
    obtidas = [planilha.cell(4, coluna).value for coluna in range(1, max_coluna + 1)]
    if obtidas != esperadas:
        raise ErroAtlas(f"Cabeçalhos inesperados na aba {nome}.")
    return obtidas, max_linha, max_coluna


def ler_registros(planilha: Any, colunas: list[str], fim_linha: int, fim_coluna: int) -> list[dict[str, Any]]:
    registros = []
    for linha in range(5, fim_linha + 1):
        valores = [planilha.cell(linha, coluna).value for coluna in range(1, fim_coluna + 1)]
        if not any(valor is not None for valor in valores):
            continue
        registros.append(dict(zip(colunas, valores)))
    return registros


def eh_atlas_tracking_total(registro: dict[str, Any]) -> bool:
    return (
        normalizar(registro.get("instituto")) == "atlas"
        and normalizar(registro.get("tipo_pesquisa")) == "tracking"
        and normalizar(registro.get("nivel_geografico")) == "brasil"
        and normalizar(registro.get("geografia")) == "brasil"
        and normalizar(registro.get("segmento_tipo")) == "total"
        and normalizar(registro.get("segmento")) == "total"
    )


def chave_lula3(registro: dict[str, Any]) -> tuple[Any, ...]:
    return (
        data_real(registro["data_referencia"], "Base/Lula3"),
        *(normalizar(registro[coluna]) for coluna in (
            "instituto", "tipo_pesquisa", "frequencia_original", "nivel_geografico", "geografia",
            "segmento_tipo", "segmento",
        )),
    )


def chave_confrontos(registro: dict[str, Any]) -> tuple[Any, ...]:
    return (
        data_real(registro["data_referencia"], "Base/Confrontos"),
        *(normalizar(registro[coluna]) for coluna in (
            "instituto", "tipo_pesquisa", "frequencia_original", "turno", "tipo_cenario", "cenario",
            "adversario", "nivel_geografico", "geografia", "segmento_tipo", "segmento", "base_voto",
        )),
    )


def valores_iguais(a: dict[str, Any], b: dict[str, Any], campos: Iterable[str]) -> bool:
    for campo in campos:
        valor_a, valor_b = a.get(campo), b.get(campo)
        if valor_a is None or valor_b is None:
            if valor_a is not None or valor_b is not None:
                return False
        elif abs(float(valor_a) - float(valor_b)) > 1e-9:
            return False
    return True


def ultimo_dia(registros: Iterable[dict[str, Any]]) -> date | None:
    datas = [data_real(registro["data_referencia"], "Base") for registro in registros]
    return max(datas) if datas else None


def filtrar_novas(
    origem: list[dict[str, Any]],
    existentes: list[dict[str, Any]],
    chave: Any,
    campos: Iterable[str],
) -> tuple[list[dict[str, Any]], int]:
    indice: dict[tuple[Any, ...], dict[str, Any]] = {}
    for registro in existentes:
        chave_registro = chave(registro)
        if chave_registro in indice:
            raise ErroAtlas(f"Duplicata inequívoca já existente na base: {chave_registro}.")
        indice[chave_registro] = registro
    corte = ultimo_dia(existentes)
    novas: list[dict[str, Any]] = []
    ignoradas = 0
    for registro in origem:
        data_registro = data_real(registro["data_referencia"], "Fonte Atlas")
        registro_existente = indice.get(chave(registro))
        if registro_existente is not None and not valores_iguais(registro, registro_existente, campos):
            raise ErroAtlas(
                f"Conflito com linha já carregada em {data_registro.isoformat()}: "
                f"{chave(registro)}. A base não foi alterada."
            )
        if corte is not None and data_registro <= corte:
            ignoradas += 1
        elif registro_existente is not None:
            ignoradas += 1
        else:
            novas.append(registro)
    return novas, ignoradas


def montar_plano(fontes: dict[str, FonteAtlas], registros_lula3: list[dict[str, Any]], registros_confrontos: list[dict[str, Any]]) -> PlanoAtualizacao:
    origem_lula3 = linhas_governo(fontes["governo"])
    origem_confrontos = linhas_primeiro_turno(fontes["primeiro_turno"])
    for nome, adversario in ADVERSARIOS_SEGUNDO_TURNO.items():
        origem_confrontos.extend(linhas_segundo_turno(fontes[nome], adversario))

    existentes_lula3 = [registro for registro in registros_lula3 if eh_atlas_tracking_total(registro)]
    existentes_1t = [
        registro for registro in registros_confrontos
        if eh_atlas_tracking_total(registro)
        and normalizar(registro.get("turno")) == "1o turno"
        and normalizar(registro.get("cenario")) == "com flavio"
    ]
    existentes_2t: dict[str, list[dict[str, Any]]] = {adversario: [] for adversario in ADVERSARIOS_SEGUNDO_TURNO.values()}
    for registro in registros_confrontos:
        if not eh_atlas_tracking_total(registro) or normalizar(registro.get("turno")) != "2o turno":
            continue
        for adversario in existentes_2t:
            if normalizar(registro.get("adversario")) == normalizar(adversario):
                existentes_2t[adversario].append(registro)

    novas_lula3, ignoradas_lula3 = filtrar_novas(
        origem_lula3, existentes_lula3, chave_lula3, ["otimo_bom_pct", "regular_pct", "ruim_pessimo_pct"]
    )
    origem_1t = [registro for registro in origem_confrontos if normalizar(registro["turno"]) == "1o turno"]
    novas_1t, ignoradas_1t = filtrar_novas(
        origem_1t, existentes_1t, chave_confrontos,
        ["lula_pct", "adversario_pct", "outros_candidatos_pct", "brancos_nulos_indecisos_pct"],
    )
    novas_confrontos = list(novas_1t)
    ignoradas = ignoradas_lula3 + ignoradas_1t
    for adversario in ADVERSARIOS_SEGUNDO_TURNO.values():
        origem = [
            registro for registro in origem_confrontos
            if normalizar(registro["turno"]) == "2o turno"
            and normalizar(registro["adversario"]) == normalizar(adversario)
        ]
        novas, ignoradas_serie = filtrar_novas(
            origem, existentes_2t[adversario], chave_confrontos,
            ["lula_pct", "adversario_pct", "outros_candidatos_pct", "brancos_nulos_indecisos_pct"],
        )
        novas_confrontos.extend(novas)
        ignoradas += ignoradas_serie
    return PlanoAtualizacao(fontes=fontes, lula3=novas_lula3, confrontos=novas_confrontos, ignoradas=ignoradas)


def copiar_estilo_linha(planilha: Any, origem: int, destino: int, fim_coluna: int) -> None:
    for coluna in range(1, fim_coluna + 1):
        origem_celula = planilha.cell(origem, coluna)
        destino_celula = planilha.cell(destino, coluna)
        destino_celula._style = copy(origem_celula._style)
        if origem_celula.has_style:
            destino_celula.number_format = origem_celula.number_format
        destino_celula.protection = copy(origem_celula.protection)
        destino_celula.alignment = copy(origem_celula.alignment)


def gravar_tabela(planilha: Any, colunas: list[str], fim_antigo: int, fim_coluna: int, novos: list[dict[str, Any]]) -> None:
    atuais = ler_registros(planilha, colunas, fim_antigo, fim_coluna)
    completos = atuais + novos
    completos.sort(key=lambda registro: data_real(registro["data_referencia"], f"{planilha.title}/data_referencia"))
    fim_novo = 4 + len(completos)
    for linha in range(fim_antigo + 1, fim_novo + 1):
        copiar_estilo_linha(planilha, fim_antigo, linha, fim_coluna)
    for linha, registro in enumerate(completos, start=5):
        for coluna, nome in enumerate(colunas, start=1):
            valor = registro.get(nome)
            if nome == "data_referencia" and valor is not None:
                valor = data_real(valor, f"{planilha.title}/data_referencia")
            planilha.cell(linha, coluna).value = valor
        planilha.cell(linha, 1).number_format = "yyyy-mm-dd"
        planilha.row_dimensions[linha].hidden = False
    planilha.auto_filter.ref = None
    tabela = next(iter(planilha.tables.values()))
    referencia = f"A4:{planilha.cell(4, fim_coluna).column_letter}{fim_novo}"
    tabela.ref = referencia
    if tabela.autoFilter is not None:
        tabela.autoFilter.ref = referencia


def validar_saida(caminho: Path, esperadas_lula3: list[dict[str, Any]], esperadas_confrontos: list[dict[str, Any]]) -> None:
    workbook = load_workbook(caminho, read_only=False, data_only=True)
    try:
        for nome, colunas, esperadas, chave, campos in (
            ("Lula3", COLUNAS_LULA3, esperadas_lula3, chave_lula3, ["otimo_bom_pct", "regular_pct", "ruim_pessimo_pct"]),
            ("Confrontos", COLUNAS_CONFRONTOS, esperadas_confrontos, chave_confrontos, ["lula_pct", "adversario_pct", "outros_candidatos_pct", "brancos_nulos_indecisos_pct"]),
        ):
            planilha = workbook[nome]
            obtidas, fim, fim_coluna = cabeçalhos(planilha, colunas, nome)
            registros = ler_registros(planilha, obtidas, fim, fim_coluna)
            datas = [data_real(registro["data_referencia"], f"{nome}/data_referencia") for registro in registros]
            if datas != sorted(datas):
                raise ErroAtlas(f"Aba {nome} não ficou em ordem cronológica.")
            if any(planilha.row_dimensions[linha].hidden for linha in range(5, fim + 1)):
                raise ErroAtlas(f"Aba {nome} contém linha de dados oculta.")
            indice = {chave(registro): registro for registro in registros}
            for esperada in esperadas:
                encontrada = indice.get(chave(esperada))
                if encontrada is None or not valores_iguais(esperada, encontrada, campos):
                    raise ErroAtlas(f"Reconciliação falhou para {nome}: {chave(esperada)}.")
    finally:
        workbook.close()


def localizar_padroes(caminho_script: Path) -> tuple[Path, Path]:
    for pasta in (caminho_script.parent, *caminho_script.parents):
        base = pasta / "Base_nova_limpa.xlsx"
        fontes = pasta / "Atlas tracking"
        if base.exists() and fontes.is_dir():
            return base, fontes
    raise ErroAtlas("Não foi possível localizar Base_nova_limpa.xlsx e a pasta Atlas tracking.")


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atualiza a base com as ondas semanais do Atlas.")
    parser.add_argument("--base", type=Path, help="Caminho da Base_nova_limpa.xlsx.")
    parser.add_argument("--pasta-atlas", type=Path, help="Pasta que contém os arquivos .xlsx do Atlas.")
    parser.add_argument("--dry-run", action="store_true", help="Confere tudo, mas não altera a base.")
    return parser.parse_args()


def main() -> int:
    args = argumentos()
    try:
        padrao_base, padrao_fontes = localizar_padroes(Path(__file__).resolve())
        base = (args.base or padrao_base).resolve()
        pasta_atlas = (args.pasta_atlas or padrao_fontes).resolve()
        if not base.is_file():
            raise ErroAtlas(f"Base não encontrada: {base}")

        fontes = localizar_fontes(pasta_atlas)
        workbook = load_workbook(base, read_only=False, data_only=False)
        try:
            colunas_lula3, fim_lula3, fim_coluna_lula3 = cabeçalhos(workbook["Lula3"], COLUNAS_LULA3, "Lula3")
            colunas_confrontos, fim_confrontos, fim_coluna_confrontos = cabeçalhos(
                workbook["Confrontos"], COLUNAS_CONFRONTOS, "Confrontos"
            )
            registros_lula3 = ler_registros(workbook["Lula3"], colunas_lula3, fim_lula3, fim_coluna_lula3)
            registros_confrontos = ler_registros(
                workbook["Confrontos"], colunas_confrontos, fim_confrontos, fim_coluna_confrontos
            )
            plano = montar_plano(fontes, registros_lula3, registros_confrontos)

            print("Fontes Atlas selecionadas:")
            for nome, fonte in plano.fontes.items():
                print(f"- {nome}: {fonte.caminho.name} | até {fonte.datas[-1].isoformat()} | sha256 {hash_sha256(fonte.caminho)}")
            print(
                f"\nLinhas novas: Lula3={len(plano.lula3)} | Confrontos={len(plano.confrontos)} "
                f"| históricas/repetidas ignoradas={plano.ignoradas}"
            )
            if args.dry_run:
                print("Dry-run concluído: a base não foi alterada.")
                return 0
            if not plano.lula3 and not plano.confrontos:
                print("A base já contém a última onda disponível. Nenhuma alteração foi feita.")
                return 0

            gravar_tabela(workbook["Lula3"], colunas_lula3, fim_lula3, fim_coluna_lula3, plano.lula3)
            gravar_tabela(
                workbook["Confrontos"], colunas_confrontos, fim_confrontos, fim_coluna_confrontos, plano.confrontos
            )
            with NamedTemporaryFile(
                prefix="Base_nova_limpa_atlas_", suffix=".xlsx", dir=base.parent, delete=False
            ) as arquivo_temporario:
                temporario = Path(arquivo_temporario.name)
            workbook.save(temporario)
        finally:
            workbook.close()

        try:
            validar_saida(temporario, plano.lula3, plano.confrontos)
            os.replace(temporario, base)
        finally:
            if temporario.exists():
                temporario.unlink()
        print(f"Base atualizada com sucesso: {base}")
        return 0
    except ErroAtlas as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    except PermissionError:
        print("ERRO: feche a Base_nova_limpa.xlsx no Excel e tente novamente.", file=sys.stderr)
        return 3
    except Exception as exc:  # pragma: no cover - proteção operacional
        print(f"ERRO INESPERADO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
