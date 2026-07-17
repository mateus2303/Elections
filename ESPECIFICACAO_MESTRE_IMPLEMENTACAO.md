# Especificação Mestre — Novo Agregador de Pesquisas Políticas

## Documento de execução e aceite

**Função deste documento:** permitir que outro desenvolvedor ou agente implemente o projeto sem reinterpretar o objetivo de negócio.  
**Documentos complementares:** `ROTEIRO_NOVO_AGREGADOR.md`, `ESTUDO_METODOLOGICO_AGREGADOR.md` e `Base_nova_limpa.xlsx`.  
**Regra de precedência:** decisões explícitas deste documento prevalecem; decisões marcadas como pendentes não podem ser inventadas silenciosamente.

---

## 1. Resultado esperado

Construir um pipeline local em Python que:

1. leia um único Excel de entrada;
2. valide todas as linhas antes de calcular;
3. reproduza a metodologia do agregador antigo como baseline;
4. processe avaliação do Governo Lula III;
5. processe todos os confrontos da aba `Confrontos`, começando por Flávio e Renan;
6. agregue separadamente Brasil, regiões, UFs e segmentos demográficos disponíveis; município está fora do escopo;
7. estime séries agregadas e intervalos;
8. calcule, separadamente, probabilidade de liderança atual de Lula;
9. gere gráficos, tabelas, memória de pesos e relatório de validação;
10. exporte dados normalizados para futura carga no Databricks;
11. registre versão, parâmetros, data e identificador de cada execução.

O fluxo operacional final deve ser:

```text
abrir Excel → adicionar pesquisa → salvar e fechar → executar uma rotina → receber todos os outputs
```

Nenhuma atualização rotineira pode exigir editar código, copiar abas como valores, usar PROCV ou calcular votos válidos manualmente.

---

## 1A. Pré-requisito obrigatório: inspeção somente leitura do legado

Antes de criar ou alterar código, planilhas ou configurações, inspecionar:

- `input_agregador.xlsx`;
- `input_eleicao_2022.xlsx` ou `input_eleicao2022.xlsx`.

### Proibição de escrita

Não editar, recalcular, salvar, corrigir, reformatar, renomear, mover ou sobrescrever os originais. Calcular e registrar hash dos arquivos antes da inspeção. Se a ferramenta usada puder modificar o workbook ao abrir, criar uma cópia descartável e trabalhar somente nela.

### Relatório de inspeção obrigatório

Gerar `docs/DIAGNOSTICO_PLANILHAS_LEGADAS.md` contendo:

- arquivos e hashes;
- abas, dimensões, tabelas e intervalos usados;
- cabeçalhos e tipos inferidos;
- fórmulas e dependências entre abas;
- fontes versus abas intermediárias;
- pesquisas regulares versus tracking/mm7d;
- totais versus válidos;
- avaliação Lula III disponível;
- confrontos disponíveis, especialmente Lula × Flávio;
- rankings e pesos existentes;
- duplicidades, nulos, erros de fórmula e inconsistências;
- limitações da inspeção;
- decisões que exigem confirmação humana.

Gerar também `docs/MAPEAMENTO_MIGRACAO.md` com uma matriz:

| arquivo_origem | aba_origem | coluna_origem | significado | transformação | aba_destino | coluna_destino | automatizável | observação |
|---|---|---|---|---|---|---|---|---|

### Proposta da nova planilha

Somente depois do diagnóstico, comparar a estrutura real com `Base_nova_limpa.xlsx` e propor ajustes. A nova planilha deve reunir:

- avaliação do Governo Lula III;
- uma única aba `Confrontos` reunindo Lula × Flávio, Lula × Renan e qualquer novo adversário;
- dimensões de geografia e segmento aplicáveis tanto a `Lula3` quanto a `Confrontos`;
- cadastro de institutos;
- instruções de uso.

A migração inicial deve copiar/transformar os dados dos legados para um novo arquivo, preservando os originais. Cada linha migrada deve manter referência técnica a arquivo, aba e linha de origem. Essa rastreabilidade será criada automaticamente pelo pipeline; nunca será campo de preenchimento do operador.

