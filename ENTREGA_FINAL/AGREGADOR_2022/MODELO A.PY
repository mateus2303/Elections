"""
MODELO A — AGREGADOR HISTÓRICO DA ELEIÇÃO PRESIDENCIAL DE 2022
================================================================

Uso:
    1. Deixe este arquivo ao lado de ``Base_nova_limpa.xlsx``.
    2. Feche a base e eventuais planilhas de resultado abertas no Excel.
    3. Execute: python "MODELO A.PY"

O programa gera somente três produtos, cada um em PNG e XLSX:
    - primeiro turno em votos totais;
    - Lula × Bolsonaro no segundo turno em votos totais;
    - Lula × Bolsonaro no segundo turno em votos válidos.

O código é autocontido. Não importa scripts, configurações ou módulos locais.
Ele preserva o núcleo metodológico do Modelo A oficial: média ponderada em
janela de 30 dias, qualidade do instituto, recência linear, cap de amostra e
faixa amostral aproximada. Como POLPRES3 não publica amostras no consolidado,
o fallback conservador de 600 entrevistas é registrado e usado explicitamente.
"""

from __future__ import annotations

import math
import shutil
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ModuleNotFoundError as erro:
    print(
        "Falta uma dependência do Python. Execute uma vez:\n"
        "python -m pip install pandas numpy openpyxl matplotlib\n"
        f"Detalhe: {erro}",
        file=sys.stderr,
    )
    raise SystemExit(2)


# =============================================================================
# 1. CONTRATO E PARÂMETROS DO BASELINE
# =============================================================================

Z_95 = 1.959963984540054
JANELA_DIAS = 30
AMOSTRA_MAXIMA = 5000.0
AMOSTRA_FALLBACK = 600.0
PESO_INSTITUTO_DESCONHECIDO = 0.5

COR_LULA = "#C62828"
COR_BOLSONARO = "#1565C0"
COR_CIRO = "#EF6C00"
COR_SIMONE = "#6A1B9A"
COR_OUTROS = "#2E7D32"
COR_NAO_VOTO = "#616161"
COR_GRADE = "#B0B0B0"

SERIES_PRIMEIRO_TURNO = [
    "Lula",
    "Bolsonaro",
    "Ciro Gomes",
    "Simone Tebet",
    "Outros candidatos",
    "Branco/Nulo/Não sabe",
]
CORES_PRIMEIRO_TURNO = {
    "Lula": COR_LULA,
    "Bolsonaro": COR_BOLSONARO,
    "Ciro Gomes": COR_CIRO,
    "Simone Tebet": COR_SIMONE,
    "Outros candidatos": COR_OUTROS,
    "Branco/Nulo/Não sabe": COR_NAO_VOTO,
}

NOME_PRIMEIRO_TURNO = "01_Primeiro_Turno_2022"
NOME_SEGUNDO_TURNO_TOTAIS = "02_Segundo_Turno_2022_Lula_vs_Bolsonaro_Votos_Totais"
NOME_SEGUNDO_TURNO_VALIDOS = "03_Segundo_Turno_2022_Lula_vs_Bolsonaro_Votos_Validos"

COLUNAS_CONFRONTOS = [
    "data_referencia", "instituto", "tipo_pesquisa", "frequencia_original",
    "amostra_total", "margem_erro_pp", "nivel_confianca_pct", "turno",
    "tipo_cenario", "cenario", "adversario", "nivel_geografico", "geografia",
    "segmento_tipo", "segmento", "amostra_segmento", "lula_pct",
    "adversario_pct", "outros_candidatos_pct",
    "brancos_nulos_indecisos_pct", "base_voto",
]
COLUNAS_INSTITUTOS = ["instituto", "aliases", "peso_legacy", "situacao"]


class ErroModeloA(ValueError):
    """Erro de entrada ou de cobertura que impede publicação segura."""


@dataclass(frozen=True)
class SerieSuavizada:
    """Curva suavizada e pontos brutos usados em sua construção."""

    valores: pd.DataFrame
    pontos: pd.DataFrame


# =============================================================================
# 2. LEITURA PORTÁTIL E NORMALIZAÇÃO
# =============================================================================

def presente(valor: object) -> bool:
    """Distingue valor publicado de nulo, vazio e marcador textual de ausência."""

    if valor is None or pd.isna(valor):
        return False
    return str(valor).strip() not in {"", "-"}


def texto_normalizado(valor: object) -> str:
    """Normaliza texto apenas para comparações, preservando o rótulo publicado."""

    if not presente(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.lower().replace("_", " ").split())


def localizar_base() -> tuple[Path, Path]:
    """Localiza a base ao lado do script e define a rota histórica dos resultados."""

    pasta = Path(__file__).resolve().parent
    base = pasta / "Base_nova_limpa.xlsx"
    if not base.is_file():
        raise ErroModeloA(
            "Não encontrei Base_nova_limpa.xlsx ao lado de MODELO A.PY. "
            f"Local esperado: {base}"
        )
    saida = pasta / "RESULTADOS_ATUAIS" / "Modelo_A_2022_Baseline_Historico"
    return base, saida


