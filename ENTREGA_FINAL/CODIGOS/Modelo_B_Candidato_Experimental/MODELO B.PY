"""MODELO B — agregador eleitoral experimental, autocontido e portátil.

COMO USAR
---------
1. Coloque este arquivo junto de ``Base_nova_limpa.xlsx``; ou preserve a
   estrutura ``ENTREGA_FINAL/CODIGOS/Modelo_B_Candidato_Experimental``.
2. Instale as dependências uma única vez, se necessário:
       python -m pip install pandas numpy openpyxl matplotlib
3. Execute:
       python "MODELO B.PY"
4. Para apenas ler a explicação metodológica no terminal:
       python "MODELO B.PY" --explicar

O código procura a base automaticamente e grava os resultados em
``RESULTADOS_ATUAIS/Modelo_B_Candidato_Experimental`` ao lado dela. Não importa,
não chama e não executa nenhum outro arquivo do projeto.

O QUE MUDA EM RELAÇÃO AO MODELO A
---------------------------------
O Modelo A é o baseline oficial: ele replica a fórmula histórica do agregador,
com decaimento linear e janelas curtas. O Modelo B é um candidato experimental;
ele mantém as mesmas perguntas e os mesmos recortes do A, mas aperfeiçoa a forma
de ponderar as pesquisas e de representar a incerteza:

* RECÊNCIA: usa decaimento exponencial com meia-vida de 15 dias e descarta
  observações com mais de 90 dias. O peso diminui suavemente, sem o corte brusco
  da janela linear do A.
* QUALIDADE: aproxima parcialmente o peso de qualidade de cada instituto de um
  prior comum. Isso reduz diferenças exageradas causadas por uma nota isolada,
  sem tornar todos os institutos iguais.
* AMOSTRA EFETIVA: quando a pesquisa publica margem de erro, o código estima a
  amostra compatível com essa margem e usa o menor valor entre amostra declarada,
  amostra implícita e o teto de 5.000. Assim, uma amostra nominal muito grande
  não recebe automaticamente precisão excessiva.
* CONCENTRAÇÃO: nenhum instituto pode receber mais de 35% do peso de um ponto,
  desde que existam pelo menos três institutos independentes. Se o teto for
  matematicamente inviável, a série continua visível, mas é marcada como
  evidência insuficiente para probabilidade.
* INCERTEZA: combina erro amostral, dispersão adicional entre pesquisas e um
  piso conservador de 1,5 ponto percentual. Para diferenças entre duas opções,
  usa a covariância multinomial, evitando tratá-las como medidas independentes.
* PROBABILIDADE: calcula apenas a probabilidade experimental de Lula estar à
  frente no momento do agregado. Ela NÃO é probabilidade de vitória na eleição,
  e só aparece com pelo menos duas pesquisas, três institutos e teto viável.

As regras substantivas permanecem iguais às do A: nulo não vira zero; tracking
diário é consolidado em ondas semanais; votos válidos são calculados somente
quando cabível; e o primeiro turno usa, por candidato e pesquisa, a média dos
cenários em que o nome foi efetivamente testado. O B não substitui o A antes de
backtest e aprovação formal.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from math import erf, sqrt
from typing import Callable, Iterable

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
except ModuleNotFoundError as erro:
    print(
        "Falta uma dependência do Python. Execute uma vez:\n"
        "python -m pip install pandas numpy openpyxl matplotlib\n"
        f"Detalhe: {erro}",
        file=sys.stderr,
    )
    raise SystemExit(2)


Z_95 = 1.959963984540054
PESO_INSTITUTO_DESCONHECIDO = 0.5
AMOSTRA_MAXIMA = 5000.0
AMOSTRA_FALLBACK = 600.0

# Parâmetros metodológicos do candidato experimental model-b-candidate-0.1.
# Eles ficam explícitos aqui para que o arquivo seja auditável e não dependa de
# YAML, planilha de configuração ou valores escondidos em outro módulo.
VERSAO_METODOLOGICA = "model-b-candidate-0.1"
MEIA_VIDA_DIAS = 15.0
IDADE_MAXIMA_DIAS = 90
PRIOR_QUALIDADE = 0.70
ENCOLHIMENTO_QUALIDADE = 0.50
TETO_PESO_INSTITUTO = 0.35
PISO_INCERTEZA_PP = 1.50
MINIMO_PESQUISAS_PROBABILIDADE = 2
MINIMO_INSTITUTOS_PROBABILIDADE = 3
EXPOENTE_QUALIDADE = 0.50
EXPOENTE_RECENCIA = 0.25
EXPOENTE_AMOSTRA = 0.25

EXPLICACAO_MODELO_B = __doc__.split("O QUE MUDA EM RELAÇÃO AO MODELO A", 1)[1].strip()

NOME_GRAFICO_GOVERNO = "01_Avaliacao_do_Governo"
NOME_GRAFICO_LIQUIDO = "02_Avaliacao_Liquida_do_Governo"
NOME_GRAFICO_SEGUNDO_TURNO = "03_Segundo_Turno_Lula_vs_Flavio"
NOME_GRAFICO_SEGUNDO_TURNO_RENAN = "04_Segundo_Turno_Lula_vs_Renan"
NOME_GRAFICO_SEGUNDO_TURNO_CAIADO = "05_Segundo_Turno_Lula_vs_Caiado"
NOME_GRAFICO_PRIMEIRO_TURNO = "06_Primeiro_Turno_Media_Harmonizada_Cenarios"
NOME_GRAFICO_GOVERNO_SEXO = "07_Avaliacao_do_Governo_por_Sexo"
NOME_GRAFICO_LIQUIDO_SEXO = "08_Avaliacao_Liquida_do_Governo_por_Sexo"
NOME_GRAFICO_SEGUNDO_TURNO_FLAVIO_SEXO = "09_Segundo_Turno_Lula_vs_Flavio_por_Sexo"
NOME_GRAFICO_SEGUNDO_TURNO_RENAN_SEXO = "10_Segundo_Turno_Lula_vs_Renan_por_Sexo"
NOME_GRAFICO_SEGUNDO_TURNO_FLAVIO_RELIGIAO = "11_Segundo_Turno_Lula_vs_Flavio_por_Religiao"
NOME_GRAFICO_SEGUNDO_TURNO_RENAN_RELIGIAO = "12_Segundo_Turno_Lula_vs_Renan_por_Religiao"
NOMES_OBSOLETOS_PRIMEIRO_TURNO = [
    "06_Primeiro_Turno_Cenario_Com_Flavio.xlsx",
    "06_Primeiro_Turno_Cenario_Com_Flavio.png",
]
CANDIDATOS_PRIMEIRO_TURNO = [
    "Lula", "Flávio", "Renan Santos", "Romeu Zema", "Ronaldo Caiado", "Michelle Bolsonaro",
]
CANDIDATOS_PRIMEIRO_TURNO_NORMALIZADOS = {texto for texto in (
    "lula", "flavio", "renan santos", "romeu zema", "ronaldo caiado", "michelle bolsonaro",
)}
CANDIDATOS_PRIMEIRO_TURNO_ADVERSARIOS = CANDIDATOS_PRIMEIRO_TURNO_NORMALIZADOS.difference({"lula"})

COLUNAS_GOVERNO = [
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
COLUNAS_INSTITUTOS = ["instituto", "aliases", "peso_legacy", "situacao"]


class ErroModeloB(ValueError):
    """Erro de base ou de estrutura que impede a geração dos resultados."""


@dataclass(frozen=True)
class SerieSuavizada:
    valores: pd.DataFrame
    pontos_publicados: pd.DataFrame
    pesos_ultimo_ponto: pd.DataFrame


def presente(valor: object) -> bool:
    if valor is None:
        return False
    if isinstance(valor, str):
        return bool(valor.strip())
    try:
        return not bool(pd.isna(valor))
    except (TypeError, ValueError):
        return True


def texto_normalizado(valor: object) -> str:
    if not presente(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor).strip()).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


def localizar_base() -> tuple[Path, Path]:
    """Localiza a base tanto na estrutura atual quanto ao lado deste arquivo."""
    pasta_script = Path(__file__).resolve().parent
    candidatos = [
        pasta_script.parent.parent / "Base_nova_limpa.xlsx",
        pasta_script / "Base_nova_limpa.xlsx",
        Path.cwd() / "Base_nova_limpa.xlsx",
    ]
    for candidato in candidatos:
        if candidato.is_file():
            return candidato, candidato.parent / "RESULTADOS_ATUAIS" / "Modelo_B_Candidato_Experimental"
    locais = "\n".join(f"- {candidato}" for candidato in candidatos)
    raise ErroModeloB(
        "Não encontrei Base_nova_limpa.xlsx. Deixe a base nesta pasta ou mantenha a "
        "estrutura ENTREGA_FINAL/CODIGOS/Modelo_B_Candidato_Experimental. Procurei em:\n" + locais
    )


def localizar_cabecalho(planilha_bruta: pd.DataFrame, obrigatorias: list[str], nome_aba: str) -> int:
    alvo = set(obrigatorias)
    for posicao in range(len(planilha_bruta)):
        cabecalhos = {
            texto_normalizado(valor).replace(" ", "_")
            for valor in planilha_bruta.iloc[posicao].tolist()
        }
        if alvo.issubset(cabecalhos):
            return posicao
    raise ErroModeloB(
        f"Não foi localizado o cabeçalho operacional da aba '{nome_aba}'. "
        f"Campos esperados: {', '.join(obrigatorias[:4])}..."
    )


def ler_aba(caminho_base: Path, nome_aba: str, obrigatorias: list[str]) -> pd.DataFrame:
    try:
        bruto = pd.read_excel(caminho_base, sheet_name=nome_aba, header=None, dtype=object, engine="openpyxl")
    except ValueError as erro:
        raise ErroModeloB(f"Aba obrigatória ausente: '{nome_aba}'.") from erro
    indice_cabecalho = localizar_cabecalho(bruto, obrigatorias, nome_aba)
    cabecalhos = [texto_normalizado(valor).replace(" ", "_") for valor in bruto.iloc[indice_cabecalho].tolist()]
    dados = bruto.iloc[indice_cabecalho + 1 :].copy()
    dados.columns = cabecalhos
    dados = dados.loc[dados[obrigatorias].apply(lambda linha: any(presente(valor) for valor in linha), axis=1)].copy()
    return dados.reset_index(drop=True)


def pesos_dos_institutos(institutos: pd.DataFrame) -> dict[str, float]:
    """Resolve o cadastro e os aliases publicados na aba Institutos."""
    pesos: dict[str, float] = {}
    aliases: dict[str, str] = {}
    for _, linha in institutos.iterrows():
        nome = str(linha["instituto"]).strip() if presente(linha["instituto"]) else ""
        if not nome:
            continue
        peso = pd.to_numeric(linha["peso_legacy"], errors="coerce")
        pesos[nome] = float(peso) if presente(peso) else PESO_INSTITUTO_DESCONHECIDO
        for candidato in [nome, *str(linha["aliases"] if presente(linha["aliases"]) else "").split(";")]:
            chave = texto_normalizado(candidato)
            if chave:
                aliases[chave] = nome
    return {chave: pesos.get(nome, PESO_INSTITUTO_DESCONHECIDO) for chave, nome in aliases.items()}


def preparar(frame: pd.DataFrame, colunas_valor: Iterable[str], pesos: dict[str, float]) -> pd.DataFrame:
    """Padroniza datas e números em memória, sem modificar a planilha de entrada."""
    resultado = frame.copy()
    resultado["data_referencia"] = pd.to_datetime(resultado["data_referencia"], errors="coerce").dt.normalize()
    resultado = resultado.loc[resultado["data_referencia"].notna()].copy()
    for coluna in {*colunas_valor, "margem_erro_pp", "nivel_confianca_pct"}:
        resultado[coluna] = pd.to_numeric(resultado[coluna], errors="coerce")
    for coluna in ["amostra_total", "amostra_segmento"]:
        resultado[coluna] = pd.to_numeric(resultado[coluna], errors="coerce")
    resultado["peso_legacy"] = resultado["instituto"].map(
        lambda valor: pesos.get(texto_normalizado(valor), PESO_INSTITUTO_DESCONHECIDO)
    )
    return resultado


def amostra_utilizada(linha: pd.Series) -> float:
    """Retorna a amostra declarada ou um fallback conservador e transparente."""
    amostra_total = linha["amostra_total"] if presente(linha["amostra_total"]) else None
    amostra_segmento = linha["amostra_segmento"] if presente(linha["amostra_segmento"]) else None
    if texto_normalizado(linha["segmento_tipo"]) == "total":
        if amostra_segmento is not None:
            return float(amostra_segmento)
        if amostra_total is not None:
            return float(amostra_total)
        return AMOSTRA_FALLBACK
    if amostra_segmento is not None:
        return float(amostra_segmento)
    if amostra_total is not None:
        return min(float(amostra_total), 300.0)
    return 300.0


def z_da_confianca(valor: object) -> float:
    """Usa o quantil normal mais próximo entre os níveis publicados usuais."""
    if not presente(valor):
        return Z_95
    confianca = float(valor)
    opcoes = ((90.0, 1.6448536269514722), (95.0, Z_95), (99.0, 2.5758293035489004))
    return min(opcoes, key=lambda item: abs(item[0] - confianca))[1]


def amostra_efetiva(linha: pd.Series) -> tuple[float, str]:
    """Estima a informação efetiva sem confundir amostra nominal com precisão.

    Para recortes, a margem de erro total nunca é reutilizada como se fosse a
    margem do subgrupo. Para o total, quando a margem é publicada, comparamos a
    amostra declarada com a amostra implícita na margem e ficamos com o menor
    valor. Esse é um dos aperfeiçoamentos centrais do Modelo B.
    """
    declarada = max(float(amostra_utilizada(linha)), 1.0)
    declarada = min(declarada, AMOSTRA_MAXIMA)
    if texto_normalizado(linha.get("segmento_tipo", "")) != "total":
        return declarada, "amostra_segmento_ou_fallback"
    margem_pp = pd.to_numeric(linha.get("margem_erro_pp"), errors="coerce")
    if not presente(margem_pp) or float(margem_pp) <= 0:
        return declarada, "amostra_declarada_ou_fallback"
    margem = float(margem_pp) / 100.0
    implicita = (z_da_confianca(linha.get("nivel_confianca_pct")) ** 2 * 0.25) / (margem ** 2)
    return max(1.0, min(declarada, implicita, AMOSTRA_MAXIMA)), "min_declarada_implicita_teto"


def identificador_onda(linha: pd.Series) -> str:
    """Cria uma chave legível para contar pesquisas sem pedir IDs ao operador."""
    campos = (
        "data_referencia", "instituto", "tipo_pesquisa", "frequencia_original",
        "turno", "tipo_cenario", "cenario", "adversario", "nivel_geografico",
        "geografia", "segmento_tipo", "segmento",
    )
    return "|".join(texto_normalizado(linha.get(campo, "")) for campo in campos)


def aplicar_teto_por_instituto(
    pesos_brutos: np.ndarray,
    institutos: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, bool]:
    """Normaliza pesos e limita cada instituto a 35%, quando isso é viável.

    Com um ou dois institutos, três parcelas de 35% não existem e o teto não
    poderia somar 100%. Nessa situação preservamos o agregado, registramos a
    insuficiência e suprimimos a probabilidade experimental.
    """
    preliminares = pesos_brutos / pesos_brutos.sum()
    grupos, inverso = np.unique(institutos.astype(str), return_inverse=True)
    pesos_grupo = np.bincount(inverso, weights=preliminares, minlength=len(grupos))
    viavel = len(grupos) * TETO_PESO_INSTITUTO >= 1.0 - 1e-12
    if not viavel or TETO_PESO_INSTITUTO >= 1.0:
        return preliminares, preliminares, np.zeros(len(preliminares), dtype=bool), viavel

    pesos_finais_grupo = np.zeros(len(grupos), dtype=float)
    disponiveis = np.ones(len(grupos), dtype=bool)
    restante = 1.0
    while disponiveis.any():
        pesos_disponiveis = pesos_grupo[disponiveis]
        posicoes = np.flatnonzero(disponiveis)
        if pesos_disponiveis.sum() <= 0:
            pesos_finais_grupo[posicoes] = restante / len(posicoes)
            break
        provisoria = pesos_disponiveis / pesos_disponiveis.sum() * restante
        excede = provisoria > TETO_PESO_INSTITUTO + 1e-12
        if not excede.any():
            pesos_finais_grupo[posicoes] = provisoria
            break
        limitadas = posicoes[excede]
        pesos_finais_grupo[limitadas] = TETO_PESO_INSTITUTO
        disponiveis[limitadas] = False
        restante = 1.0 - pesos_finais_grupo[~disponiveis].sum()
        if restante <= 0:
            pesos_finais_grupo[disponiveis] = 0.0
            break

    finais = np.zeros(len(preliminares), dtype=float)
    for indice_grupo, peso_grupo in enumerate(pesos_grupo):
        membros = inverso == indice_grupo
        if peso_grupo > 0:
            finais[membros] = preliminares[membros] * pesos_finais_grupo[indice_grupo] / peso_grupo
    limitados = pesos_finais_grupo[inverso] < pesos_grupo[inverso] - 1e-12
    return preliminares, finais, limitados, viavel


def cdf_normal(valor: float) -> float:
    return 0.5 * (1.0 + erf(valor / sqrt(2.0)))


def numerador_variancia(
    preparado: pd.DataFrame,
    coluna_valor: str,
    colunas_variancia: tuple[str, ...] | None,
) -> np.ndarray:
    """Calcula p(1-p) ou a variância multinomial de uma diferença A - B."""
    colunas = colunas_variancia or (coluna_valor,)
    if len(colunas) == 1:
        proporcao = preparado[colunas[0]].to_numpy(dtype=float) / 100.0
        return proporcao * (1.0 - proporcao)
    if len(colunas) == 2:
        primeira = preparado[colunas[0]].to_numpy(dtype=float) / 100.0
        segunda = preparado[colunas[1]].to_numpy(dtype=float) / 100.0
        # Para categorias mutuamente exclusivas, Cov(A,B) é negativa. A fórmula
        # abaixo incorpora essa covariância na variância de A - B.
        return primeira + segunda - (primeira - segunda) ** 2
    variancia = np.zeros(len(preparado), dtype=float)
    for coluna in colunas:
        proporcao = preparado[coluna].to_numpy(dtype=float) / 100.0
        variancia += proporcao * (1.0 - proporcao)
    return variancia


def suavizar(
    frame: pd.DataFrame,
    coluna_valor: str,
    janela_dias: int | None = None,
    colunas_variancia: tuple[str, ...] | None = None,
    limites: tuple[float, float] | None = (0.0, 100.0),
    calcular_probabilidade: bool = False,
) -> SerieSuavizada:
    """Agrega uma série pelo Modelo B e devolve curva, pontos e pesos finais.

    ``janela_dias`` é aceito apenas para manter as chamadas visualmente simples;
    o Modelo B sempre usa seus parâmetros próprios: meia-vida de 15 dias e idade
    máxima de 90 dias. Isso impede que uma chamada reutilizada introduza, sem
    querer, a janela linear do Modelo A.
    """
    del janela_dias
    preparado = frame.copy()
    preparado["data_referencia"] = pd.to_datetime(preparado["data_referencia"], errors="coerce").dt.normalize()
    preparado = preparado.loc[preparado["data_referencia"].notna()].copy()
    for coluna in {coluna_valor, *(colunas_variancia or (coluna_valor,))}:
        preparado[coluna] = pd.to_numeric(preparado[coluna], errors="coerce")
    amostras = preparado.apply(amostra_efetiva, axis=1)
    preparado["_amostra_efetiva"] = [item[0] for item in amostras]
    preparado["_fonte_amostra"] = [item[1] for item in amostras]
    qualidade_bruta = pd.to_numeric(preparado["peso_legacy"], errors="coerce").fillna(PESO_INSTITUTO_DESCONHECIDO)
    preparado["_qualidade_bruta"] = qualidade_bruta
    preparado["_qualidade_ajustada"] = np.clip(
        PRIOR_QUALIDADE + ENCOLHIMENTO_QUALIDADE * (qualidade_bruta - PRIOR_QUALIDADE),
        0.01,
        None,
    )
    preparado["_amostra_relativa"] = np.minimum(preparado["_amostra_efetiva"], AMOSTRA_MAXIMA) / AMOSTRA_MAXIMA
    preparado["_id_onda"] = preparado.apply(identificador_onda, axis=1)

    colunas_pontos = [coluna for coluna in ["data_referencia", "instituto", coluna_valor] if coluna in preparado]
    pontos = preparado.loc[preparado[coluna_valor].notna(), colunas_pontos].copy()
    pontos = pontos.rename(columns={coluna_valor: "valor_pct"}).sort_values("data_referencia")
    if pontos.empty:
        vazio = pd.DataFrame(
            columns=[
                "estimativa_pct", "ic_baixo_pct", "ic_alto_pct", "se_pp",
                "variancia_amostral", "variancia_heterogeneidade", "pesquisas",
                "institutos", "informacao_efetiva", "teto_viavel", "status_evidencia",
                "probabilidade_lula_a_frente", "motivo_probabilidade",
            ]
        )
        return SerieSuavizada(vazio, pontos, pd.DataFrame())

    validos = preparado.loc[preparado[coluna_valor].notna()].copy()
    datas = validos["data_referencia"].to_numpy(dtype="datetime64[D]").astype("int64")
    valores = validos[coluna_valor].to_numpy(dtype=float)
    qualidade = validos["_qualidade_ajustada"].to_numpy(dtype=float)
    amostra_relativa = validos["_amostra_relativa"].to_numpy(dtype=float)
    amostra = validos["_amostra_efetiva"].to_numpy(dtype=float)
    variancia = numerador_variancia(validos, coluna_valor, colunas_variancia)
    institutos = validos["instituto"].fillna("Instituto desconhecido").astype(str).to_numpy()
    ids_onda = validos["_id_onda"].to_numpy()
    registros_base = validos.to_dict(orient="records")

    registros: list[dict[str, object]] = []
    memoria_ultimo_ponto: list[dict[str, object]] = []
    ultima_referencia = int(np.unique(datas)[-1])
    for referencia in np.unique(datas):
        idades = referencia - datas
        selecionados = np.flatnonzero((idades >= 0) & (idades <= IDADE_MAXIMA_DIAS))
        if not len(selecionados):
            continue
        # Meia-vida: após 15 dias o componente de recência cai pela metade.
        componente_tempo = np.power(0.5, idades[selecionados] / MEIA_VIDA_DIAS)
        peso_bruto = (
            qualidade[selecionados] ** EXPOENTE_QUALIDADE
            * componente_tempo ** EXPOENTE_RECENCIA
            * amostra_relativa[selecionados] ** EXPOENTE_AMOSTRA
        )
        positivos = peso_bruto > 0
        selecionados = selecionados[positivos]
        peso_bruto = peso_bruto[positivos]
        if not len(selecionados):
            continue
        componente_tempo = componente_tempo[positivos]
        idades_selecionadas = idades[selecionados]
        peso_pre_teto, peso, limitado, teto_viavel = aplicar_teto_por_instituto(
            peso_bruto, institutos[selecionados]
        )
        estimativa = float(np.sum(peso * valores[selecionados]))
        variancia_amostral = float(np.sum(peso ** 2 * variancia[selecionados] / amostra[selecionados]))
        informacao_efetiva = float(1.0 / np.sum(peso ** 2))
        dispersao_observada = float(
            np.sum(peso * ((valores[selecionados] - estimativa) / 100.0) ** 2)
        )
        dispersao_esperada = float(
            np.sum(peso * variancia[selecionados] / amostra[selecionados])
        )
        variancia_heterogeneidade = max(0.0, dispersao_observada - dispersao_esperada) / max(
            informacao_efetiva, 1.0
        )
        variancia_total = (
            variancia_amostral
            + variancia_heterogeneidade
            + (PISO_INCERTEZA_PP / 100.0) ** 2
        )
        erro_padrao = float(np.sqrt(max(variancia_total, 0.0)) * 100.0)
        pesquisas = int(len(np.unique(ids_onda[selecionados])))
        quantidade_institutos = int(len(np.unique(institutos[selecionados])))
        if not teto_viavel:
            status = "evidencia_insuficiente_concentracao"
        elif pesquisas < MINIMO_PESQUISAS_PROBABILIDADE or quantidade_institutos < MINIMO_INSTITUTOS_PROBABILIDADE:
            status = "evidencia_insuficiente"
        else:
            status = "evidencia_suficiente"

        probabilidade: float | None = None
        motivo_probabilidade = "nao_solicitada"
        if calcular_probabilidade:
            if status == "evidencia_suficiente" and erro_padrao > 0:
                probabilidade = cdf_normal(estimativa / erro_padrao)
                motivo_probabilidade = ""
            else:
                motivo_probabilidade = status
        inferior, superior = estimativa - Z_95 * erro_padrao, estimativa + Z_95 * erro_padrao
        if limites is not None:
            inferior, superior = max(limites[0], inferior), min(limites[1], superior)
        data = pd.Timestamp(np.datetime64(int(referencia), "D"))
        registros.append(
            {
                "data": data,
                "estimativa_pct": estimativa,
                "ic_baixo_pct": inferior,
                "ic_alto_pct": superior,
                "se_pp": erro_padrao,
                "variancia_amostral": variancia_amostral,
                "variancia_heterogeneidade": variancia_heterogeneidade,
                "pesquisas": pesquisas,
                "institutos": quantidade_institutos,
                "informacao_efetiva": informacao_efetiva,
                "teto_viavel": bool(teto_viavel),
                "status_evidencia": status,
                "probabilidade_lula_a_frente": probabilidade,
                "motivo_probabilidade": motivo_probabilidade,
            }
        )
        # A memória detalhada é exportada somente para o ponto mais recente. Isso
        # mantém a planilha auditável sem multiplicar milhares de linhas que o
        # usuário não precisa para a apresentação.
        if int(referencia) == ultima_referencia:
            for posicao, idade, tempo, bruto, pre_teto, final, foi_limitado in zip(
                selecionados,
                idades_selecionadas,
                componente_tempo,
                peso_bruto,
                peso_pre_teto,
                peso,
                limitado,
                strict=True,
            ):
                origem = registros_base[int(posicao)]
                memoria_ultimo_ponto.append(
                    {
                        "data_ponto": data,
                        "data_pesquisa": origem["data_referencia"],
                        "instituto": origem.get("instituto"),
                        "valor_pct": origem.get(coluna_valor),
                        "idade_dias": int(idade),
                        "amostra_efetiva": origem.get("_amostra_efetiva"),
                        "fonte_amostra": origem.get("_fonte_amostra"),
                        "qualidade_bruta": origem.get("_qualidade_bruta"),
                        "qualidade_ajustada": origem.get("_qualidade_ajustada"),
                        "componente_recencia": float(tempo),
                        "peso_bruto": float(bruto),
                        "peso_antes_teto": float(pre_teto),
                        "peso_final": float(final),
                        "peso_limitado": bool(foi_limitado),
                        "teto_viavel": bool(teto_viavel),
                    }
                )
    curva = pd.DataFrame.from_records(registros).set_index("data")
    memoria = pd.DataFrame.from_records(memoria_ultimo_ponto)
    return SerieSuavizada(curva, pontos, memoria)


def somente_brasil_total(frame: pd.DataFrame) -> pd.DataFrame:
    mascara = (
        frame["nivel_geografico"].map(texto_normalizado).eq("brasil")
        & frame["geografia"].map(texto_normalizado).eq("brasil")
        & frame["segmento_tipo"].map(texto_normalizado).eq("total")
        & frame["segmento"].map(texto_normalizado).eq("total")
    )
    return frame.loc[mascara].copy()


def somente_brasil(frame: pd.DataFrame) -> pd.DataFrame:
    """Mantém recortes nacionais, sem exigir que o segmento seja Total."""
    mascara = (
        frame["nivel_geografico"].map(texto_normalizado).eq("brasil")
        & frame["geografia"].map(texto_normalizado).eq("brasil")
    )
    return frame.loc[mascara].copy()


def sexo_padronizado(valor: object) -> str:
    """Une os rótulos publicados equivalentes, sem criar uma nova categoria."""
    chave = texto_normalizado(valor)
    if chave in {"fem", "feminino", "mulher", "mulheres"}:
        return "Mulheres"
    if chave in {"mas", "masculino", "homem", "homens"}:
        return "Homens"
    return ""


def religiao_padronizada(valor: object) -> str:
    """Harmoniza somente rótulos religiosos semanticamente equivalentes."""
    chave = texto_normalizado(valor)
    if chave in {"catolica", "catolico", "catolicas", "catolicos"}:
        return "Católicos"
    if chave in {"evangelica", "evangelico", "evangelicas", "evangelicos"}:
        return "Evangélicos"
    if chave in {"outra religiao", "outras religioes"}:
        return "Outras religiões"
    if chave in {"sem religiao", "nenhuma"}:
        return "Sem religião"
    return ""


def renda_padronizada(valor: object) -> str:
    """Harmoniza somente faixas de renda equivalentes e preserva faixas distintas.

    As faixas em salários mínimos têm pequenas variações de escrita entre
    institutos. Faixas em reais, ou faixas que não sejam comprovadamente
    equivalentes, continuam separadas para não produzir uma comparação falsa.
    """
    if not presente(valor):
        return ""
    rotulo_publicado = str(valor).strip()
    chave = texto_normalizado(rotulo_publicado)
    chave = re.sub(r"\b0+(\d)\b", r"\1", chave).replace("s m", "sm")
    if chave in {"ns nr", "nao sabe nao respondeu", "nao respondeu"}:
        return ""
    if chave in {"ate 1 sm", "ate 1 salario minimo"}:
        return "Até 1 SM"
    if chave in {"de 1 a 2 sm", "de 1 ate 2 sm", "mais de 1 a 2 sm"}:
        return "Mais de 1 a 2 SM"
    if chave in {"de 2 a 5 sm", "de 2 ate 5 sm", "mais de 2 a 5 sm"}:
        return "Mais de 2 a 5 SM"
    if chave == "mais de 5 sm":
        return "Mais de 5 SM"
    if chave == "mais de 5 a 10 sm":
        return "Mais de 5 a 10 SM"
    if chave == "mais de 10 sm":
        return "Mais de 10 SM"
    return rotulo_publicado


def recorte_segmentado(
    frame: pd.DataFrame,
    tipo_segmento: str,
    normalizador_grupo,
) -> pd.DataFrame:
    """Seleciona Brasil e padroniza um recorte publicado, sem preencher ausências."""
    nacionais = somente_brasil(frame)
    resultado = nacionais.loc[
        nacionais["segmento_tipo"].map(texto_normalizado).eq(texto_normalizado(tipo_segmento))
    ].copy()
    resultado["grupo_abertura"] = resultado["segmento"].map(normalizador_grupo)
    return resultado.loc[resultado["grupo_abertura"].ne("")].copy()


def confrontos_segundo_turno(confrontos: pd.DataFrame, termo_adversario: str) -> pd.DataFrame:
    nacionais = somente_brasil_total(confrontos)
    mascara = (
        nacionais["turno"].map(texto_normalizado).str.startswith("2", na=False)
        & nacionais["tipo_cenario"].map(texto_normalizado).eq("estimulada")
        & nacionais["base_voto"].map(texto_normalizado).eq("totais")
        & nacionais["adversario"].map(texto_normalizado).str.contains(termo_adversario, na=False)
    )
    return nacionais.loc[mascara].copy()


def confrontos_segundo_turno_segmentados(
    confrontos: pd.DataFrame,
    termo_adversario: str,
    tipo_segmento: str,
    normalizador_grupo,
) -> pd.DataFrame:
    """Seleciona um confronto de 2º turno e uma abertura publicada no Brasil."""
    nacionais = somente_brasil(confrontos)
    mascara = (
        nacionais["turno"].map(texto_normalizado).str.startswith("2", na=False)
        & nacionais["tipo_cenario"].map(texto_normalizado).eq("estimulada")
        & nacionais["base_voto"].map(texto_normalizado).eq("totais")
        & nacionais["adversario"].map(texto_normalizado).str.contains(termo_adversario, na=False)
        & nacionais["segmento_tipo"].map(texto_normalizado).eq(texto_normalizado(tipo_segmento))
    )
    resultado = nacionais.loc[mascara].copy()
    resultado["grupo_abertura"] = resultado["segmento"].map(normalizador_grupo)
    return resultado.loc[resultado["grupo_abertura"].ne("")].copy()


def tracking_semanal(tracking_diario: pd.DataFrame) -> pd.DataFrame:
    """Consolida tracking diário em uma observação semanal de sete dias completos."""
    if tracking_diario.empty:
        return tracking_diario.copy()
    grupos = [
        "instituto", "turno", "tipo_cenario", "cenario", "adversario", "nivel_geografico",
        "geografia", "segmento_tipo", "segmento", "base_voto", "tipo_pesquisa",
    ]
    valores = [
        "lula_pct", "adversario_pct", "outros_candidatos_pct", "brancos_nulos_indecisos_pct",
        "amostra_total", "amostra_segmento", "peso_legacy",
    ]
    registros: list[dict[object, object]] = []
    for _, curva in tracking_diario.groupby(grupos, dropna=False, sort=False):
        curva = curva.sort_values("data_referencia").copy()
        numerica = curva.set_index("data_referencia")[valores].apply(pd.to_numeric, errors="coerce")
        semanal = numerica.resample("W-SUN").mean()
        dias_publicados = curva.set_index("data_referencia").resample("W-SUN").size()
        semanal = semanal.loc[dias_publicados.reindex(semanal.index).eq(7)]
        if semanal.empty:
            continue
        modelo = curva.iloc[0].to_dict()
        for data, medias in semanal.iterrows():
            registro = modelo.copy()
            registro["data_referencia"] = pd.Timestamp(data)
            registro["frequencia_original"] = "semanal"
            for coluna, valor in medias.items():
                registro[coluna] = valor
            registros.append(registro)
    if not registros:
        return tracking_diario.iloc[0:0].copy()
    return pd.DataFrame.from_records(registros, columns=tracking_diario.columns)


def preparar_segundo_turno(linhas: pd.DataFrame) -> pd.DataFrame:
    regular = linhas.loc[linhas["tipo_pesquisa"].map(texto_normalizado).eq("regular")].copy()
    tracking = linhas.loc[linhas["tipo_pesquisa"].map(texto_normalizado).eq("tracking")].copy()
    diario = tracking.loc[tracking["frequencia_original"].map(texto_normalizado).eq("diaria")].copy()
    nao_diario = tracking.loc[~tracking["frequencia_original"].map(texto_normalizado).eq("diaria")].copy()
    return pd.concat([regular, tracking_semanal(diario), nao_diario], ignore_index=True).sort_values("data_referencia")


def confrontos_primeiro_turno(confrontos: pd.DataFrame) -> pd.DataFrame:
    """Seleciona todos os cenários nacionais/total, estimulados, de primeiro turno."""
    nacionais = somente_brasil_total(confrontos)
    mascara = (
        nacionais["turno"].map(texto_normalizado).str.startswith("1", na=False)
        & nacionais["tipo_cenario"].map(texto_normalizado).eq("estimulada")
        & nacionais["base_voto"].map(texto_normalizado).eq("totais")
        & nacionais["adversario"].map(presente)
    )
    return nacionais.loc[mascara].copy()


def confrontos_primeiro_turno_segmentados(
    confrontos: pd.DataFrame,
    termo_adversario: str,
    tipo_segmento: str,
    normalizador_grupo,
) -> pd.DataFrame:
    """Seleciona um confronto de 1º turno e uma abertura nacional publicada."""
    nacionais = somente_brasil(confrontos)
    mascara = (
        nacionais["turno"].map(texto_normalizado).str.startswith("1", na=False)
        & nacionais["tipo_cenario"].map(texto_normalizado).eq("estimulada")
        & nacionais["base_voto"].map(texto_normalizado).eq("totais")
        & nacionais["adversario"].map(texto_normalizado).str.contains(termo_adversario, na=False)
        & nacionais["segmento_tipo"].map(texto_normalizado).eq(texto_normalizado(tipo_segmento))
    )
    resultado = nacionais.loc[mascara].copy()
    resultado["grupo_abertura"] = resultado["segmento"].map(normalizador_grupo)
    return resultado.loc[resultado["grupo_abertura"].ne("")].copy()


def chaves_onda_primeiro_turno() -> list[str]:
    """Campos que identificam uma mesma onda, antes da abertura por cenário."""
    return [
        "data_referencia", "instituto", "tipo_pesquisa", "frequencia_original",
        "turno", "tipo_cenario", "nivel_geografico", "geografia",
        "segmento_tipo", "segmento", "base_voto",
    ]


def preparar_primeiro_turno(linhas: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Harmoniza cenários, sem transformar ausência de candidato em zero.

    Primeiro, cada candidato recebe a média simples dos cenários em que foi
    testado dentro da mesma onda. Depois, o agregador pondera essas observações
    por data. Assim, uma pesquisa com vários cenários não ganha peso extra e
    um candidato ausente de uma lista não é artificialmente penalizado.
    """
    linhas = preparar_segundo_turno(linhas).copy()
    if linhas.empty:
        return linhas, pd.DataFrame()

    chaves = chaves_onda_primeiro_turno()
    chaves_cenario = [*chaves, "cenario"]
    linhas["adversario"] = linhas["adversario"].astype(str).str.strip()
    linhas = linhas.loc[
        linhas["adversario"].map(texto_normalizado).isin(CANDIDATOS_PRIMEIRO_TURNO_ADVERSARIOS)
    ].copy()
    if linhas.empty:
        return linhas, pd.DataFrame()
    linhas["lula_pct"] = pd.to_numeric(linhas["lula_pct"], errors="coerce")
    linhas["adversario_pct"] = pd.to_numeric(linhas["adversario_pct"], errors="coerce")

    # Lula aparece repetido nas linhas dos adversários de um mesmo cenário.
    # Deduplicamos somente essa repetição mecânica, preservando Lula uma vez
    # por cenário antes de fazer a média entre cenários da mesma onda.
    lula_por_cenario = (
        linhas.loc[linhas["lula_pct"].notna()]
        .sort_values(chaves_cenario + ["adversario"])
        .drop_duplicates(chaves_cenario, keep="first")
        .copy()
    )
    lula_por_cenario = lula_por_cenario.assign(candidato="Lula", valor_pct=lula_por_cenario["lula_pct"])
    adversarios_por_cenario = linhas.loc[linhas["adversario_pct"].notna()].copy()
    adversarios_por_cenario = adversarios_por_cenario.assign(
        candidato=adversarios_por_cenario["adversario"], valor_pct=adversarios_por_cenario["adversario_pct"]
    )
    manter = [
        *chaves,
        "cenario",
        "candidato",
        "valor_pct",
        "peso_legacy",
        "amostra_total",
        "amostra_segmento",
        "margem_erro_pp",
        "nivel_confianca_pct",
    ]
    por_cenario = pd.concat(
        [lula_por_cenario[manter], adversarios_por_cenario[manter]], ignore_index=True
    )
    pontos = (
        por_cenario.groupby([*chaves, "candidato"], dropna=False, sort=False)
        .agg(
            valor_pct=("valor_pct", "mean"),
            cenarios_testados=("cenario", "nunique"),
            cenarios_incluidos=("cenario", lambda valores: " | ".join(sorted(set(map(str, valores))))),
            peso_legacy=("peso_legacy", "first"),
            amostra_total=("amostra_total", "first"),
            amostra_segmento=("amostra_segmento", "first"),
            margem_erro_pp=("margem_erro_pp", "first"),
            nivel_confianca_pct=("nivel_confianca_pct", "first"),
        )
        .reset_index()
        .sort_values(["data_referencia", "candidato", "instituto"])
        .reset_index(drop=True)
    )
    return linhas, pontos


