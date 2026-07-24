"""MODELO A — agregador eleitoral oficial, portátil e autocontido.

COMO EXECUTAR
-------------
Abra um terminal na pasta deste arquivo e rode::

    python "MODELO A.PY"

O script procura ``Base_nova_limpa.xlsx`` ao lado dele ou na estrutura oficial
``ENTREGA_FINAL/CODIGOS/Modelo_A_Baseline_Oficial``. Os resultados são gravados
em ``RESULTADOS_ATUAIS/Modelo_A_Baseline_Oficial`` ao lado da base. Este arquivo
não importa, chama ou executa nenhum outro código local do projeto.

O QUE O PROGRAMA PRODUZ
-----------------------
1. Avaliação do governo: Ótimo/Bom, Regular e Ruim/Péssimo.
2. Avaliação líquida: Ótimo/Bom menos Ruim/Péssimo, em janelas de 15 e 30 dias.
3. Segundo turno Lula x Flávio, Renan e Caiado, em votos válidos e votos totais.
4. Primeiro turno harmonizado com Lula, Flávio, Renan Santos, Romeu Zema,
   Ronaldo Caiado e a resposta publicada Branco/Nulo/Não sei.
5. Aberturas por sexo, religião e renda quando a base possui cobertura mínima.

REGRAS METODOLÓGICAS CENTRAIS
------------------------------
- A ponderação replica o baseline legado: qualidade do instituto, recência
  linear e tamanho da amostra, com os expoentes definidos na função ``suavizar``.
- Tracking diário só entra depois de ser consolidado em semanas completas.
- Votos válidos reescalam apenas Lula e o adversário para somarem 100%.
- Votos totais preservam branco/nulo/indeciso no denominador.
- No primeiro turno, uma pesquisa entra uma vez por candidato: primeiro se faz
  a média dos cenários em que aquele candidato apareceu.
- Ausência de candidato ou grupo nunca vira zero.
- Branco/Nulo/Não sei vem literalmente da base; nenhum residual fecha 100%.

MAPA DO ARQUIVO
---------------
1. Dependências e constantes.
2. Leitura e validação das abas do Excel.
3. Padronização dos dados e pesos dos institutos.
4. Fórmula de suavização do Modelo A.
5. Seleção dos recortes eleitorais e demográficos.
6. Geração das planilhas e dos gráficos.
7. Função ``executar``, que coordena todo o processo.

DEPENDÊNCIAS
-------------
Se necessário, instale uma vez no outro computador::

    python -m pip install pandas numpy openpyxl matplotlib
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# =============================================================================
# 1. DEPENDÊNCIAS EXTERNAS
# Matplotlib usa o modo "Agg" para criar PNGs sem precisar abrir uma janela.
# =============================================================================
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


# =============================================================================
# 2. CONSTANTES E CONTRATOS DA ENTREGA
# Estes valores concentram a metodologia fixa, os nomes dos outputs e as
# colunas obrigatórias. Alterá-los pode mudar resultados ou quebrar a base.
# =============================================================================

# Parâmetros recuperados do agregador legado.
Z_95 = 1.959963984540054
PESO_INSTITUTO_DESCONHECIDO = 0.5
AMOSTRA_MAXIMA = 5000.0
AMOSTRA_FALLBACK = 600.0

# Paleta institucional simples e consistente entre todos os produtos.
COR_LULA = "#C62828"
COR_ADVERSARIO = "#1565C0"
COR_OTIMO = "#2E7D32"
COR_REGULAR = "#F9A825"
COR_RUIM = "#C62828"
COR_TEXTO = "#303030"
COR_GRADE = "#B0B0B0"

# Nomes estáveis dos arquivos que serão entregues ao time.
NOME_GRAFICO_GOVERNO = "01_Avaliacao_do_Governo"
NOME_GRAFICO_LIQUIDO = "02_Avaliacao_Liquida_do_Governo"
NOME_GRAFICO_SEGUNDO_TURNO = "03_Segundo_Turno_Lula_vs_Flavio"
NOME_GRAFICO_SEGUNDO_TURNO_RENAN = "04_Segundo_Turno_Lula_vs_Renan"
NOME_GRAFICO_SEGUNDO_TURNO_CAIADO = "05_Segundo_Turno_Lula_vs_Caiado"
NOME_GRAFICO_SEGUNDO_TURNO_TOTAIS = "03_Segundo_Turno_Lula_vs_Flavio_Votos_Totais"
NOME_GRAFICO_SEGUNDO_TURNO_RENAN_TOTAIS = "04_Segundo_Turno_Lula_vs_Renan_Votos_Totais"
NOME_GRAFICO_SEGUNDO_TURNO_CAIADO_TOTAIS = "05_Segundo_Turno_Lula_vs_Caiado_Votos_Totais"
NOME_GRAFICO_PRIMEIRO_TURNO = "06_Primeiro_Turno_Media_Harmonizada_Cenarios"
NOME_GRAFICO_GOVERNO_SEXO = "07_Avaliacao_do_Governo_por_Sexo"
NOME_GRAFICO_LIQUIDO_SEXO = "08_Avaliacao_Liquida_do_Governo_por_Sexo"
NOME_GRAFICO_SEGUNDO_TURNO_FLAVIO_SEXO = "09_Segundo_Turno_Lula_vs_Flavio_por_Sexo"
NOME_GRAFICO_SEGUNDO_TURNO_RENAN_SEXO = "10_Segundo_Turno_Lula_vs_Renan_por_Sexo"
NOME_GRAFICO_SEGUNDO_TURNO_FLAVIO_RELIGIAO = "11_Segundo_Turno_Lula_vs_Flavio_por_Religiao"
NOME_GRAFICO_SEGUNDO_TURNO_RENAN_RELIGIAO = "12_Segundo_Turno_Lula_vs_Renan_por_Religiao"
NOME_GRAFICO_SEGUNDO_TURNO_CAIADO_SEXO = "13_Segundo_Turno_Lula_vs_Caiado_por_Sexo"
NOME_GRAFICO_SEGUNDO_TURNO_CAIADO_RELIGIAO = "14_Segundo_Turno_Lula_vs_Caiado_por_Religiao"

# Versões antigas deste produto são removidas para não coexistirem com a atual.
NOMES_OBSOLETOS_PRIMEIRO_TURNO = [
    "06_Primeiro_Turno_Cenario_Com_Flavio.xlsx",
    "06_Primeiro_Turno_Cenario_Com_Flavio.png",
]

# Séries do gráfico nacional de primeiro turno e candidatos dos pares por grupo.
ROTULO_NAO_VOTO_PRIMEIRO_TURNO = "Branco/Nulo/Não sei"
CANDIDATOS_PRIMEIRO_TURNO = [
    "Lula", "Flávio", "Renan Santos", "Romeu Zema", "Ronaldo Caiado",
    ROTULO_NAO_VOTO_PRIMEIRO_TURNO,
]
CANDIDATOS_PRIMEIRO_TURNO_PARES = [
    "Flávio", "Renan Santos", "Romeu Zema", "Ronaldo Caiado",
]
CANDIDATOS_PRIMEIRO_TURNO_NORMALIZADOS = {texto for texto in (
    "lula", "flavio", "renan santos", "romeu zema", "ronaldo caiado",
)}
CANDIDATOS_PRIMEIRO_TURNO_ADVERSARIOS = CANDIDATOS_PRIMEIRO_TURNO_NORMALIZADOS.difference({"lula"})

# Cabeçalhos mínimos esperados em cada aba. A ordem visual no Excel não importa.
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


# =============================================================================
# 3. TIPOS DE DADOS E ERROS CONTROLADOS
# =============================================================================
class ErroModeloA(ValueError):
    """Erro de base ou de estrutura que impede a geração dos resultados."""


@dataclass(frozen=True)
class SerieSuavizada:
    """Agrupa a curva calculada e os pontos publicados usados para calculá-la."""

    valores: pd.DataFrame
    pontos_publicados: pd.DataFrame


# =============================================================================
# 4. FUNÇÕES BÁSICAS DE TEXTO E VALORES AUSENTES
# =============================================================================
def presente(valor: object) -> bool:
    """Retorna ``True`` somente para valores realmente preenchidos."""

    if valor is None:
        return False
    if isinstance(valor, str):
        return bool(valor.strip())
    try:
        return not bool(pd.isna(valor))
    except (TypeError, ValueError):
        return True


def texto_normalizado(valor: object) -> str:
    """Remove acentos e pontuação para comparações tolerantes de rótulos."""

    if not presente(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor).strip()).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


# =============================================================================
# 5. LOCALIZAÇÃO E LEITURA DA BASE EXCEL
# =============================================================================
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
            return candidato, candidato.parent / "RESULTADOS_ATUAIS" / "Modelo_A_Baseline_Oficial"
    locais = "\n".join(f"- {candidato}" for candidato in candidatos)
    raise ErroModeloA(
        "Não encontrei Base_nova_limpa.xlsx. Deixe a base nesta pasta ou mantenha a "
        "estrutura ENTREGA_FINAL/CODIGOS/Modelo_A_Baseline_Oficial. Procurei em:\n" + locais
    )


def localizar_cabecalho(planilha_bruta: pd.DataFrame, obrigatorias: list[str], nome_aba: str) -> int:
    """Encontra a linha real do cabeçalho, mesmo que existam instruções acima."""

    alvo = set(obrigatorias)
    for posicao in range(len(planilha_bruta)):
        cabecalhos = {
            texto_normalizado(valor).replace(" ", "_")
            for valor in planilha_bruta.iloc[posicao].tolist()
        }
        if alvo.issubset(cabecalhos):
            return posicao
    raise ErroModeloA(
        f"Não foi localizado o cabeçalho operacional da aba '{nome_aba}'. "
        f"Campos esperados: {', '.join(obrigatorias[:4])}..."
    )


def ler_aba(caminho_base: Path, nome_aba: str, obrigatorias: list[str]) -> pd.DataFrame:
    """Lê uma aba, localiza seu cabeçalho e devolve apenas linhas preenchidas."""

    try:
        bruto = pd.read_excel(caminho_base, sheet_name=nome_aba, header=None, dtype=object, engine="openpyxl")
    except ValueError as erro:
        raise ErroModeloA(f"Aba obrigatória ausente: '{nome_aba}'.") from erro
    indice_cabecalho = localizar_cabecalho(bruto, obrigatorias, nome_aba)
    cabecalhos = [texto_normalizado(valor).replace(" ", "_") for valor in bruto.iloc[indice_cabecalho].tolist()]
    dados = bruto.iloc[indice_cabecalho + 1 :].copy()
    dados.columns = cabecalhos
    dados = dados.loc[dados[obrigatorias].apply(lambda linha: any(presente(valor) for valor in linha), axis=1)].copy()
    # A linha é calculada automaticamente para que qualquer erro possa ser
    # localizado no Excel sem exigir que o operador preencha IDs técnicos.
    dados["_linha_excel"] = [int(indice) + 1 for indice in dados.index]
    return dados.reset_index(drop=True)


def validar_base(
    governo: pd.DataFrame,
    confrontos: pd.DataFrame,
    institutos: pd.DataFrame,
) -> pd.DataFrame:
    """Valida a entrada antes de qualquer publicação e devolve alertas auditáveis.

    Erros objetivos interrompem a execução. Situações que podem ser legítimas,
    como duas pesquisas do mesmo instituto na mesma data, permanecem na base e
    são registradas como alerta para conferência humana.
    """

    problemas: list[dict[str, object]] = []

    def registrar(severidade: str, aba: str, linha: object, campo: str, mensagem: str) -> None:
        problemas.append(
            {
                "severidade": severidade,
                "aba": aba,
                "linha_excel": linha,
                "campo": campo,
                "mensagem": mensagem,
            }
        )

    # Alias duplicado entre institutos é ambíguo e não pode ser resolvido
    # silenciosamente escolhendo a última linha do cadastro.
    donos_alias: dict[str, tuple[str, object]] = {}
    for _, linha in institutos.iterrows():
        nome = str(linha["instituto"]).strip() if presente(linha["instituto"]) else ""
        linha_excel = linha.get("_linha_excel", "")
        if not nome:
            registrar("ERRO", "Institutos", linha_excel, "instituto", "Instituto vazio no cadastro.")
            continue
        for alias in [nome, *str(linha["aliases"] if presente(linha["aliases"]) else "").split(";")]:
            chave = texto_normalizado(alias)
            if not chave:
                continue
            if chave in donos_alias and donos_alias[chave][0] != nome:
                registrar(
                    "ERRO",
                    "Institutos",
                    linha_excel,
                    "aliases",
                    f"O alias '{alias.strip()}' também pertence a {donos_alias[chave][0]}.",
                )
            else:
                donos_alias[chave] = (nome, linha_excel)

        peso = pd.to_numeric(linha["peso_legacy"], errors="coerce")
        if presente(linha["peso_legacy"]) and (pd.isna(peso) or not 0 <= float(peso) <= 1):
            registrar("ERRO", "Institutos", linha_excel, "peso_legacy", "Peso deve estar entre 0 e 1.")
        if not presente(linha["peso_legacy"]):
            registrar(
                "ALERTA",
                "Institutos",
                linha_excel,
                "peso_legacy",
                f"{nome} usa o peso provisório {PESO_INSTITUTO_DESCONHECIDO:.2f} do Modelo A.",
            )

    def validar_tabela(
        frame: pd.DataFrame,
        aba: str,
        campos_chave: tuple[str, ...],
        percentuais: tuple[str, ...],
    ) -> None:
        for _, linha in frame.iterrows():
            linha_excel = linha.get("_linha_excel", "")
            for campo in campos_chave:
                if not presente(linha[campo]):
                    registrar("ERRO", aba, linha_excel, campo, "Campo obrigatório vazio.")
            data = pd.to_datetime(linha["data_referencia"], errors="coerce")
            if pd.isna(data):
                registrar("ERRO", aba, linha_excel, "data_referencia", "Data inválida.")
            for campo in percentuais:
                if not presente(linha[campo]):
                    continue
                valor = pd.to_numeric(linha[campo], errors="coerce")
                if pd.isna(valor) or not 0 <= float(valor) <= 100:
                    registrar("ERRO", aba, linha_excel, campo, "Percentual deve estar entre 0 e 100.")
            total = pd.to_numeric(linha["amostra_total"], errors="coerce")
            segmento = pd.to_numeric(linha["amostra_segmento"], errors="coerce")
            if presente(linha["amostra_total"]) and (pd.isna(total) or float(total) <= 0):
                registrar("ERRO", aba, linha_excel, "amostra_total", "Amostra deve ser positiva.")
            if presente(linha["amostra_segmento"]) and (pd.isna(segmento) or float(segmento) <= 0):
                registrar("ERRO", aba, linha_excel, "amostra_segmento", "Amostra deve ser positiva.")
            if presente(total) and presente(segmento) and float(segmento) > float(total):
                registrar("ERRO", aba, linha_excel, "amostra_segmento", "Amostra do segmento supera a amostra total.")

    validar_tabela(
        governo,
        "Lula3",
        ("data_referencia", "instituto", "tipo_pesquisa", "frequencia_original", "nivel_geografico", "geografia", "segmento_tipo", "segmento"),
        ("otimo_bom_pct", "regular_pct", "ruim_pessimo_pct"),
    )
    validar_tabela(
        confrontos,
        "Confrontos",
        (
            "data_referencia", "instituto", "tipo_pesquisa", "frequencia_original", "turno",
            "tipo_cenario", "cenario", "adversario", "nivel_geografico", "geografia",
            "segmento_tipo", "segmento", "base_voto",
        ),
        ("lula_pct", "adversario_pct", "outros_candidatos_pct", "brancos_nulos_indecisos_pct"),
    )

    # Ausência de amostra não invalida uma observação publicada, mas muda o
    # peso e a faixa amostral. O relatório torna esse fallback visível.
    for aba, frame in (("Lula3", governo), ("Confrontos", confrontos)):
        sem_total = int(frame["amostra_total"].map(lambda valor: not presente(valor)).sum())
        segmentadas = frame.loc[~frame["segmento_tipo"].map(texto_normalizado).eq("total")]
        sem_segmento = int(segmentadas["amostra_segmento"].map(lambda valor: not presente(valor)).sum())
        if sem_total:
            registrar(
                "ALERTA", aba, "várias", "amostra_total",
                f"{sem_total} linha(s) sem amostra total usarão fallback quando entrarem em um produto.",
            )
        if sem_segmento:
            registrar(
                "ALERTA", aba, "várias", "amostra_segmento",
                f"{sem_segmento} linha(s) segmentada(s) sem amostra própria usarão fallback conservador quando entrarem.",
            )

    # Duplicata exata é erro; colisão de chave com valores diferentes é alerta.
    colunas_operacionais = [coluna for coluna in COLUNAS_GOVERNO if coluna in governo]
    duplicadas_governo = governo.duplicated(colunas_operacionais, keep=False)
    for _, linha in governo.loc[duplicadas_governo].iterrows():
        registrar("ERRO", "Lula3", linha["_linha_excel"], "linha", "Duplicata exata.")
    colunas_operacionais = [coluna for coluna in COLUNAS_CONFRONTOS if coluna in confrontos]
    duplicadas_confrontos = confrontos.duplicated(colunas_operacionais, keep=False)
    for _, linha in confrontos.loc[duplicadas_confrontos].iterrows():
        registrar("ERRO", "Confrontos", linha["_linha_excel"], "linha", "Duplicata exata.")

    chave_colisao = [
        "data_referencia", "instituto", "tipo_pesquisa", "frequencia_original", "turno",
        "tipo_cenario", "cenario", "adversario", "nivel_geografico", "geografia",
        "segmento_tipo", "segmento", "base_voto",
    ]
    for _, grupo in confrontos.groupby(chave_colisao, dropna=False, sort=False):
        if len(grupo) <= 1 or grupo[COLUNAS_CONFRONTOS].drop_duplicates().shape[0] <= 1:
            continue
        linhas = ", ".join(map(str, sorted(grupo["_linha_excel"].astype(int))))
        registrar(
            "ALERTA",
            "Confrontos",
            linhas,
            "chave_da_pesquisa",
            "Mais de uma linha compartilha a mesma chave, mas os valores diferem; todas foram preservadas.",
        )

    # Categorias incompatíveis com a função de cada campo não devem sumir em filtros.
    for _, linha in confrontos.iterrows():
        if texto_normalizado(linha["base_voto"]) not in {"totais", "validos"}:
            registrar("ERRO", "Confrontos", linha["_linha_excel"], "base_voto", "Use Totais ou Validos.")
    for aba, frame in (("Lula3", governo), ("Confrontos", confrontos)):
        for _, linha in frame.iterrows():
            if texto_normalizado(linha["nivel_geografico"]) == "brasil" and texto_normalizado(linha["geografia"]) != "brasil":
                registrar("ERRO", aba, linha["_linha_excel"], "geografia", "Nível Brasil exige geografia Brasil.")
            if texto_normalizado(linha["segmento_tipo"]) == "total" and texto_normalizado(linha["segmento"]) != "total":
                registrar("ERRO", aba, linha["_linha_excel"], "segmento", "Segmento_tipo Total exige segmento Total.")

    resultado = pd.DataFrame(
        problemas,
        columns=["severidade", "aba", "linha_excel", "campo", "mensagem"],
    )
    erros = resultado.loc[resultado["severidade"].eq("ERRO")]
    if not erros.empty:
        resumo = "\n".join(
            f"- {linha.aba}, linha {linha.linha_excel}, {linha.campo}: {linha.mensagem}"
            for linha in erros.head(12).itertuples()
        )
        complemento = "" if len(erros) <= 12 else f"\n- ... e mais {len(erros) - 12} erro(s)."
        raise ErroModeloA(f"A base possui {len(erros)} erro(s) bloqueante(s):\n{resumo}{complemento}")
    return resultado


# =============================================================================
# 6. PREPARAÇÃO DOS DADOS E FÓRMULA DO MODELO A
# =============================================================================
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
    """Padroniza datas, números e componentes de peso sem alterar a planilha."""
    resultado = frame.copy()
    resultado["data_referencia"] = pd.to_datetime(resultado["data_referencia"], errors="coerce").dt.normalize()
    resultado = resultado.loc[resultado["data_referencia"].notna()].copy()
    for coluna in colunas_valor:
        resultado[coluna] = pd.to_numeric(resultado[coluna], errors="coerce")
    for coluna in ["amostra_total", "amostra_segmento"]:
        resultado[coluna] = pd.to_numeric(resultado[coluna], errors="coerce")
    resultado["peso_legacy"] = resultado["instituto"].map(
        lambda valor: pesos.get(texto_normalizado(valor), PESO_INSTITUTO_DESCONHECIDO)
    )
    return resultado


def amostra_utilizada(linha: pd.Series) -> float:
    """Escolhe a amostra usada no peso e na faixa, com fallback conservador.

    Para o total, prioriza ``amostra_segmento`` e depois ``amostra_total``.
    Para uma abertura, nunca herda toda a amostra como se fosse o tamanho real
    do grupo: na falta da amostra publicada do segmento, limita o fallback a 300.
    """

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


def suavizar(
    frame: pd.DataFrame,
    coluna_valor: str,
    janela_dias: int,
    colunas_variancia: tuple[str, ...] | None = None,
    limites: tuple[float, float] | None = (0.0, 100.0),
) -> SerieSuavizada:
    """Replica a média ponderada e a faixa amostral do agregador legado.

    Para cada data publicada, entram observações dos ``janela_dias`` anteriores.
    O peso bruto de cada observação é::

        qualidade**0,50 * recência_linear**0,25 * amostra_relativa**0,25

    Depois os pesos são normalizados para somar 1. A faixa usa 1,96 erros-padrão
    e combina os pesos com a variância amostral das proporções informadas. Ela
    não incorpora efeitos de instituto, desenho amostral ou heterogeneidade.
    """
    preparado = frame.copy()
    preparado["data_referencia"] = pd.to_datetime(preparado["data_referencia"], errors="coerce").dt.normalize()
    preparado = preparado.loc[preparado["data_referencia"].notna()].copy()
    for coluna in {coluna_valor, *(colunas_variancia or (coluna_valor,))}:
        preparado[coluna] = pd.to_numeric(preparado[coluna], errors="coerce")
    preparado["_amostra_usada"] = preparado.apply(amostra_utilizada, axis=1)
    preparado["_qualidade"] = pd.to_numeric(preparado["peso_legacy"], errors="coerce").fillna(PESO_INSTITUTO_DESCONHECIDO)
    preparado["_amostra_relativa"] = np.minimum(preparado["_amostra_usada"].astype(float), AMOSTRA_MAXIMA) / AMOSTRA_MAXIMA

    pontos = preparado.loc[preparado[coluna_valor].notna(), ["data_referencia", coluna_valor]].copy()
    pontos = pontos.rename(columns={coluna_valor: "valor_pct"}).sort_values("data_referencia")
    if pontos.empty:
        vazio = pd.DataFrame(columns=["estimativa_pct", "ic_baixo_pct", "ic_alto_pct", "se_pp"])
        return SerieSuavizada(vazio, pontos)

    validos = preparado.loc[preparado[coluna_valor].notna()].copy()
    datas = validos["data_referencia"].to_numpy(dtype="datetime64[D]").astype("int64")
    valores = validos[coluna_valor].to_numpy(dtype=float)
    qualidade = validos["_qualidade"].to_numpy(dtype=float)
    amostra_relativa = validos["_amostra_relativa"].to_numpy(dtype=float)
    amostra = validos["_amostra_usada"].to_numpy(dtype=float)
    variancia = np.zeros(len(validos), dtype=float)
    for coluna in colunas_variancia or (coluna_valor,):
        proporcao = validos[coluna].to_numpy(dtype=float) / 100
        variancia += proporcao * (1 - proporcao)

    registros: list[dict[str, float | pd.Timestamp]] = []
    for referencia in np.unique(datas):
        idades = referencia - datas
        selecionados = np.flatnonzero((idades >= 0) & (idades <= janela_dias))
        if not len(selecionados):
            continue
        componente_tempo = np.maximum(0.0, 1 - idades[selecionados] / janela_dias)
        peso_bruto = (
            qualidade[selecionados] ** 0.50
            * componente_tempo ** 0.25
            * amostra_relativa[selecionados] ** 0.25
        )
        positivos = peso_bruto > 0
        selecionados, peso_bruto = selecionados[positivos], peso_bruto[positivos]
        if not len(selecionados):
            continue
        peso = peso_bruto / peso_bruto.sum()
        estimativa = float(np.sum(peso * valores[selecionados]))
        erro_padrao = float(np.sqrt(np.sum(peso ** 2 * variancia[selecionados] / amostra[selecionados])) * 100)
        inferior, superior = estimativa - Z_95 * erro_padrao, estimativa + Z_95 * erro_padrao
        if limites is not None:
            inferior, superior = max(limites[0], inferior), min(limites[1], superior)
        registros.append(
            {
                "data": pd.Timestamp(np.datetime64(int(referencia), "D")),
                "estimativa_pct": estimativa,
                "ic_baixo_pct": inferior,
                "ic_alto_pct": superior,
                "se_pp": erro_padrao,
            }
        )
    return SerieSuavizada(pd.DataFrame.from_records(registros).set_index("data"), pontos)


# =============================================================================
# 7. FILTROS GEOGRÁFICOS E PADRONIZAÇÃO DAS ABERTURAS
# As funções abaixo só unem grafias equivalentes; nunca inventam grupos.
# =============================================================================
def somente_brasil_total(frame: pd.DataFrame) -> pd.DataFrame:
    """Mantém apenas linhas nacionais cujo segmento publicado é Total."""

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
    """Seleciona um confronto nacional/Total de 2º turno em votos totais.

    A base de origem permanece em votos totais. A conversão opcional para votos
    válidos ocorre depois, na função ``votos_validos``.
    """

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


# =============================================================================
# 8. PREPARAÇÃO DOS CENÁRIOS ELEITORAIS
# =============================================================================
def consolidar_tracking_diario(
    tracking_diario: pd.DataFrame,
    grupos: list[str],
    valores: list[str],
) -> pd.DataFrame:
    """Consolida tracking diário em ondas semanais completas, encerradas no domingo.

    A regra reproduz a preparação do legado: somente blocos com sete datas
    publicadas entram no agregado. Linhas diárias nunca são tratadas como sete
    pesquisas independentes dentro da janela do Modelo A.
    """

    if tracking_diario.empty:
        return tracking_diario.copy()
    registros: list[dict[object, object]] = []
    for _, curva in tracking_diario.groupby(grupos, dropna=False, sort=False):
        curva = curva.sort_values("data_referencia").copy()
        # Mais de uma linha no mesmo dia tornaria a regra de sete observações
        # ambígua. A validação registra a colisão; aqui usamos a média diária
        # apenas para impedir que a duplicata fabrique uma semana completa.
        numerica_diaria = (
            curva.set_index("data_referencia")[valores]
            .apply(pd.to_numeric, errors="coerce")
            .groupby(level=0, sort=True)
            .mean()
        )
        semanal = numerica_diaria.resample("W-SUN").mean()
        dias_publicados = numerica_diaria.resample("W-SUN").size()
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


def tracking_semanal(tracking_diario: pd.DataFrame) -> pd.DataFrame:
    """Aplica a consolidação semanal aos confrontos eleitorais."""

    grupos = [
        "instituto", "turno", "tipo_cenario", "cenario", "adversario", "nivel_geografico",
        "geografia", "segmento_tipo", "segmento", "base_voto", "tipo_pesquisa",
    ]
    valores = [
        "lula_pct", "adversario_pct", "outros_candidatos_pct", "brancos_nulos_indecisos_pct",
        "amostra_total", "amostra_segmento", "peso_legacy",
    ]
    return consolidar_tracking_diario(tracking_diario, grupos, valores)


def preparar_governo(linhas: pd.DataFrame) -> pd.DataFrame:
    """Combina pesquisas regulares e tracking semanal para a avaliação do governo."""

    regular = linhas.loc[linhas["tipo_pesquisa"].map(texto_normalizado).eq("regular")].copy()
    tracking = linhas.loc[linhas["tipo_pesquisa"].map(texto_normalizado).eq("tracking")].copy()
    diario = tracking.loc[tracking["frequencia_original"].map(texto_normalizado).eq("diaria")].copy()
    nao_diario = tracking.loc[~tracking["frequencia_original"].map(texto_normalizado).eq("diaria")].copy()
    grupos = [
        "instituto", "nivel_geografico", "geografia", "segmento_tipo", "segmento", "tipo_pesquisa",
    ]
    valores = [
        "otimo_bom_pct", "regular_pct", "ruim_pessimo_pct",
        "amostra_total", "amostra_segmento", "peso_legacy",
    ]
    semanal = consolidar_tracking_diario(diario, grupos, valores)
    return pd.concat([regular, semanal, nao_diario], ignore_index=True).sort_values("data_referencia")


def preparar_segundo_turno(linhas: pd.DataFrame) -> pd.DataFrame:
    """Combina pesquisas regulares, tracking semanal e tracking não diário.

    Leituras diárias não entram como pesquisas independentes: somente semanas
    completas com sete dias publicados são consolidadas e aproveitadas.
    """

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
    linhas["brancos_nulos_indecisos_pct"] = pd.to_numeric(
        linhas["brancos_nulos_indecisos_pct"], errors="coerce"
    )

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
    # A resposta não-voto também se repete nas linhas de um mesmo cenário.
    # Ela é lida literalmente da base: não usamos residual nem completamos 100%.
    nao_voto_por_cenario = (
        linhas.loc[linhas["brancos_nulos_indecisos_pct"].notna()]
        .sort_values(chaves_cenario + ["adversario"])
        .drop_duplicates(chaves_cenario, keep="first")
        .copy()
    )
    nao_voto_por_cenario = nao_voto_por_cenario.assign(
        candidato=ROTULO_NAO_VOTO_PRIMEIRO_TURNO,
        valor_pct=nao_voto_por_cenario["brancos_nulos_indecisos_pct"],
    )
    adversarios_por_cenario = linhas.loc[linhas["adversario_pct"].notna()].copy()
    adversarios_por_cenario = adversarios_por_cenario.assign(
        candidato=adversarios_por_cenario["adversario"], valor_pct=adversarios_por_cenario["adversario_pct"]
    )
    manter = [*chaves, "cenario", "candidato", "valor_pct", "peso_legacy", "amostra_total", "amostra_segmento"]
    por_cenario = pd.concat(
        [lula_por_cenario[manter], adversarios_por_cenario[manter], nao_voto_por_cenario[manter]],
        ignore_index=True,
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
        )
        .reset_index()
        .sort_values(["data_referencia", "candidato", "instituto"])
        .reset_index(drop=True)
    )
    return linhas, pontos


def votos_validos(linhas: pd.DataFrame) -> pd.DataFrame:
    """Reescala Lula e o adversário para somarem 100% dos votos válidos."""

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
    """Interrompe a execução se uma série obrigatória ficou sem observações."""

    if serie.valores.empty:
        raise ErroModeloA(f"Não há observações válidas para gerar '{nome}'.")
    return serie


# =============================================================================
# 9. PUBLICAÇÃO DE PLANILHAS E GRÁFICOS NACIONAIS
# =============================================================================
def escrever_planilha(caminho: Path, abas: dict[str, pd.DataFrame], indice: bool = True) -> None:
    """Grava um XLSX auditável, preservando datas e índices temporais.

    O parâmetro ``indice`` é mantido por compatibilidade interna, mas a decisão
    final é automática: índices temporais ou explicitamente nomeados viram uma
    coluna visível; qualquer índice técnico do pandas é descartado.
    """

    with pd.ExcelWriter(caminho, engine="openpyxl", datetime_format="yyyy-mm-dd", date_format="yyyy-mm-dd") as escritor:
        for nome_aba, tabela in abas.items():
            indice_significativo = isinstance(tabela.index, pd.DatetimeIndex) or tabela.index.name is not None
            tabela.to_excel(escritor, sheet_name=nome_aba, index=indice_significativo)
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    livro = load_workbook(caminho)
    for aba in livro.worksheets:
        aba.freeze_panes = "A2"
        aba.sheet_view.showGridLines = False
        aba.auto_filter.ref = aba.dimensions if aba.max_row > 1 else None
        aba.row_dimensions[1].height = 24
        preenchimento = PatternFill("solid", fgColor="1F4E78")
        fonte = Font(color="FFFFFF", bold=True)
        borda = Border(bottom=Side(style="thin", color="A6A6A6"))
        for celula in aba[1]:
            celula.fill = preenchimento
            celula.font = fonte
            celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            celula.border = borda
        for linha in aba.iter_rows():
            for celula in linha:
                if hasattr(celula.value, "year") and hasattr(celula.value, "month") and hasattr(celula.value, "day"):
                    celula.number_format = "yyyy-mm-dd"
                elif isinstance(celula.value, float):
                    celula.number_format = "0.00"
        # Larguras são calculadas sobre o conteúdo real e limitadas para que
        # textos longos não tornem a aba impraticável.
        for coluna in aba.columns:
            letra = coluna[0].column_letter
            cabecalho = str(coluna[0].value or "")
            maior = max(
                [len(cabecalho), *[len(str(celula.value)) for celula in coluna[1:201] if celula.value is not None]],
                default=len(cabecalho),
            )
            largura = min(max(maior + 2, 11), 42)
            if texto_normalizado(cabecalho) in {"descricao", "mensagem", "institutos", "rotulos publicados"}:
                largura = min(max(largura, 32), 72)
                for celula in coluna[1:]:
                    celula.alignment = Alignment(vertical="top", wrap_text=True)
            aba.column_dimensions[letra].width = largura
    livro.save(caminho)


def percentual_pt(valor: float, sufixo: str = "%") -> str:
    """Formata percentuais para apresentação em Português-BR."""

    return f"{float(valor):.1f}".replace(".", ",") + sufixo


def estilizar_eixo(eixo) -> None:
    """Aplica uma identidade visual discreta e consistente."""

    eixo.grid(True, axis="y", color=COR_GRADE, alpha=0.28, linewidth=0.8)
    eixo.grid(False, axis="x")
    eixo.spines["top"].set_visible(False)
    eixo.spines["right"].set_visible(False)
    eixo.tick_params(colors=COR_TEXTO)


def adicionar_rotulos_finais(
    eixo,
    itens: list[tuple[str, str, pd.Timestamp, float]],
    sufixo: str = "%",
) -> None:
    """Escreve rótulos diretos no último ponto e evita sobreposições."""

    itens = [item for item in itens if presente(item[3])]
    if not itens:
        return
    datas = [pd.Timestamp(item[2]) for item in itens]
    inicio, fim = min(datas), max(datas)
    limite_atual = eixo.get_xlim()
    inicio_eixo = pd.Timestamp(mdates.num2date(limite_atual[0])).tz_localize(None)
    fim_eixo = pd.Timestamp(mdates.num2date(limite_atual[1])).tz_localize(None)
    inicio = min(inicio, inicio_eixo)
    fim = max(fim, fim_eixo)
    amplitude_dias = max((fim - inicio).days, 30)
    data_rotulo = max(datas) + pd.Timedelta(days=max(4, int(amplitude_dias * 0.035)))
    extensao_dias = min(max(12, int(amplitude_dias * 0.13)), 75)
    eixo.set_xlim(inicio, max(datas) + pd.Timedelta(days=extensao_dias))

    inferior, superior = eixo.get_ylim()
    separacao = max((superior - inferior) * 0.035, 0.8)
    ordenados = sorted(enumerate(itens), key=lambda par: par[1][3])
    posicoes: dict[int, float] = {}
    anterior = inferior - separacao
    for indice_item, (_, _, _, valor) in ordenados:
        ajustado = max(float(valor), anterior + separacao)
        posicoes[indice_item] = ajustado
        anterior = ajustado
    excesso = max(posicoes.values()) - (superior - separacao * 0.30)
    if excesso > 0:
        posicoes = {indice_item: valor - excesso for indice_item, valor in posicoes.items()}

    for indice_item, (rotulo, cor, data, valor) in enumerate(itens):
        y_rotulo = posicoes[indice_item]
        eixo.plot([pd.Timestamp(data), data_rotulo], [valor, y_rotulo], color=cor, linewidth=0.8, alpha=0.65)
        eixo.text(
            data_rotulo,
            y_rotulo,
            f"{rotulo} {percentual_pt(valor, sufixo)}",
            color=cor,
            fontsize=9.5,
            fontweight="bold",
            va="center",
            ha="left",
        )


def texto_atualizacao(datas: Iterable[pd.Timestamp]) -> str:
    """Retorna a data mais recente no formato usado nos rodapés."""

    data = max(pd.Timestamp(valor) for valor in datas)
    return data.strftime("%d/%m/%Y")


def rotulo_curto_candidato(nome: str) -> str:
    """Encurta apenas o rótulo final em painéis, preservando o nome no título."""

    chave = texto_normalizado(nome)
    if "flavio" in chave:
        return "Flávio"
    if "renan" in chave:
        return "Renan"
    if "zema" in chave:
        return "Zema"
    if "caiado" in chave:
        return "Caiado"
    return nome


def grafico_governo(series: dict[str, SerieSuavizada], caminho: Path) -> None:
    """Desenha a composição nacional da avaliação do governo."""

    cores = {"Ótimo/Bom": COR_OTIMO, "Regular": COR_REGULAR, "Ruim/Péssimo": COR_RUIM}
    figura, eixo = plt.subplots(figsize=(16, 8))
    rotulos_finais: list[tuple[str, str, pd.Timestamp, float]] = []
    for rotulo, serie in series.items():
        if not serie.pontos_publicados.empty:
            eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color=cores[rotulo], alpha=0.22, s=22)
        eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cores[rotulo], linewidth=2.4)
        eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cores[rotulo], alpha=0.12)
        ultimo = serie.valores.iloc[-1]
        rotulos_finais.append((rotulo, cores[rotulo], serie.valores.index[-1], float(ultimo["estimativa_pct"])))
    limites = pd.concat([serie.valores[["ic_baixo_pct", "ic_alto_pct"]] for serie in series.values()])
    inferior = max(0.0, float(np.floor((limites["ic_baixo_pct"].min() - 3) / 5) * 5))
    superior = min(100.0, float(np.ceil((limites["ic_alto_pct"].max() + 3) / 5) * 5))
    eixo.set_ylim(inferior, superior)
    eixo.set_title("Avaliação do Governo Lula III\nMédia ponderada de 30 dias", fontsize=17, pad=14)
    eixo.set_xlabel("Data")
    eixo.set_ylabel("Percentual")
    estilizar_eixo(eixo)
    eixo.set_xlim(pd.Timestamp("2023-02-01"), None)
    adicionar_rotulos_finais(eixo, rotulos_finais)
    figura.text(
        0.01,
        0.02,
        f"Atualizado até {texto_atualizacao([serie.valores.index[-1] for serie in series.values()])}. "
        "Faixas: intervalo amostral aproximado do baseline; não incluem heterogeneidade entre pesquisas.",
        ha="left",
        fontsize=9,
        color="#555555",
    )
    figura.subplots_adjust(left=0.07, right=0.96, bottom=0.13, top=0.87)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def grafico_liquido(serie_15: SerieSuavizada, serie_30: SerieSuavizada, caminho: Path) -> None:
    """Compara a avaliação líquida suavizada em janelas de 15 e 30 dias."""

    figura, eixo = plt.subplots(figsize=(14, 7))
    eixo.scatter(serie_15.pontos_publicados["data_referencia"], serie_15.pontos_publicados["valor_pct"], color="#757575", alpha=0.25, s=20)
    rotulos_finais: list[tuple[str, str, pd.Timestamp, float]] = []
    for rotulo, cor, estilo, serie in [("15 dias", COR_ADVERSARIO, "--", serie_15), ("30 dias", COR_LULA, "-", serie_30)]:
        eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2.3, linestyle=estilo, label=rotulo)
        eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cor, alpha=0.10)
        ultimo = serie.valores.iloc[-1]
        rotulos_finais.append((rotulo, cor, serie.valores.index[-1], float(ultimo["estimativa_pct"])))
    eixo.axhline(0, color="black", linewidth=0.8)
    eixo.set_title("Avaliação líquida do Governo Lula III\nÓtimo/Bom menos Ruim/Péssimo", fontsize=17, pad=14)
    eixo.set_xlabel("Data")
    eixo.set_ylabel("Pontos percentuais")
    estilizar_eixo(eixo)
    eixo.set_xlim(pd.Timestamp("2023-02-01"), None)
    adicionar_rotulos_finais(eixo, rotulos_finais, " p.p.")
    figura.text(
        0.01,
        0.02,
        f"Atualizado até {texto_atualizacao([serie_15.valores.index[-1], serie_30.valores.index[-1]])}. "
        "Faixas amostrais aproximadas do baseline; a covariância entre categorias não é modelada.",
        ha="left",
        fontsize=9,
        color="#555555",
    )
    figura.subplots_adjust(left=0.08, right=0.96, bottom=0.14, top=0.85)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def grafico_segundo_turno(
    lula: SerieSuavizada,
    adversario: SerieSuavizada,
    nome_adversario: str,
    caminho: Path,
    base_percentual: str,
) -> None:
    """Desenha o confronto deixando o denominador explícito no título e no eixo."""
    figura, eixo = plt.subplots(figsize=(14, 7))
    rotulos_finais: list[tuple[str, str, pd.Timestamp, float]] = []
    for rotulo, cor, serie in [("Lula", COR_LULA, lula), (nome_adversario, COR_ADVERSARIO, adversario)]:
        eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color=cor, alpha=0.25, s=20)
        eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2.4)
        eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cor, alpha=0.11)
        ultimo = serie.valores.iloc[-1]
        rotulos_finais.append((rotulo, cor, serie.valores.index[-1], float(ultimo["estimativa_pct"])))
    eixo.set_title(
        f"Segundo Turno 2026: Lula vs {nome_adversario} — {base_percentual}\n"
        "Média ponderada de 30 dias",
        fontsize=17,
        pad=12,
    )
    eixo.set_xlabel("Data")
    eixo.set_ylabel(f"Percentual ({base_percentual.lower()})")
    if base_percentual == "Votos válidos":
        eixo.set_ylim(30, 70)
        eixo.axhline(50, color="#555555", linewidth=1.0, linestyle="--", alpha=0.70)
    else:
        eixo.set_ylim(20, 60)
    estilizar_eixo(eixo)
    adicionar_rotulos_finais(eixo, rotulos_finais)
    complemento = (
        "Brancos, nulos e indecisos permanecem no denominador; as curvas não precisam somar 100%. "
        if base_percentual == "Votos totais"
        else "Percentuais reescalados somente entre Lula e o adversário. "
    )
    figura.text(
        0.01,
        0.02,
        f"Atualizado até {texto_atualizacao([lula.valores.index[-1], adversario.valores.index[-1]])}. "
        + complemento
        + "Faixa amostral aproximada do baseline.",
        ha="left",
        fontsize=8.8,
        color="#555555",
    )
    figura.subplots_adjust(left=0.08, right=0.96, bottom=0.15, top=0.84)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


# =============================================================================
# 10. ABERTURAS DEMOGRÁFICAS DE GOVERNO E SEGUNDO TURNO
# Cada produto só é criado quando existem grupos publicados suficientes.
# =============================================================================
def grupos_disponiveis(linhas: pd.DataFrame, ordem: tuple[str, ...]) -> list[str]:
    """Devolve somente grupos presentes, preservando a ordem visual definida."""

    return [grupo for grupo in ordem if grupo in set(linhas["grupo_abertura"])]


def nome_curto_grupo(grupo: str) -> str:
    """Transforma o nome de um grupo em sufixo curto e seguro para abas do Excel."""

    return texto_normalizado(grupo).replace(" ", "_").title()


def cobertura_abertura(linhas: pd.DataFrame) -> pd.DataFrame:
    """Resume observações, período e institutos disponíveis por grupo."""

    preparado = linhas.copy()
    preparado["_amostra_segmento_publicada"] = pd.to_numeric(
        preparado["amostra_segmento"], errors="coerce"
    ).notna()
    return (
        preparado.groupby("grupo_abertura", sort=False)
        .agg(
            observacoes_publicadas=("grupo_abertura", "size"),
            primeira_data=("data_referencia", "min"),
            ultima_data=("data_referencia", "max"),
            numero_institutos=("instituto", "nunique"),
            institutos=("instituto", lambda valores: ", ".join(sorted(set(map(str, valores))))),
            amostras_segmento_publicadas=("_amostra_segmento_publicada", "sum"),
        )
        .reset_index()
        .rename(columns={"grupo_abertura": "grupo"})
        .assign(
            fallbacks_amostra_segmento=lambda tabela: (
                tabela["observacoes_publicadas"] - tabela["amostras_segmento_publicadas"]
            )
        )
    )


def limites_comuns(series_por_grupo: dict[str, tuple[SerieSuavizada, SerieSuavizada]]) -> tuple[float, float]:
    """Calcula uma escala vertical comum para comparar painéis sem distorção."""

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
    """Desenha Mulheres e Homens em painéis com a mesma escala vertical."""

    cores = {"Ótimo/Bom": COR_OTIMO, "Regular": COR_REGULAR, "Ruim/Péssimo": COR_RUIM}
    grupos = ["Mulheres", "Homens"]
    figura, eixos = plt.subplots(1, 2, figsize=(18, 7.5), sharey=True)
    limites = pd.concat(
        [
            serie.valores[["ic_baixo_pct", "ic_alto_pct"]]
            for grupo in grupos
            for serie in series_por_grupo[grupo].values()
        ]
    )
    inferior = max(0.0, float(np.floor((limites["ic_baixo_pct"].min() - 3) / 5) * 5))
    superior = min(100.0, float(np.ceil((limites["ic_alto_pct"].max() + 3) / 5) * 5))
    for eixo, grupo in zip(eixos, grupos, strict=True):
        rotulos_finais: list[tuple[str, str, pd.Timestamp, float]] = []
        for rotulo, serie in series_por_grupo[grupo].items():
            eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color=cores[rotulo], alpha=0.20, s=22)
            eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cores[rotulo], linewidth=2.2)
            eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cores[rotulo], alpha=0.10)
            rotulos_finais.append(
                (rotulo, cores[rotulo], serie.valores.index[-1], float(serie.valores["estimativa_pct"].iloc[-1]))
            )
        eixo.set_title(grupo, fontsize=14, pad=10)
        eixo.set_xlabel("Data")
        eixo.set_ylim(inferior, superior)
        estilizar_eixo(eixo)
        adicionar_rotulos_finais(eixo, rotulos_finais)
    eixos[0].set_ylabel("Percentual")
    figura.suptitle("Avaliação do Governo Lula III por sexo\nMédia ponderada de 30 dias", fontsize=17)
    ultima_data = texto_atualizacao(
        [serie.valores.index[-1] for grupo in grupos for serie in series_por_grupo[grupo].values()]
    )
    figura.text(
        0.01,
        0.02,
        f"Atualizado até {ultima_data}. Faixas amostrais aproximadas; quando a amostra do grupo não é publicada, o Modelo A usa fallback conservador de 300.",
        ha="left",
        fontsize=8.8,
        color="#555555",
    )
    figura.subplots_adjust(left=0.07, right=0.97, bottom=0.14, top=0.83, wspace=0.10)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def grafico_liquido_por_sexo(
    series_por_grupo: dict[str, tuple[SerieSuavizada, SerieSuavizada]],
    caminho: Path,
) -> None:
    """Desenha a avaliação líquida por sexo nas janelas de 15 e 30 dias."""

    figura, eixos = plt.subplots(1, 2, figsize=(18, 7.5), sharey=True)
    limites = pd.concat(
        [
            serie.valores[["ic_baixo_pct", "ic_alto_pct"]]
            for dupla in series_por_grupo.values()
            for serie in dupla
        ]
    )
    inferior = float(np.floor((min(limites["ic_baixo_pct"].min(), 0) - 2) / 5) * 5)
    superior = float(np.ceil((max(limites["ic_alto_pct"].max(), 0) + 2) / 5) * 5)
    for eixo, grupo in zip(eixos, ["Mulheres", "Homens"], strict=True):
        serie_15, serie_30 = series_por_grupo[grupo]
        eixo.scatter(serie_15.pontos_publicados["data_referencia"], serie_15.pontos_publicados["valor_pct"], color="#757575", alpha=0.25, s=22)
        rotulos_finais: list[tuple[str, str, pd.Timestamp, float]] = []
        for rotulo, cor, estilo, serie in [("15 dias", COR_ADVERSARIO, "--", serie_15), ("30 dias", COR_LULA, "-", serie_30)]:
            eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2.2, linestyle=estilo)
            eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cor, alpha=0.10)
            rotulos_finais.append(
                (rotulo, cor, serie.valores.index[-1], float(serie.valores["estimativa_pct"].iloc[-1]))
            )
        eixo.axhline(0, color="black", linewidth=0.8)
        eixo.set_title(grupo, fontsize=14, pad=10)
        eixo.set_xlabel("Data")
        eixo.set_ylim(inferior, superior)
        estilizar_eixo(eixo)
        adicionar_rotulos_finais(eixo, rotulos_finais, " p.p.")
    eixos[0].set_ylabel("Pontos percentuais")
    figura.suptitle("Avaliação líquida do Governo Lula III por sexo\nÓtimo/Bom menos Ruim/Péssimo", fontsize=17)
    ultima_data = texto_atualizacao(
        [serie.valores.index[-1] for dupla in series_por_grupo.values() for serie in dupla]
    )
    figura.text(
        0.01,
        0.02,
        f"Atualizado até {ultima_data}. Faixas amostrais aproximadas do baseline; a covariância entre categorias não é modelada.",
        ha="left",
        fontsize=8.8,
        color="#555555",
    )
    figura.subplots_adjust(left=0.07, right=0.97, bottom=0.14, top=0.82, wspace=0.10)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def gerar_governo_por_sexo(governo: pd.DataFrame, pasta_saida: Path) -> bool:
    """Gera composição e avaliação líquida para Mulheres e Homens quando publicados."""
    linhas = recorte_segmentado(governo, "Sexo", sexo_padronizado)
    grupos = grupos_disponiveis(linhas, ("Mulheres", "Homens"))
    grupos = [
        grupo
        for grupo in grupos
        if linhas.loc[linhas["grupo_abertura"].eq(grupo), "data_referencia"].nunique() >= 2
    ]
    if grupos != ["Mulheres", "Homens"]:
        print("Aviso: a base não possui avaliação nacional de governo para Mulheres e Homens; nenhum arquivo por sexo foi gerado.")
        return False

    composicao_por_grupo: dict[str, dict[str, SerieSuavizada]] = {}
    liquida_por_grupo: dict[str, tuple[SerieSuavizada, SerieSuavizada]] = {}
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
            abas_composicao[nome_aba] = tabela

        fonte_liquida = recorte.loc[recorte["otimo_bom_pct"].map(presente) & recorte["ruim_pessimo_pct"].map(presente)].copy()
        fonte_liquida["avaliacao_liquida_pct"] = fonte_liquida["otimo_bom_pct"] - fonte_liquida["ruim_pessimo_pct"]
        serie_15 = exigir(suavizar(fonte_liquida, "avaliacao_liquida_pct", 15, ("otimo_bom_pct", "ruim_pessimo_pct"), (-100.0, 100.0)), f"Avaliação líquida 15 dias entre {grupo.lower()}")
        serie_30 = exigir(suavizar(fonte_liquida, "avaliacao_liquida_pct", 30, ("otimo_bom_pct", "ruim_pessimo_pct"), (-100.0, 100.0)), f"Avaliação líquida 30 dias entre {grupo.lower()}")
        liquida_por_grupo[grupo] = (serie_15, serie_30)
        for sufixo, serie in [("15d", serie_15), ("30d", serie_30)]:
            tabela = serie.valores.reset_index().rename(columns={"estimativa_pct": "avaliacao_liquida_suavizada", "ic_baixo_pct": "ic_baixo", "ic_alto_pct": "ic_alto"})
            abas_liquida[f"{curto}_{sufixo}"] = tabela[["data", "avaliacao_liquida_suavizada", "ic_baixo", "ic_alto", "se_pp"]]

    cobertura = cobertura_abertura(linhas)
    metodologia = pd.DataFrame({"item": ["Universo", "Grupos", "Cobertura mínima", "Amostra e faixa", "Interpretação"], "descricao": ["Brasil, abertura publicada de sexo.", "Rótulos FEM/Feminino e MAS/Masculino são harmonizados como Mulheres e Homens.", "Exige Mulheres e Homens com ao menos duas datas publicadas em cada grupo.", "Usa amostra do segmento quando publicada; na ausência, aplica fallback conservador. A faixa é somente amostral e aproximada.", "As curvas são agregados de pesquisas disponíveis; não são previsão eleitoral."]})
    abas_composicao["Cobertura"] = cobertura
    abas_composicao["Metodologia"] = metodologia
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
    nome_adversario: str,
    titulo_abertura: str,
    caminho: Path,
) -> None:
    """Desenha painéis comparáveis, com rótulo direto no fim das curvas."""
    grupos = list(series_por_grupo)
    colunas = 2
    linhas = int(np.ceil(len(grupos) / colunas))
    figura, eixos = plt.subplots(linhas, colunas, figsize=(17, 5.8 * linhas), sharey=True)
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
        rotulos_finais: list[tuple[str, str, pd.Timestamp, float]] = []
        for rotulo, cor, serie in [("Lula", COR_LULA, lula), (nome_adversario, COR_ADVERSARIO, adversario)]:
            eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color=cor, alpha=0.25, s=22)
            eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2.2)
            eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cor, alpha=0.10)
            rotulos_finais.append(
                (rotulo_curto_candidato(rotulo), cor, serie.valores.index[-1], float(serie.valores["estimativa_pct"].iloc[-1]))
            )
        eixo.axhline(50, color="#666666", linewidth=0.8, linestyle=":", alpha=0.7)
        eixo.set_title(grupo, fontsize=13, pad=9, wrap=True)
        eixo.set_xlabel("Data")
        eixo.xaxis.set_major_locator(localizador_data)
        eixo.xaxis.set_major_formatter(formatador_data)
        eixo.set_ylim(inferior, superior)
        estilizar_eixo(eixo)
        adicionar_rotulos_finais(eixo, rotulos_finais)
    for eixo in eixos_planos[len(grupos):]:
        eixo.set_visible(False)
    for eixo in eixos_planos[::colunas]:
        eixo.set_ylabel("Votos válidos (%)")
    ultima_data = texto_atualizacao(
        [serie.valores.index[-1] for dupla in series_por_grupo.values() for serie in dupla]
    )
    figura.suptitle(
        f"Segundo turno 2026: Lula vs {nome_adversario} por {titulo_abertura}\n"
        "Votos válidos — média ponderada de 30 dias",
        fontsize=16,
    )
    figura.text(
        0.01,
        0.018,
        f"Atualizado até {ultima_data}. Pontos: valores publicados. Faixas amostrais aproximadas; "
        "na falta da amostra do segmento, usa-se fallback conservador.",
        ha="left",
        fontsize=8.8,
        color="#444444",
    )
    figura.subplots_adjust(bottom=0.11 if linhas == 1 else 0.09, top=0.80 if linhas == 1 else 0.86, hspace=0.42, wspace=0.14)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def gerar_segundo_turno_por_abertura(
    confrontos: pd.DataFrame,
    nome_adversario: str,
    termo_adversario: str,
    tipo_segmento: str,
    normalizador_grupo,
    ordem_grupos: tuple[str, ...],
    titulo_abertura: str,
    nome_saida: str,
    pasta_saida: Path,
) -> bool:
    """Gera um confronto de 2º turno aberto por segmento, sem imputar grupos ausentes."""
    linhas = confrontos_segundo_turno_segmentados(confrontos, termo_adversario, tipo_segmento, normalizador_grupo)
    grupos = grupos_disponiveis(linhas, ordem_grupos)
    # Uma curva demográfica não deve nascer de uma fotografia isolada. Exigimos
    # ao menos duas datas publicadas em cada grupo, como nos pares de 1º turno.
    grupos = [
        grupo
        for grupo in grupos
        if linhas.loc[linhas["grupo_abertura"].eq(grupo), "data_referencia"].nunique() >= 2
    ]
    if len(grupos) < 2:
        print(f"Aviso: não há cobertura suficiente por {titulo_abertura} para Lula × {nome_adversario}; nenhum arquivo foi gerado.")
        return False
    preparado = votos_validos(preparar_segundo_turno(linhas))
    series_por_grupo: dict[str, tuple[SerieSuavizada, SerieSuavizada]] = {}
    for grupo in grupos:
        recorte = preparado.loc[preparado["grupo_abertura"].eq(grupo)].copy()
        if recorte.empty:
            continue
        lula = exigir(suavizar(recorte, "lula_validos_pct", 30), f"Lula entre {grupo.lower()} contra {nome_adversario}")
        adversario = exigir(suavizar(recorte, "adversario_validos_pct", 30), f"{nome_adversario} entre {grupo.lower()}")
        series_por_grupo[grupo] = (lula, adversario)
    if len(series_por_grupo) < 2:
        print(f"Aviso: não há séries válidas por {titulo_abertura} para Lula × {nome_adversario}; nenhum arquivo foi gerado.")
        return False

    abas: dict[str, pd.DataFrame] = {}
    for grupo, (lula, adversario) in series_por_grupo.items():
        curto = nome_curto_grupo(grupo)
        for prefixo, coluna in [("Suavizados", "estimativa_pct"), ("IC_Baixo", "ic_baixo_pct"), ("IC_Alto", "ic_alto_pct")]:
            tabela = pd.concat([lula.valores[coluna].rename("Lula"), adversario.valores[coluna].rename(nome_adversario)], axis=1).sort_index()
            tabela.index.name = "data"
            abas[f"{prefixo}_{curto}"] = tabela
    cobertura = cobertura_abertura(linhas.loc[linhas["grupo_abertura"].isin(series_por_grupo)])
    metodologia = pd.DataFrame({"item": ["Universo", "Abertura", "Medida", "Cobertura mínima", "Amostra e faixa", "Interpretação"], "descricao": [f"Brasil, 2º turno, estimulada, Lula × {nome_adversario}.", f"Grupos publicados de {titulo_abertura}; somente rótulos equivalentes são harmonizados.", "Lula e adversário convertidos para votos válidos dentro de cada grupo.", "Exige ao menos dois grupos e duas datas publicadas em cada grupo desenhado.", "Usa amostra do segmento quando publicada; na ausência, aplica fallback conservador. A faixa é apenas amostral e aproximada.", "As curvas são agregados de pesquisas disponíveis; não são previsão eleitoral nem probabilidade de vitória."]})
    abas["Cobertura"] = cobertura
    abas["Metodologia"] = metodologia
    abas["Linhas_publicadas"] = linhas.sort_values(["data_referencia", "grupo_abertura"])
    escrever_planilha(pasta_saida / f"{nome_saida}.xlsx", abas, indice=False)
    grafico_segundo_turno_por_abertura(series_por_grupo, nome_adversario, titulo_abertura, pasta_saida / f"{nome_saida}.png")
    return True


# =============================================================================
# 11. PARES DE PRIMEIRO TURNO POR SEXO, RELIGIÃO E RENDA
# A cobertura mínima evita gráficos baseados em uma única data ou grupo.
# =============================================================================
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


def grafico_primeiro_turno_por_abertura(
    series_por_grupo: dict[str, tuple[SerieSuavizada, SerieSuavizada]],
    nome_adversario: str,
    titulo_abertura: str,
    caminho: Path,
) -> None:
    """Desenha Lula e um adversário em painéis demográficos comparáveis."""
    grupos = list(series_por_grupo)
    colunas = 2
    linhas = int(np.ceil(len(grupos) / colunas))
    figura, eixos = plt.subplots(linhas, colunas, figsize=(17, 6.2 * linhas), sharey=True)
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
        rotulos_finais: list[tuple[str, str, pd.Timestamp, float]] = []
        for rotulo, cor, serie in [("Lula", COR_LULA, lula), (nome_adversario, COR_ADVERSARIO, adversario)]:
            eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color=cor, alpha=0.25, s=22)
            eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2.2)
            eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cor, alpha=0.10)
            rotulos_finais.append(
                (rotulo_curto_candidato(rotulo), cor, serie.valores.index[-1], float(serie.valores["estimativa_pct"].iloc[-1]))
            )
        eixo.set_title(grupo, fontsize=13, pad=10, wrap=True)
        eixo.set_xlabel("Data")
        eixo.xaxis.set_major_locator(localizador_data)
        eixo.xaxis.set_major_formatter(formatador_data)
        eixo.set_ylim(inferior, superior)
        estilizar_eixo(eixo)
        adicionar_rotulos_finais(eixo, rotulos_finais)
    for eixo in eixos_planos[len(grupos):]:
        eixo.set_visible(False)
    for eixo in eixos_planos[::colunas]:
        eixo.set_ylabel("Intenção de voto (% dos votos totais)")
    ultima_data = texto_atualizacao(
        [serie.valores.index[-1] for dupla in series_por_grupo.values() for serie in dupla]
    )
    figura.suptitle(
        f"Primeiro turno 2026: Lula vs {nome_adversario} por {titulo_abertura}\n"
        "Votos totais — média harmonizada e ponderada de 30 dias",
        fontsize=16,
    )
    figura.text(
        0.01,
        0.016,
        f"Atualizado até {ultima_data}. Pontos: valores publicados. Cada pesquisa contribui uma vez por candidato e grupo; "
        "ausência não vira zero. Faixas amostrais aproximadas, com fallback conservador quando necessário.",
        ha="left",
        fontsize=8.7,
        color="#444444",
    )
    figura.subplots_adjust(bottom=0.12 if linhas == 1 else 0.09, top=0.80 if linhas == 1 else 0.86, hspace=0.50, wspace=0.14)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def gerar_primeiro_turno_por_abertura(
    confrontos: pd.DataFrame,
    nome_adversario: str,
    termo_adversario: str,
    tipo_segmento: str,
    normalizador_grupo,
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
        series_por_grupo[grupo] = (lula, adversario)
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
            abas[f"{prefixo}_{curto}"] = tabela
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
    metodologia = pd.DataFrame(
        {
            "item": ["Universo", "Abertura", "Medida", "Harmonização por cenário", "Cobertura mínima", "Amostra e faixa", "Interpretação"],
            "descricao": [
                f"Brasil, 1º turno, estimulada, votos totais, Lula × {nome_adversario}.",
                f"Grupos publicados de {titulo_abertura}; somente rótulos equivalentes são harmonizados.",
                "Lula e o adversário são mostrados separadamente em cada grupo publicado.",
                "Em cada onda, candidato e grupo, o valor é a média simples dos cenários em que o candidato foi testado. A pesquisa entra uma vez por candidato e grupo.",
                "O gráfico exige ao menos dois grupos e duas datas publicadas para Lula e o adversário em cada grupo; grupos sem essa cobertura não são desenhados.",
                "Usa amostra do segmento quando publicada; na ausência, usa fallback conservador. A faixa é somente amostral e aproximada.",
                "As curvas acompanham pesquisas e cenários disponíveis; não são previsão eleitoral nem probabilidade de vitória.",
            ],
        }
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
    """Converte rótulos de candidato ou abertura em nomes de arquivo legíveis."""

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
    for nome_adversario in CANDIDATOS_PRIMEIRO_TURNO_PARES:
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


# =============================================================================
# 12. GRÁFICO NACIONAL HARMONIZADO DE PRIMEIRO TURNO
# =============================================================================
def cores_primeiro_turno(candidatos: list[str]) -> dict[str, object]:
    """Define cores estáveis para os nomes mais recorrentes e cores distintas para os demais."""
    conhecidas = {
        "lula": "#C62828",
        "flavio": "#1565C0",
        "renan santos": "#6A1B9A",
        "romeu zema": "#2E7D32",
        "ronaldo caiado": "#EF6C00",
        "branco nulo nao sei": "#616161",
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
    rotulos_finais: list[tuple[str, str, pd.Timestamp, float]] = []
    for candidato in candidatos:
        observados = pontos.loc[pontos["candidato"].eq(candidato)]
        eixo.scatter(
            observados["data_referencia"], observados["valor_pct"], color=cores[candidato], alpha=0.42, s=26,
        )
        curva = series.loc[series["candidato"].eq(candidato)]
        eixo.plot(curva["data"], curva["estimativa_pct"], color=cores[candidato], linewidth=2.25)
        rotulos_finais.append(
            (candidato, cores[candidato], pd.Timestamp(curva["data"].iloc[-1]), float(curva["estimativa_pct"].iloc[-1]))
        )
    minimo = float(pontos["valor_pct"].min())
    maximo = float(pontos["valor_pct"].max())
    inferior = max(0.0, float(np.floor((minimo - 4) / 5) * 5))
    superior = min(100.0, float(np.ceil((maximo + 4) / 5) * 5))
    eixo.set_ylim(inferior, superior)
    eixo.set_title("Primeiro turno 2026 — média harmonizada dos cenários estimulados\nMédia ponderada de 30 dias", fontsize=16, pad=16)
    eixo.text(
        0.5,
        1.01,
        f"{institutos} | {len(candidatos)} séries selecionadas; cada pesquisa contribui uma vez por série",
        transform=eixo.transAxes, ha="center", va="bottom", fontsize=10, color="#444444",
    )
    eixo.set_xlabel("Data")
    eixo.set_ylabel("Intenção de voto (% dos votos totais)")
    estilizar_eixo(eixo)
    adicionar_rotulos_finais(eixo, rotulos_finais)
    figura.text(
        0.01,
        0.016,
        f"Atualizado até {texto_atualizacao(series['data'])}. Candidato ausente não recebe zero. Branco/Nulo/Não sei usa "
        "somente o valor publicado, sem residual. As curvas são médias de cenários disponíveis, não previsão.",
        ha="left", fontsize=9, color="#444444",
    )
    figura.subplots_adjust(left=0.07, right=0.95, bottom=0.11, top=0.84)
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
    pontos = pontos.copy()
    pontos["_fallback_amostra"] = pontos.apply(
        lambda linha: (
            not presente(linha["amostra_total"])
            if texto_normalizado(linha["segmento_tipo"]) == "total"
            else not presente(linha["amostra_segmento"])
        ),
        axis=1,
    )

    registros: list[pd.DataFrame] = []
    for candidato, curva in pontos.groupby("candidato", sort=False):
        serie = exigir(suavizar(curva, "valor_pct", 30), f"{candidato} no primeiro turno")
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
            fallbacks_de_amostra=("_fallback_amostra", "sum"),
            institutos=("instituto", lambda valores: ", ".join(sorted(set(map(str, valores))))),
        )
        .reset_index()
    )
    metodologia = pd.DataFrame(
        {
            "item": [
                "Séries incluídas", "Universo", "Harmonização por cenário", "Candidato ausente",
                "Branco/Nulo/Não sei", "Média ponderada", "Faixa amostral", "Interpretação",
            ],
            "descricao": [
                "Lula, Flávio, Renan Santos, Romeu Zema, Ronaldo Caiado e Branco/Nulo/Não sei.",
                "Brasil, Total, 1º turno, estimulada e votos totais, independentemente do rótulo do cenário.",
                "Em cada onda e para cada candidato, a observação é a média simples dos cenários em que o candidato foi testado. A mesma pesquisa entra uma única vez por candidato.",
                "Ausência em uma lista não é interpretada como 0%. O candidato só é calculado nos cenários em que aparece publicado.",
                "Usa literalmente brancos_nulos_indecisos_pct nos cenários incluídos. Célula vazia permanece ausente e nenhum residual é calculado para completar 100%.",
                "Média ponderada do baseline legado em janela de 30 dias sobre as observações já harmonizadas por candidato.",
                "Faixa amostral aproximada de 1,96 erros-padrão; não é uma margem de erro completa e não modela heterogeneidade ou efeito de instituto.",
                "É uma média de cenários disponíveis para acompanhamento. Não é previsão de resultado eleitoral nem probabilidade de vitória.",
            ],
        }
    )
    pontos_planilha = pontos.drop(columns=["peso_legacy", "_fallback_amostra"], errors="ignore").copy()
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
            "Linhas_originais": linhas_planilha,
        },
        indice=False,
    )
    grafico_primeiro_turno(pontos, series, pasta_saida / f"{NOME_GRAFICO_PRIMEIRO_TURNO}.png")
    return True


# =============================================================================
# 13. GERAÇÃO DOS CONFRONTOS NACIONAIS E ORQUESTRAÇÃO COMPLETA
# =============================================================================
def gerar_segundo_turno(
    confrontos: pd.DataFrame,
    nome_adversario: str,
    termo_adversario: str,
    nome_saida_validos: str,
    nome_saida_totais: str,
    pasta_saida: Path,
) -> bool:
    """Gera o mesmo confronto em votos válidos e em votos totais."""
    linhas = confrontos_segundo_turno(confrontos, termo_adversario)
    if linhas.empty:
        print(
            f"Aviso: não há cenário nacional, estimulado, de 2º turno Lula × {nome_adversario} "
            "na base; nenhum arquivo foi gerado para esse confronto."
        )
        return False
    segundo_turno_totais = preparar_segundo_turno(linhas)
    segundo_turno_validos = votos_validos(segundo_turno_totais)
    configuracoes = [
        (
            "Votos válidos", segundo_turno_validos, "lula_validos_pct", "adversario_validos_pct",
            nome_saida_validos,
            "Reescala apenas Lula e o adversário para somarem 100%; brancos, nulos e indecisos saem do denominador.",
        ),
        (
            "Votos totais", segundo_turno_totais, "lula_pct", "adversario_pct", nome_saida_totais,
            "Usa os percentuais publicados no total da amostra; brancos, nulos e indecisos permanecem no denominador.",
        ),
    ]
    for base_percentual, fonte, coluna_lula, coluna_adversario, nome_saida, denominador in configuracoes:
        lula = exigir(
            suavizar(fonte, coluna_lula, 30),
            f"Lula no 2º turno contra {nome_adversario} em {base_percentual.lower()}",
        )
        adversario = exigir(
            suavizar(fonte, coluna_adversario, 30),
            f"{nome_adversario} no 2º turno em {base_percentual.lower()}",
        )
        abas: dict[str, pd.DataFrame] = {}
        for nome_aba, coluna in [
            ("Suavizados", "estimativa_pct"), ("IC_Baixo", "ic_baixo_pct"), ("IC_Alto", "ic_alto_pct")
        ]:
            tabela = pd.concat(
                [lula.valores[coluna].rename("Lula"), adversario.valores[coluna].rename(nome_adversario)], axis=1
            ).sort_index()
            tabela.index.name = "data"
            abas[nome_aba] = tabela
        fonte_cobertura = fonte.loc[
            fonte[coluna_lula].notna() & fonte[coluna_adversario].notna()
        ].copy()
        cobertura = pd.DataFrame(
            {
                "indicador": [
                    "observacoes_utilizadas", "datas_distintas", "institutos_distintos",
                    "primeira_data", "ultima_data", "fallbacks_de_amostra",
                ],
                "valor": [
                    len(fonte_cobertura),
                    fonte_cobertura["data_referencia"].nunique(),
                    fonte_cobertura["instituto"].nunique(),
                    fonte_cobertura["data_referencia"].min(),
                    fonte_cobertura["data_referencia"].max(),
                    int((
                        fonte_cobertura["amostra_segmento"].isna()
                        & fonte_cobertura["amostra_total"].isna()
                    ).sum()),
                ],
            }
        )
        abas["Cobertura"] = cobertura
        abas["Metodologia"] = pd.DataFrame(
            {
                "item": ["Base dos percentuais", "Denominador", "Média ponderada", "Faixa", "Interpretação"],
                "descricao": [
                    base_percentual, denominador,
                    "Baseline legado em janela de 30 dias: qualidade do instituto, recência linear e tamanho de amostra.",
                    "Faixa amostral aproximada de 1,96 erros-padrão; não incorpora heterogeneidade, efeito de instituto ou desenho amostral.",
                    "Agregado de pesquisas para acompanhamento; não é previsão eleitoral nem probabilidade de vitória.",
                ],
            }
        )
        escrever_planilha(pasta_saida / f"{nome_saida}.xlsx", abas)
        grafico_segundo_turno(
            lula, adversario, nome_adversario, pasta_saida / f"{nome_saida}.png", base_percentual
        )
    return True


def gerar_todos_resultados(
    governo: pd.DataFrame,
    confrontos: pd.DataFrame,
    validacao: pd.DataFrame,
    pasta_saida: Path,
) -> None:
    """Gera todos os produtos em uma pasta de preparação ainda não publicada."""

    governo_total = somente_brasil_total(governo)
    if governo_total.empty:
        raise ErroModeloA("Não há avaliação nacional total na aba Lula3.")

    # Etapa 3 — calcular a composição da avaliação com janela de 30 dias.
    composicao = {
        "Ótimo/Bom": exigir(suavizar(governo_total, "otimo_bom_pct", 30), "Ótimo/Bom"),
        "Regular": exigir(suavizar(governo_total, "regular_pct", 30), "Regular"),
        "Ruim/Péssimo": exigir(suavizar(governo_total, "ruim_pessimo_pct", 30), "Ruim/Péssimo"),
    }

    # Etapa 4 — calcular avaliação líquida como aprovação menos reprovação.
    # As janelas de 15 e 30 dias reproduzem os dois recortes do legado.
    fonte_liquida = governo_total.loc[governo_total["otimo_bom_pct"].map(presente) & governo_total["ruim_pessimo_pct"].map(presente)].copy()
    fonte_liquida["avaliacao_liquida_pct"] = fonte_liquida["otimo_bom_pct"] - fonte_liquida["ruim_pessimo_pct"]
    liquida_15 = exigir(suavizar(fonte_liquida, "avaliacao_liquida_pct", 15, ("otimo_bom_pct", "ruim_pessimo_pct"), (-100.0, 100.0)), "Avaliação líquida em 15 dias")
    liquida_30 = exigir(suavizar(fonte_liquida, "avaliacao_liquida_pct", 30, ("otimo_bom_pct", "ruim_pessimo_pct"), (-100.0, 100.0)), "Avaliação líquida em 30 dias")

    # Criar os produtos nacionais de governo na área temporária de trabalho.
    pasta_saida.mkdir(parents=True, exist_ok=True)
    suavizados = pd.concat([serie.valores["estimativa_pct"].rename(nome) for nome, serie in composicao.items()], axis=1).sort_index()
    ic_baixo = pd.concat([serie.valores["ic_baixo_pct"].rename(nome) for nome, serie in composicao.items()], axis=1).sort_index()
    ic_alto = pd.concat([serie.valores["ic_alto_pct"].rename(nome) for nome, serie in composicao.items()], axis=1).sort_index()
    for tabela in (suavizados, ic_baixo, ic_alto):
        tabela.index.name = "data"
    relatorio_validacao = validacao.copy()
    if relatorio_validacao.empty:
        relatorio_validacao = pd.DataFrame(
            [{"severidade": "OK", "aba": "Base", "linha_excel": "", "campo": "", "mensagem": "Nenhum alerta encontrado."}]
        )
    cobertura_governo = pd.DataFrame(
        {
            "indicador": [
                "observacoes_utilizadas", "datas_distintas", "institutos_distintos",
                "primeira_data", "ultima_data", "fallbacks_de_amostra",
            ],
            "valor": [
                len(governo_total),
                governo_total["data_referencia"].nunique(),
                governo_total["instituto"].nunique(),
                governo_total["data_referencia"].min(),
                governo_total["data_referencia"].max(),
                int((governo_total["amostra_segmento"].isna() & governo_total["amostra_total"].isna()).sum()),
            ],
        }
    )
    metodologia_governo = pd.DataFrame(
        {
            "item": ["Universo", "Tracking", "Média ponderada", "Faixa", "Interpretação"],
            "descricao": [
                "Brasil, segmento Total, avaliação do Governo Lula III.",
                "Tracking diário é consolidado em semanas encerradas no domingo; somente semanas com sete datas publicadas entram.",
                "Baseline legado em janelas móveis: qualidade do instituto, recência linear e tamanho de amostra.",
                "Faixa amostral aproximada de 1,96 erros-padrão; não incorpora heterogeneidade, efeito de instituto ou desenho amostral.",
                "Agregado de pesquisas para acompanhamento; não é previsão eleitoral.",
            ],
        }
    )
    escrever_planilha(
        pasta_saida / f"{NOME_GRAFICO_GOVERNO}.xlsx",
        {
            "Suavizados": suavizados,
            "IC_Baixo": ic_baixo,
            "IC_Alto": ic_alto,
            "Cobertura": cobertura_governo,
            "Metodologia": metodologia_governo,
            "Validacao_da_base": relatorio_validacao,
        },
    )

    abas_liquida: dict[str, pd.DataFrame] = {}
    for nome_aba, serie in [("Serie_Janela_15d", liquida_15), ("Serie_Janela_30d", liquida_30)]:
        tabela = serie.valores.reset_index().rename(columns={"estimativa_pct": "aprov_liq_suavizado", "ic_baixo_pct": "ci_low", "ic_alto_pct": "ci_high"})
        abas_liquida[nome_aba] = tabela[["data", "aprov_liq_suavizado", "ci_low", "ci_high", "se_pp"]]
    abas_liquida["Cobertura"] = cobertura_governo
    abas_liquida["Metodologia"] = metodologia_governo
    escrever_planilha(pasta_saida / f"{NOME_GRAFICO_LIQUIDO}.xlsx", abas_liquida, indice=False)

    grafico_governo(composicao, pasta_saida / f"{NOME_GRAFICO_GOVERNO}.png")
    grafico_liquido(liquida_15, liquida_30, pasta_saida / f"{NOME_GRAFICO_LIQUIDO}.png")

    # Etapa 6 — publicar a avaliação do governo por Mulheres e Homens.
    gerar_governo_por_sexo(governo, pasta_saida)

    # Etapa 7 — gerar cada confronto nacional de 2º turno em duas bases:
    # votos válidos (sem não-voto) e votos totais (com não-voto no denominador).
    cenarios = [
        ("Flávio Bolsonaro", "flavio", NOME_GRAFICO_SEGUNDO_TURNO, NOME_GRAFICO_SEGUNDO_TURNO_TOTAIS),
        ("Renan Santos", "renan", NOME_GRAFICO_SEGUNDO_TURNO_RENAN, NOME_GRAFICO_SEGUNDO_TURNO_RENAN_TOTAIS),
        ("Ronaldo Caiado", "caiado", NOME_GRAFICO_SEGUNDO_TURNO_CAIADO, NOME_GRAFICO_SEGUNDO_TURNO_CAIADO_TOTAIS),
    ]
    for nome_adversario, termo_adversario, nome_saida_validos, nome_saida_totais in cenarios:
        gerado = gerar_segundo_turno(
            confrontos, nome_adversario, termo_adversario,
            nome_saida_validos, nome_saida_totais, pasta_saida,
        )
        if nome_adversario == "Flávio Bolsonaro" and not gerado:
            raise ErroModeloA("A base não possui o cenário nacional, estimulado, de 2º turno Lula × Flávio.")

    # Etapa 8 — gerar quebras de 2º turno somente quando os grupos existem.
    aberturas_sexo = [
        ("Flávio Bolsonaro", "flavio", NOME_GRAFICO_SEGUNDO_TURNO_FLAVIO_SEXO),
        ("Renan Santos", "renan", NOME_GRAFICO_SEGUNDO_TURNO_RENAN_SEXO),
        ("Ronaldo Caiado", "caiado", NOME_GRAFICO_SEGUNDO_TURNO_CAIADO_SEXO),
    ]
    for nome_adversario, termo_adversario, nome_saida in aberturas_sexo:
        gerar_segundo_turno_por_abertura(
            confrontos, nome_adversario, termo_adversario, "Sexo", sexo_padronizado,
            ("Mulheres", "Homens"), "sexo", nome_saida, pasta_saida,
        )
    aberturas_religiao = [
        ("Flávio Bolsonaro", "flavio", NOME_GRAFICO_SEGUNDO_TURNO_FLAVIO_RELIGIAO),
        ("Renan Santos", "renan", NOME_GRAFICO_SEGUNDO_TURNO_RENAN_RELIGIAO),
        ("Ronaldo Caiado", "caiado", NOME_GRAFICO_SEGUNDO_TURNO_CAIADO_RELIGIAO),
    ]
    for nome_adversario, termo_adversario, nome_saida in aberturas_religiao:
        gerar_segundo_turno_por_abertura(
            confrontos, nome_adversario, termo_adversario, "Religião", religiao_padronizada,
            ("Católicos", "Evangélicos", "Outras religiões", "Sem religião"), "religião", nome_saida, pasta_saida,
        )

    # Etapa 9 — por último, publicar o primeiro turno nacional harmonizado e
    # os pares demográficos que atendem ao contrato mínimo de cobertura.
    gerar_primeiro_turno(confrontos, pasta_saida)
    gerar_aberturas_primeiro_turno(confrontos, pasta_saida)


def publicar_resultados(pasta_preparacao: Path, pasta_destino: Path) -> None:
    """Troca o conjunto anterior pelo novo somente após geração completa.

    Se qualquer movimentação falhar, os arquivos antigos são restaurados. Isso
    evita misturar outputs velhos e novos ou deixar meia execução publicada.
    """

    novos = sorted(
        caminho
        for caminho in pasta_preparacao.iterdir()
        if caminho.is_file() and caminho.suffix.lower() in {".xlsx", ".png"}
    )
    if not novos:
        raise ErroModeloA("A rotina terminou sem produzir planilhas ou gráficos.")
    pasta_destino.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="Modelo_A_backup_", dir=pasta_destino.parent) as pasta_backup_texto:
        pasta_backup = Path(pasta_backup_texto)
        antigos = [
            caminho
            for caminho in pasta_destino.iterdir()
            if caminho.is_file() and caminho.suffix.lower() in {".xlsx", ".png"}
        ]
        publicados: list[Path] = []
        try:
            for antigo in antigos:
                shutil.move(str(antigo), str(pasta_backup / antigo.name))
            for novo in novos:
                destino = pasta_destino / novo.name
                shutil.move(str(novo), str(destino))
                publicados.append(destino)
        except Exception:
            for publicado in publicados:
                if publicado.exists():
                    shutil.move(str(publicado), str(pasta_preparacao / publicado.name))
            for copia in pasta_backup.iterdir():
                shutil.move(str(copia), str(pasta_destino / copia.name))
            raise


def executar() -> Path:
    """Lê, valida, calcula e publica toda a rotina oficial do Modelo A."""

    # 1. Leitura: nenhuma linha é descartada silenciosamente; cada registro
    # recebe a linha de origem no Excel para permitir auditoria dos alertas.
    base, pasta_saida = localizar_base()
    governo_bruto = ler_aba(base, "Lula3", COLUNAS_GOVERNO)
    confrontos_brutos = ler_aba(base, "Confrontos", COLUNAS_CONFRONTOS)
    institutos = ler_aba(base, "Institutos", COLUNAS_INSTITUTOS)

    # 2. Validação: erros objetivos bloqueiam a publicação; alertas legítimos
    # são preservados e seguem para a planilha principal de avaliação.
    validacao = validar_base(governo_bruto, confrontos_brutos, institutos)
    pesos = pesos_dos_institutos(institutos)
    governo = preparar(governo_bruto, ("otimo_bom_pct", "regular_pct", "ruim_pessimo_pct"), pesos)
    confrontos = preparar(confrontos_brutos, ("lula_pct", "adversario_pct"), pesos)

    # 3. Tracking diário vira uma única onda semanal somente quando a semana
    # contém sete datas. Essa consolidação é necessária para reproduzir o legado.
    governo = preparar_governo(governo)

    # 4. Todos os arquivos nascem numa pasta temporária. A pasta oficial só é
    # substituída depois que a geração inteira termina sem erros.
    pasta_saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="Modelo_A_preparacao_", dir=pasta_saida.parent) as temporaria:
        pasta_preparacao = Path(temporaria)
        gerar_todos_resultados(governo, confrontos, validacao, pasta_preparacao)
        publicar_resultados(pasta_preparacao, pasta_saida)
    return pasta_saida


if __name__ == "__main__":
    # Este bloco só roda quando a pessoa executa diretamente "MODELO A.PY".
    # Erros esperados recebem mensagens curtas; uma base aberta no Excel costuma
    # provocar PermissionError no Windows, por isso há orientação específica.
    try:
        print(f"Resultados gerados em: {executar()}")
    except ErroModeloA as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        raise SystemExit(2)
    except PermissionError:
        print("Erro: feche a Base_nova_limpa.xlsx e as planilhas de resultado antes de rodar.", file=sys.stderr)
        raise SystemExit(2)
