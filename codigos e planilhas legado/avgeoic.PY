import pandas as pd  
import numpy as np 
import matplotlib.pyplot as plt  
from pathlib import Path

# Sheets
sheet_3 = "padrao e tracking mm7d"
BASE_DIR = Path(__file__).resolve().parent

df = pd.read_excel(
    BASE_DIR / "input_agregador.xlsx",
    sheet_name=sheet_3
) 

# Índices (somente o usado)
indice_1 = "Índice Pindograma"
indice_2 = "Índice Pollstergraph"
indice_3 = "Ranking V1T"
indice_4 =	"Ranking B1T"
indice_5 =	"Ranking L1T"
indice_6 = 	"Ranking 2T"
indice_7 =	"Ranking MV"
indice_8 =	"Ranking MB"
indice_9 =	"Ranking ML"


# Formatar coluna data
df['data'] = pd.to_datetime(df['data'])

# Pesos base
df['peso_qualidade'] = df[indice_1]
df['peso_amostra']   = (df['Amostra'].clip(upper=5000) / 5000)

# Parâmetros de pesos e janela
w_qualidade = 0.50
w_tempo     = 0.25
w_amostra   = 0.25
janela_dias = 30

#Data de início dos gráficos
inicio = pd.Timestamp(2023, 2, 1)

# Colunas de interesse (percentuais 0–100)
colunas = ['Ótimo/Bom', 'Regular', 'Ruim/Péssimo']

def suavizacao_com_ic(df, data_alvo, coluna, janela_dias=30):
    """
    Retorna (p_hat_percent, ic_low_percent, ic_high_percent)
    onde p_hat é a média ponderada suavizada em percentuais (0–100),
    e IC 95% calculado via variância binomial e pesos normalizados.
    """
    diff = (data_alvo - df['data']).dt.days
    mask = (diff >= 0) & (diff <= janela_dias)
    df_f = df.loc[mask, ['data', 'Amostra', 'peso_qualidade', 'peso_amostra', coluna]].copy()

    # Remover NaNs na coluna
    df_f = df_f.dropna(subset=[coluna])
    if df_f.empty:
        return np.nan, np.nan, np.nan

    # Peso de tempo (decaimento linear)
    df_f['peso_tempo'] = 1 - (diff[mask] / janela_dias)

    # Peso total (média geométrica ponderada dos componentes)
    weights = (
        (df_f['peso_qualidade'] ** w_qualidade) *
        (df_f['peso_tempo']     ** w_tempo)     *
        (df_f['peso_amostra']   ** w_amostra)
    )

    sum_w = weights.sum()
    if not np.isfinite(sum_w) or sum_w <= 0:
        return np.nan, np.nan, np.nan

    # Média ponderada em proporção (0–1)
    p_i = (df_f[coluna] / 100.0).astype(float)
    alpha = weights / sum_w  # pesos normalizados

    # Média suavizada
    p_hat = np.sum(alpha * p_i)

    # Variância do estimador ponderado (assumindo independência)
    # var(p_hat) = sum(alpha_i^2 * var_i), com var_i = p_i(1-p_i)/n_i
    n_i = df_f['Amostra'].clip(upper=5000).astype(float)
    var_i = p_i * (1.0 - p_i) / n_i
    var_hat = np.sum((alpha**2) * var_i)

    # Erro padrão e IC 95% (aproximação normal)
    se_hat = np.sqrt(var_hat)
    z = 1.96
    ci_low = p_hat - z * se_hat
    ci_high = p_hat + z * se_hat

    # Clampar ao intervalo [0,1]
    ci_low = max(0.0, ci_low)
    ci_high = min(1.0, ci_high)

    # Retornar em percentuais (0–100)
    return p_hat * 100.0, ci_low * 100.0, ci_high * 100.0

# Datas únicas
datas_unicas = df['data'].sort_values().unique()

# DFs de resultado
df_suavizados = pd.DataFrame({'data': datas_unicas})
df_suavizados.set_index('data', inplace=True)

df_ci_low = pd.DataFrame(index=datas_unicas)
df_ci_high = pd.DataFrame(index=datas_unicas)

# Calcular séries suavizadas e ICs
for col in colunas:
    vals = []
    lows = []
    highs = []
    for data_ref in datas_unicas:
        p_hat, ci_low, ci_high = suavizacao_com_ic(df, data_ref, col, janela_dias=janela_dias)
        vals.append(p_hat)
        lows.append(ci_low)
        highs.append(ci_high)
    df_suavizados[col] = vals
    df_ci_low[col] = lows
    df_ci_high[col] = highs

# Plot
plt.figure(figsize=(16, 8))

cores = {'Ótimo/Bom': 'green', 'Regular': 'orange', 'Ruim/Péssimo': 'red'}

# Pontos originais (dispersão)
for col in colunas:
    plt.scatter(df['data'], df[col], color=cores[col], alpha=0.15, s=20)

# Linhas suavizadas e bandas de IC
for col in colunas:
    plt.plot(df_suavizados.index.to_numpy(), df_suavizados[col].to_numpy(), color=cores[col], label=f'{col}', linewidth=2)
    # Banda sombreada do IC 95%
    plt.fill_between(
        df_suavizados.index.to_numpy(),
        df_ci_low[col].to_numpy(),
        df_ci_high[col].to_numpy(),
        color=cores[col],
        alpha=0.15
    )

# Anotar último ponto suavizado
for col in colunas:
    ultimo_x = df_suavizados.index[-1]
    ultimo_y = df_suavizados[col].iloc[-1]
    if pd.notna(ultimo_y):
        plt.annotate(f'{ultimo_y:.2f}%', (ultimo_x, ultimo_y),
                     textcoords="offset points", xytext=(0, -10), ha='left',
                     color=cores[col], fontsize=12)

plt.title('Avaliação do Governo Lula III')
plt.xlabel('Data')
plt.xlim(inicio)
plt.ylabel('Percentual (%)')
plt.legend()
plt.grid(True)
plt.show()

# Salvar resultados em Excel
with pd.ExcelWriter(BASE_DIR / 'output_avaliacao_liquida_suavizada_janela_movel.xlsx') as writer:
    df_suavizados.to_excel(writer, sheet_name='Suavizados')
    df_ci_low.to_excel(writer, sheet_name='IC_Baixo')
    df_ci_high.to_excel(writer, sheet_name='IC_Alto')