def votos_validos(linhas: pd.DataFrame) -> pd.DataFrame:
    resultado = linhas.copy()
    lula = pd.to_numeric(resultado["lula_pct"], errors="coerce")
    flavio = pd.to_numeric(resultado["adversario_pct"], errors="coerce")
    denominador = lula + flavio
    resultado = resultado.loc[denominador.gt(0)].copy()
    denominador = denominador.loc[resultado.index]
    resultado["lula_validos_pct"] = lula.loc[resultado.index] / denominador * 100
    resultado["adversario_validos_pct"] = flavio.loc[resultado.index] / denominador * 100
    return resultado


def exigir(serie: SerieSuavizada, nome: str) -> SerieSuavizada:
    if serie.valores.empty:
        raise ErroModeloB(f"Não há observações válidas para gerar '{nome}'.")
    return serie


def metodologia_modelo_b(contexto: str, observacao: str = "") -> pd.DataFrame:
    """Tabela curta que acompanha cada workbook e explica o resultado."""
    itens = [
        ("Versão", VERSAO_METODOLOGICA),
        ("Contexto", contexto),
        ("Recência", f"Decaimento exponencial; meia-vida de {MEIA_VIDA_DIAS:g} dias e idade máxima de {IDADE_MAXIMA_DIAS} dias."),
        ("Qualidade", f"Peso publicado aproximado em {ENCOLHIMENTO_QUALIDADE:.0%} do prior {PRIOR_QUALIDADE:.2f}; expoente {EXPOENTE_QUALIDADE:.2f}."),
        ("Amostra efetiva", f"Menor entre amostra declarada, amostra implícita na margem quando aplicável e teto {AMOSTRA_MAXIMA:,.0f}."),
        ("Concentração", f"Teto de {TETO_PESO_INSTITUTO:.0%} por instituto quando houver ao menos três institutos."),
        ("Incerteza", f"Erro amostral + heterogeneidade observada + piso de {PISO_INCERTEZA_PP:.1f} p.p.; IC de 95%."),
        ("Probabilidade", "Probabilidade experimental de Lula estar à frente hoje; exige 2 pesquisas, 3 institutos e teto viável. Não é previsão de vitória."),
        ("Status", "Modelo candidato experimental; não substitui o Modelo A antes de backtest e aprovação."),
    ]
    if observacao:
        itens.append(("Observação específica", observacao))
    return pd.DataFrame(itens, columns=["item", "descricao"])