def localizar_cabecalho(bruto: pd.DataFrame, obrigatorias: list[str], aba: str) -> int:
    """Encontra a linha do cabeçalho mesmo com títulos e instruções acima."""

    alvo = set(obrigatorias)
    for posicao in range(len(bruto)):
        encontrados = {
            texto_normalizado(valor).replace(" ", "_")
            for valor in bruto.iloc[posicao].tolist()
        }
        if alvo.issubset(encontrados):
            return posicao
    raise ErroModeloA(
        f"Cabeçalho operacional não encontrado na aba '{aba}'. "
        f"Campos esperados: {', '.join(obrigatorias[:5])}..."
    )


def ler_aba(base: Path, aba: str, obrigatorias: list[str]) -> pd.DataFrame:
    """Lê uma aba e registra automaticamente a linha de origem no Excel."""

    try:
        bruto = pd.read_excel(base, sheet_name=aba, header=None, dtype=object, engine="openpyxl")
    except ValueError as erro:
        raise ErroModeloA(f"Aba obrigatória ausente: '{aba}'.") from erro
    cabecalho = localizar_cabecalho(bruto, obrigatorias, aba)
    nomes = [texto_normalizado(valor).replace(" ", "_") for valor in bruto.iloc[cabecalho].tolist()]
    dados = bruto.iloc[cabecalho + 1 :].copy()
    dados.columns = nomes
    dados = dados.loc[
        dados[obrigatorias].apply(lambda linha: any(presente(valor) for valor in linha), axis=1)
    ].copy()
    dados["_linha_excel"] = [int(indice) + 1 for indice in dados.index]
    return dados.reset_index(drop=True)


def cadastro_pesos(institutos: pd.DataFrame) -> tuple[dict[str, float], set[str]]:
    """Resolve nomes e aliases, bloqueando qualquer ambiguidade."""

    pesos: dict[str, float] = {}
    nomes_canonicos: set[str] = set()
    donos: dict[str, str] = {}
    for _, linha in institutos.iterrows():
        nome = str(linha["instituto"]).strip() if presente(linha["instituto"]) else ""
        if not nome:
            raise ErroModeloA(f"Instituto vazio na linha {linha['_linha_excel']} da aba Institutos.")
        peso_num = pd.to_numeric(linha["peso_legacy"], errors="coerce")
        if presente(linha["peso_legacy"]) and (pd.isna(peso_num) or not 0 <= float(peso_num) <= 1):
            raise ErroModeloA(f"Peso inválido para {nome} na aba Institutos.")
        peso = float(peso_num) if presente(peso_num) else PESO_INSTITUTO_DESCONHECIDO
        nomes_canonicos.add(nome)
        candidatos = [nome, *str(linha["aliases"] if presente(linha["aliases"]) else "").split(";")]
        for candidato in candidatos:
            chave = texto_normalizado(candidato)
            if not chave:
                continue
            if chave in donos and donos[chave] != nome:
                raise ErroModeloA(f"Alias ambíguo '{candidato.strip()}': {donos[chave]} e {nome}.")
            donos[chave] = nome
            pesos[chave] = peso
    return pesos, nomes_canonicos


