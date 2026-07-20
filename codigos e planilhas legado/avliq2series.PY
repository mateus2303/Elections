import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Sheets
sheet_3 = "padrao e tracking mm7d"

# Leitura da planilha
BASE_DIR = Path(__file__).resolve().parent

df = pd.read_excel(
    BASE_DIR / "input_agregador.xlsx",
    sheet_name=sheet_3
)

# Definição dos índices disponíveis
indice_1 = "Índice Pindograma"
indice_2 = "Índice Pollstergraph"
indice_3 = "Ranking V1T"
indice_4 = "Ranking B1T"
indice_5 = "Ranking L1T"
indice_6 = "Ranking 2T"
indice_7 = "Ranking MV"
indice_8 = "Ranking MB"
indice_9 = "Ranking ML"

df['data'] = pd.to_datetime(df['data'])

# Parâmetros de pesos (média geométrica ponderada)
w_qualidade = 0.50
w_tempo     = 0.25
w_amostra   = 0.25
cap_amostra = 5000

# Nomes padrão das componentes de avaliação (se existirem)
col_approve    = 'Ótimo/Bom'
col_disapprove = 'Ruim/Péssimo'

def calcular_serie_suavizada_com_ic(
    df,
    indice_qualidade,
    janela_dias,
    coluna_valor='aprov liq',
    wq=w_qualidade,
    wt=w_tempo,
    wa=w_amostra,
    cap_amostra=cap_amostra,
    col_approve=col_approve,
    col_disapprove=col_disapprove
):
    """
    Retorna DataFrame indexado por data com:
    - <coluna_valor>_suavizado
    - ci_low
    - ci_high
    - se_pp  (erro-padrão em pontos percentuais)

    Média ponderada por janela (pesos geométricos: qualidade, tempo, amostra).
    IC 95%:
      - Se col_approve e col_disapprove existem: usa Var(A-D) ≈ Var(A)+Var(D) com variâncias binomiais e pesos normalizados.
      - Caso contrário: fallback conservador com Var(A-D) ≤ 0.5/n (pior caso binomial), ponderado pelos mesmos pesos.
    """
    # Checagens mínimas
    required = ['data', 'Amostra', indice_qualidade, coluna_valor]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes para cálculo: {missing}")

    # Vetores pré-calculados (evita mutação do df e acelera loop)
    datas = df['data']
    datas_unicas = datas.sort_values().unique()
    qual = df[indice_qualidade].astype(float)
    amostra_norm = (df['Amostra'].clip(upper=cap_amostra) / cap_amostra).astype(float)
    amostra_raw = df['Amostra'].clip(upper=cap_amostra).astype(float)
    valores = df[coluna_valor].astype(float)

    has_components = (col_approve in df.columns) and (col_disapprove in df.columns)
    if has_components:
        A = (df[col_approve].astype(float) / 100.0).clip(0.0, 1.0)
        D = (df[col_disapprove].astype(float) / 100.0).clip(0.0, 1.0)

    suav, lo, hi, se_pp = [], [], [], []

    for data_alvo in datas_unicas:
        diff = (data_alvo - datas).dt.days
        mask = (diff >= 0) & (diff <= janela_dias)
        if not mask.any():
            suav.append(np.nan); lo.append(np.nan); hi.append(np.nan); se_pp.append(np.nan)
            continue

        vals = valores[mask]
        qual_loc = qual[mask]
        amostra_loc = amostra_norm[mask]
        amostra_i = amostra_raw[mask]
        peso_tempo = 1.0 - (diff[mask].astype(float) / float(janela_dias))

        # Pesos geométricos
        weights = (qual_loc ** wq) * (peso_tempo ** wt) * (amostra_loc ** wa)

        # Remover NaNs alinhados
        valid = vals.notna() & np.isfinite(weights)
        if not valid.any() or np.nansum(weights[valid]) <= 0:
            suav.append(np.nan); lo.append(np.nan); hi.append(np.nan); se_pp.append(np.nan)
            continue

        # Média ponderada suavizada (em p.p)
        w = weights[valid].to_numpy()
        x = vals[valid].to_numpy()
        sw = w.sum()
        alpha = w / sw
        x_hat_pp = np.sum(alpha * x)

        # Variância (proporção) por pesquisa
        if has_components:
            a_i = A[mask][valid].to_numpy()
            d_i = D[mask][valid].to_numpy()
            n_i = amostra_i[valid].to_numpy()
            var_a = a_i * (1.0 - a_i) / n_i
            var_d = d_i * (1.0 - d_i) / n_i
            var_liq_prop = var_a + var_d  # Var(A-D)
        else:
            # Fallback conservador: Var(A-D) ≤ 0.5/n_i
            n_i = amostra_i[valid].to_numpy()
            var_liq_prop = 0.5 / n_i

        # Variância do estimador ponderado
        var_hat_prop = np.sum((alpha**2) * var_liq_prop)
        se_hat_prop = np.sqrt(var_hat_prop)

        # Converter erro-padrão para p.p
        se_hat_pp = se_hat_prop * 100.0

        # IC 95% (em p.p)
        z = 1.96
        lo_pp = x_hat_pp - z * se_hat_pp
        hi_pp = x_hat_pp + z * se_hat_pp
        # Clareza: aprovação líquida pode ser negativa; clamp suave a [-100, 100]
        lo_pp = max(lo_pp, -100.0)
        hi_pp = min(hi_pp,  100.0)

        suav.append(x_hat_pp)
        lo.append(lo_pp)
        hi.append(hi_pp)
        se_pp.append(se_hat_pp)

    out = pd.DataFrame({
        'data': datas_unicas,
        f"{coluna_valor.replace(' ', '_')}_suavizado": suav,
        'ci_low': lo,
        'ci_high': hi,
        'se_pp': se_pp
    }).set_index('data')

    return out

