# Manual de execução — Novo Agregador

## Objetivo

O operador atualiza somente `ENTREGA_FINAL/Base_nova_limpa.xlsx`: adiciona as linhas publicadas nas abas `Lula3` e/ou `Confrontos`, salva, fecha o Excel e executa um único comando. O pipeline lê a planilha sem alterá-la, gera IDs, validações, Modelo A, tabelas, gráficos e memória de pesos.

## Preparação única

É necessário Python 3.12 ou superior, com `pandas`, `numpy`, `openpyxl`, `matplotlib` e `PyYAML`. A partir da pasta do projeto:

```powershell
python -m pip install -e .
```

O arquivo `config/agregador.yaml` é a única configuração operacional. Ele está escrito em JSON, que também é YAML válido; instalações com PyYAML também aceitam YAML convencional. Não coloque senhas, tokens ou dados de conexão Databricks nesse arquivo.

## Rotina do operador

1. Abra `ENTREGA_FINAL/Base_nova_limpa.xlsx` e inclua a pesquisa ou onda publicada.
2. Preserve o rótulo publicado, datas como datas e células publicadas em branco como nulas.
3. Salve e feche o Excel.
4. Valide antes de publicar:

```powershell
python -m agregador validate --config config/agregador.yaml
```

5. Se não houver erro bloqueante, execute o baseline oficial (Modelo A):

```powershell
python -m agregador run --config config/agregador.yaml
```

6. A entrega atual fica em `ENTREGA_FINAL/RESULTADOS_ATUAIS/Modelo_A_Baseline_Oficial/`. O pipeline arquiva automaticamente a versão anterior em `ARQUIVOS_ANTIGOS/EXECUCOES_PIPELINE/`; não use uma saída anterior como entrada de uma execução posterior.

## Avaliação do Modelo B candidato

O Modelo B é uma rota experimental, separada do Modelo A e nunca substitui o baseline. Para executá-lo sobre a mesma base, use:

```powershell
python -m agregador run --config config/agregador.yaml --model b
```

O candidato `model-b-candidate-0.1` aplica meia-vida de 15 dias, janela máxima de 90 dias, `n` efetivo conservador, shrinkage de qualidade em direção a 0,70, covariância multinomial para métricas de diferença, piso de incerteza de 1,5 p.p. e teto de 35% por instituto. O teto só é viável com ao menos três institutos independentes: abaixo disso, a série recebe `evidencia_insuficiente_concentracao` e a probabilidade é suprimida. Use o campo `methodology_version` para nunca misturar suas saídas com as do Modelo A.

## Saídas

Todos os caminhos abaixo são relativos a `ENTREGA_FINAL/RESULTADOS_ATUAIS/Modelo_A_Baseline_Oficial/`:

- `tables/polls_raw.csv`: Bronze com arquivo, aba, linha e payload de origem.
- `tables/polls_standardized.csv`: Silver com IDs automáticos, dimensões e métricas normalizadas.
- `tables/aggregates_timeseries.csv`: Gold com estimativas, intervalos, cobertura, versão metodológica e, no Modelo B, decomposição de incerteza e viabilidade do teto de concentração.
- `tables/poll_weights.csv`: memória por ponto calculado; seus pesos normalizados recompõem a estimativa.
- `tables/win_probability_timeseries.csv`: probabilidade de liderança atual, sempre marcada como experimental nesta versão.
- `tables/validation_issues.csv` e `reports/validation_report.html`: erros e alertas com aba, linha, campo e sugestão.
- `graficos_diagnostico/`: gráficos técnicos e de conferência, inclusive séries curtas quando houver dados.
- `apresentacao/Resultados_Modelo_A.xlsx`: planilha enxuta para leitura e apresentação.
- `apresentacao/Resultados_Modelo_B.xlsx`: planilha enxuta do candidato experimental, quando a execução usa `--model b`.
- `apresentacao/graficos/`: gráficos executivos gerados automaticamente para cada adversário encontrado na aba `Confrontos`.
- `apresentacao/LEIA_ME.txt`: ordem recomendada de leitura e alertas de interpretação.
- `reports/methodology_snapshot.json`: parâmetros e hash da entrada usados na execução.

### Pacote de apresentação

Comece por `apresentacao/Resultados_Modelo_A.xlsx` ou `apresentacao/Resultados_Modelo_B.xlsx`, na aba `Resumo_Executivo`. As abas `Segundo_Turno`, `Aberturas`, `Primeiro_Turno` e `Cobertura` sustentam os gráficos; a aba `Agregados_Modelo_A` ou `Agregados_Modelo_B` e `Notas_Metodologicas` ficam disponíveis para auditoria.

Os gráficos de segundo turno são criados por adversário, sem código específico para Flávio, Renan ou qualquer outro nome. Ao inserir um novo confronto em `Confrontos`, o mesmo conjunto é criado em `apresentacao/graficos/lula_vs_<adversario>/` na próxima execução. O painel comparativo reúne o último ponto de cada adversário, enquanto o gráfico por instituto mostra a dispersão publicada e diferencia pesquisas regulares de tracking.

As aberturas demográficas são uma fotografia da onda mais recente publicada para cada combinação disponível de sexo, idade e religião; não são médias entre rótulos diferentes. O primeiro-turno é apresentado como mapa de composição dos cenários, sem média automática entre listas incompatíveis de candidatos.

No Modelo B, a aba `Incerteza_Modelo_B` mostra a faixa experimental e os gates de concentração/cobertura. A aba `Probabilidade_Experimental` deve ser lida com cautela: linhas sem probabilidade não são zero; trazem o motivo da supressão. O Modelo B continua candidato e não substitui o baseline oficial.

CSV é sempre produzido em UTF-8. Parquet é exportado automaticamente quando o ambiente dispõe de motor compatível; caso contrário, o fato fica registrado em `run_log.csv`, sem bloquear a entrega local.

## Regras do Modelo A

O baseline preserva cap de amostra de 5.000 e a fórmula recuperada do legado:

```text
peso = qualidade^0,50 × recência_linear^0,25 × amostra^0,25
```

As curvas são separadas por produto, turno, tipo e composição de cenário, adversário, geografia, segmento e base de voto. Segundo turno em votos totais gera também votos válidos automaticamente. Nenhuma regra é específica a um adversário.

## O que ainda não é oficial

- A probabilidade de liderança é experimental: a incerteza total, o piso de erro e os gates definitivos ainda aguardam validação metodológica.
- Modelos B e C não foram incorporados ao baseline; suas interfaces permanecem separadas até backtest e aprovação.
- O Modelo B candidato foi implementado para comparação, mas não passou por backtest/homologação e não deve ser usado como série oficial.
- Backtest usa `config/backtest.yaml`, que aponta para a configuração operacional e mede, sem informação futura, a previsão da próxima observação publicada.
- Databricks recebe contratos CSV/Parquet locais; conexão direta depende de workspace, catálogo, schema, armazenamento e autenticação corporativos.

## Diagnóstico de erros

Código `1` significa erro bloqueante: não há publicação Gold. Corrija somente a linha apontada no relatório, sem alterar o dado publicado para forçar soma de 100%.

Código `2` indica configuração ou caminho inválido. Código `3` indica falha inesperada; guarde a pasta de saída e o texto do erro para análise técnica.