def juntar_pesos(series: dict[str, SerieSuavizada]) -> pd.DataFrame:
    """Une as memórias do último ponto, identificando a série de origem."""
    tabelas: list[pd.DataFrame] = []
    for nome, serie in series.items():
        if serie.pesos_ultimo_ponto.empty:
            continue
        tabela = serie.pesos_ultimo_ponto.copy()
        tabela.insert(0, "serie", nome)
        tabelas.append(tabela)
    return pd.concat(tabelas, ignore_index=True) if tabelas else pd.DataFrame()


def escrever_planilha(caminho: Path, abas: dict[str, pd.DataFrame], indice: bool = True) -> None:
    """Grava um workbook legível, auditável e sem depender do Excel aberto."""
    with pd.ExcelWriter(caminho, engine="openpyxl", datetime_format="yyyy-mm-dd", date_format="yyyy-mm-dd") as escritor:
        for nome_aba, tabela in abas.items():
            tabela.to_excel(escritor, sheet_name=nome_aba, index=indice)
    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    livro = load_workbook(caminho)
    for aba in livro.worksheets:
        aba.freeze_panes = "A2"
        if aba.max_row >= 1 and aba.max_column >= 1:
            aba.auto_filter.ref = aba.dimensions
        for celula in aba[1]:
            celula.font = Font(bold=True, color="FFFFFF")
            celula.fill = PatternFill("solid", fgColor="1F4E78")
        for linha in aba.iter_rows():
            for celula in linha:
                if hasattr(celula.value, "year") and hasattr(celula.value, "month") and hasattr(celula.value, "day"):
                    celula.number_format = "yyyy-mm-dd"
                elif isinstance(celula.value, float):
                    celula.number_format = "0.0000"
        for indice_coluna, coluna in enumerate(aba.iter_cols(), start=1):
            largura = min(42, max(11, max(len(str(celula.value or "")) for celula in coluna) + 2))
            aba.column_dimensions[get_column_letter(indice_coluna)].width = largura
    livro.save(caminho)


