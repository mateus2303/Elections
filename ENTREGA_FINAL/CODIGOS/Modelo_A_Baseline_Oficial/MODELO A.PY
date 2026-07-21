"""MODELO A — agregador eleitoral autocontido.

Uso:
    python "MODELO A.PY"

O arquivo procura ``Base_nova_limpa.xlsx`` nesta pasta ou dois níveis acima
(a estrutura ``ENTREGA_FINAL/CODIGOS/Modelo_A_Baseline_Oficial``). Os
resultados são gravados em ``RESULTADOS_ATUAIS/Modelo_A_Baseline_Oficial`` ao
lado da base. Os confrontos contra Renan e Caiado e o gráfico de primeiro turno
são criados automaticamente quando houver dados publicados compatíveis. No
primeiro turno, cada candidato recebe a média dos cenários em que foi testado
dentro da mesma pesquisa antes da suavização temporal. Não importa nem executa
nenhum outro código deste projeto. As aberturas por sexo e religião são geradas
somente quando os grupos publicados oferecerem cobertura suficiente.

Dependências do Python (instalar uma vez no outro computador, se necessário):
    python -m pip install pandas numpy openpyxl matplotlib
"""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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


class ErroModeloA(ValueError):
    """Erro de base ou de estrutura que impede a geração dos resultados."""


@dataclass(frozen=True)
class SerieSuavizada:
    valores: pd.DataFrame
    pontos_publicados: pd.DataFrame


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
            return candidato, candidato.parent / "RESULTADOS_ATUAIS" / "Modelo_A_Baseline_Oficial"
    locais = "\n".join(f"- {candidato}" for candidato in candidatos)
    raise ErroModeloA(
        "Não encontrei Base_nova_limpa.xlsx. Deixe a base nesta pasta ou mantenha a "
        "estrutura ENTREGA_FINAL/CODIGOS/Modelo_A_Baseline_Oficial. Procurei em:\n" + locais
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
    raise ErroModeloA(
        f"Não foi localizado o cabeçalho operacional da aba '{nome_aba}'. "
        f"Campos esperados: {', '.join(obrigatorias[:4])}..."
    )


def ler_aba(caminho_base: Path, nome_aba: str, obrigatorias: list[str]) -> pd.DataFrame:
    try:
        bruto = pd.read_excel(caminho_base, sheet_name=nome_aba, header=None, dtype=object, engine="openpyxl")
    except ValueError as erro:
        raise ErroModeloA(f"Aba obrigatória ausente: '{nome_aba}'.") from erro
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
    """Replica a média ponderada e o intervalo de 95% do agregador legado."""
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
    manter = [*chaves, "cenario", "candidato", "valor_pct", "peso_legacy", "amostra_total", "amostra_segmento"]
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
        raise ErroModeloA(f"Não há observações válidas para gerar '{nome}'.")
    return serie


def escrever_planilha(caminho: Path, abas: dict[str, pd.DataFrame], indice: bool = True) -> None:
    with pd.ExcelWriter(caminho, engine="openpyxl", datetime_format="yyyy-mm-dd", date_format="yyyy-mm-dd") as escritor:
        for nome_aba, tabela in abas.items():
            tabela.to_excel(escritor, sheet_name=nome_aba, index=indice)
    from openpyxl import load_workbook

    livro = load_workbook(caminho)
    for aba in livro.worksheets:
        for linha in aba.iter_rows():
            for celula in linha:
                if hasattr(celula.value, "year") and hasattr(celula.value, "month") and hasattr(celula.value, "day"):
                    celula.number_format = "yyyy-mm-dd"
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
    eixo.set_title("Avaliação do Governo Lula III", fontsize=16)
    eixo.set_xlabel("Data")
    eixo.set_ylabel("Percentual")
    eixo.grid(True, alpha=0.35)
    eixo.legend()
    eixo.set_xlim(pd.Timestamp("2023-02-01"), None)
    figura.tight_layout()
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def grafico_liquido(serie_15: SerieSuavizada, serie_30: SerieSuavizada, caminho: Path) -> None:
    figura, eixo = plt.subplots(figsize=(14, 7))
    eixo.scatter(serie_15.pontos_publicados["data_referencia"], serie_15.pontos_publicados["valor_pct"], color="gray", alpha=0.25, s=20)
    for rotulo, cor, serie in [("Janela 15 dias", "blue", serie_15), ("Janela 30 dias", "red", serie_30)]:
        eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2, label=rotulo)
        eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cor, alpha=0.15)
        ultimo = serie.valores.iloc[-1]
        eixo.text(serie.valores.index[-1], ultimo["estimativa_pct"], f" {ultimo['estimativa_pct']:.2f}", color=cor, va="center")
    eixo.axhline(0, color="black", linewidth=0.8)
    eixo.set_title("Avaliação Líquida do Governo Lula III (duas séries com IC 95%)", fontsize=16)
    eixo.set_xlabel("Data")
    eixo.set_ylabel("Pontos percentuais")
    eixo.grid(True, alpha=0.35)
    eixo.legend()
    eixo.set_xlim(pd.Timestamp("2023-02-01"), None)
    figura.tight_layout()
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def grafico_segundo_turno(lula: SerieSuavizada, adversario: SerieSuavizada, nome_adversario: str, caminho: Path) -> None:
    figura, eixo = plt.subplots(figsize=(14, 7))
    for rotulo, cor, serie in [("Lula", "red", lula), (nome_adversario, "blue", adversario)]:
        eixo.scatter(serie.pontos_publicados["data_referencia"], serie.pontos_publicados["valor_pct"], color=cor, alpha=0.25, s=20)
        eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2, label=rotulo)
        eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cor, alpha=0.15)
        ultimo = serie.valores.iloc[-1]
        eixo.text(serie.valores.index[-1], ultimo["estimativa_pct"], f" {ultimo['estimativa_pct']:.2f}%", color=cor, va="center")
    eixo.set_title(f"Segundo Turno 2026: Lula vs {nome_adversario} (suavização geométrica + IC 95%)", fontsize=16)
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
    figura.suptitle("Avaliação do Governo Lula III por sexo (suavização de 30 dias + IC 95%)", fontsize=16)
    figura.text(0.5, 0.03, "Pontos: resultados publicados. As faixas usam a amostra do segmento quando publicada; caso contrário, aplicam fallback conservador.", ha="center", fontsize=9, color="#444444")
    figura.subplots_adjust(bottom=0.18, top=0.86, wspace=0.08)
    figura.savefig(caminho, dpi=160, bbox_inches="tight")
    plt.close(figura)