def validar_e_preparar(
    confrontos: pd.DataFrame,
    institutos: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Valida percentuais, cobertura, duplicatas e cadastro antes do cálculo."""

    problemas: list[dict[str, object]] = []

    def registrar(severidade: str, linha: object, campo: str, mensagem: str) -> None:
        problemas.append(
            {"severidade": severidade, "aba": "Confrontos", "linha_excel": linha,
             "campo": campo, "mensagem": mensagem}
        )

    pesos, _ = cadastro_pesos(institutos)
    resultado = confrontos.copy()
    resultado["data_referencia"] = pd.to_datetime(resultado["data_referencia"], errors="coerce").dt.normalize()
    percentuais = ["lula_pct", "adversario_pct", "outros_candidatos_pct", "brancos_nulos_indecisos_pct"]
    numericas = ["amostra_total", "amostra_segmento", *percentuais]
    for coluna in numericas:
        resultado[coluna] = pd.to_numeric(resultado[coluna], errors="coerce")

    obrigatorias = [
        "data_referencia", "instituto", "tipo_pesquisa", "frequencia_original", "turno",
        "tipo_cenario", "cenario", "adversario", "nivel_geografico", "geografia",
        "segmento_tipo", "segmento", "base_voto",
    ]
    for _, linha in resultado.iterrows():
        origem = linha["_linha_excel"]
        for campo in obrigatorias:
            if not presente(linha[campo]):
                registrar("ERRO", origem, campo, "Campo obrigatório vazio.")
        if pd.isna(linha["data_referencia"]):
            registrar("ERRO", origem, "data_referencia", "Data inválida.")
        for campo in percentuais:
            valor = linha[campo]
            if pd.notna(valor) and not 0 <= float(valor) <= 100:
                registrar("ERRO", origem, campo, "Percentual fora do intervalo 0–100.")
        if pd.isna(linha["lula_pct"]) or pd.isna(linha["adversario_pct"]):
            registrar("ERRO", origem, "resultados", "Lula e adversário precisam estar publicados.")
        if texto_normalizado(linha["base_voto"]) != "totais":
            registrar("ERRO", origem, "base_voto", "A base histórica operacional deve conter votos totais.")
        chave_instituto = texto_normalizado(linha["instituto"])
        if chave_instituto not in pesos:
            registrar(
                "ALERTA", origem, "instituto",
                f"{linha['instituto']} não está no cadastro e usará peso provisório {PESO_INSTITUTO_DESCONHECIDO:.2f}.",
            )

    colunas_operacionais = [coluna for coluna in COLUNAS_CONFRONTOS if coluna in resultado]
    duplicadas = resultado.duplicated(colunas_operacionais, keep=False)
    for _, linha in resultado.loc[duplicadas].iterrows():
        registrar("ERRO", linha["_linha_excel"], "linha", "Duplicata exata.")

    primeiro = resultado["turno"].map(texto_normalizado).str.startswith("1", na=False)
    segundo = resultado["turno"].map(texto_normalizado).str.startswith("2", na=False)
    if int(primeiro.sum()) != 1041:
        registrar("ERRO", "várias", "cobertura", f"Primeiro turno: esperado 1041, encontrado {int(primeiro.sum())}.")
    if int(segundo.sum()) != 148:
        registrar("ERRO", "várias", "cobertura", f"Segundo turno: esperado 148, encontrado {int(segundo.sum())}.")
    sem_amostra = int(resultado["amostra_total"].isna().sum())
    registrar(
        "ALERTA", "várias", "amostra_total",
        f"{sem_amostra} linhas sem amostra publicada usarão fallback {AMOSTRA_FALLBACK:.0f}.",
    )

    validacao = pd.DataFrame(problemas)
    erros = validacao.loc[validacao["severidade"].eq("ERRO")]
    if not erros.empty:
        resumo = "; ".join(erros["mensagem"].astype(str).head(8))
        raise ErroModeloA(f"A base contém {len(erros)} erro(s) bloqueante(s): {resumo}")

    resultado["peso_legacy"] = resultado["instituto"].map(
        lambda valor: pesos.get(texto_normalizado(valor), PESO_INSTITUTO_DESCONHECIDO)
    )
    return resultado.sort_values(["data_referencia", "turno", "instituto", "adversario"]), validacao


# =============================================================================
# 3. PESOS E SUAVIZAÇÃO DO MODELO A
# =============================================================================

def amostra_utilizada(linha: pd.Series) -> float:
    """Escolhe a amostra do total e aplica fallback sem inventar valor na base."""

    if presente(linha.get("amostra_segmento")):
        return float(linha["amostra_segmento"])
    if presente(linha.get("amostra_total")):
        return float(linha["amostra_total"])
    return AMOSTRA_FALLBACK


def suavizar(frame: pd.DataFrame, coluna_valor: str) -> SerieSuavizada:
    """Replica a média ponderada de 30 dias e a faixa amostral aproximada."""

    preparado = frame.copy()
    preparado["data_referencia"] = pd.to_datetime(preparado["data_referencia"], errors="coerce").dt.normalize()
    preparado[coluna_valor] = pd.to_numeric(preparado[coluna_valor], errors="coerce")
    preparado = preparado.loc[preparado["data_referencia"].notna() & preparado[coluna_valor].notna()].copy()
    pontos = preparado[["data_referencia", coluna_valor]].rename(columns={coluna_valor: "valor_pct"}).sort_values("data_referencia")
    if preparado.empty:
        return SerieSuavizada(pd.DataFrame(columns=["estimativa_pct", "ic_baixo_pct", "ic_alto_pct", "se_pp"]), pontos)

    preparado["_amostra"] = preparado.apply(amostra_utilizada, axis=1)
    preparado["_amostra_relativa"] = np.minimum(preparado["_amostra"], AMOSTRA_MAXIMA) / AMOSTRA_MAXIMA
    preparado["_qualidade"] = pd.to_numeric(preparado["peso_legacy"], errors="coerce").fillna(PESO_INSTITUTO_DESCONHECIDO)

    datas = preparado["data_referencia"].to_numpy(dtype="datetime64[D]").astype("int64")
    valores = preparado[coluna_valor].to_numpy(dtype=float)
    amostras = preparado["_amostra"].to_numpy(dtype=float)
    qualidade = preparado["_qualidade"].to_numpy(dtype=float)
    amostra_relativa = preparado["_amostra_relativa"].to_numpy(dtype=float)
    proporcao = valores / 100.0
    variancia = proporcao * (1 - proporcao)
    registros: list[dict[str, object]] = []

    for referencia in np.unique(datas):
        idades = referencia - datas
        selecionados = np.flatnonzero((idades >= 0) & (idades <= JANELA_DIAS))
        tempo = np.maximum(0.0, 1 - idades[selecionados] / JANELA_DIAS)
        peso_bruto = (
            qualidade[selecionados] ** 0.50
            * tempo ** 0.25
            * amostra_relativa[selecionados] ** 0.25
        )
        positivos = peso_bruto > 0
        selecionados = selecionados[positivos]
        peso_bruto = peso_bruto[positivos]
        if not len(selecionados):
            continue
        peso = peso_bruto / peso_bruto.sum()
        estimativa = float(np.sum(peso * valores[selecionados]))
        se = float(np.sqrt(np.sum(peso ** 2 * variancia[selecionados] / amostras[selecionados])) * 100)
        registros.append(
            {
                "data": pd.Timestamp(np.datetime64(int(referencia), "D")),
                "estimativa_pct": estimativa,
                "ic_baixo_pct": max(0.0, estimativa - Z_95 * se),
                "ic_alto_pct": min(100.0, estimativa + Z_95 * se),
                "se_pp": se,
            }
        )
    valores_suavizados = pd.DataFrame.from_records(registros).set_index("data")
    return SerieSuavizada(valores_suavizados, pontos)


def exigir(serie: SerieSuavizada, nome: str) -> SerieSuavizada:
    """Interrompe a publicação quando uma série obrigatória está vazia."""

    if serie.valores.empty:
        raise ErroModeloA(f"Não há observações suficientes para gerar '{nome}'.")
    return serie


# =============================================================================
# 4. PREPARAÇÃO DO PRIMEIRO TURNO
# =============================================================================

def primeiro_turno_por_pesquisa(confrontos: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Converte as linhas por candidato em uma composição única por pesquisa."""

    mascara = (
        confrontos["turno"].map(texto_normalizado).str.startswith("1", na=False)
        & confrontos["tipo_cenario"].map(texto_normalizado).eq("estimulada")
        & confrontos["nivel_geografico"].map(texto_normalizado).eq("brasil")
        & confrontos["geografia"].map(texto_normalizado).eq("brasil")
        & confrontos["segmento_tipo"].map(texto_normalizado).eq("total")
        & confrontos["segmento"].map(texto_normalizado).eq("total")
        & confrontos["base_voto"].map(texto_normalizado).eq("totais")
    )
    linhas = confrontos.loc[mascara].copy()
    if linhas.empty:
        raise ErroModeloA("Não há pesquisas nacionais estimuladas de primeiro turno.")

    chaves = [
        "data_referencia", "instituto", "tipo_pesquisa", "frequencia_original",
        "nivel_geografico", "geografia", "segmento_tipo", "segmento", "cenario", "base_voto",
    ]
    registros: list[dict[str, object]] = []
    composicoes: list[dict[str, object]] = []
    selecionados = {"bolsonaro": "Bolsonaro", "ciro gomes": "Ciro Gomes", "simone tebet": "Simone Tebet"}

    for chave, grupo in linhas.groupby(chaves, dropna=False, sort=False):
        base = dict(zip(chaves, chave))
        grupo = grupo.sort_values("adversario").copy()
        lula = pd.to_numeric(grupo["lula_pct"], errors="coerce").dropna()
        if lula.empty:
            continue
        valores: dict[str, float | None] = {nome: None for nome in SERIES_PRIMEIRO_TURNO}
        valores["Lula"] = float(lula.iloc[0])
        outros: list[float] = []
        for _, linha in grupo.iterrows():
            nome_norm = texto_normalizado(linha["adversario"])
            valor = pd.to_numeric(linha["adversario_pct"], errors="coerce")
            if pd.isna(valor):
                continue
            if nome_norm in selecionados:
                valores[selecionados[nome_norm]] = float(valor)
            else:
                outros.append(float(valor))
        valores["Outros candidatos"] = float(sum(outros)) if outros else None
        nao_voto = pd.to_numeric(grupo["brancos_nulos_indecisos_pct"], errors="coerce").dropna()
        valores["Branco/Nulo/Não sabe"] = float(nao_voto.iloc[0]) if not nao_voto.empty else None

        meta = grupo.iloc[0]
        linha_composicao = {
            **base,
            "amostra_total": meta["amostra_total"],
            "amostra_segmento": meta["amostra_segmento"],
            "peso_legacy": meta["peso_legacy"],
            **valores,
        }
        composicoes.append(linha_composicao)
        for serie, valor in valores.items():
            if valor is None:
                continue
            registros.append(
                {
                    **base,
                    "amostra_total": meta["amostra_total"],
                    "amostra_segmento": meta["amostra_segmento"],
                    "peso_legacy": meta["peso_legacy"],
                    "serie": serie,
                    "valor_pct": valor,
                }
            )
    pontos = pd.DataFrame.from_records(registros).sort_values(["data_referencia", "serie", "instituto"])
    composicao = pd.DataFrame.from_records(composicoes).sort_values(["data_referencia", "instituto"])
    return pontos, composicao


def gerar_primeiro_turno(
    confrontos: pd.DataFrame,
    validacao: pd.DataFrame,
    pasta: Path,
) -> None:
    """Calcula e publica o primeiro turno em votos totais."""

    pontos, composicao = primeiro_turno_por_pesquisa(confrontos)
    series: dict[str, SerieSuavizada] = {}
    tabelas: list[pd.DataFrame] = []
    for nome in SERIES_PRIMEIRO_TURNO:
        fonte = pontos.loc[pontos["serie"].eq(nome)].copy()
        serie = exigir(suavizar(fonte, "valor_pct"), nome)
        series[nome] = serie
        tabela = serie.valores.reset_index()
        tabela.insert(1, "serie", nome)
        tabelas.append(tabela)
    series_longas = pd.concat(tabelas, ignore_index=True).sort_values(["data", "serie"])
    cobertura = (
        pontos.groupby("serie", sort=False)
        .agg(
            observacoes=("valor_pct", "size"), datas_distintas=("data_referencia", "nunique"),
            institutos_distintos=("instituto", "nunique"), primeira_data=("data_referencia", "min"),
            ultima_data=("data_referencia", "max"),
            institutos=("instituto", lambda valores: ", ".join(sorted(set(map(str, valores))))),
        )
        .reset_index()
    )
    metodologia = pd.DataFrame(
        {
            "item": [
                "Universo", "Séries", "Outros candidatos", "Não voto", "Ausência",
                "Média ponderada", "Amostra", "Faixa", "Interpretação",
            ],
            "descricao": [
                "Brasil, Total, primeiro turno, estimulada e votos totais.",
                ", ".join(SERIES_PRIMEIRO_TURNO) + ".",
                "Soma literal, por pesquisa, de todas as candidaturas fora de Lula, Bolsonaro, Ciro Gomes e Simone Tebet, incluindo Outros quando publicado.",
                "Soma já preservada na base a partir de Branco/Nulos e Não Sabe; nenhum residual completa 100%.",
                "Candidato ou resposta ausente permanece nulo e não recebe zero.",
                "Baseline legado em janela de 30 dias: qualidade do instituto^0,50 × recência linear^0,25 × amostra relativa^0,25.",
                f"A fonte não publica amostra; todas as observações sem n usam fallback {AMOSTRA_FALLBACK:.0f}.",
                "Faixa amostral aproximada de 1,96 erros-padrão; não modela heterogeneidade, desenho amostral ou efeito de instituto.",
                "Agregado de pesquisas para acompanhamento histórico; não é previsão eleitoral.",
            ],
        }
    )
    escrever_planilha(
        pasta / f"{NOME_PRIMEIRO_TURNO}.xlsx",
        {
            "Series_suavizadas": series_longas,
            "Pontos_por_pesquisa": pontos.drop(columns=["peso_legacy"], errors="ignore"),
            "Composicao_pesquisa": composicao.drop(columns=["peso_legacy"], errors="ignore"),
            "Cobertura": cobertura,
            "Metodologia": metodologia,
            "Linhas_originais": confrontos.loc[confrontos["turno"].map(texto_normalizado).str.startswith("1", na=False)].drop(columns=["peso_legacy"], errors="ignore"),
            "Validacao": validacao,
        },
    )
    grafico_primeiro_turno(pontos, series, pasta / f"{NOME_PRIMEIRO_TURNO}.png")


# =============================================================================
# 5. PREPARAÇÃO E PUBLICAÇÃO DO SEGUNDO TURNO
# =============================================================================

def segundo_turno(confrontos: pd.DataFrame) -> pd.DataFrame:
    """Seleciona o confronto nacional Lula × Bolsonaro em votos totais."""

    mascara = (
        confrontos["turno"].map(texto_normalizado).str.startswith("2", na=False)
        & confrontos["tipo_cenario"].map(texto_normalizado).eq("estimulada")
        & confrontos["adversario"].map(texto_normalizado).str.contains("bolsonaro", na=False)
        & confrontos["nivel_geografico"].map(texto_normalizado).eq("brasil")
        & confrontos["geografia"].map(texto_normalizado).eq("brasil")
        & confrontos["segmento_tipo"].map(texto_normalizado).eq("total")
        & confrontos["segmento"].map(texto_normalizado).eq("total")
        & confrontos["base_voto"].map(texto_normalizado).eq("totais")
    )
    linhas = confrontos.loc[mascara].copy().sort_values("data_referencia")
    if linhas.empty:
        raise ErroModeloA("Não há confronto nacional estimulado Lula × Bolsonaro no segundo turno.")
    denominador = linhas["lula_pct"] + linhas["adversario_pct"]
    linhas = linhas.loc[denominador.gt(0)].copy()
    denominador = denominador.loc[linhas.index]
    linhas["lula_validos_pct"] = linhas["lula_pct"] / denominador * 100
    linhas["bolsonaro_validos_pct"] = linhas["adversario_pct"] / denominador * 100
    return linhas


def gerar_segundo_turno(
    confrontos: pd.DataFrame,
    validacao: pd.DataFrame,
    pasta: Path,
) -> None:
    """Publica o mesmo confronto com os dois denominadores obrigatórios."""

    linhas = segundo_turno(confrontos)
    configuracoes = [
        (
            "Votos totais", "lula_pct", "adversario_pct", NOME_SEGUNDO_TURNO_TOTAIS,
            "Percentuais publicados no total da amostra; não voto permanece no denominador.",
        ),
        (
            "Votos válidos", "lula_validos_pct", "bolsonaro_validos_pct", NOME_SEGUNDO_TURNO_VALIDOS,
            "Lula e Bolsonaro são reescalados para somarem 100%; branco, nulo e indeciso saem do denominador.",
        ),
    ]
    for base_voto, coluna_lula, coluna_bolsonaro, nome, denominador in configuracoes:
        lula = exigir(suavizar(linhas, coluna_lula), f"Lula — {base_voto}")
        bolsonaro = exigir(suavizar(linhas, coluna_bolsonaro), f"Bolsonaro — {base_voto}")
        suavizados = pd.concat(
            [lula.valores["estimativa_pct"].rename("Lula"), bolsonaro.valores["estimativa_pct"].rename("Bolsonaro")],
            axis=1,
        ).sort_index().reset_index()
        ic_baixo = pd.concat(
            [lula.valores["ic_baixo_pct"].rename("Lula"), bolsonaro.valores["ic_baixo_pct"].rename("Bolsonaro")],
            axis=1,
        ).sort_index().reset_index()
        ic_alto = pd.concat(
            [lula.valores["ic_alto_pct"].rename("Lula"), bolsonaro.valores["ic_alto_pct"].rename("Bolsonaro")],
            axis=1,
        ).sort_index().reset_index()
        cobertura = pd.DataFrame(
            {
                "indicador": [
                    "observacoes", "datas_distintas", "institutos_distintos", "primeira_data",
                    "ultima_data", "fallbacks_de_amostra", "max_desvio_soma_validos",
                ],
                "valor": [
                    len(linhas), linhas["data_referencia"].nunique(), linhas["instituto"].nunique(),
                    linhas["data_referencia"].min(), linhas["data_referencia"].max(),
                    int(linhas["amostra_total"].isna().sum()),
                    float((linhas["lula_validos_pct"] + linhas["bolsonaro_validos_pct"] - 100).abs().max()),
                ],
            }
        )
        metodologia = pd.DataFrame(
            {
                "item": ["Universo", "Base", "Denominador", "Média ponderada", "Amostra", "Faixa", "Interpretação"],
                "descricao": [
                    "Brasil, Total, segundo turno estimulado, Lula × Bolsonaro.", base_voto, denominador,
                    "Baseline legado em janela de 30 dias: qualidade do instituto^0,50 × recência linear^0,25 × amostra relativa^0,25.",
                    f"A fonte não publica amostra; observações sem n usam fallback {AMOSTRA_FALLBACK:.0f}.",
                    "Faixa amostral aproximada de 1,96 erros-padrão; não modela heterogeneidade, desenho amostral ou efeito de instituto.",
                    "Agregado histórico de pesquisas; não é previsão eleitoral.",
                ],
            }
        )
        escrever_planilha(
            pasta / f"{nome}.xlsx",
            {
                "Suavizados": suavizados,
                "IC_Baixo": ic_baixo,
                "IC_Alto": ic_alto,
                "Pesquisas_utilizadas": linhas.drop(columns=["peso_legacy"], errors="ignore"),
                "Cobertura": cobertura,
                "Metodologia": metodologia,
                "Validacao": validacao,
            },
        )
        grafico_segundo_turno(
            linhas, lula, bolsonaro, base_voto, pasta / f"{nome}.png",
            coluna_lula, coluna_bolsonaro,
        )


# =============================================================================
# 6. PLANILHAS DE MEMÓRIA DE CÁLCULO
# =============================================================================

def escrever_planilha(caminho: Path, abas: dict[str, pd.DataFrame]) -> None:
    """Escreve uma memória auditável, sem índices técnicos ou filtros ativos."""

    with pd.ExcelWriter(caminho, engine="openpyxl", datetime_format="yyyy-mm-dd") as writer:
        for nome, frame in abas.items():
            saida = frame.copy()
            if saida.empty:
                saida = pd.DataFrame([{"status": "Sem registros"}])
            saida.to_excel(writer, sheet_name=nome[:31], index=False)

    wb = load_workbook(caminho)
    azul = PatternFill("solid", fgColor="4472C4")
    azul_claro = PatternFill("solid", fgColor="D9EAF7")
    for ws in wb.worksheets:
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = None
        ws.sheet_view.showGridLines = False
        for celula in ws[1]:
            celula.fill = azul
            celula.font = Font(color="FFFFFF", bold=True)
            celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[1].height = 34
        for linha in range(2, ws.max_row + 1):
            if linha % 2 == 0:
                for celula in ws[linha]:
                    celula.fill = azul_claro
        for coluna in range(1, ws.max_column + 1):
            cabecalho = str(ws.cell(1, coluna).value or "")
            valores = [str(ws.cell(linha, coluna).value or "") for linha in range(1, min(ws.max_row, 80) + 1)]
            largura = min(max(12, max(map(len, valores), default=len(cabecalho)) + 2), 55)
            ws.column_dimensions[get_column_letter(coluna)].width = largura
            campo_data = texto_normalizado(cabecalho) in {
                "data", "data referencia", "primeira data", "ultima data",
            }
            if campo_data:
                for linha in range(2, ws.max_row + 1):
                    ws.cell(linha, coluna).number_format = "yyyy-mm-dd"
            elif any(termo in texto_normalizado(cabecalho) for termo in ["pct", "percent", "estimativa", "ic ", "se pp", "lula", "bolsonaro"]):
                for linha in range(2, ws.max_row + 1):
                    if isinstance(ws.cell(linha, coluna).value, (int, float)):
                        ws.cell(linha, coluna).number_format = "0.000"
            else:
                for linha in range(2, ws.max_row + 1):
                    valor = ws.cell(linha, coluna).value
                    if isinstance(valor, (pd.Timestamp, datetime, date)):
                        ws.cell(linha, coluna).number_format = "yyyy-mm-dd"
    wb.save(caminho)


# =============================================================================
# 7. GRÁFICOS
# =============================================================================

def percentual_pt(valor: float) -> str:
    """Formata percentual com vírgula decimal."""

    return f"{valor:.1f}%".replace(".", ",")


def estilizar_eixo(eixo) -> None:
    """Aplica o padrão visual comum aos três gráficos."""

    eixo.grid(axis="y", color=COR_GRADE, linewidth=0.7, alpha=0.35)
    eixo.spines["top"].set_visible(False)
    eixo.spines["right"].set_visible(False)
    eixo.tick_params(colors="#333333")
    eixo.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    eixo.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))