# ------- Configurações para as duas séries --------
indice_serie1 = indice_1    
janela_serie1 = 15

indice_serie2 = indice_1    
janela_serie2 = 30

# Calcular as duas séries com IC 95%
df_s1 = calcular_serie_suavizada_com_ic(df, indice_serie1, janela_serie1, coluna_valor='aprov liq')
df_s2 = calcular_serie_suavizada_com_ic(df, indice_serie2, janela_serie2, coluna_valor='aprov liq')

# Plot conjunto
plt.figure(figsize=(14,7))

# Dados originais (dispersão)
plt.scatter(df['data'], df['aprov liq'], color='gray', alpha=0.25, s=20, label='Pesquisas Originais')

# Série 1
col_s1 = df_s1.filter(like='_suavizado').columns[0]
plt.plot(df_s1.index.to_numpy(), df_s1[col_s1].to_numpy(), color='blue',
         label=f'{indice_serie1}, janela = {janela_serie1} dias', linewidth=2)
plt.fill_between(df_s1.index.to_numpy(), df_s1['ci_low'].to_numpy(), df_s1['ci_high'].to_numpy(),
                 color='blue', alpha=0.15)
# Anotação último ponto
y1_last = df_s1[col_s1].iloc[-1]
if pd.notna(y1_last):
    plt.annotate(f"{y1_last:.2f}", (df_s1.index[-1], y1_last),
                 textcoords="offset points", xytext=(0, -15), ha='left', color='blue', fontsize=12)

# Série 2
col_s2 = df_s2.filter(like='_suavizado').columns[0]
plt.plot(df_s2.index.to_numpy(), df_s2[col_s2].to_numpy(), color='red',
         label=f'{indice_serie2}, janela = {janela_serie2} dias', linewidth=2)
plt.fill_between(df_s2.index.to_numpy(), df_s2['ci_low'].to_numpy(), df_s2['ci_high'].to_numpy(),
                 color='red', alpha=0.15)
# Anotação último ponto
y2_last = df_s2[col_s2].iloc[-1]
if pd.notna(y2_last):
    plt.annotate(f"{y2_last:.2f}", (df_s2.index[-1], y2_last),
                 textcoords="offset points", xytext=(0, 10), ha='left', color='red', fontsize=12)

plt.title('Avaliação Líquida do Governo Lula III (duas séries com IC 95%)')
plt.xlabel('Data')
plt.ylabel('Avaliação Líquida (p.p.)')
plt.legend()
plt.grid(True)

# Limitar janela só na visualização (sem cortar df)
inicio_plot = pd.Timestamp(2023, 2, 1)
plt.xlim(inicio_plot, max(df_s1.index.max(), df_s2.index.max()))

plt.show()

# Salvar dados das duas séries em Excel
with pd.ExcelWriter(BASE_DIR / 'output_avaliacao_liquida_duas_series.xlsx') as writer:
    df_s1.to_excel(writer, sheet_name='Serie_Janela_15d')
    df_s2.to_excel(writer, sheet_name='Serie_Janela_100d')