### Teste de facilidade operacional

Antes de aprovar o layout, simular no mínimo:

1. pesquisa apenas de avaliação;
2. pesquisa apenas Lula × Flávio;
3. pesquisa com avaliação e dois confrontos;
4. nova pesquisa Lula × Renan;
5. novo adversário relevante.
6. Lula × adversário em São Paulo;
7. Lula × adversário no Sudeste;
8. Lula × adversário por faixa etária;

O operador deve conseguir registrar cada caso sem fórmulas, cópias entre abas ou edição de código. O agente deve cronometrar/descrever os passos e eliminar campos que não tragam valor suficiente para justificar o esforço manual.

---

## 2. Restrições obrigatórias

- Não substituir o baseline antigo antes da comparação e aprovação.
- Não misturar avaliação Ótimo/Bom com Aprova/Desaprova.
- Não tratar probabilidade de liderança atual como previsão do dia da eleição.
- Não excluir pesquisa apenas porque diverge do consenso.
- Não assumir que ondas sobrepostas de tracking são independentes.
- Não gravar credenciais do Databricks no código.
- Não versionar planilhas confidenciais.
- Não alterar silenciosamente dados digitados.
- Não usar outputs anteriores como input da execução seguinte.
- Não criar um script separado para cada candidato.
- Não criar aba separada por candidato, região, UF ou segmento.
- Não tratar recortes da mesma pesquisa como observações nacionais independentes.

---

## 3. Entradas

### 3.1 Arquivo principal

Nome configurável, default:

```text
data/input/Base_nova_limpa.xlsx
```

### 3.2 Abas obrigatórias

- `Lula3`
- `Confrontos`
- `Institutos`
- `Controle`
- `Instrucoes`

### 3.3 Regra de extensibilidade

Não existem abas opcionais por candidato ou recorte. Novo adversário, geografia e segmento entram por novas linhas.

As dimensões são:

- `adversario`;
- `nivel_geografico`: `Brasil`, `Regiao`, `UF`;
- `geografia`: nome/código controlado, como `Brasil`, `Sudeste`, `SP`;
- `segmento_tipo`: `Total`, `Idade`, `Sexo`, `Escolaridade`, `Renda`, `Religiao`, `Outro`;
- `segmento`: categoria publicada, como `Total` ou `16-24`.

O núcleo legado inicial era integralmente `Brasil / Brasil / Total / Total`. A base de referência entregue em 15/07/2026 incorpora 56 aberturas de Lula3 e, em `Confrontos`, preserva 371 linhas de segundo turno e inclui 157 linhas de primeiro turno. Dessas, 11 são espontâneas classificadas como parciais/baixo risco e exigem tratamento conservador. A dimensão `Religiao` está disponível com `Católico` e `Evangélico`, ainda sem observações porque a fonte recebida não publicou esses percentuais.

#### Experiência de preenchimento obrigatória

- `Lula3` e `Confrontos` exibem uma instrução curta acima da tabela e bandas visuais para dados da pesquisa, cenário/adversário, geografia, segmento e resultados;
- `nivel_geografico` alimenta um menu dependente em `geografia`: `Brasil → Brasil`, `Regiao → cinco regiões`, `UF → 27 siglas`;
- `segmento_tipo` alimenta um menu dependente em `segmento`;
- `Instrucoes` é a fonte visível e auditável das listas; não criar aba técnica adicional;
- listas de segmento começam com categorias comuns e crescem quando o operador escreve, sem deixar buracos, na primeira célula vazia da coluna correspondente;
- o rótulo publicado deve ser preservado; nenhuma faixa é convertida ou harmonizada no Excel.

### 3.4 Colunas da aba `Lula3`