def rotulos_finais(
    eixo,
    entradas: list[tuple[str, str, pd.Timestamp, float]],
    separacao: float,
) -> None:
    """Posiciona rótulos finais com separação mínima e linhas-guia."""

    if not entradas:
        return
    ordenadas = sorted(entradas, key=lambda item: item[3])
    ajustadas: list[tuple[str, str, pd.Timestamp, float, float]] = []
    anterior = -math.inf
    for nome, cor, data, valor in ordenadas:
        y = max(valor, anterior + separacao)
        ajustadas.append((nome, cor, data, valor, y))
        anterior = y
    limite = eixo.get_ylim()[1]
    excesso = max(0.0, ajustadas[-1][4] - (limite - separacao / 2))
    if excesso:
        ajustadas = [(n, c, d, v, y - excesso) for n, c, d, v, y in ajustadas]

    datas = [item[2] for item in ajustadas]
    amplitude = max(pd.Timedelta(days=30), max(datas) - min(datas))
    x_texto = max(datas) + amplitude * 0.055
    for nome, cor, data, valor, y in ajustadas:
        eixo.plot([data, x_texto], [valor, y], color=cor, linewidth=1.0, alpha=0.75, clip_on=False)
        eixo.text(x_texto, y, f"{nome} {percentual_pt(valor)}", color=cor, fontsize=10, fontweight="bold", va="center")