def grafico_governo(series: dict[str, SerieSuavizada], caminho: Path) -> None:
    cores = {"Ótimo/Bom": "green", "Regular": "orange", "Ruim/Péssimo": "red"}
    figura, eixo = plt.subplots(figsize=(16, 8))
    for rotulo, serie in series.items():
        if not serie.pontos_publicados.empty:
            eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color=cores[rotulo], alpha=0.15, s=20)
        eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cores[rotulo], linewidth=2, label=rotulo)
        eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cores[rotulo], alpha=0.15)
        ultimo = serie.valores.iloc[-1]
        eixo.text(serie.valores.index[-1], ultimo["estimativa_pct"], f" {ultimo['estimativa_pct']:.2f}%", color=cores[rotulo], va="center")
    eixo.set_title("Avaliação do Governo Lula III — Modelo B experimental", fontsize=16)
    eixo.set_xlabel("Data")
    eixo.set_ylabel("Percentual")
    eixo.grid(True, alpha=0.35)
    eixo.legend()
    eixo.set_xlim(pd.Timestamp("2023-02-01"), None)
    figura.tight_layout()
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def grafico_liquido(serie: SerieSuavizada, caminho: Path) -> None:
    figura, eixo = plt.subplots(figsize=(14, 7))
    eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color="gray", alpha=0.25, s=20)
    eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color="red", linewidth=2.2, label="Modelo B")
    eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color="red", alpha=0.15)
    ultimo = serie.valores.iloc[-1]
    eixo.text(serie.valores.index[-1], ultimo["estimativa_pct"], f" {ultimo['estimativa_pct']:.2f}", color="red", va="center")
    eixo.axhline(0, color="black", linewidth=0.8)
    eixo.set_title("Avaliação Líquida do Governo Lula III — Modelo B experimental", fontsize=16)
    eixo.set_xlabel("Data")
    eixo.set_ylabel("Pontos percentuais")
    eixo.grid(True, alpha=0.35)
    eixo.legend()
    eixo.set_xlim(pd.Timestamp("2023-02-01"), None)
    figura.tight_layout()
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def grafico_segundo_turno(
    lula: SerieSuavizada,
    adversario: SerieSuavizada,
    margem: SerieSuavizada,
    nome_adversario: str,
    caminho: Path,
) -> None:
    figura, eixo = plt.subplots(figsize=(14, 7))
    for rotulo, cor, serie in [("Lula", "red", lula), (nome_adversario, "blue", adversario)]:
        eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color=cor, alpha=0.25, s=20)
        eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2, label=rotulo)
        eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cor, alpha=0.15)
        ultimo = serie.valores.iloc[-1]
        eixo.text(serie.valores.index[-1], ultimo["estimativa_pct"], f" {ultimo['estimativa_pct']:.2f}%", color=cor, va="center")
    ultimo_margem = margem.valores.iloc[-1]
    probabilidade = ultimo_margem["probabilidade_lula_a_frente"]
    if presente(probabilidade):
        complemento = f"Prob. experimental de Lula estar à frente: {float(probabilidade):.1%}"
    else:
        complemento = f"Probabilidade não publicada: {ultimo_margem['motivo_probabilidade']}"
    eixo.set_title(
        f"Segundo Turno 2026: Lula vs {nome_adversario} — Modelo B experimental",
        fontsize=16,
        pad=38,
    )
    eixo.text(0.5, 1.012, complemento, transform=eixo.transAxes, ha="center", va="bottom", fontsize=10, color="#444444")
    eixo.set_xlabel("Data")
    eixo.set_ylabel("Percentual")
    if nome_adversario == "Flavio":
        eixo.set_ylim(40, 60)
    else:
        limites = pd.concat([
            lula.valores[["ic_baixo_pct", "ic_alto_pct"]],
            adversario.valores[["ic_baixo_pct", "ic_alto_pct"]],
        ])
        inferior = max(0.0, float(np.floor((limites["ic_baixo_pct"].min() - 3) / 5) * 5))
        superior = min(100.0, float(np.ceil((limites["ic_alto_pct"].max() + 3) / 5) * 5))
        eixo.set_ylim(inferior, superior)
    eixo.grid(True, alpha=0.35)
    eixo.legend()
    figura.tight_layout()
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def grupos_disponiveis(linhas: pd.DataFrame, ordem: tuple[str, ...]) -> list[str]:
    return [grupo for grupo in ordem if grupo in set(linhas["grupo_abertura"])]