| Coluna | Tipo | Obrigatória | Regra |
|---|---|---:|---|
| data_referencia | data | sim | data original da observação/onda; não expandir semana em dias |
| instituto | texto | sim | nome canônico ou alias |
| tipo_pesquisa | categoria | sim | `regular` ou `tracking` |
| frequencia_original | categoria | sim | `pontual`, `diaria` ou `semanal` |
| amostra_total | inteiro | não | amostra integral da pesquisa; maior que zero quando preenchida |
| margem_erro_pp | decimal | não | entre 0 e 20 |
| nivel_confianca_pct | decimal | não | entre 50 e 100 |
| nivel_geografico | categoria | sim | `Brasil`, `Regiao` ou `UF` |
| geografia | texto | sim | `Brasil`, uma das cinco regiões ou sigla da UF |
| segmento_tipo | categoria | sim | `Total`, `Idade`, `Sexo`, `Escolaridade`, `Renda`, `Religiao` ou `Outro` |
| segmento | texto | sim | `Total` ou categoria publicada |
| amostra_segmento | inteiro | não | tamanho do recorte; para Total, repetir `amostra_total` quando disponível |
| otimo_bom_pct | decimal | sim | 0 a 100 |
| regular_pct | decimal | não | 0 a 100 |
| ruim_pessimo_pct | decimal | sim | 0 a 100 |

Não adicionar campos manuais de ID, fonte, observação ou rastreabilidade. A avaliação líquida será derivada. Se futuramente houver série de Aprova/Desaprova, criar família de métrica separada e não misturá-la com Ótimo/Bom–Ruim/Péssimo.

### 3.5 Colunas da aba `Confrontos`

| Coluna | Tipo | Obrigatória | Regra |
|---|---|---:|---|
| data_referencia | data | sim | data original da pesquisa/onda |
| instituto | texto | sim | nome canônico ou alias |
| tipo_pesquisa | categoria | sim | `regular` ou `tracking` |
| frequencia_original | categoria | sim | `pontual`, `diaria` ou `semanal` |
| amostra_total | inteiro | não | amostra integral da pesquisa |
| margem_erro_pp | decimal | não | entre 0 e 20 |
| nivel_confianca_pct | decimal | não | entre 50 e 100 |
| turno | categoria | sim | `1º turno` ou `2º turno` |
| tipo_cenario | categoria | sim | `Estimulada` ou `Espontânea` |
| cenario | texto | sim | `Único`, `Cenário 1`, `Cenário 2`, `Espontânea`, etc. |
| adversario | texto | sim | nome canônico dentro do cenário |
| nivel_geografico | categoria | sim | `Brasil`, `Regiao` ou `UF` |
| geografia | texto | sim | `Brasil`, `Sudeste`, `SP`, etc. |
| segmento_tipo | categoria | sim | `Total`, `Idade`, `Sexo`, `Escolaridade`, `Renda`, `Religiao` ou `Outro` |
| segmento | texto | sim | `Total`, `16-24`, etc. |
| amostra_segmento | inteiro | não | tamanho do recorte quando divulgado |
| lula_pct | decimal | sim | 0 a 100 |
| adversario_pct | decimal | sim | 0 a 100 |
| outros_candidatos_pct | decimal | sim | soma das demais candidaturas publicadas no 1º turno; zero no 2º turno |
| brancos_nulos_indecisos_pct | decimal | não | soma das categorias não candidatas publicadas, de 0 a 100 |
| base_voto | categoria | sim | `Totais` ou `Validos` |

Não adicionar campos manuais de ID, fonte, observação ou rastreabilidade. O pipeline gera `scenario_id`, `geography_id` e `segment_id`. Linhas só são comparáveis quando turno, tipo de cenário, cenário, adversário, geografia, segmento e base de voto coincidirem. No primeiro turno, nunca derive `outros_candidatos_pct` ou `brancos_nulos_indecisos_pct` como residual para forçar 100%: some as colunas publicadas e preserve a diferença de arredondamento da fonte.

### 3.6 Aba `Institutos`

| Coluna | Tipo | Obrigatória | Regra |
|---|---|---:|---|
| instituto | texto | sim | nome canônico único |
| aliases | texto | não | grafias equivalentes separadas por `;` |
| peso_legacy | decimal | não | entre 0 e 1; pode ficar vazio para instituto provisório |
| situacao | categoria | sim | `Aprovado`, `Provisorio` ou `Inativo` |

