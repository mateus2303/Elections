import pandas as pd  
import numpy as np 
import matplotlib.pyplot as plt  
import datetime
from pathlib import Path
from scipy.stats import norm  # (não usado aqui, pode remover se quiser)

# Passo 1: Ler a planilha Excel  
# Sheets
sheet_1 = "Lula vs Flavio padrao"
sheet_2 = "Lula vs Flavio tracking mm7d"
sheet_3 = "padrao e tracking mm7d válidos2"

BASE_DIR = Path(__file__).resolve().parent

df = pd.read_excel(
    BASE_DIR / "input_eleicao_2022.xlsx",
    sheet_name=sheet_3
)  

indice_1 = "Índice Pindograma"
indice_2 = "Índice Pollstergraph"

# Converter coluna data para datetime  
df['data'] = pd.to_datetime(df['data'])  

# Parâmetros de pesos (média geométrica) e janela
w_qualidade = 0.50
w_tempo     = 0.25
w_amostra   = 0.25
janela_dias = 30

# Pesos base: qualidade do instituto e amostra (cap 5000)
# Para manter consistência com seus outros scripts, uso o indice_2 como qualidade
df['peso_qualidade'] = df[indice_1].astype(float)
df['peso_amostra']   = (df['Amostra'].clip(upper=5000) / 5000).astype(float)

# Função de suavização com janela móvel e pesos geométricos
def suavizacao_geometrica(df, data_alvo, coluna, janela_dias=30):
    diff = (data_alvo - df['data']).dt.days
    mask = (diff >= 0) & (diff <= janela_dias)
    df_f = df.loc[mask, ['data','Amostra','peso_qualidade','peso_amostra',coluna]].dropna(subset=[coluna]).copy()
    if df_f.empty:
        return np.nan

    # Peso de tempo: decaimento linear na janela
    df_f['peso_tempo'] = 1.0 - (diff[mask].astype(float) / float(janela_dias))
    # Peso total geométrico
    weights = (
        (df_f['peso_qualidade'] ** w_qualidade) *
        (df_f['peso_tempo']     ** w_tempo)     *
        (df_f['peso_amostra']   ** w_amostra)
    ).astype(float)

    sw = weights.sum()
    if not np.isfinite(sw) or sw <= 0:
        return np.nan

    return np.average(df_f[coluna].astype(float), weights=weights)

# IC 95% para a média suavizada (binomial ponderado)
def ic95_geometrico(df, data_alvo, coluna, janela_dias=30):
    """
    Assume coluna em percentuais (0–100).
    Var_i = p_i(1-p_i)/n_i por pesquisa (binomial, com n_i = min(Amostra, 5000)).
    Var_est = sum(alpha_i^2 * Var_i), alpha = peso_i / sum(pesos).
    Retorna (ci_low_percent, ci_high_percent).
    """
    diff = (data_alvo - df['data']).dt.days
    mask = (diff >= 0) & (diff <= janela_dias)
    df_f = df.loc[mask, ['data','Amostra','peso_qualidade','peso_amostra',coluna]].dropna(subset=[coluna]).copy()
    if df_f.empty:
        return np.nan, np.nan

    df_f['peso_tempo'] = 1.0 - (diff[mask].astype(float) / float(janela_dias))
    weights = (
        (df_f['peso_qualidade'] ** w_qualidade) *
        (df_f['peso_tempo']     ** w_tempo)     *
        (df_f['peso_amostra']   ** w_amostra)
    ).astype(float)

    sw = weights.sum()
    if not np.isfinite(sw) or sw <= 0:
        return np.nan, np.nan

    alpha = (weights / sw).to_numpy()

    p_i = (df_f[coluna].astype(float).to_numpy() / 100.0).clip(0.0, 1.0)
    n_i = df_f['Amostra'].clip(upper=5000).astype(float).to_numpy()

    var_i  = p_i * (1.0 - p_i) / n_i
    var_hat = np.sum((alpha**2) * var_i)
    se_hat  = np.sqrt(var_hat)

    # média central (proporção) para o IC
    p_hat = np.sum(alpha * p_i)

    z = 1.96
    lo = max(0.0, p_hat - z * se_hat)
    hi = min(1.0, p_hat + z * se_hat)
    return lo * 100.0, hi * 100.0