def nome_curto_grupo(grupo: str) -> str:
    return texto_normalizado(grupo).replace(" ", "_").title()


def cobertura_abertura(linhas: pd.DataFrame) -> pd.DataFrame:
    return (
        linhas.groupby("grupo_abertura", sort=False)
        .agg(
            observacoes_publicadas=("grupo_abertura", "size"),
            primeira_data=("data_referencia", "min"),
            ultima_data=("data_referencia", "max"),
            institutos=("instituto", lambda valores: ", ".join(sorted(set(map(str, valores))))),
        )
        .reset_index()
        .rename(columns={"grupo_abertura": "grupo"})
    )


def limites_comuns(series_por_grupo: dict[str, tuple[SerieSuavizada, SerieSuavizada]]) -> tuple[float, float]:
    limites = pd.concat(
        [
            serie.valores[["ic_baixo_pct", "ic_alto_pct"]]
            for dupla in series_por_grupo.values()
            for serie in dupla
        ]
    )
    inferior = max(0.0, float(np.floor((limites["ic_baixo_pct"].min() - 3) / 5) * 5))
    superior = min(100.0, float(np.ceil((limites["ic_alto_pct"].max() + 3) / 5) * 5))
    return inferior, superior


def grafico_governo_por_sexo(
    series_por_grupo: dict[str, dict[str, SerieSuavizada]],
    caminho: Path,
) -> None:
    cores = {"Ótimo/Bom": "green", "Regular": "orange", "Ruim/Péssimo": "red"}
    grupos = ["Mulheres", "Homens"]
    figura, eixos = plt.subplots(1, 2, figsize=(18, 8), sharey=True)
    for eixo, grupo in zip(eixos, grupos, strict=True):
        for rotulo, serie in series_por_grupo[grupo].items():
            eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color=cores[rotulo], alpha=0.20, s=22)
            eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cores[rotulo], linewidth=2.1, label=rotulo)
            eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cores[rotulo], alpha=0.10)
        eixo.set_title(grupo)
        eixo.set_xlabel("Data")
        eixo.grid(True, alpha=0.30)
        eixo.set_ylim(0, 100)
    eixos[0].set_ylabel("Percentual")
    identificadores, rotulos = eixos[0].get_legend_handles_labels()
    figura.legend(identificadores, rotulos, loc="lower center", ncol=3, frameon=False)
    figura.suptitle("Avaliação do Governo Lula III por sexo — Modelo B experimental", fontsize=16)
    figura.text(0.5, 0.03, "Pontos: resultados publicados. Faixas: incerteza amostral, heterogeneidade entre pesquisas e piso conservador.", ha="center", fontsize=9, color="#444444")
    figura.subplots_adjust(bottom=0.18, top=0.86, wspace=0.08)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def grafico_liquido_por_sexo(
    series_por_grupo: dict[str, SerieSuavizada],
    caminho: Path,
) -> None:
    figura, eixos = plt.subplots(1, 2, figsize=(18, 8), sharey=True)
    for eixo, grupo in zip(eixos, ["Mulheres", "Homens"], strict=True):
        serie = series_por_grupo[grupo]
        eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color="gray", alpha=0.25, s=22)
        eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color="red", linewidth=2.1, label="Modelo B")
        eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color="red", alpha=0.10)
        eixo.axhline(0, color="black", linewidth=0.8)
        eixo.set_title(grupo)
        eixo.set_xlabel("Data")
        eixo.grid(True, alpha=0.30)
    eixos[0].set_ylabel("Pontos percentuais")
    identificadores, rotulos = eixos[0].get_legend_handles_labels()
    figura.legend(identificadores, rotulos, loc="lower center", ncol=2, frameon=False)
    figura.suptitle("Avaliação líquida do Governo Lula III por sexo — Modelo B experimental", fontsize=16)
    figura.subplots_adjust(bottom=0.15, top=0.86, wspace=0.08)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def gerar_governo_por_sexo(governo: pd.DataFrame, pasta_saida: Path) -> bool:
    """Gera composição e avaliação líquida para Mulheres e Homens quando publicados."""
    linhas = recorte_segmentado(governo, "Sexo", sexo_padronizado)
    grupos = grupos_disponiveis(linhas, ("Mulheres", "Homens"))
    if grupos != ["Mulheres", "Homens"]:
        print("Aviso: a base não possui avaliação nacional de governo para Mulheres e Homens; nenhum arquivo por sexo foi gerado.")
        return False

    composicao_por_grupo: dict[str, dict[str, SerieSuavizada]] = {}
    liquida_por_grupo: dict[str, SerieSuavizada] = {}
    abas_composicao: dict[str, pd.DataFrame] = {}
    abas_liquida: dict[str, pd.DataFrame] = {}
    for grupo in grupos:
        recorte = linhas.loc[linhas["grupo_abertura"].eq(grupo)].copy()
        composicao = {
            "Ótimo/Bom": exigir(suavizar(recorte, "otimo_bom_pct", 30), f"Ótimo/Bom entre {grupo.lower()}"),
            "Regular": exigir(suavizar(recorte, "regular_pct", 30), f"Regular entre {grupo.lower()}"),
            "Ruim/Péssimo": exigir(suavizar(recorte, "ruim_pessimo_pct", 30), f"Ruim/Péssimo entre {grupo.lower()}"),
        }
        composicao_por_grupo[grupo] = composicao
        curto = nome_curto_grupo(grupo)
        for nome_aba, coluna in [(f"Suavizados_{curto}", "estimativa_pct"), (f"IC_Baixo_{curto}", "ic_baixo_pct"), (f"IC_Alto_{curto}", "ic_alto_pct")]:
            tabela = pd.concat([serie.valores[coluna].rename(nome) for nome, serie in composicao.items()], axis=1).sort_index()
            tabela.index.name = "data"
            abas_composicao[nome_aba] = tabela.reset_index()

        fonte_liquida = recorte.loc[recorte["otimo_bom_pct"].map(presente) & recorte["ruim_pessimo_pct"].map(presente)].copy()
        fonte_liquida["avaliacao_liquida_pct"] = fonte_liquida["otimo_bom_pct"] - fonte_liquida["ruim_pessimo_pct"]
        serie_liquida = exigir(
            suavizar(
                fonte_liquida,
                "avaliacao_liquida_pct",
                colunas_variancia=("otimo_bom_pct", "ruim_pessimo_pct"),
                limites=(-100.0, 100.0),
            ),
            f"Avaliação líquida entre {grupo.lower()}",
        )
        liquida_por_grupo[grupo] = serie_liquida
        tabela = serie_liquida.valores.reset_index().rename(
            columns={"estimativa_pct": "avaliacao_liquida", "ic_baixo_pct": "ic_baixo", "ic_alto_pct": "ic_alto"}
        )
        abas_liquida[f"Serie_{curto}"] = tabela
        abas_liquida[f"Pesos_{curto}"] = serie_liquida.pesos_ultimo_ponto

    cobertura = cobertura_abertura(linhas)
    metodologia = metodologia_modelo_b(
        "Brasil, avaliação do Governo Lula III por sexo.",
        "Rótulos FEM/Feminino e MAS/Masculino são harmonizados como Mulheres e Homens; ausência não vira zero.",
    )
    abas_composicao["Cobertura"] = cobertura
    abas_composicao["Metodologia"] = metodologia
    abas_composicao["Pesos_ultimo_ponto"] = juntar_pesos(
        {f"{grupo} - {nome}": serie for grupo, composicao in composicao_por_grupo.items() for nome, serie in composicao.items()}
    )
    abas_composicao["Linhas_publicadas"] = linhas.sort_values(["data_referencia", "grupo_abertura"])
    abas_liquida["Cobertura"] = cobertura
    abas_liquida["Metodologia"] = metodologia
    escrever_planilha(pasta_saida / f"{NOME_GRAFICO_GOVERNO_SEXO}.xlsx", abas_composicao, indice=False)
    escrever_planilha(pasta_saida / f"{NOME_GRAFICO_LIQUIDO_SEXO}.xlsx", abas_liquida, indice=False)
    grafico_governo_por_sexo(composicao_por_grupo, pasta_saida / f"{NOME_GRAFICO_GOVERNO_SEXO}.png")
    grafico_liquido_por_sexo(liquida_por_grupo, pasta_saida / f"{NOME_GRAFICO_LIQUIDO_SEXO}.png")
    return True