O operador cotidiano não preencherá nenhum outro cadastro metodológico. Normalizar caixa, espaços e acentos antes do lookup. Alias duplicado entre institutos é erro bloqueante. Instituto não encontrado deve ser inserido automaticamente no registro técnico como `Provisorio`, com `peso_legacy` vazio. O pipeline aplica um prior conservador configurado e gera alerta sem gravar um peso arbitrário no Excel.

### 3.7 Registro técnico de institutos

O pipeline deve gerar e versionar, fora do formulário operacional, no mínimo:

- instituto canônico e versão de metodologia;
- início e fim de validade;
- quantidade e recência da evidência histórica;
- viés médio, MAE e RMSE da margem Lula − adversário;
- house effect regularizado;
- erro excedente/heterogeneidade;
- tamanho de amostra efetivo;
- peso bruto e peso normalizado aplicados;
- indicadores de transparência recuperados automaticamente;
- origem da estimativa e status de aprovação.

House effect, precisão e transparência são dimensões separadas. O pipeline não deve condensá-las em uma nota opaca sem mostrar os componentes.

### 3.8 Identificação automática da pesquisa-mãe e das células

O operador não digita IDs. O pipeline gera:

- `poll_group_id`: identifica a pesquisa/onda-mãe compartilhada por todos os confrontos e recortes publicados no mesmo levantamento;
- `poll_id`: identifica uma célula específica de produto, adversário, geografia, segmento, métrica e base de voto.

O `poll_group_id` deve ser um hash estável da assinatura normalizada composta por instituto canônico, datas de campo/publicação quando disponíveis — ou `data_referencia` como fallback —, `amostra_total`, `tipo_pesquisa` e `frequencia_original`. O `poll_id` adiciona à assinatura da pesquisa-mãe as dimensões e a métrica da célula. Ausência de componentes reduz a confiança do pareamento e gera alerta. Colisão ou ambiguidade é erro de revisão: o sistema não pode fundir pesquisas silenciosamente.

---

## 4. Configuração externa

Criar arquivo versionável, sem dados confidenciais:

```text
config/agregador.yaml
```

Conteúdo mínimo:

```yaml
methodology_version: "legacy-baseline-1.0"
input_file: "data/input/Base_nova_limpa.xlsx"
sample_cap: 5000
missing_sample_fallback: 600
missing_segment_sample_fallback: 300
unknown_institute_weight: 0.50
confidence_level: 0.95
weights:
  quality: 0.50
  recency: 0.25
  sample: 0.25
sheets:
  government: "Lula3"
  contests: "Confrontos"
dimensions:
  geographic_levels: ["Brasil", "Regiao", "UF"]
  segment_types: ["Total", "Idade", "Sexo", "Escolaridade", "Renda", "Religiao", "Outro"]
  default_geographic_level: "Brasil"
  default_geography: "Brasil"
  default_segment_type: "Total"
  default_segment: "Total"
windows:
  government_days: 30
  contest_days: 30
```

Parâmetros não podem ser duplicados em vários scripts.

---

## 5. Baseline metodológico obrigatório

### 5.1 Data usada no baseline

Para reproduzir o legado, usar inicialmente a mesma definição encontrada nos scripts/planilhas antigas. Enquanto isso não for recuperado, registrar como decisão pendente e implementar a escolha por configuração.

### 5.2 Peso

Para cada pesquisa disponível na data de cálculo:

```text
quality_component = peso_legacy
time_component = max(0, 1 - idade_dias / janela_dias)
se segmento = Total:
    sample_used = amostra_segmento, senão amostra_total, senão missing_sample_fallback
se segmento != Total:
    sample_used = amostra_segmento, senão min(amostra_total, missing_segment_sample_fallback)
    se amostra_total também ausente, usar missing_segment_sample_fallback
sample_component = min(sample_used, 5000) / 5000

raw_weight = quality_component^0.50
           × time_component^0.25
           × sample_component^0.25
```

Instituto desconhecido e amostra ausente usam os fallbacks configurados, sempre com alerta. Excluir do cálculo somente pesos iguais a zero ou linhas objetivamente inválidas. Preservar a linha no relatório.

