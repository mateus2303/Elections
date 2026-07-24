# Códigos dos modelos

Esta pasta é o pacote portátil para levar ao computador do trabalho.

## Estrutura

- `Modelo_A_Baseline_Oficial/`: contém somente `MODELO A.PY`, o agregador autocontido do baseline oficial.
- `Modelo_B_Candidato_Experimental/`: configuração e comando do Modelo B, candidato experimental.
- `MOTOR_COMUM/`: motor Python compartilhado pelos dois modelos. O código não é duplicado: cada modelo escolhe a metodologia pelo parâmetro `--model`.

## Preparação no computador do trabalho

Para rodar o Modelo A em outro computador, basta copiar `MODELO A.PY` e `Base_nova_limpa.xlsx` para a mesma pasta. Instale Python 3.12 ou superior e as bibliotecas necessárias:

```powershell
python -m pip install pandas numpy openpyxl matplotlib
```

## Execução

Para o baseline oficial:

```powershell
python ".\ENTREGA_FINAL\CODIGOS\Modelo_A_Baseline_Oficial\MODELO A.PY"
```

Para o candidato experimental:

```powershell
powershell -ExecutionPolicy Bypass -File .\ENTREGA_FINAL\CODIGOS\Modelo_B_Candidato_Experimental\executar_modelo_b.ps1
```

Os resultados continuam sendo gravados em `ENTREGA_FINAL\RESULTADOS_ATUAIS\`, em pastas separadas. Os arquivos de configuração de cada modelo usam caminhos relativos e não dependem do computador de origem.

## Atualização recorrente

1. Abra `ENTREGA_FINAL\Base_nova_limpa.xlsx`.
2. Adicione as novas linhas publicadas em `Confrontos` e/ou `Lula3`.
3. Salve e feche o Excel.
4. Para o Modelo A, rode `MODELO A.PY`.
5. Para o Modelo A, abra as planilhas e os gráficos diretamente em `RESULTADOS_ATUAIS\Modelo_A_Baseline_Oficial`. Além das duas saídas de governo e de cada segundo turno disponível contra Flávio, Renan e Caiado, o código gera um único gráfico de primeiro turno, avaliação do governo por sexo, quebras de sexo e religião para os confrontos de segundo turno e pares de primeiro turno por sexo, religião e renda quando houver dados publicados suficientes.

Novos adversários entram por novas linhas em `Confrontos`; não é necessário criar uma pasta ou alterar a estrutura da base para cada nome. No primeiro turno, o gráfico atual e os pares por abertura são deliberadamente restritos a Lula, Flávio, Renan Santos, Romeu Zema, Ronaldo Caiado e Michelle Bolsonaro; para cada um, usam a média dos cenários em que foi testado. Ausência em um cenário não recebe valor zero. Os pares `Primeiro_Turno_Lula_vs_<Candidato>_por_<Abertura>` exigem ao menos dois grupos e duas datas publicadas por grupo; assim, novos candidatos e novas aberturas entram automaticamente quando passarem a ter cobertura suficiente.
