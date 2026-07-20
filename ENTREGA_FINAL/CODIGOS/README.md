# Códigos dos modelos

Esta pasta é o pacote portátil para levar ao computador do trabalho.

## Estrutura

- `Modelo_A_Baseline_Oficial/`: configuração e comando do Modelo A, baseline oficial.
- `Modelo_B_Candidato_Experimental/`: configuração e comando do Modelo B, candidato experimental.
- `MOTOR_COMUM/`: motor Python compartilhado pelos dois modelos. O código não é duplicado: cada modelo escolhe a metodologia pelo parâmetro `--model`.

## Preparação no computador do trabalho

Mantenha a pasta `ENTREGA_FINAL` inteira, com `Base_nova_limpa.xlsx`, `CODIGOS` e `RESULTADOS_ATUAIS`. Instale Python 3.12 ou superior e, a partir da pasta que contém `ENTREGA_FINAL`, execute:

```powershell
python -m pip install -e ENTREGA_FINAL\CODIGOS\MOTOR_COMUM
```

## Execução

Para o baseline oficial:

```powershell
powershell -ExecutionPolicy Bypass -File .\ENTREGA_FINAL\CODIGOS\Modelo_A_Baseline_Oficial\executar_modelo_a.ps1
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
4. Rode o script do modelo desejado.
5. Abra o workbook correspondente em `RESULTADOS_ATUAIS`.

Novos adversários entram por novas linhas em `Confrontos`; não é necessário criar uma pasta ou alterar o código para cada nome.