### 5.3 Média

```text
normalized_weight_i = raw_weight_i / sum(raw_weight)
aggregate = sum(normalized_weight_i × value_i)
```

### 5.4 Avaliação líquida

Gerar separadamente:

```text
favorabilidade_liquida = otimo_bom_pct - ruim_pessimo_pct
aprovacao_liquida = aprovacao_pct - desaprovacao_pct
```

### 5.5 Confrontos

Preservar valores originais.

No segundo turno, se `base_voto = Totais`, gerar válidos somente entre Lula e adversário:

```text
lula_validos = lula / (lula + adversario) × 100
adversario_validos = adversario / (lula + adversario) × 100
```

Se `lula + adversario = 0`, erro bloqueante.

No primeiro turno, preservar o cenário completo por meio de `outros_candidatos_pct` e gerar válidos sobre todos os candidatos:

```text
total_candidatos = lula + adversario + outros_candidatos
lula_validos = lula / total_candidatos × 100
adversario_validos = adversario / total_candidatos × 100
outros_validos = outros_candidatos / total_candidatos × 100
```

Cada adversário do mesmo cenário é uma célula de comparação, não uma nova pesquisa independente. Todas essas linhas devem compartilhar o mesmo `poll_group_id`.

Se `base_voto = Validos`, verificar soma com tolerância configurável; não renormalizar silenciosamente.

Cada curva deve ser particionada por:

```text
turno × tipo_cenario × cenario × adversario
× nivel_geografico × geografia × segmento_tipo × segmento × base_voto
```

Brasil/Total, SP/Total e Brasil/16–24 são três produtos distintos. Recortes de uma mesma pesquisa não podem ser somados como novas evidências para estreitar a curva Brasil/Total.

### 5.6 Datas calculadas

Produzir um ponto para cada data única da grade configurada. O baseline deve permitir reproduzir a grade antiga. A versão futura poderá usar grade diária.

### 5.7 Modelo B — legado aperfeiçoado

Implementar como metodologia separada, nunca como alteração silenciosa do baseline:

- `n_efetivo = min(n_declarado, n_implícito_na_margem, cap)` quando os dados existirem;
- para recortes, usar `amostra_segmento`; a margem de erro da amostra total não é a margem do subgrupo;
- covariância multinomial para avaliação líquida e margem do confronto;
- uma observação por onda efetivamente publicada;
- teto de contribuição por instituto/tracking antes da normalização;
- variância total com erro amostral, heterogeneidade e piso histórico;
- peso histórico de instituto com *shrinkage* para a média;
- janela linear e meia-vida comparadas por backtest.

### 5.8 Modelo C — challenger temporal

Construir, após a homologação do baseline, um modelo temporal hierárquico robusto com estado latente, efeitos de instituto, erro excedente, correlação de tracking e distribuição t-Student. Manter valores brutos e ajustados. Não excluir outlier apenas por divergir do consenso.

### 5.9 Regra de promoção

Modelos B ou C só podem se tornar oficiais após backtest walk-forward sem vazamento, melhora material predefinida, intervalos calibrados, execução paralela, documentação e aprovação. Para avaliar uma eleição, os parâmetros de instituto devem ser estimados apenas com informação disponível antes dela.

---

## 6. Intervalos e probabilidades

### 6.1 Primeira entrega

Implementar o intervalo antigo para reprodução. Identificá-lo como `sampling_interval_legacy` nos dados técnicos.

### 6.2 Correção candidata

Implementar atrás de feature flag a covariância multinomial descrita no estudo metodológico. Não torná-la default antes dos testes.

### 6.3 Probabilidade de liderança

Produto inicial:

```text
P(margem_Lula > 0 | informação disponível)
```

Ela deve ser rotulada como `probabilidade_lideranca_atual`.

Não usar o nome `probabilidade_vitoria_eleicao` até que exista modelo temporal preditivo aprovado.

### 6.4 Condição de bloqueio

Se a distribuição/erro total da margem ainda não estiver validado, gerar a série agregada e marcar a probabilidade como experimental. Não apresentar probabilidades extremas sem piso de incerteza documentado.