def grafico_primeiro_turno(
    pontos: pd.DataFrame,
    series: dict[str, SerieSuavizada],
    caminho: Path,
) -> None:
    """Desenha o agregado de primeiro turno com pontos e curvas suavizadas."""

    figura, eixo = plt.subplots(figsize=(18, 10))
    finais: list[tuple[str, str, pd.Timestamp, float]] = []
    for nome in SERIES_PRIMEIRO_TURNO:
        cor = CORES_PRIMEIRO_TURNO[nome]
        observados = pontos.loc[pontos["serie"].eq(nome)]
        eixo.scatter(observados["data_referencia"], observados["valor_pct"], color=cor, alpha=0.34, s=24)
        curva = series[nome].valores
        eixo.plot(curva.index, curva["estimativa_pct"], color=cor, linewidth=2.25)
        finais.append((nome, cor, pd.Timestamp(curva.index[-1]), float(curva["estimativa_pct"].iloc[-1])))

    minimo = max(0.0, math.floor((float(pontos["valor_pct"].min()) - 4) / 5) * 5)
    maximo = min(100.0, math.ceil((float(pontos["valor_pct"].max()) + 5) / 5) * 5)
    eixo.set_ylim(minimo, maximo)
    eixo.set_title("Primeiro turno 2022 — agregado das pesquisas estimuladas\nMédia ponderada de 30 dias", fontsize=17, pad=18)
    eixo.set_xlabel("Data")
    eixo.set_ylabel("Intenção de voto (% dos votos totais)")
    estilizar_eixo(eixo)
    rotulos_finais(eixo, finais, separacao=2.0)
    ultima = max(serie.valores.index.max() for serie in series.values())
    primeira = min(serie.valores.index.min() for serie in series.values())
    eixo.set_xlim(primeira - pd.Timedelta(days=15), ultima + (ultima - primeira) * 0.13)
    figura.text(
        0.01, 0.015,
        f"Atualizado até {ultima.strftime('%d/%m/%Y')}. Janela de 30 dias. Ausência não recebe zero; não voto e Outros usam somente somas publicadas, sem residual. Faixa amostral não exibida para reduzir poluição visual.",
        ha="left", fontsize=9, color="#444444",
    )
    figura.subplots_adjust(left=0.07, right=0.91, bottom=0.11, top=0.86)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def grafico_segundo_turno(
    linhas: pd.DataFrame,
    lula: SerieSuavizada,
    bolsonaro: SerieSuavizada,
    base_voto: str,
    caminho: Path,
    coluna_lula: str,
    coluna_bolsonaro: str,
) -> None:
    """Desenha Lula × Bolsonaro com faixas, linha de 50% e marco do primeiro turno."""

    figura, eixo = plt.subplots(figsize=(18, 10))
    eixo.scatter(linhas["data_referencia"], linhas[coluna_lula], color=COR_LULA, alpha=0.34, s=25)
    eixo.scatter(linhas["data_referencia"], linhas[coluna_bolsonaro], color=COR_BOLSONARO, alpha=0.34, s=25)
    for serie, cor in [(lula, COR_LULA), (bolsonaro, COR_BOLSONARO)]:
        eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2.6)
        eixo.fill_between(
            serie.valores.index,
            serie.valores["ic_baixo_pct"].to_numpy(dtype=float),
            serie.valores["ic_alto_pct"].to_numpy(dtype=float),
            color=cor, alpha=0.11,
        )
    eixo.axhline(50, color="#666666", linestyle="--", linewidth=1.1, alpha=0.8)
    marco = pd.Timestamp("2022-10-02")
    eixo.axvline(marco, color="#444444", linestyle=":", linewidth=1.2, alpha=0.8)
    eixo.text(marco, 0.985, "1º turno — 02/10", transform=eixo.get_xaxis_transform(), ha="right", va="top", fontsize=9, color="#444444")

    valores = pd.concat([linhas[coluna_lula], linhas[coluna_bolsonaro]], ignore_index=True).dropna()
    inferior = max(0.0, math.floor((float(valores.min()) - 5) / 5) * 5)
    superior = min(100.0, math.ceil((float(valores.max()) + 5) / 5) * 5)
    eixo.set_ylim(inferior, superior)
    titulo_base = base_voto.lower()
    eixo.set_title(f"Segundo turno 2022: Lula × Bolsonaro — {titulo_base}\nMédia ponderada de 30 dias", fontsize=17, pad=18)
    eixo.set_xlabel("Data")
    eixo.set_ylabel(f"Percentual ({titulo_base})")
    estilizar_eixo(eixo)
    finais = [
        ("Lula", COR_LULA, pd.Timestamp(lula.valores.index[-1]), float(lula.valores["estimativa_pct"].iloc[-1])),
        ("Bolsonaro", COR_BOLSONARO, pd.Timestamp(bolsonaro.valores.index[-1]), float(bolsonaro.valores["estimativa_pct"].iloc[-1])),
    ]
    rotulos_finais(eixo, finais, separacao=1.5)
    primeira = min(lula.valores.index.min(), bolsonaro.valores.index.min())
    ultima = max(lula.valores.index.max(), bolsonaro.valores.index.max())
    eixo.set_xlim(primeira - pd.Timedelta(days=15), ultima + (ultima - primeira) * 0.12)
    denominador = (
        "Percentuais publicados no total da amostra; não voto permanece no denominador."
        if texto_normalizado(base_voto) == "votos totais"
        else "Percentuais reescalados somente entre Lula e Bolsonaro; não voto sai do denominador."
    )
    figura.text(
        0.01, 0.015,
        f"Atualizado até {ultima.strftime('%d/%m/%Y')}. {denominador} Faixa amostral aproximada com fallback n={AMOSTRA_FALLBACK:.0f}.",
        ha="left", fontsize=9, color="#444444",
    )
    figura.subplots_adjust(left=0.07, right=0.91, bottom=0.11, top=0.86)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