def grafico_segundo_turno_por_abertura(
    series_por_grupo: dict[str, tuple[SerieSuavizada, SerieSuavizada]],
    margens_por_grupo: dict[str, SerieSuavizada],
    nome_adversario: str,
    titulo_abertura: str,
    caminho: Path,
) -> None:
    grupos = list(series_por_grupo)
    colunas = 2
    linhas = int(np.ceil(len(grupos) / colunas))
    figura, eixos = plt.subplots(linhas, colunas, figsize=(17, 6 * linhas), sharey=True)
    eixos_planos = np.atleast_1d(eixos).ravel()
    inferior, superior = limites_comuns(series_por_grupo)
    inicio = min(serie.valores.index.min() for dupla in series_por_grupo.values() for serie in dupla)
    fim = max(serie.valores.index.max() for dupla in series_por_grupo.values() for serie in dupla)
    if (fim - inicio).days <= 60:
        localizador_data = mdates.DayLocator(interval=14)
        formatador_data = mdates.DateFormatter("%m-%d")
    else:
        localizador_data = mdates.MonthLocator(interval=1)
        formatador_data = mdates.DateFormatter("%Y-%m")
    for eixo, grupo in zip(eixos_planos, grupos):
        lula, adversario = series_por_grupo[grupo]
        for rotulo, cor, serie in [("Lula", "red", lula), (nome_adversario, "blue", adversario)]:
            eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color=cor, alpha=0.25, s=22)
            eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2.1, label=rotulo)
            eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cor, alpha=0.10)
        ultima_margem = margens_por_grupo[grupo].valores.iloc[-1]
        probabilidade = ultima_margem["probabilidade_lula_a_frente"]
        detalhe = f" | P(Lula à frente) {float(probabilidade):.0%}" if presente(probabilidade) else ""
        eixo.set_title(f"{grupo}{detalhe}")
        eixo.set_xlabel("Data")
        eixo.xaxis.set_major_locator(localizador_data)
        eixo.xaxis.set_major_formatter(formatador_data)
        eixo.set_ylim(inferior, superior)
        eixo.grid(True, alpha=0.30)
    for eixo in eixos_planos[len(grupos):]:
        eixo.set_visible(False)
    for eixo in eixos_planos[::colunas]:
        eixo.set_ylabel("Votos válidos (%)")
    identificadores, rotulos = eixos_planos[0].get_legend_handles_labels()
    figura.legend(identificadores, rotulos, loc="lower center", ncol=2, frameon=False)
    figura.suptitle(f"Segundo turno 2026: Lula vs {nome_adversario} por {titulo_abertura} — Modelo B", fontsize=16)
    figura.text(0.5, 0.03, "Pontos publicados em votos válidos. Probabilidade experimental só aparece com cobertura suficiente; não é previsão da eleição.", ha="center", fontsize=9, color="#444444")
    figura.subplots_adjust(bottom=0.15, top=0.90, hspace=0.25, wspace=0.08)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def gerar_segundo_turno_por_abertura(
    confrontos: pd.DataFrame,
    nome_adversario: str,
    termo_adversario: str,
    tipo_segmento: str,
    normalizador_grupo: Callable[[object], str],
    ordem_grupos: tuple[str, ...],
    titulo_abertura: str,
    nome_saida: str,
    pasta_saida: Path,
) -> bool:
    """Gera um confronto de 2º turno aberto por segmento, sem imputar grupos ausentes."""
    linhas = confrontos_segundo_turno_segmentados(confrontos, termo_adversario, tipo_segmento, normalizador_grupo)
    grupos = grupos_disponiveis(linhas, ordem_grupos)
    if len(grupos) < 2:
        print(f"Aviso: não há cobertura suficiente por {titulo_abertura} para Lula × {nome_adversario}; nenhum arquivo foi gerado.")
        return False
    preparado = votos_validos(preparar_segundo_turno(linhas))
    series_por_grupo: dict[str, tuple[SerieSuavizada, SerieSuavizada]] = {}
    margens_por_grupo: dict[str, SerieSuavizada] = {}
    for grupo in grupos:
        recorte = preparado.loc[preparado["grupo_abertura"].eq(grupo)].copy()
        if recorte.empty:
            continue
        lula = exigir(suavizar(recorte, "lula_validos_pct", 30), f"Lula entre {grupo.lower()} contra {nome_adversario}")
        adversario = exigir(suavizar(recorte, "adversario_validos_pct", 30), f"{nome_adversario} entre {grupo.lower()}")
        recorte["margem_lula_pct"] = recorte["lula_validos_pct"] - recorte["adversario_validos_pct"]
        margem = exigir(
            suavizar(
                recorte,
                "margem_lula_pct",
                colunas_variancia=("lula_validos_pct", "adversario_validos_pct"),
                limites=(-100.0, 100.0),
                calcular_probabilidade=True,
            ),
            f"Margem de Lula entre {grupo.lower()} contra {nome_adversario}",
        )
        series_por_grupo[grupo] = (lula, adversario)
        margens_por_grupo[grupo] = margem
    if len(series_por_grupo) < 2:
        print(f"Aviso: não há séries válidas por {titulo_abertura} para Lula × {nome_adversario}; nenhum arquivo foi gerado.")
        return False

    abas: dict[str, pd.DataFrame] = {}
    for grupo, (lula, adversario) in series_por_grupo.items():
        curto = nome_curto_grupo(grupo)
        for prefixo, coluna in [("Suavizados", "estimativa_pct"), ("IC_Baixo", "ic_baixo_pct"), ("IC_Alto", "ic_alto_pct")]:
            tabela = pd.concat([lula.valores[coluna].rename("Lula"), adversario.valores[coluna].rename(nome_adversario)], axis=1).sort_index()
            tabela.index.name = "data"
            abas[f"{prefixo}_{curto}"] = tabela.reset_index()
        abas[f"Margem_{curto}"] = margens_por_grupo[grupo].valores.reset_index()
        abas[f"Pesos_{curto}"] = juntar_pesos(
            {"Lula": lula, nome_adversario: adversario, "Margem Lula": margens_por_grupo[grupo]}
        )
    cobertura = cobertura_abertura(linhas.loc[linhas["grupo_abertura"].isin(series_por_grupo)])
    metodologia = metodologia_modelo_b(
        f"Brasil, 2º turno, estimulada, Lula × {nome_adversario}, por {titulo_abertura}.",
        "Lula e adversário são convertidos para votos válidos dentro de cada grupo. A margem total da pesquisa não é aplicada como margem do segmento.",
    )
    abas["Cobertura"] = cobertura
    abas["Metodologia"] = metodologia
    abas["Linhas_publicadas"] = linhas.sort_values(["data_referencia", "grupo_abertura"])
    escrever_planilha(pasta_saida / f"{nome_saida}.xlsx", abas, indice=False)
    grafico_segundo_turno_por_abertura(
        series_por_grupo,
        margens_por_grupo,
        nome_adversario,
        titulo_abertura,
        pasta_saida / f"{nome_saida}.png",
    )
    return True


def grupos_primeiro_turno_com_cobertura(
    pontos: pd.DataFrame,
    nome_adversario: str,
    ordem_grupos: tuple[str, ...],
) -> list[str]:
    """Mantém somente grupos com Lula e o adversário em pelo menos duas datas."""
    candidatos_necessarios = {"lula", texto_normalizado(nome_adversario)}
    elegiveis: set[str] = set()
    for grupo, recorte in pontos.groupby("grupo_abertura", sort=False):
        por_candidato = (
            recorte.assign(_candidato=recorte["candidato"].map(texto_normalizado))
            .groupby("_candidato")["data_referencia"]
            .nunique()
        )
        if candidatos_necessarios.issubset(set(por_candidato.index)) and all(
            int(por_candidato[candidato]) >= 2 for candidato in candidatos_necessarios
        ):
            elegiveis.add(str(grupo))
    ordenados = [grupo for grupo in ordem_grupos if grupo in elegiveis]
    return [*ordenados, *sorted(elegiveis.difference(ordenados), key=texto_normalizado)]


def margens_harmonizadas_primeiro_turno(
    pontos: pd.DataFrame,
    nome_adversario: str,
) -> pd.DataFrame:
    """Alinha Lula e adversário na mesma onda antes de calcular a diferença.

    A intenção de cada nome já é a média apenas dos cenários em que ele foi
    testado. O ``merge`` interno mantém somente ondas com os dois nomes, evitando
    comparar datas ou pesquisas diferentes e sem transformar ausência em zero.
    """
    chaves = chaves_onda_primeiro_turno()
    normalizados = pontos["candidato"].map(texto_normalizado)
    lula = pontos.loc[normalizados.eq("lula")].copy()
    adversario = pontos.loc[normalizados.eq(texto_normalizado(nome_adversario))].copy()
    if lula.empty or adversario.empty:
        return pd.DataFrame()
    metadados = [
        "peso_legacy", "amostra_total", "amostra_segmento", "margem_erro_pp",
        "nivel_confianca_pct", "cenarios_testados", "cenarios_incluidos",
    ]
    esquerda = lula[[*chaves, "valor_pct", *metadados]].rename(
        columns={"valor_pct": "lula_harmonizado_pct"}
    )
    direita = adversario[[*chaves, "valor_pct", "cenarios_testados", "cenarios_incluidos"]].rename(
        columns={
            "valor_pct": "adversario_harmonizado_pct",
            "cenarios_testados": "cenarios_testados_adversario",
            "cenarios_incluidos": "cenarios_incluidos_adversario",
        }
    )
    resultado = esquerda.merge(direita, on=chaves, how="inner", validate="one_to_one")
    if resultado.empty:
        return resultado
    resultado["margem_lula_pct"] = (
        resultado["lula_harmonizado_pct"] - resultado["adversario_harmonizado_pct"]
    )
    resultado["adversario"] = nome_adversario
    return resultado


def grafico_primeiro_turno_por_abertura(
    series_por_grupo: dict[str, tuple[SerieSuavizada, SerieSuavizada]],
    nome_adversario: str,
    titulo_abertura: str,
    caminho: Path,
) -> None:
    """Desenha Lula e um adversário em painéis comparáveis de primeiro turno."""
    grupos = list(series_por_grupo)
    colunas = 2
    linhas = int(np.ceil(len(grupos) / colunas))
    figura, eixos = plt.subplots(linhas, colunas, figsize=(17, 6 * linhas), sharey=True)
    eixos_planos = np.atleast_1d(eixos).ravel()
    inferior, superior = limites_comuns(series_por_grupo)
    inicio = min(serie.valores.index.min() for dupla in series_por_grupo.values() for serie in dupla)
    fim = max(serie.valores.index.max() for dupla in series_por_grupo.values() for serie in dupla)
    if (fim - inicio).days <= 60:
        localizador_data = mdates.DayLocator(interval=14)
        formatador_data = mdates.DateFormatter("%m-%d")
    else:
        localizador_data = mdates.MonthLocator(interval=1)
        formatador_data = mdates.DateFormatter("%Y-%m")
    for eixo, grupo in zip(eixos_planos, grupos):
        lula, adversario = series_por_grupo[grupo]
        for rotulo, cor, serie in [("Lula", "red", lula), (nome_adversario, "blue", adversario)]:
            eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color=cor, alpha=0.25, s=22)
            eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2.1, label=rotulo)
            eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cor, alpha=0.10)
        eixo.set_title(grupo, wrap=True)
        eixo.set_xlabel("Data")
        eixo.xaxis.set_major_locator(localizador_data)
        eixo.xaxis.set_major_formatter(formatador_data)
        eixo.set_ylim(inferior, superior)
        eixo.grid(True, alpha=0.30)
    for eixo in eixos_planos[len(grupos):]:
        eixo.set_visible(False)
    for eixo in eixos_planos[::colunas]:
        eixo.set_ylabel("Intenção de voto (% dos votos totais)")
    identificadores, rotulos = eixos_planos[0].get_legend_handles_labels()
    figura.legend(identificadores, rotulos, loc="lower center", ncol=2, frameon=False)
    figura.suptitle(f"Primeiro turno 2026: Lula vs {nome_adversario} por {titulo_abertura} — Modelo B", fontsize=16)
    figura.text(
        0.5,
        0.03,
        "Pontos publicados em votos totais. Curvas: Modelo B experimental sobre a média dos cenários em que cada nome foi testado; ausência não vira zero.",
        ha="center",
        fontsize=9,
        color="#444444",
    )
    figura.subplots_adjust(bottom=0.19, top=0.90, hspace=0.36, wspace=0.08)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def gerar_primeiro_turno_por_abertura(
    confrontos: pd.DataFrame,
    nome_adversario: str,
    termo_adversario: str,
    tipo_segmento: str,
    normalizador_grupo: Callable[[object], str],
    ordem_grupos: tuple[str, ...],
    titulo_abertura: str,
    nome_saida: str,
    pasta_saida: Path,
) -> bool:
    """Gera Lula × um adversário em 1º turno, por abertura publicada."""
    linhas = confrontos_primeiro_turno_segmentados(
        confrontos, termo_adversario, tipo_segmento, normalizador_grupo
    )
    if linhas.empty:
        print(f"Aviso: não há abertura de {titulo_abertura} para Lula × {nome_adversario} no 1º turno.")
        return False
    linhas = linhas.copy()
    linhas["segmento_publicado"] = linhas["segmento"]
    # A padronização ocorre antes da média entre cenários, para unir apenas
    # rótulos equivalentes (por exemplo, Feminino e Mulheres).
    linhas["segmento"] = linhas["grupo_abertura"]
    linhas_harmonizadas, pontos = preparar_primeiro_turno(linhas)
    if pontos.empty:
        print(f"Aviso: não há percentuais válidos por {titulo_abertura} para Lula × {nome_adversario} no 1º turno.")
        return False
    pontos = pontos.copy()
    pontos["grupo_abertura"] = pontos["segmento"]
    candidatos = pontos["candidato"].map(texto_normalizado)
    pontos = pontos.loc[candidatos.isin({"lula", texto_normalizado(nome_adversario)})].copy()
    grupos = grupos_primeiro_turno_com_cobertura(pontos, nome_adversario, ordem_grupos)
    if len(grupos) < 2:
        print(
            f"Aviso: a abertura de {titulo_abertura} para Lula × {nome_adversario} no 1º turno "
            "ainda não possui ao menos dois grupos com duas datas publicadas; nenhum arquivo foi gerado."
        )
        return False

    series_por_grupo: dict[str, tuple[SerieSuavizada, SerieSuavizada]] = {}
    margens_por_grupo: dict[str, SerieSuavizada] = {}
    pontos_utilizados: list[pd.DataFrame] = []
    for grupo in grupos:
        recorte = pontos.loc[pontos["grupo_abertura"].eq(grupo)].copy()
        lula_origem = recorte.loc[recorte["candidato"].map(texto_normalizado).eq("lula")].copy()
        adversario_origem = recorte.loc[
            recorte["candidato"].map(texto_normalizado).eq(texto_normalizado(nome_adversario))
        ].copy()
        if lula_origem.empty or adversario_origem.empty:
            continue
        lula = exigir(suavizar(lula_origem, "valor_pct", 30), f"Lula entre {grupo.lower()} no 1º turno")
        adversario = exigir(
            suavizar(adversario_origem, "valor_pct", 30),
            f"{nome_adversario} entre {grupo.lower()} no 1º turno",
        )
        pontos_margem = margens_harmonizadas_primeiro_turno(recorte, nome_adversario)
        if pontos_margem.empty:
            continue
        margem = exigir(
            suavizar(
                pontos_margem,
                "margem_lula_pct",
                colunas_variancia=("lula_harmonizado_pct", "adversario_harmonizado_pct"),
                limites=(-100.0, 100.0),
                calcular_probabilidade=True,
            ),
            f"Margem de Lula contra {nome_adversario} entre {grupo.lower()} no 1º turno",
        )
        series_por_grupo[grupo] = (lula, adversario)
        margens_por_grupo[grupo] = margem
        pontos_utilizados.extend([lula_origem, adversario_origem])
    if len(series_por_grupo) < 2:
        print(f"Aviso: não há séries válidas por {titulo_abertura} para Lula × {nome_adversario} no 1º turno.")
        return False

    pontos_planilha = pd.concat(pontos_utilizados, ignore_index=True).sort_values(
        ["data_referencia", "grupo_abertura", "candidato"]
    )
    abas: dict[str, pd.DataFrame] = {}
    for grupo, (lula, adversario) in series_por_grupo.items():
        curto = nome_curto_grupo(grupo)
        for prefixo, coluna in [("Suavizados", "estimativa_pct"), ("IC_Baixo", "ic_baixo_pct"), ("IC_Alto", "ic_alto_pct")]:
            tabela = pd.concat(
                [lula.valores[coluna].rename("Lula"), adversario.valores[coluna].rename(nome_adversario)], axis=1
            ).sort_index()
            tabela.index.name = "data"
            abas[f"{prefixo}_{curto}"] = tabela.reset_index()
        abas[f"Margem_{curto}"] = margens_por_grupo[grupo].valores.reset_index()
        abas[f"Pesos_{curto}"] = juntar_pesos(
            {"Lula": lula, nome_adversario: adversario, "Margem Lula": margens_por_grupo[grupo]}
        )
    cobertura = (
        pontos_planilha.loc[pontos_planilha["candidato"].map(texto_normalizado).eq(texto_normalizado(nome_adversario))]
        .groupby("grupo_abertura", sort=False)
        .agg(
            ondas_harmonizadas=("data_referencia", "size"),
            primeira_data=("data_referencia", "min"),
            ultima_data=("data_referencia", "max"),
            cenarios_no_total=("cenarios_testados", "sum"),
            institutos=("instituto", lambda valores: ", ".join(sorted(set(map(str, valores))))),
        )
        .reset_index()
        .rename(columns={"grupo_abertura": "grupo"})
    )
    rotulos_publicados = (
        linhas_harmonizadas.loc[linhas_harmonizadas["grupo_abertura"].isin(series_por_grupo)]
        .groupby("grupo_abertura", sort=False)["segmento_publicado"]
        .agg(lambda valores: " | ".join(sorted(set(map(str, valores)))))
        .rename("rotulos_publicados")
        .reset_index()
        .rename(columns={"grupo_abertura": "grupo"})
    )
    cobertura = cobertura.merge(rotulos_publicados, on="grupo", how="left")
    ordem_cobertura = list(series_por_grupo)
    cobertura["grupo"] = pd.Categorical(cobertura["grupo"], categories=ordem_cobertura, ordered=True)
    cobertura = cobertura.sort_values("grupo").reset_index(drop=True)
    cobertura["grupo"] = cobertura["grupo"].astype(str)
    metodologia = metodologia_modelo_b(
        f"Brasil, 1º turno, estimulada, votos totais, Lula × {nome_adversario}, por {titulo_abertura}.",
        "Cada pesquisa entra uma vez por candidato e grupo, pela média dos cenários em que o nome foi testado. O gráfico exige dois grupos e duas datas para ambos; ausência não vira zero.",
    )
    abas["Cobertura"] = cobertura
    abas["Metodologia"] = metodologia
    abas["Pontos_harmonizados"] = pontos_planilha.drop(columns=["peso_legacy"], errors="ignore")
    abas["Linhas_publicadas"] = linhas_harmonizadas.loc[
        linhas_harmonizadas["grupo_abertura"].isin(series_por_grupo)
    ].sort_values(["data_referencia", "grupo_abertura", "adversario", "cenario"])
    escrever_planilha(pasta_saida / f"{nome_saida}.xlsx", abas, indice=False)
    grafico_primeiro_turno_por_abertura(
        series_por_grupo, nome_adversario, titulo_abertura, pasta_saida / f"{nome_saida}.png"
    )
    return True


