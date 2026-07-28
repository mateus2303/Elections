"""
Modelo A — agregador histórico da eleição presidencial de 2018.

Uso: coloque este arquivo na mesma pasta de Base_nova_limpa.xlsx e execute
    python "MODELO A.PY"

São gerados três produtos regeneráveis: primeiro turno; Fernando Haddad × Jair
Bolsonaro em votos totais; e o mesmo confronto em votos válidos. A rotina não
usa resíduos para completar 100% e preserva valores ausentes como nulos.
"""
from __future__ import annotations

import math
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


PASTA = Path(__file__).resolve().parent
BASE = PASTA / "Base_nova_limpa.xlsx"
DESTINO = PASTA / "RESULTADOS_ATUAIS" / "Modelo_A_2018_Baseline_Historico"
JANELA_DIAS = 30
AMOSTRA_FALLBACK = 600
AMOSTRA_TETO = 5000
SERIES_1T = [
    "Lula", "Jair Bolsonaro", "Fernando Haddad", "Ciro Gomes",
    "Geraldo Alckmin", "Marina Silva", "Outros candidatos", "Branco/Nulo/Não sabe",
]
CORES = {
    "Lula": "#D62728", "Jair Bolsonaro": "#1F4E79", "Fernando Haddad": "#B2182B",
    "Ciro Gomes": "#E67E22", "Geraldo Alckmin": "#5B9BD5", "Marina Silva": "#2E8B57",
    "Outros candidatos": "#7F7F7F", "Branco/Nulo/Não sabe": "#9E9E9E",
}
COLUNAS = [
    "turno", "tipo_cenario", "cenario", "adversario", "nivel_geografico", "geografia", "segmento", "grupo",
    "instituto", "instituto_original", "data_inicio", "data_fim", "amostra_total", "amostra_segmento", "peso_qualidade",
    "base_voto", "percentual", "fonte_arquivo", "fonte_aba", "linha_origem",
]


def localizar_cabecalho(arquivo: Path, aba: str, esperadas: list[str]) -> pd.DataFrame:
    """Lê uma aba cuja linha de cabeçalho pode estar abaixo de título e observação."""
    bruto = pd.read_excel(arquivo, sheet_name=aba, header=None, dtype=object, engine="openpyxl")
    for indice in range(min(20, len(bruto))):
        linha = [str(valor).strip() if pd.notna(valor) else None for valor in bruto.iloc[indice].tolist()]
        if set(esperadas).issubset(set(linha)):
            dados = bruto.iloc[indice + 1:].copy()
            dados.columns = linha
            dados = dados.dropna(how="all")
            return dados[esperadas]
    raise ValueError(f"Não foi encontrado o cabeçalho de {aba}.")


def texto(valor: object) -> str:
    return "" if pd.isna(valor) else str(valor).strip()