---

## 7. Validação

### 7.1 Erros bloqueantes

- arquivo ou aba obrigatória ausente;
- coluna obrigatória ausente;
- instituto vazio;
- alias associado a mais de um instituto;
- data de referência impossível;
- amostra não positiva ou não numérica quando preenchida;
- percentual fora de 0 a 100;
- confronto sem Lula ou adversário;
- dimensão geográfica ou segmento ausente/inválido;
- `nivel_geografico = Brasil` com `geografia` diferente de `Brasil`;
- `segmento_tipo = Total` com `segmento` diferente de `Total`;
- `amostra_segmento > amostra_total` quando ambas existirem;
- base de voto inválida;
- duplicata exata inequívoca;
- soma zero na conversão para válidos.

Com erro bloqueante, não publicar outputs Gold. Gerar somente relatório de validação.

### 7.2 Alertas

- margem ausente;
- confiança ausente;
- amostra ausente e fallback conservador aplicado;
- recorte não total sem `amostra_segmento`;
- soma incompleta;
- pesquisa discrepante;
- instituto novo com peso provisório;
- divulgação muito posterior ao campo;
- cenário com poucas pesquisas;
- recorte com menos pesquisas ou institutos que o gate configurado;
- concentração excessiva em um instituto;
- tracking sem identificação suficiente.

Alertas não alteram valores.

### 7.3 Relatório

Gerar:

```text
outputs/<run_id>/validation_issues.csv
outputs/<run_id>/validation_report.html
```

Cada item deve conter severidade, aba, linha, `poll_id` gerado, campo, mensagem e sugestão. O `poll_id` e a rastreabilidade são criados pelo pipeline a partir do arquivo lido; nunca são digitados no Excel.

---

## 8. Outputs locais

Estrutura obrigatória:

```text
outputs/<run_id>/
  charts/
    lula3_otimo_ruim.png
    lula3_aprovacao.png
    lula_vs_<adversario>__<geografia>__<segmento>.png
    prob_lideranca__<adversario>__<geografia>__<segmento>.png
  tables/
    aggregates_timeseries.csv
    win_probability_timeseries.csv
    poll_weights.csv
    polls_standardized.csv
    institutes_registry.csv
    institutes_diagnostics.csv
    validation_issues.csv
    run_log.csv
  reports/
    validation_report.html
    methodology_snapshot.json
    latest_composition.html
```

Somente gráficos aplicáveis devem ser gerados. Novo adversário ou recorte deve gerar outputs automaticamente com slug seguro, sem configuração específica.

---

## 9. Contratos para Databricks

### 9.1 Bronze — `polls_raw`

Campos mínimos:

- `run_id`
- `ingested_at`
- `source_file`
- `source_sheet`
- `source_row`
- `raw_payload_json`

### 9.2 Silver — `polls_standardized`

Campos mínimos:

- `run_id`
- `poll_group_id`
- `poll_id`
- `scenario_id`
- `scenario_type`
- `opponent`
- `geographic_level`
- `geography`
- `segment_type`
- `segment`
- `candidate_or_metric`
- `value_pct`
- `vote_base`
- `institute`
- `field_start`
- `field_end`
- `field_midpoint`
- `publication_date`
- `reference_date_input`
- `sample_size`
- `segment_sample_size`
- `effective_sample_size`
- `margin_error_pp`
- `confidence_level_pct`
- `quality_weight`
- `institute_status`
- `house_effect_pp`
- `excess_error_pp`
- `raw_value_pct`
- `adjusted_value_pct`
- `source_file`
- `source_sheet`
- `source_row`
- `methodology_version`

`field_start`, `field_end` e `publication_date` são nulos quando não puderem ser recuperados automaticamente do legado ou de fonte oficial. A ausência não cria trabalho manual. `data_referencia` permanece o fallback operacional e deve ser preservada como `reference_date_input` na Silver. `poll_group_id` permite modelar a dependência entre células da mesma pesquisa e impede que vários recortes sejam tratados como levantamentos independentes.

### 9.3 Gold — `aggregates_timeseries`