def grafico_liquido_por_sexo(
    series_por_grupo: dict[str, tuple[SerieSuavizada, SerieSuavizada]],
    caminho: Path,
) -> None:
    figura, eixos = plt.subplots(1, 2, figsize=(18, 8), sharey=True)
    for eixo, grupo in zip(eixos, ["Mulheres", "Homens"], strict=True):
        serie_15, serie_30 = series_por_grupo[grupo]
        eixo.scatter(serie_15.pontos_publicados["data_referencia"], serie_15.pontos_publicados["valor_pct"], color="gray", alpha=0.25, s=22)
        for rotulo, cor, serie in [("Janela 15 dias", "blue", serie_15), ("Janela 30 dias", "red", serie_30)]:
            eixo.plot(serie.valores.index, serie.valores["estimativa_pct"], color=cor, linewidth=2.1, label=rotulo)
            eixo.fill_between(serie.valores.index, serie.valores["ic_baixo_pct"], serie.valores["ic_alto_pct"], color=cor, alpha=0.10)
        eixo.axhline(0, color="black", linewidth=0.8)
        eixo.set_title(grupo)
        eixo.set_xlabel("Data")
        eixo.grid(True, alpha=0.30)
    eixos[0].set_ylabel("Pontos percentuais")
    identificadores, rotulos = eixos[0].get_legend_handles_labels()
    figura.legend(identificadores, rotulos, loc="lower center", ncol=2, frameon=False)
    figura.suptitle("Avaliação líquida do Governo Lula III por sexo (IC 95%)", fontsize=16)
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
    metodologia = pd.DataFrame({"item": ["Universo", "Grupos", "Amostra e IC", "Interpretação"], "descricao": ["Brasil, abertura publicada de sexo.", "Rótulos FEM/Feminino e MAS/Masculino são harmonizados como Mulheres e Homens.", "Usa amostra do segmento quando publicada; na ausência, o código aplica o fallback conservador já usado para aberturas.", "As curvas são agregados de pesquisas disponíveis; não são previsão eleitoral."]})
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
        eixo.set_title(grupo)
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
    figura.suptitle(f"Segundo turno 2026: Lula vs {nome_adversario} por {titulo_abertura} (IC 95%)", fontsize=16)
    figura.text(0.5, 0.03, "Pontos: resultados publicados em votos válidos. As faixas usam a amostra do segmento quando publicada; caso contrário, aplicam fallback conservador.", ha="center", fontsize=9, color="#444444")
    figura.subplots_adjust(bottom=0.15, top=0.90, hspace=0.25, wspace=0.08)
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
    metodologia = pd.DataFrame({"item": ["Universo", "Abertura", "Medida", "Amostra e IC", "Interpretação"], "descricao": [f"Brasil, 2º turno, estimulada, Lula × {nome_adversario}.", f"Grupos publicados de {titulo_abertura}; rótulos equivalentes são harmonizados conforme a aba Metodologia.", "Lula e adversário convertidos para votos válidos dentro de cada grupo.", "Usa amostra do segmento quando publicada; na ausência, o código aplica fallback conservador e isso não equivale à margem de erro total da pesquisa.", "As curvas são agregados de pesquisas disponíveis; não são previsão eleitoral."]})
    abas["Cobertura"] = cobertura
    abas["Metodologia"] = metodologia
    abas["Linhas_publicadas"] = linhas.sort_values(["data_referencia", "grupo_abertura"])
    escrever_planilha(pasta_saida / f"{nome_saida}.xlsx", abas, indice=False)
    grafico_segundo_turno_por_abertura(series_por_grupo, nome_adversario, titulo_abertura, pasta_saida / f"{nome_saida}.png")
    return True


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
    eixo.set_title("Primeiro turno 2026 — média harmonizada dos cenários estimulados", fontsize=16, pad=18)
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
        "A curva não é previsão eleitoral.",
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
            institutos=("instituto", lambda valores: ", ".join(sorted(set(map(str, valores))))),
        )
        .reset_index()
    )
    metodologia = pd.DataFrame(
        {
            "item": [
                "Candidatos incluídos", "Universo", "Harmonização por cenário", "Candidato ausente", "Suavização", "Interpretação",
            ],
            "descricao": [
                "Lula, Flávio, Renan Santos, Romeu Zema, Ronaldo Caiado e Michelle Bolsonaro.",
                "Brasil, Total, 1º turno, estimulada e votos totais, independentemente do rótulo do cenário.",
                "Em cada onda e para cada candidato, a observação é a média simples dos cenários em que o candidato foi testado. A mesma pesquisa entra uma única vez por candidato.",
                "Ausência em uma lista não é interpretada como 0%. O candidato só é calculado nos cenários em que aparece publicado.",
                "Média ponderada do baseline legado em janela de 30 dias sobre as observações já harmonizadas por candidato.",
                "É uma média de cenários disponíveis para acompanhamento. Não é previsão de resultado eleitoral nem probabilidade de vitória.",
            ],
        }
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
    abas: dict[str, pd.DataFrame] = {}
    for nome_aba, coluna in [("Suavizados", "estimativa_pct"), ("IC_Baixo", "ic_baixo_pct"), ("IC_Alto", "ic_alto_pct")]:
        tabela = pd.concat(
            [lula.valores[coluna].rename("Lula"), adversario.valores[coluna].rename(nome_adversario)], axis=1
        ).sort_index()
        tabela.index.name = "data"
        abas[nome_aba] = tabela
    escrever_planilha(pasta_saida / f"{nome_saida}.xlsx", abas)
    grafico_segundo_turno(lula, adversario, nome_adversario, pasta_saida / f"{nome_saida}.png")
    return True


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
        raise ErroModeloA("Não há avaliação nacional total na aba Lula3.")

    composicao = {
        "Ótimo/Bom": exigir(suavizar(governo_total, "otimo_bom_pct", 30), "Ótimo/Bom"),
        "Regular": exigir(suavizar(governo_total, "regular_pct", 30), "Regular"),
        "Ruim/Péssimo": exigir(suavizar(governo_total, "ruim_pessimo_pct", 30), "Ruim/Péssimo"),
    }
    fonte_liquida = governo_total.loc[governo_total["otimo_bom_pct"].map(presente) & governo_total["ruim_pessimo_pct"].map(presente)].copy()
    fonte_liquida["avaliacao_liquida_pct"] = fonte_liquida["otimo_bom_pct"] - fonte_liquida["ruim_pessimo_pct"]
    liquida_15 = exigir(suavizar(fonte_liquida, "avaliacao_liquida_pct", 15, ("otimo_bom_pct", "ruim_pessimo_pct"), (-100.0, 100.0)), "Avaliação líquida em 15 dias")
    liquida_30 = exigir(suavizar(fonte_liquida, "avaliacao_liquida_pct", 30, ("otimo_bom_pct", "ruim_pessimo_pct"), (-100.0, 100.0)), "Avaliação líquida em 30 dias")

    pasta_saida.mkdir(parents=True, exist_ok=True)
    suavizados = pd.concat([serie.valores["estimativa_pct"].rename(nome) for nome, serie in composicao.items()], axis=1).sort_index()
    ic_baixo = pd.concat([serie.valores["ic_baixo_pct"].rename(nome) for nome, serie in composicao.items()], axis=1).sort_index()
    ic_alto = pd.concat([serie.valores["ic_alto_pct"].rename(nome) for nome, serie in composicao.items()], axis=1).sort_index()
    for tabela in (suavizados, ic_baixo, ic_alto):
        tabela.index.name = "data"
    escrever_planilha(pasta_saida / f"{NOME_GRAFICO_GOVERNO}.xlsx", {"Suavizados": suavizados, "IC_Baixo": ic_baixo, "IC_Alto": ic_alto})

    abas_liquida: dict[str, pd.DataFrame] = {}
    for nome_aba, serie in [("Serie_Janela_15d", liquida_15), ("Serie_Janela_30d", liquida_30)]:
        tabela = serie.valores.reset_index().rename(columns={"estimativa_pct": "aprov_liq_suavizado", "ic_baixo_pct": "ci_low", "ic_alto_pct": "ci_high"})
        abas_liquida[nome_aba] = tabela[["data", "aprov_liq_suavizado", "ci_low", "ci_high", "se_pp"]]
    escrever_planilha(pasta_saida / f"{NOME_GRAFICO_LIQUIDO}.xlsx", abas_liquida, indice=False)

    grafico_governo(composicao, pasta_saida / f"{NOME_GRAFICO_GOVERNO}.png")
    grafico_liquido(liquida_15, liquida_30, pasta_saida / f"{NOME_GRAFICO_LIQUIDO}.png")
    gerar_governo_por_sexo(governo, pasta_saida)
    cenarios = [
        ("Flavio", "flavio", NOME_GRAFICO_SEGUNDO_TURNO),
        ("Renan", "renan", NOME_GRAFICO_SEGUNDO_TURNO_RENAN),
        ("Caiado", "caiado", NOME_GRAFICO_SEGUNDO_TURNO_CAIADO),
    ]
    for nome_adversario, termo_adversario, nome_saida in cenarios:
        gerado = gerar_segundo_turno(confrontos, nome_adversario, termo_adversario, nome_saida, pasta_saida)
        if nome_adversario == "Flavio" and not gerado:
            raise ErroModeloA("A base não possui o cenário nacional, estimulado, de 2º turno Lula × Flávio.")
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
    return pasta_saida


if __name__ == "__main__":
    try:
        print(f"Resultados gerados em: {executar()}")
    except ErroModeloA as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        raise SystemExit(2)
    except PermissionError:
        print("Erro: feche a Base_nova_limpa.xlsx e as planilhas de resultado antes de rodar.", file=sys.stderr)
        raise SystemExit(2)