def validar(confrontos: pd.DataFrame, institutos: pd.DataFrame) -> list[dict]:
    """Executa contratos mínimos de qualidade antes de qualquer cálculo."""
    achados: list[dict] = []
    if list(confrontos.columns) != COLUNAS:
        achados.append({"severidade": "Erro", "regra": "Esquema", "detalhe": "Colunas de Confrontos divergentes."})
        return achados
    confrontos["data_fim"] = pd.to_datetime(confrontos["data_fim"], errors="coerce")
    confrontos["percentual"] = pd.to_numeric(confrontos["percentual"], errors="coerce")
    for campo in ["data_fim", "instituto", "adversario", "turno", "cenario"]:
        faltantes = int(confrontos[campo].isna().sum()) if campo != "instituto" else int(confrontos[campo].map(texto).eq("").sum())
        if faltantes:
            achados.append({"severidade": "Erro", "regra": "Campo obrigatório", "detalhe": f"{campo}: {faltantes} ausências."})
    fora = confrontos[confrontos["percentual"].notna() & ~confrontos["percentual"].between(0, 100)]
    if not fora.empty:
        achados.append({"severidade": "Erro", "regra": "Percentual", "detalhe": f"{len(fora)} valores fora de 0–100."})
    duplicatas = confrontos.duplicated(["fonte_arquivo", "fonte_aba", "linha_origem", "adversario"], keep=False)
    if duplicatas.any():
        achados.append({"severidade": "Erro", "regra": "Duplicidade", "detalhe": f"{int(duplicatas.sum())} linhas duplicadas."})
    primeiro = confrontos[confrontos["turno"].map(texto).eq("1º turno")]
    segundo = confrontos[confrontos["turno"].map(texto).eq("2º turno")]
    if len(primeiro) != 1242:
        achados.append({"severidade": "Erro", "regra": "Cobertura 1º turno", "detalhe": f"Esperado 1242; encontrado {len(primeiro)}."})
    if len(segundo) != 76:
        achados.append({"severidade": "Erro", "regra": "Cobertura 2º turno", "detalhe": f"Esperado 76; encontrado {len(segundo)}."})
    cadastro = {texto(valor).casefold() for valor in institutos["instituto"].tolist()}
    desconhecidos = sorted({texto(valor) for valor in confrontos["instituto"].tolist() if texto(valor).casefold() not in cadastro})
    if desconhecidos:
        achados.append({"severidade": "Erro", "regra": "Instituto", "detalhe": f"Fora do cadastro: {', '.join(desconhecidos)}."})
    if not achados:
        achados.append({"severidade": "OK", "regra": "Validação", "detalhe": "Todos os contratos de entrada foram aprovados."})
    return achados


def peso(linha: pd.Series, data_referencia: pd.Timestamp) -> float:
    """Replica a estrutura de peso legado: qualidade, recência e amostra conservadora."""
    qualidade = float(linha["peso_qualidade"]) if pd.notna(linha["peso_qualidade"]) else 0.70
    amostra = float(linha["amostra_total"]) if pd.notna(linha["amostra_total"]) else AMOSTRA_FALLBACK
    dias = (data_referencia - linha["data"]).days
    recencia = max(0.0, 1.0 - dias / JANELA_DIAS)
    return (qualidade ** 0.50) * (recencia ** 0.25) * ((min(amostra, AMOSTRA_TETO) / AMOSTRA_TETO) ** 0.25)