- `run_id`
- `methodology_version`
- `scenario_id`
- `opponent`
- `geographic_level`
- `geography`
- `segment_type`
- `segment`
- `metric`
- `reference_date`
- `estimate_pct`
- `interval_low_pct`
- `interval_high_pct`
- `interval_type`
- `poll_count`
- `institute_count`
- `effective_information`

### 9.4 Gold — `win_probability_timeseries`

- `run_id`
- `methodology_version`
- `scenario_id`
- `opponent`
- `geographic_level`
- `geography`
- `segment_type`
- `segment`
- `reference_date`
- `probability_type`
- `probability_lula`
- `experimental_flag`

### 9.5 Primeira integração

Exportar CSV UTF-8 e Parquet quando a biblioteca aprovada estiver disponível. Escrita direta em Delta fica condicionada a:

- workspace;
- catálogo;
- schema;
- volume/storage;
- autenticação;
- política de execução.

Esses itens são decisões pendentes do ambiente Kinea.

---

## 10. Interface de execução

Fornecer uma entrada única:

```text
python -m agregador run --config config/agregador.yaml
```

E comandos auxiliares:

```text
python -m agregador validate --config config/agregador.yaml
python -m agregador backtest --config config/backtest.yaml
python -m agregador compare --run-a <id> --run-b <id>
```

No Windows, opcionalmente disponibilizar `Atualizar Agregador.bat` ou atalho equivalente que invoque o comando oficial sem duplicar lógica.

### Códigos de saída

- `0`: sucesso;
- `1`: erro de validação bloqueante;
- `2`: erro de configuração;
- `3`: falha inesperada de processamento/publicação.

---

## 11. Arquitetura mínima sugerida

```text
agregador/
  pyproject.toml
  README.md
  .gitignore
  config/
    agregador.example.yaml
    backtest.example.yaml
  src/agregador/
    __main__.py
    cli.py
    config.py
    ingestion.py
    validation.py
    standardization.py
    weighting.py
    aggregation.py
    uncertainty.py
    probability.py
    plotting.py
    publishing.py
    audit.py
    institutes.py
    databricks_export.py
  tests/
    fixtures/
    test_validation.py
    test_standardization.py
    test_weighting.py
    test_aggregation.py
    test_uncertainty.py
    test_extensibility.py
    test_outputs.py
  data/
    input/.gitkeep
  outputs/.gitkeep
  docs/
```

Nomes podem ser ajustados, mas as responsabilidades não devem voltar a se misturar em scripts por cenário.

---

## 12. Testes obrigatórios

### 12.1 Unidade

- peso de pesquisa mais recente;
- peso no limite da janela;
- cap de amostra;
- normalização soma 1;
- média ponderada manual;
- conversão totais para válidos;
- avaliação líquida nas duas escalas;
- intervalos do baseline;
- validações de cada erro bloqueante;
- normalização e resolução de aliases;
- cadastro automático de instituto novo com `peso_legacy` vazio, prior conservador no pipeline e alerta;
- fallback conservador para amostra ausente;
- fallback específico para amostra de segmento ausente;
- validação das combinações Brasil/Região/UF;
- menus dependentes `nivel_geografico → geografia` e `segmento_tipo → segmento`;
- expansão de uma lista de segmento ao preencher sua primeira célula vazia;
- validação de `Total/Total` e faixas de idade;
- partição estrita por adversário, geografia, segmento e base de voto;
- geração estável de `poll_group_id` e `poll_id`, incluindo alerta para assinatura ambígua;
- recortes da mesma pesquisa não aumentam o peso de Brasil/Total;
- separação entre house effect e erro excedente;
- teto de contribuição por instituto/tracking.

### 12.2 Integração

- ler workbook mínimo;
- processar `Lula3` e `Confrontos`;
- adicionar candidato X somente por novas linhas;
- processar Brasil/Total, SP/Total, Sudeste/Total e Brasil/Idade;
- gerar outputs automaticamente para cada recorte válido;
- impedir publicação Gold com erro;
- produzir todos os arquivos esperados;
- preservar rastreabilidade da linha original;
- processar a base sem exigir ID, fonte, aba, linha ou observação manuais.