def nome_arquivo_abertura_primeiro_turno(nome: str) -> str:
    return texto_normalizado(nome).replace(" ", "_").title()


def gerar_aberturas_primeiro_turno(confrontos: pd.DataFrame, pasta_saida: Path) -> None:
    """Publica pares Lula × candidato por sexo, religião e renda quando houver cobertura."""
    for extensao in ("xlsx", "png"):
        for caminho_antigo in pasta_saida.glob(f"Primeiro_Turno_Lula_vs_*_por_*.{extensao}"):
            caminho_antigo.unlink()
    aberturas = [
        ("Sexo", sexo_padronizado, ("Mulheres", "Homens"), "sexo"),
        ("Religião", religiao_padronizada, ("Católicos", "Evangélicos", "Outras religiões", "Sem religião"), "religião"),
        (
            "Renda",
            renda_padronizada,
            ("Até 1 SM", "Mais de 1 a 2 SM", "Mais de 2 a 5 SM", "Mais de 5 SM", "Mais de 5 a 10 SM", "Mais de 10 SM"),
            "renda",
        ),
    ]
    for nome_adversario in CANDIDATOS_PRIMEIRO_TURNO[1:]:
        termo_adversario = texto_normalizado(nome_adversario)
        for tipo_segmento, normalizador_grupo, ordem_grupos, titulo_abertura in aberturas:
            nome_saida = (
                f"Primeiro_Turno_Lula_vs_{nome_arquivo_abertura_primeiro_turno(nome_adversario)}"
                f"_por_{nome_arquivo_abertura_primeiro_turno(tipo_segmento)}"
            )
            gerar_primeiro_turno_por_abertura(
                confrontos,
                nome_adversario,
                termo_adversario,
                tipo_segmento,
                normalizador_grupo,
                ordem_grupos,
                titulo_abertura,
                nome_saida,
                pasta_saida,
            )


def cores_primeiro_turno(candidatos: list[str]) -> dict[str, object]:
    """Define cores estáveis para os nomes mais recorrentes e cores distintas para os demais."""
    conhecidas = {
        "lula": "#C62828",
        "flavio": "#1565C0",
        "renan santos": "#6A1B9A",
        "romeu zema": "#2E7D32",
        "ronaldo caiado": "#EF6C00",
    }
    paleta = ["#546E7A", "#8D6E63", "#9E9D24", "#00838F", "#AD1457", "#7B1FA2"]
    complemento = list(plt.get_cmap("tab20").colors)
    resultado: dict[str, object] = {}
    proxima_cor = 0
    for candidato in candidatos:
        chave = texto_normalizado(candidato)
        if chave in conhecidas:
            resultado[candidato] = conhecidas[chave]
        else:
            while proxima_cor < len(paleta) and paleta[proxima_cor] in resultado.values():
                proxima_cor += 1
            if proxima_cor < len(paleta):
                resultado[candidato] = paleta[proxima_cor]
            else:
                resultado[candidato] = complemento[(proxima_cor - len(paleta)) % len(complemento)]
            proxima_cor += 1
    return resultado


def grafico_primeiro_turno(
    pontos: pd.DataFrame,
    series: pd.DataFrame,
    caminho: Path,
) -> None:
    """Desenha a média harmonizada de cenários, candidato a candidato."""
    todos = set(pontos["candidato"].unique())
    candidatos = [candidato for candidato in CANDIDATOS_PRIMEIRO_TURNO if candidato in todos]
    candidatos.extend(sorted(todos.difference(candidatos)))
    cores = cores_primeiro_turno(candidatos)
    institutos = ", ".join(sorted(set(pontos["instituto"].astype(str))))
    figura, eixo = plt.subplots(figsize=(18, 10))
    for candidato in candidatos:
        observados = pontos.loc[pontos["candidato"].eq(candidato)]
        eixo.scatter(
            observados["data_referencia"], observados["valor_pct"], color=cores[candidato], alpha=0.42, s=26,
        )
        curva = series.loc[series["candidato"].eq(candidato)]
        eixo.plot(curva["data"], curva["estimativa_pct"], color=cores[candidato], linewidth=2.25, label=candidato)
    minimo = float(pontos["valor_pct"].min())
    maximo = float(pontos["valor_pct"].max())
    inferior = max(0.0, float(np.floor((minimo - 4) / 5) * 5))
    superior = min(100.0, float(np.ceil((maximo + 4) / 5) * 5))
    eixo.set_ylim(inferior, superior)
    eixo.set_title("Primeiro turno 2026 — média harmonizada — Modelo B experimental", fontsize=16, pad=18)
    eixo.text(
        0.5,
        1.01,
        f"{institutos} | {len(candidatos)} candidatos selecionados; cada pesquisa contribui uma vez por candidato",
        transform=eixo.transAxes, ha="center", va="bottom", fontsize=10, color="#444444",
    )
    eixo.set_xlabel("Data")
    eixo.set_ylabel("Intenção de voto (% dos votos totais)")
    eixo.grid(True, alpha=0.30)
    eixo.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=4, frameon=False)
    figura.text(
        0.5,
        0.01,
        "Candidato ausente de um cenário não recebe zero: cada linha usa apenas os cenários em que o nome foi testado. "
        "A curva usa meia-vida e incerteza conservadora; não é previsão eleitoral.",
        ha="center", fontsize=9, color="#444444",
    )
    figura.subplots_adjust(bottom=0.22, top=0.88)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def gerar_primeiro_turno(confrontos: pd.DataFrame, pasta_saida: Path) -> bool:
    """Gera um único gráfico harmonizando os cenários de primeiro turno por candidato."""
    linhas = confrontos_primeiro_turno(confrontos)
    if linhas.empty:
        print(
            "Aviso: não há cenários nacionais, estimulados, de 1º turno na base; "
            "nenhum arquivo foi gerado para o primeiro turno."
        )
        return False
    linhas, pontos = preparar_primeiro_turno(linhas)
    if pontos.empty:
        print("Aviso: os cenários de primeiro turno não possuem percentuais válidos; nenhum arquivo foi gerado.")
        return False

    registros: list[pd.DataFrame] = []
    objetos_series: dict[str, SerieSuavizada] = {}
    for candidato, curva in pontos.groupby("candidato", sort=False):
        serie = exigir(suavizar(curva, "valor_pct", 30), f"{candidato} no primeiro turno")
        objetos_series[str(candidato)] = serie
        tabela = serie.valores.reset_index()
        tabela.insert(1, "candidato", candidato)
        registros.append(tabela)
    series = pd.concat(registros, ignore_index=True).sort_values(["data", "candidato"])
    cobertura = (
        pontos.groupby("candidato", sort=False)
        .agg(
            primeira_data=("data_referencia", "min"), ultima_data=("data_referencia", "max"),
            ondas_harmonizadas=("data_referencia", "size"),
            cenarios_no_total=("cenarios_testados", "sum"),
            institutos=("instituto", lambda valores: ", ".join(sorted(set(map(str, valores))))),
        )
        .reset_index()
    )
    metodologia = metodologia_modelo_b(
        "Brasil, Total, 1º turno, estimulada e votos totais: Lula, Flávio, Renan Santos, Romeu Zema, Ronaldo Caiado e Michelle Bolsonaro.",
        "Em cada pesquisa e candidato, usa a média simples somente dos cenários em que o nome foi testado. Ausência não é 0% e a série não é previsão eleitoral.",
    )
    pontos_planilha = pontos.drop(columns=["peso_legacy"], errors="ignore").copy()
    linhas_planilha = linhas.sort_values(["data_referencia", "adversario"]).copy()
    for nome_obsoleto in NOMES_OBSOLETOS_PRIMEIRO_TURNO:
        caminho_obsoleto = pasta_saida / nome_obsoleto
        if caminho_obsoleto.exists():
            caminho_obsoleto.unlink()
    escrever_planilha(
        pasta_saida / f"{NOME_GRAFICO_PRIMEIRO_TURNO}.xlsx",
        {
            "Series_harmonizadas": series,
            "Pontos_harmonizados": pontos_planilha,
            "Cobertura_candidatos": cobertura,
            "Metodologia": metodologia,
            "Pesos_ultimo_ponto": juntar_pesos(objetos_series),
            "Linhas_originais": linhas_planilha,
        },
        indice=False,
    )
    grafico_primeiro_turno(pontos, series, pasta_saida / f"{NOME_GRAFICO_PRIMEIRO_TURNO}.png")
    return True