# =============================================================================
# 8. PUBLICAÇÃO CONJUNTA E EXECUÇÃO
# =============================================================================

def publicar_resultados(preparacao: Path, destino: Path) -> None:
    """Substitui a entrega anterior somente depois da geração integral."""

    novos = sorted(
        arquivo for arquivo in preparacao.iterdir()
        if arquivo.is_file() and arquivo.suffix.lower() in {".xlsx", ".png"}
    )
    if len(novos) != 6:
        raise ErroModeloA(f"A rotina deveria gerar 6 arquivos, mas produziu {len(novos)}.")
    destino.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="Modelo_A_2022_backup_", dir=destino.parent) as temp:
        backup = Path(temp)
        antigos = [
            arquivo for arquivo in destino.iterdir()
            if arquivo.is_file() and arquivo.suffix.lower() in {".xlsx", ".png"}
        ]
        publicados: list[Path] = []
        try:
            for arquivo in antigos:
                shutil.move(str(arquivo), str(backup / arquivo.name))
            for arquivo in novos:
                alvo = destino / arquivo.name
                shutil.move(str(arquivo), str(alvo))
                publicados.append(alvo)
        except Exception:
            for arquivo in publicados:
                if arquivo.exists():
                    shutil.move(str(arquivo), str(preparacao / arquivo.name))
            for arquivo in backup.iterdir():
                shutil.move(str(arquivo), str(destino / arquivo.name))
            raise


def executar() -> Path:
    """Lê, valida, calcula, verifica e publica o pacote histórico completo."""

    base, pasta_saida = localizar_base()
    confrontos_brutos = ler_aba(base, "Confrontos", COLUNAS_CONFRONTOS)
    institutos = ler_aba(base, "Institutos", COLUNAS_INSTITUTOS)
    confrontos, validacao = validar_e_preparar(confrontos_brutos, institutos)

    pasta_saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="Modelo_A_2022_preparacao_", dir=pasta_saida.parent) as temp:
        preparacao = Path(temp)
        gerar_primeiro_turno(confrontos, validacao, preparacao)
        gerar_segundo_turno(confrontos, validacao, preparacao)
        publicar_resultados(preparacao, pasta_saida)
    return pasta_saida


if __name__ == "__main__":
    try:
        print(f"Resultados gerados em: {executar()}")
    except ErroModeloA as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        raise SystemExit(2)
    except PermissionError:
        print("Erro: feche Base_nova_limpa.xlsx e as planilhas de resultado antes de executar.", file=sys.stderr)
        raise SystemExit(2)