# Datas e colunas alvo
datas_unicas = df['data'].sort_values().unique()
colunas = ['Lula', 'Flavio']
cores  = {'Lula': 'red', 'Flavio': 'blue'}

# Calcular séries suavizadas e ICs
resultados_suavizados = {col: [] for col in colunas}
resultados_ci_low     = {col: [] for col in colunas}
resultados_ci_high    = {col: [] for col in colunas}

for data_ref in datas_unicas:
    for col in colunas:
        val = suavizacao_geometrica(df, data_ref, col, janela_dias=janela_dias)
        lo, hi = ic95_geometrico(df, data_ref, col, janela_dias=janela_dias)
        resultados_suavizados[col].append(val)
        resultados_ci_low[col].append(lo)
        resultados_ci_high[col].append(hi)

# DataFrames para plotagem
df_suav = pd.DataFrame({'data': datas_unicas})
df_ci_lo = pd.DataFrame({'data': datas_unicas})
df_ci_hi = pd.DataFrame({'data': datas_unicas})
for col in colunas:
    df_suav[col]  = resultados_suavizados[col]
    df_ci_lo[col] = resultados_ci_low[col]
    df_ci_hi[col] = resultados_ci_high[col]
df_suav.set_index('data', inplace=True)
df_ci_lo.set_index('data', inplace=True)
df_ci_hi.set_index('data', inplace=True)

# Plot
plt.figure(figsize=(14, 7))  

# Scatter original
plt.scatter(df['data'], df['Lula'], color='red', alpha=0.25, s=20)
plt.scatter(df['data'], df['Flavio'], color='blue', alpha=0.25, s=20)
#plt.scatter(df['data'], df['Brancos/Nulos/NS/NR'], color='grey', alpha=0.25, s=20)

# Linhas suavizadas + bandas de IC
for col in colunas:
    plt.plot(df_suav.index.to_numpy(), df_suav[col].to_numpy(), color=cores[col], label=col)
    plt.fill_between(df_suav.index.to_numpy(), df_ci_lo[col].to_numpy(), df_ci_hi[col].to_numpy(), color=cores[col], alpha=0.15)

# Anotações do último ponto de cada série
ultimo_x = df_suav.index[-1]
for col in colunas:
    ultimo_y = df_suav[col].iloc[-1]
    if pd.notna(ultimo_y):
        offset = -5 if col == 'Lula' else 10
        plt.annotate(f'{ultimo_y:.2f}%', (ultimo_x, ultimo_y),
                     textcoords="offset points", xytext=(0, offset), ha='left', va='center',
                     color=cores[col], fontsize=12)

# Ajustes de gráfico
plt.xlabel('Data')  
plt.ylabel('Percentual')  
plt.ylim(40, 60) 
plt.title('Segundo Turno 2026: Lula vs Flavio (suavização geométrica + IC 95%)')  
plt.legend()  
plt.grid(True)  

# Salvar gráfico
plt.savefig(BASE_DIR / 'segundo_turno_2026_lula_vs_flavio.png', dpi=300, bbox_inches='tight')

# Salvar dados em Excel (cada DataFrame em uma aba)
with pd.ExcelWriter(BASE_DIR / 'resultado_segundo_turno_2026_lula_vs_flavio.xlsx') as writer:
    df_suav.to_excel(writer, sheet_name='Suavizados')
    df_ci_lo.to_excel(writer, sheet_name='IC_Baixo')
    df_ci_hi.to_excel(writer, sheet_name='IC_Alto')

print("Arquivos salvos:")
print("- Gráfico: segundo_turno_2026_lula_vs_flavio.png")
print("- Dados: resultado_segundo_turno_2026_lula_vs_flavio.xlsx")

plt.show()