def gerar_segundo_turno(
    confrontos: pd.DataFrame,
    nome_adversario: str,
    termo_adversario: str,
    nome_saida: str,
    pasta_saida: Path,
) -> bool:
    """Gera a planilha e o gráfico de um adversário quando houver dados na base."""
    linhas = confrontos_segundo_turno(confrontos, termo_adversario)
    if linhas.empty:
        print(
            f"Aviso: não há cenário nacional, estimulado, de 2º turno Lula × {nome_adversario} "
            "na base; nenhum arquivo foi gerado para esse confronto."
        )
        return False
    segundo_turno = votos_validos(preparar_segundo_turno(linhas))
    lula = exigir(suavizar(segundo_turno, "lula_validos_pct", 30), f"Lula no 2º turno contra {nome_adversario}")
    adversario = exigir(
        suavizar(segundo_turno, "adversario_validos_pct", 30),
        f"{nome_adversario} no 2º turno",
    )
    segundo_turno["margem_lula_pct"] = (
        segundo_turno["lula_validos_pct"] - segundo_turno["adversario_validos_pct"]
    )
    margem = exigir(
        suavizar(
            segundo_turno,
            "margem_lula_pct",
            colunas_variancia=("lula_validos_pct", "adversario_validos_pct"),
            limites=(-100.0, 100.0),
            calcular_probabilidade=True,
        ),
        f"Margem de Lula no 2º turno contra {nome_adversario}",
    )
    abas: dict[str, pd.DataFrame] = {}
    for nome_aba, coluna in [("Suavizados", "estimativa_pct"), ("IC_Baixo", "ic_baixo_pct"), ("IC_Alto", "ic_alto_pct")]:
        tabela = pd.concat(
            [lula.valores[coluna].rename("Lula"), adversario.valores[coluna].rename(nome_adversario)], axis=1
        ).sort_index()
        tabela.index.name = "data"
        abas[nome_aba] = tabela.reset_index()
    abas["Margem_e_probabilidade"] = margem.valores.reset_index()
    abas["Pesos_ultimo_ponto"] = juntar_pesos(
        {"Lula": lula, nome_adversario: adversario, "Margem Lula": margem}
    )
    abas["Metodologia"] = metodologia_modelo_b(
        f"Brasil, Total, 2º turno, estimulada, Lula × {nome_adversario}, em votos válidos.",
        "A probabilidade mede apenas Lula estar à frente no ponto agregado atual; não mede vitória no dia da eleição.",
    )
    abas["Linhas_publicadas"] = linhas.sort_values("data_referencia")
    escrever_planilha(pasta_saida / f"{nome_saida}.xlsx", abas, indice=False)
    grafico_segundo_turno(lula, adversario, margem, nome_adversario, pasta_saida / f"{nome_saida}.png")
    return True


def limpar_saidas_geradas(pasta_saida: Path) -> None:
    """Remove somente arquivos que este código sabe regenerar.

    A limpeza evita que um gráfico antigo continue parecendo atual depois que a
    cobertura some da base. Diretórios, documentos e resultados de outros fluxos
    nunca são apagados.
    """
    nomes_fixos = [
        NOME_GRAFICO_GOVERNO,
        NOME_GRAFICO_LIQUIDO,
        NOME_GRAFICO_SEGUNDO_TURNO,
        NOME_GRAFICO_SEGUNDO_TURNO_RENAN,
        NOME_GRAFICO_SEGUNDO_TURNO_CAIADO,
        NOME_GRAFICO_PRIMEIRO_TURNO,
        NOME_GRAFICO_GOVERNO_SEXO,
        NOME_GRAFICO_LIQUIDO_SEXO,
        NOME_GRAFICO_SEGUNDO_TURNO_FLAVIO_SEXO,
        NOME_GRAFICO_SEGUNDO_TURNO_RENAN_SEXO,
        NOME_GRAFICO_SEGUNDO_TURNO_FLAVIO_RELIGIAO,
        NOME_GRAFICO_SEGUNDO_TURNO_RENAN_RELIGIAO,
    ]
    for nome in nomes_fixos:
        for extensao in ("xlsx", "png"):
            caminho = pasta_saida / f"{nome}.{extensao}"
            if caminho.is_file():
                caminho.unlink()
    for extensao in ("xlsx", "png"):
        for caminho in pasta_saida.glob(f"Primeiro_Turno_Lula_vs_*_por_*.{extensao}"):
            if caminho.is_file():
                caminho.unlink()


def executar() -> Path:
    base, pasta_saida = localizar_base()
    governo = ler_aba(base, "Lula3", COLUNAS_GOVERNO)
    confrontos = ler_aba(base, "Confrontos", COLUNAS_CONFRONTOS)
    institutos = ler_aba(base, "Institutos", COLUNAS_INSTITUTOS)
    pesos = pesos_dos_institutos(institutos)

    governo = preparar(governo, ("otimo_bom_pct", "regular_pct", "ruim_pessimo_pct"), pesos)
    confrontos = preparar(confrontos, ("lula_pct", "adversario_pct"), pesos)
    governo_total = somente_brasil_total(governo)
    if governo_total.empty:
        raise ErroModeloB("Não há avaliação nacional total na aba Lula3.")

    composicao = {
        "Ótimo/Bom": exigir(suavizar(governo_total, "otimo_bom_pct", 30), "Ótimo/Bom"),
        "Regular": exigir(suavizar(governo_total, "regular_pct", 30), "Regular"),
        "Ruim/Péssimo": exigir(suavizar(governo_total, "ruim_pessimo_pct", 30), "Ruim/Péssimo"),
    }
    fonte_liquida = governo_total.loc[governo_total["otimo_bom_pct"].map(presente) & governo_total["ruim_pessimo_pct"].map(presente)].copy()
    fonte_liquida["avaliacao_liquida_pct"] = fonte_liquida["otimo_bom_pct"] - fonte_liquida["ruim_pessimo_pct"]
    liquida = exigir(
        suavizar(
            fonte_liquida,
            "avaliacao_liquida_pct",
            colunas_variancia=("otimo_bom_pct", "ruim_pessimo_pct"),
            limites=(-100.0, 100.0),
        ),
        "Avaliação líquida",
    )

    pasta_saida.mkdir(parents=True, exist_ok=True)
    limpar_saidas_geradas(pasta_saida)
    suavizados = pd.concat([serie.valores["estimativa_pct"].rename(nome) for nome, serie in composicao.items()], axis=1).sort_index()
    ic_baixo = pd.concat([serie.valores["ic_baixo_pct"].rename(nome) for nome, serie in composicao.items()], axis=1).sort_index()
    ic_alto = pd.concat([serie.valores["ic_alto_pct"].rename(nome) for nome, serie in composicao.items()], axis=1).sort_index()
    for tabela in (suavizados, ic_baixo, ic_alto):
        tabela.index.name = "data"
    diagnostico_governo = pd.concat(
        [serie.valores.reset_index().assign(serie=nome) for nome, serie in composicao.items()],
        ignore_index=True,
    )
    escrever_planilha(
        pasta_saida / f"{NOME_GRAFICO_GOVERNO}.xlsx",
        {
            "Estimativas": suavizados.reset_index(),
            "IC_Baixo": ic_baixo.reset_index(),
            "IC_Alto": ic_alto.reset_index(),
            "Diagnostico": diagnostico_governo,
            "Pesos_ultimo_ponto": juntar_pesos(composicao),
            "Metodologia": metodologia_modelo_b("Brasil, Total, avaliação do Governo Lula III."),
        },
        indice=False,
    )

    escrever_planilha(
        pasta_saida / f"{NOME_GRAFICO_LIQUIDO}.xlsx",
        {
            "Serie_Modelo_B": liquida.valores.reset_index(),
            "Pesos_ultimo_ponto": liquida.pesos_ultimo_ponto,
            "Metodologia": metodologia_modelo_b(
                "Brasil, Total, avaliação líquida do Governo Lula III.",
                "Avaliação líquida = Ótimo/Bom - Ruim/Péssimo; a incerteza usa a covariância multinomial entre as categorias.",
            ),
        },
        indice=False,
    )

    grafico_governo(composicao, pasta_saida / f"{NOME_GRAFICO_GOVERNO}.png")
    grafico_liquido(liquida, pasta_saida / f"{NOME_GRAFICO_LIQUIDO}.png")
    gerar_governo_por_sexo(governo, pasta_saida)
    cenarios = [
        ("Flavio", "flavio", NOME_GRAFICO_SEGUNDO_TURNO),
        ("Renan", "renan", NOME_GRAFICO_SEGUNDO_TURNO_RENAN),
        ("Caiado", "caiado", NOME_GRAFICO_SEGUNDO_TURNO_CAIADO),
    ]
    for nome_adversario, termo_adversario, nome_saida in cenarios:
        gerado = gerar_segundo_turno(confrontos, nome_adversario, termo_adversario, nome_saida, pasta_saida)
        if nome_adversario == "Flavio" and not gerado:
            raise ErroModeloB("A base não possui o cenário nacional, estimulado, de 2º turno Lula × Flávio.")
    aberturas_sexo = [
        ("Flávio", "flavio", NOME_GRAFICO_SEGUNDO_TURNO_FLAVIO_SEXO),
        ("Renan Santos", "renan", NOME_GRAFICO_SEGUNDO_TURNO_RENAN_SEXO),
    ]
    for nome_adversario, termo_adversario, nome_saida in aberturas_sexo:
        gerar_segundo_turno_por_abertura(
            confrontos, nome_adversario, termo_adversario, "Sexo", sexo_padronizado,
            ("Mulheres", "Homens"), "sexo", nome_saida, pasta_saida,
        )
    aberturas_religiao = [
        ("Flávio", "flavio", NOME_GRAFICO_SEGUNDO_TURNO_FLAVIO_RELIGIAO),
        ("Renan Santos", "renan", NOME_GRAFICO_SEGUNDO_TURNO_RENAN_RELIGIAO),
    ]
    for nome_adversario, termo_adversario, nome_saida in aberturas_religiao:
        gerar_segundo_turno_por_abertura(
            confrontos, nome_adversario, termo_adversario, "Religião", religiao_padronizada,
            ("Católicos", "Evangélicos", "Outras religiões", "Sem religião"), "religião", nome_saida, pasta_saida,
        )
    gerar_primeiro_turno(confrontos, pasta_saida)
    gerar_aberturas_primeiro_turno(confrontos, pasta_saida)
    return pasta_saida


if __name__ == "__main__":
    try:
        if "--explicar" in sys.argv:
            print(EXPLICACAO_MODELO_B)
        else:
            print(f"Resultados gerados em: {executar()}")
    except ErroModeloB as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        raise SystemExit(2)
    except PermissionError:
        print("Erro: feche a Base_nova_limpa.xlsx e as planilhas de resultado antes de rodar.", file=sys.stderr)
        raise SystemExit(2)