### 12.3 Regressão

Quando os dados antigos forem recuperados:

- congelar input de referência;
- congelar outputs esperados;
- comparar com tolerância explícita;
- exigir justificativa para qualquer mudança.

### 12.4 Segurança e privacidade

- `.gitignore` cobre xlsx, csv/parquet reais, credenciais e outputs;
- logs não expõem dados desnecessários;
- configuração de conexão vem de ambiente/secret store.

---

## 13. Critérios de aceite do MVP

O MVP está concluído somente quando:

1. uma pesquisa é digitada uma vez;
2. uma única execução atualiza todos os cenários;
3. o baseline é reproduzido e testado;
4. erros são localizados por aba e linha;
5. novo confronto entra sem novo módulo estatístico;
6. novo confronto entra sem nova aba ou configuração específica;
7. geografia e segmento aparecem em Silver, Gold, gráficos e memória de pesos;
8. outputs têm `run_id` e versão;
9. memória de pesos reconstrói o último ponto;
10. CSVs seguem os contratos Databricks;
11. não há dados confidenciais no Git;
12. outra pessoa executa usando apenas o README;
13. testes automatizados passam;
14. limitações da probabilidade estão visíveis;
15. instituto novo e amostra ausente não interrompem a atualização, mas ficam claramente sinalizados;
16. células da mesma pesquisa compartilham `poll_group_id`, enquanto células distintas mantêm `poll_id` próprio.

---

## 14. Fases de implementação

### Fase −1 — Diagnóstico e mapeamento das planilhas

- preservar e calcular hash dos originais;
- inspecionar em modo somente leitura;
- documentar estrutura e dependências;
- construir mapeamento origem-destino;
- propor ajustes ao Excel-modelo;
- validar a facilidade de atualização;
- obter aceite antes de migrar.

### Fase 1 — Fundação

- estrutura do projeto;
- configuração;
- leitura do Excel;
- validação;
- dados sintéticos;
- testes iniciais.

### Fase 2 — Baseline

- pesos antigos;
- agregados;
- intervalos antigos;
- outputs;
- memória de cálculo.

### Fase 3 — Extensibilidade e Databricks

- cenários por configuração;
- dimensões geográficas e demográficas sem novas abas;
- tabelas Bronze/Silver/Gold;
- CSV/Parquet;
- run log.

### Fase 4 — Melhorias seguras

- covariância;
- amostra efetiva;
- tracking;
- cap por instituto;
- erro extra.
- qualidade histórica com shrinkage e prevenção de vazamento;
- incerteza específica de subgrupo e gates de cobertura;

### Fase 5 — Challenger

- espaço de estados;
- house effects;
- probabilidade calibrada;
- backtest comparativo.

Não iniciar a Fase 5 antes de a Fase 2 estar homologada.

---

## 15. Decisões pendentes que bloqueiam partes do trabalho

### Não bloqueiam a fundação

- caminho final no Databricks;
- recalibração futura dos pesos de institutos;
- aparência final dos dashboards;
- modelo temporal avançado.

### Bloqueiam homologação metodológica

- scripts e outputs antigos para reprodução;
- definição histórica da data usada pelo legado;
- base histórica de backtest;
- aprovação do peso legacy inicial e do fallback conservador;
- definição oficial de probabilidade;
- tratamento oficial de tracking.
- cobertura mínima para curva/probabilidade por recorte;
- política de harmonização de faixas etárias incompatíveis.

Se faltarem, implementar interfaces e fixtures, mas marcar o resultado como não homologado.

---

## 16. Definição de pronto para um agente autônomo

O agente não deve declarar conclusão apenas porque o código executa. Deve apresentar:

- árvore de arquivos;
- comandos de instalação e execução;
- resultado dos testes;
- exemplo de validação com erro;
- exemplo de execução bem-sucedida;
- lista de outputs;
- comparação com o baseline, quando disponível;
- decisões tomadas;
- decisões ainda pendentes;
- limitações conhecidas;
- instruções de handoff.