def suavizar(pontos: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Suaviza cada série apenas nas datas publicadas, usando janela móvel de 30 dias."""
    saida, memoria = [], []
    for serie, grupo in pontos.groupby("serie", sort=False):
        grupo = grupo.sort_values("data").reset_index(drop=True)
        for data in grupo["data"].drop_duplicates().tolist():
            janela = grupo[(grupo["data"] <= data) & (grupo["data"] >= data - pd.Timedelta(days=JANELA_DIAS))].copy()
            janela["peso"] = janela.apply(lambda linha: peso(linha, data), axis=1)
            total_peso = janela["peso"].sum()
            estimativa = float(np.average(janela["valor_pct"], weights=janela["peso"]))
            variancia = float(np.average((janela["valor_pct"] - estimativa) ** 2, weights=janela["peso"])) if len(janela) > 1 else 0.0
            se = max(0.80, math.sqrt(variancia / max(1, len(janela))))
            saida.append({"data": data, "serie": serie, "estimativa_pct": estimativa, "ic_baixo_pct": max(0, estimativa - 1.96 * se), "ic_alto_pct": min(100, estimativa + 1.96 * se), "se_pp": se})
            memoria.extend(janela.assign(data_referencia=data, serie=serie, peso_normalizado=janela["peso"] / total_peso).to_dict("records"))
    return pd.DataFrame(saida), pd.DataFrame(memoria)


def compor_primeiro_turno(confrontos: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Monta uma observação por pesquisa e série, somando literalmente os demais candidatos."""
    bruto = confrontos[confrontos["turno"].map(texto).eq("1º turno")].copy()
    chaves = ["fonte_arquivo", "fonte_aba", "linha_origem", "instituto", "data_fim", "peso_qualidade", "amostra_total"]
    pontos = []
    for chave, grupo in bruto.groupby(chaves, dropna=False, sort=False):
        mapa = {texto(linha.adversario): float(linha.percentual) for linha in grupo.itertuples() if pd.notna(linha.percentual)}
        comum = {"Lula", "Jair Bolsonaro", "Fernando Haddad", "Ciro Gomes", "Geraldo Alckmin", "Marina Silva", "Branco/Nulo/Não sabe"}
        valores = {serie: mapa.get(serie) for serie in comum}
        outros = sum(valor for nome, valor in mapa.items() if nome not in comum)
        if outros or any(nome in mapa for nome in mapa if nome not in comum):
            valores["Outros candidatos"] = outros
        for serie, valor in valores.items():
            if valor is None:
                continue
            pontos.append({"data": chave[4], "serie": serie, "valor_pct": valor, "instituto": chave[3], "peso_qualidade": chave[5], "amostra_total": chave[6], "fonte_arquivo": chave[0], "fonte_aba": chave[1], "linha_origem": chave[2]})
    resultado = pd.DataFrame(pontos)
    return resultado, bruto


def compor_segundo_turno(confrontos: pd.DataFrame) -> pd.DataFrame:
    """Seleciona as duas séries nacionais do confronto Haddad × Bolsonaro em votos totais."""
    filtro = confrontos["turno"].map(texto).eq("2º turno") & confrontos["cenario"].map(texto).eq("Fernando Haddad × Jair Bolsonaro")
    bruto = confrontos[filtro].copy()
    bruto = bruto[bruto["adversario"].isin(["Fernando Haddad", "Jair Bolsonaro"])].copy()
    bruto.rename(columns={"data_fim": "data", "adversario": "serie", "percentual": "valor_pct"}, inplace=True)
    return bruto[["data", "serie", "valor_pct", "instituto", "peso_qualidade", "amostra_total", "fonte_arquivo", "fonte_aba", "linha_origem"]]


def estilo_cabecalho(ws, linha: int = 1) -> None:
    azul = "17365D"
    ws.freeze_panes = "A2"
    for celula in ws[linha]:
        celula.fill = PatternFill("solid", fgColor=azul)
        celula.font = Font(color="FFFFFF", bold=True)
        celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.sheet_view.showGridLines = False


def escrever_tabela(ws, dataframe: pd.DataFrame, formatos: dict[str, str] | None = None) -> None:
    """Escreve DataFrame como valores tipados em uma aba auditável, sem filtro ativo."""
    formatos = formatos or {}
    ws.append(list(dataframe.columns))
    for linha in dataframe.itertuples(index=False, name=None):
        ws.append([None if pd.isna(valor) else (valor.to_pydatetime() if isinstance(valor, pd.Timestamp) else valor) for valor in linha])
    estilo_cabecalho(ws)
    ws.auto_filter.ref = None
    ws.row_dimensions[1].height = 28
    for indice, coluna in enumerate(dataframe.columns, 1):
        tamanho = max(len(str(coluna)), *(len(str(valor)) for valor in dataframe[coluna].head(200).dropna().tolist()), 10)
        ws.column_dimensions[get_column_letter(indice)].width = min(max(tamanho + 2, 12), 34)
        if coluna in formatos:
            for celula in ws[get_column_letter(indice)][1:]:
                celula.number_format = formatos[coluna]
    for linha in ws.iter_rows(min_row=2):
        for celula in linha:
            celula.alignment = Alignment(vertical="top")


def criar_workbook_primeiro(serie: pd.DataFrame, pontos: pd.DataFrame, memoria: pd.DataFrame, bruto: pd.DataFrame, validacao: list[dict], imagem: Path, destino: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Series_suavizadas"
    escrever_tabela(ws, serie, {"data": "yyyy-mm-dd", "estimativa_pct": "0.0", "ic_baixo_pct": "0.0", "ic_alto_pct": "0.0", "se_pp": "0.00"})
    for titulo, dados, formatos in [
        ("Pontos_por_pesquisa", pontos, {"data": "yyyy-mm-dd", "valor_pct": "0.0", "peso_qualidade": "0.000000"}),
        ("Composicao_pesquisa", memoria, {"data": "yyyy-mm-dd", "data_referencia": "yyyy-mm-dd", "valor_pct": "0.0", "peso": "0.000000", "peso_normalizado": "0.000000"}),
        ("Cobertura", cobertura(serie, pontos), {"primeira_data": "yyyy-mm-dd", "ultima_data": "yyyy-mm-dd"}),
        ("Metodologia", metodologia("Primeiro turno: categorias publicadas; outros candidatos são soma literal dos nomes não destacados."), {}),
        ("Linhas_originais", bruto, {"data_inicio": "yyyy-mm-dd", "data_fim": "yyyy-mm-dd", "percentual": "0.0", "peso_qualidade": "0.000000"}),
        ("Validacao", pd.DataFrame(validacao), {}),
    ]:
        aba = wb.create_sheet(titulo)
        escrever_tabela(aba, dados, formatos)
    inserir_grafico(ws, imagem)
    wb.save(destino)


def cobertura(serie: pd.DataFrame, pontos: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for nome, grupo in serie.groupby("serie", sort=False):
        entradas = pontos[pontos["serie"] == nome]
        linhas.append({"serie": nome, "pontos_suavizados": len(grupo), "pesquisas_publicadas": len(entradas), "institutos": entradas["instituto"].nunique(), "primeira_data": grupo["data"].min(), "ultima_data": grupo["data"].max()})
    return pd.DataFrame(linhas)


def metodologia(escopo: str) -> pd.DataFrame:
    return pd.DataFrame([
        {"item": "Fonte", "valor": "Base_nova_limpa.xlsx — migração rastreável de POLELE05.xls"},
        {"item": "Peso", "valor": "qualidade^0,50 × recência linear^0,25 × amostra relativa^0,25"},
        {"item": "Janela", "valor": f"{JANELA_DIAS} dias; pontos somente nas datas publicadas"},
        {"item": "Amostra", "valor": f"fallback conservador de {AMOSTRA_FALLBACK} quando ausente na fonte"},
        {"item": "Escopo", "valor": escopo},
        {"item": "Não voto", "valor": "Apenas resposta publicada; sem residual."},
    ])


def inserir_grafico(ws, imagem: Path) -> None:
    """Inclui no workbook a mesma figura PNG gerada externamente, em área reservada."""
    if imagem.exists():
        figura = ExcelImage(str(imagem))
        figura.width, figura.height = 960, 520
        ws.add_image(figura, "H2")


def criar_workbook_segundo(serie: pd.DataFrame, pontos: pd.DataFrame, memoria: pd.DataFrame, validacao: list[dict], imagem: Path, destino: Path, denominador: str) -> None:
    wb = Workbook()
    wide = serie.pivot(index="data", columns="serie", values="estimativa_pct").reset_index().sort_values("data")
    baixo = serie.pivot(index="data", columns="serie", values="ic_baixo_pct").reset_index().sort_values("data")
    alto = serie.pivot(index="data", columns="serie", values="ic_alto_pct").reset_index().sort_values("data")
    ws = wb.active
    ws.title = "Suavizados"
    escrever_tabela(ws, wide, {"data": "yyyy-mm-dd", "Fernando Haddad": "0.0", "Jair Bolsonaro": "0.0"})
    inserir_grafico(ws, imagem)
    for titulo, dados, formatos in [
        ("IC_Baixo", baixo, {"data": "yyyy-mm-dd", "Fernando Haddad": "0.0", "Jair Bolsonaro": "0.0"}),
        ("IC_Alto", alto, {"data": "yyyy-mm-dd", "Fernando Haddad": "0.0", "Jair Bolsonaro": "0.0"}),
        ("Pesquisas_utilizadas", memoria, {"data": "yyyy-mm-dd", "data_referencia": "yyyy-mm-dd", "valor_pct": "0.0", "peso": "0.000000", "peso_normalizado": "0.000000"}),
        ("Cobertura", cobertura(serie, pontos), {"primeira_data": "yyyy-mm-dd", "ultima_data": "yyyy-mm-dd"}),
        ("Metodologia", metodologia(f"Segundo turno nacional Haddad × Bolsonaro — denominador: {denominador}."), {}),
        ("Validacao", pd.DataFrame(validacao), {}),
    ]:
        aba = wb.create_sheet(titulo)
        escrever_tabela(aba, dados, formatos)
    wb.save(destino)


def plotar(serie: pd.DataFrame, arquivo: Path, titulo: str, segundo_turno: bool = False) -> None:
    """Gera gráfico PNG legível com intervalo aproximado e marcadores eleitorais."""
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(13, 7.3), dpi=180)
    for nome, grupo in serie.groupby("serie", sort=False):
        grupo = grupo.sort_values("data")
        cor = CORES.get(nome, "#444444")
        ax.plot(grupo["data"], grupo["estimativa_pct"], label=nome, color=cor, linewidth=2.7)
        ax.fill_between(grupo["data"], grupo["ic_baixo_pct"], grupo["ic_alto_pct"], color=cor, alpha=0.09)
        ultimo = grupo.iloc[-1]
        ax.annotate(f"{nome}: {ultimo.estimativa_pct:.1f}%", xy=(ultimo.data, ultimo.estimativa_pct), xytext=(8, 0), textcoords="offset points", va="center", color=cor, fontsize=9, fontweight="bold")
    if segundo_turno:
        ax.axhline(50, color="#6B7280", lw=1.1, ls="--", alpha=.8)
        ax.axvline(pd.Timestamp("2018-10-07"), color="#6B7280", lw=1.1, ls="--", alpha=.75)
        ax.text(pd.Timestamp("2018-10-07"), 2, "1º turno\n07/out", color="#4B5563", fontsize=8, ha="left", va="bottom")
    ax.set_title(titulo, loc="left", fontsize=15, fontweight="bold", color="#17365D", pad=16)
    ax.text(0, 1.01, "Modelo A histórico • janela móvel de 30 dias • fonte: POLELE05.xls", transform=ax.transAxes, fontsize=9, color="#4B5563")
    ax.set_ylabel("Intenção de voto (%)")
    ax.set_ylim(0, 100 if segundo_turno else max(55, float(serie["ic_alto_pct"].max()) + 6))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.legend(ncol=2 if segundo_turno else 4, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.13))
    ax.grid(axis="y", color="#DDE6EE")
    ax.grid(axis="x", visible=False)
    # Margens explícitas impedem que títulos longos, especialmente "votos válidos",
    # sejam cortados na exportação PNG ou quando inseridos novamente no Excel.
    fig.subplots_adjust(left=0.07, right=0.91, top=0.88, bottom=0.18)
    fig.savefig(arquivo, facecolor="white")
    plt.close(fig)


def validar_saida(serie: pd.DataFrame, segundo: bool = False) -> None:
    """Bloqueia a publicação se o agregado estiver fora da escala ou se válidos não fecharem 100%."""
    if serie.empty or not serie["estimativa_pct"].between(0, 100).all():
        raise ValueError("Série agregada vazia ou fora da escala de 0–100.")
    if segundo:
        checagem = serie.pivot(index="data", columns="serie", values="estimativa_pct")
        if not np.allclose(checagem["Fernando Haddad"] + checagem["Jair Bolsonaro"], 100, atol=1e-9):
            raise ValueError("Votos válidos não fecham 100%.")


def main() -> None:
    if not BASE.exists():
        raise FileNotFoundError(f"Base ausente: {BASE}")
    confrontos = localizar_cabecalho(BASE, "Confrontos", COLUNAS)
    institutos = localizar_cabecalho(BASE, "Institutos", ["instituto", "aliases", "peso_legacy", "situacao"])
    achados = validar(confrontos, institutos)
    if any(item["severidade"] == "Erro" for item in achados):
        detalhes = "\n".join(f"- {item['regra']}: {item['detalhe']}" for item in achados)
        raise ValueError(f"A base não passou na validação:\n{detalhes}")

    primeiro_pontos, primeiro_bruto = compor_primeiro_turno(confrontos)
    primeiro, memoria_primeiro = suavizar(primeiro_pontos)
    primeiro = primeiro[primeiro["serie"].isin(SERIES_1T)].copy()
    validar_saida(primeiro)

    segundo_pontos = compor_segundo_turno(confrontos)
    segundo_total, memoria_segundo = suavizar(segundo_pontos)
    validar_saida(segundo_total)
    base_validos = segundo_total.pivot(index="data", columns="serie", values="estimativa_pct")
    base_validos = base_validos.dropna(subset=["Fernando Haddad", "Jair Bolsonaro"]).copy()
    base_validos["denominador"] = base_validos["Fernando Haddad"] + base_validos["Jair Bolsonaro"]
    validos = []
    for data, linha in base_validos.iterrows():
        for candidato in ["Fernando Haddad", "Jair Bolsonaro"]:
            percentual = 100 * linha[candidato] / linha["denominador"]
            validos.append({"data": data, "serie": candidato, "estimativa_pct": percentual, "ic_baixo_pct": max(0, percentual - 1.96), "ic_alto_pct": min(100, percentual + 1.96), "se_pp": 1.0})
    segundo_validos = pd.DataFrame(validos)
    validar_saida(segundo_validos, segundo=True)

    with tempfile.TemporaryDirectory(prefix="modelo_a_2018_") as temporario:
        trabalho = Path(temporario)
        grafico_1 = trabalho / "01_Primeiro_Turno_2018.png"
        grafico_2 = trabalho / "02_Segundo_Turno_2018_Haddad_vs_Bolsonaro_Votos_Totais.png"
        grafico_3 = trabalho / "03_Segundo_Turno_2018_Haddad_vs_Bolsonaro_Votos_Validos.png"
        plotar(primeiro, grafico_1, "Agregador de pesquisas — 1º turno presidencial de 2018")
        plotar(segundo_total, grafico_2, "Agregador de pesquisas — Haddad × Bolsonaro (votos totais)", segundo_turno=True)
        plotar(segundo_validos, grafico_3, "Agregador de pesquisas — Haddad × Bolsonaro (votos válidos)", segundo_turno=True)
        criar_workbook_primeiro(primeiro, primeiro_pontos, memoria_primeiro, primeiro_bruto, achados, grafico_1, trabalho / "01_Primeiro_Turno_2018.xlsx")
        criar_workbook_segundo(segundo_total, segundo_pontos, memoria_segundo, achados, grafico_2, trabalho / "02_Segundo_Turno_2018_Haddad_vs_Bolsonaro_Votos_Totais.xlsx", "votos totais")
        criar_workbook_segundo(segundo_validos, segundo_pontos, memoria_segundo, achados, grafico_3, trabalho / "03_Segundo_Turno_2018_Haddad_vs_Bolsonaro_Votos_Validos.xlsx", "votos válidos")
        destino_temporario = trabalho / "publicacao"
        destino_temporario.mkdir()
        for arquivo in trabalho.glob("*.png"):
            shutil.copy2(arquivo, destino_temporario / arquivo.name)
        for arquivo in trabalho.glob("*.xlsx"):
            shutil.copy2(arquivo, destino_temporario / arquivo.name)
        # O OneDrive pode manter o diretório aberto durante a sincronização. Em vez
        # de removê-lo inteiro, atualizamos somente os seis arquivos estáveis; isso
        # preserva a pasta e evita falha transitória de acesso negado no Windows.
        DESTINO.mkdir(parents=True, exist_ok=True)
        for origem in destino_temporario.iterdir():
            destino_final = DESTINO / origem.name
            ultima_excecao = None
            for _ in range(10):
                try:
                    shutil.copy2(origem, destino_final)
                    ultima_excecao = None
                    break
                except PermissionError as excecao:
                    ultima_excecao = excecao
                    time.sleep(0.3)
            if ultima_excecao is not None:
                raise ultima_excecao

    print("Modelo A histórico 2018 concluído.")
    print(f"Resultados: {DESTINO}")
    for arquivo in sorted(DESTINO.iterdir()):
        print(f"- {arquivo.name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        raise
