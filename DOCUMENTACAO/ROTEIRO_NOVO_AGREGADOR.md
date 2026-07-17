# Projeto Novo Agregador de Pesquisas Políticas

## Documento de visão, decisão e execução

**Status:** proposta para discussão  
**Objetivo:** orientar a decisão da liderança e a construção de um agregador confiável, simples de operar, auditável e extensível.  
**Escopo inicial:** avaliação do Governo Lula III e confrontos Lula × adversário, começando por Flávio e Renan, com abertura escalável por Brasil, região, UF e segmento demográfico e outputs preparados para Databricks. Município não faz parte do escopo.

---

## 1. Resumo executivo

O agregador atual cumpre uma função relevante, mas depende de planilhas intermediárias, cópias manuais, fórmulas, scripts duplicados e caminhos locais. Isso aumenta o risco operacional, dificulta a auditoria dos resultados e torna cada novo cenário mais caro de manter.

A proposta é construir um novo agregador a partir de uma base única e de um motor estatístico único. A operação recorrente deve ser reduzida a três ações:

1. inserir uma nova pesquisa em uma linha do Excel;
2. salvar o arquivo;
3. executar uma rotina única de atualização.

O sistema ficará responsável por validar os dados, buscar automaticamente o peso do instituto, calcular indicadores derivados, agregar as pesquisas, produzir intervalos de incerteza, atualizar gráficos e registrar quais observações determinaram cada resultado.

O projeto não deve começar escolhendo a fórmula mais sofisticada. Deve começar garantindo uma base correta, uma metodologia explicável e a capacidade de comparar versões por backtest. A recomendação é lançar primeiro um **MVP confiável e auditável**, comparável ao modelo atual, e evoluir apenas quando houver evidência de ganho.

### Decisão solicitada à liderança

Autorizar uma reconstrução controlada, mantendo o agregador antigo apenas como referência durante um período de execução paralela. O novo modelo somente se torna oficial após validação dos dados, backtests e aprovação metodológica.

---

## 2. Problema de negócio

O problema não é apenas gerar uma média de pesquisas. A organização precisa produzir uma leitura política atualizada que seja:

- rápida de atualizar;
- consistente entre cenários;
- capaz de incluir institutos de diferentes níveis de qualidade;
- transparente sobre premissas e pesos;
- resistente a erros de digitação e manipulação;
- reproduzível por outra pessoa;
- extensível para novos candidatos e perguntas;
- defensável diante de questionamentos da liderança.

Hoje, parte relevante do conhecimento está embutida em procedimentos manuais e scripts separados. Isso cria dependência da pessoa que opera o processo e dificulta distinguir erro de dado, erro de operação e efeito metodológico.

---

## 3. Visão do produto

> Uma única fonte de dados, uma única execução e resultados cuja origem possa ser explicada pesquisa por pesquisa.

### Experiência desejada

O operador abre `Base_nova_limpa.xlsx`, acessa a aba do produto correspondente, adiciona uma linha, preenche somente as informações publicadas, salva e executa `Atualizar Agregador`. Ao final, recebe:

- avaliação do governo atualizada;
- Lula × Flávio atualizado;
- Lula × Renan atualizado;
- qualquer novo Lula × adversário incluído por novas linhas, sem nova aba ou código;
- filtros por geografia e segmento demográfico quando esses dados existirem;
- probabilidade de Lula estar à frente hoje em cada confronto;
- gráficos padronizados;
- tabelas com séries históricas;
- relatório de validação;
- memória dos pesos usados no ponto mais recente;
- registro datado da execução.
- arquivos tabulares padronizados para carregamento no Databricks.

Se houver erro, o sistema deve apontar o problema em linguagem clara, indicando planilha, linha e campo. Ele não deve gerar silenciosamente um resultado possivelmente incorreto.

---

## 4. Princípios de desenho

### 4.1 Simplicidade operacional

O operador informa fatos publicados; o sistema calcula tudo o que for derivado. Não haverá PROCV manual, cópia entre abas, conversão manual para votos válidos ou edição de scripts para criar cenários.

### 4.2 Uma única fonte de verdade

Todos os gráficos e cálculos devem partir da mesma base validada. Arquivos de saída nunca devem ser utilizados como entrada manual da rodada seguinte.

### 4.3 Transparência metodológica

Todo resultado deve permitir responder:

- quais pesquisas entraram;
- quais foram excluídas e por quê;
- qual peso cada pesquisa recebeu;
- quais parâmetros estavam ativos;
- como o número final foi calculado.

### 4.4 Inclusão com ponderação

Pesquisas de menor qualidade não serão ignoradas automaticamente. Serão mantidas na base, identificadas e ponderadas de acordo com critérios previamente aprovados. Casos sem informação mínima obrigatória poderão ser exibidos, mas não necessariamente incorporados ao agregado.

### 4.5 Configuração, não duplicação

Lula × Flávio e Lula × Renan são valores da mesma tabela, não projetos diferentes. Adicionar candidato, região, UF ou faixa etária deve exigir apenas novas linhas com dimensões explícitas, nunca nova aba, fórmula ou script.

### 4.6 Evolução baseada em evidência

Alterações metodológicas devem ser comparadas por backtest, estabilidade, interpretabilidade e impacto. Sofisticação estatística sem ganho demonstrável não é prioridade.

### 4.7 Preservação e confidencialidade

Dados originais nunca serão sobrescritos. Bases confidenciais não devem ser incluídas em repositórios ou compartilhamentos não autorizados.

---

## 5. Escopo

### 5.1 Incluído no MVP

- cadastro manual simplificado em um único Excel;
- avaliação do Governo Lula III;
- confrontos Lula × adversário em uma tabela única, começando por Flávio e Renan;
- dimensões geográficas (`Brasil`, `Regiao`, `UF`), com menus guiados para Brasil, cinco regiões e 27 UFs;
- segmentos demográficos extensíveis, com menus iniciais para `Total`, `Idade`, `Renda`, `Sexo`, `Escolaridade`, `Religiao` e `Outro`;
- cadastro separado de institutos e pesos;
- validações automáticas;
- agregação temporal ponderada;
- intervalos de incerteza com limitações documentadas;
- gráficos e planilhas de saída;
- relatório de composição do último resultado;
- probabilidade separada de liderança atual; forecast eleitoral somente como produto futuro e experimental;
- exportação de tabelas normalizadas para Databricks;
- histórico das execuções;
- testes das regras críticas;
- documentação operacional e metodológica.

### 5.2 Fora do MVP

- coleta automática de pesquisas na internet;
- painel web;
- banco de dados corporativo;
- aplicação móvel;
- probabilidade de reeleição baseada em variáveis políticas ou econômicas externas ao confronto;
- correções complexas de “house effects” sem base histórica suficiente;
- automação de distribuição por e-mail ou canais internos.

Esses itens podem ser avaliados depois. Retirá-los do MVP protege prazo e qualidade.

---

## 6. Modelo mínimo de dados

### 6.1 Estrutura do arquivo único

O arquivo terá somente duas abas operacionais:

- `Lula3`;
- `Confrontos`.

Terá também três abas auxiliares, de manutenção rara:

- `Institutos`;
- `Controle`;
- `Instrucoes`.

A separação é por produto, não por candidato ou recorte. Criar `LulaxFlavio_SP`, `LulaxFlavio_Sudeste` ou `LulaxFlavio_16a24` é proibido porque multiplica estruturas. Candidato, geografia e segmento serão colunas da linha.

### 6.2 Aba `Lula3`

Uma linha representa uma pesquisa ou uma onda efetivamente publicada. A base limpa entregue usa somente campos que o time consegue manter:

- `data_referencia`;
- `instituto`;
- `tipo_pesquisa`;
- `frequencia_original`;
- `amostra_total`;
- `margem_erro_pp`;
- `nivel_confianca_pct`;
- `nivel_geografico`;
- `geografia`;
- `segmento_tipo`;
- `segmento`;
- `amostra_segmento`;
- `otimo_bom_pct`;
- `regular_pct`;
- `ruim_pessimo_pct`.

O núcleo histórico nacional é classificado como `nivel_geografico = Brasil`, `geografia = Brasil`, `segmento_tipo = Total` e `segmento = Total`. A versão entregue em 17/07/2026 contém 1.845 linhas em `Lula3`; 431 delas foram revalidadas diretamente contra os 23 PDFs aproveitados, incluindo região, idade, renda, sexo, escolaridade e categorias complementares em `Outro`. Para linhas totais, `amostra_segmento` repete `amostra_total` quando esta estiver disponível; em recortes, só é preenchida quando divulgada. Avaliação líquida, identificador, arquivo, aba, linha de origem, médias móveis e demais campos técnicos serão derivados pelo sistema.

### 6.3 Aba `Confrontos`

Uma linha representa o resultado de Lula diante de um adversário dentro de uma combinação específica de turno, tipo de cenário, cenário, geografia e segmento:

- `data_referencia`;
- `instituto`;
- `tipo_pesquisa`;
- `frequencia_original`;
- `amostra_total`;
- `margem_erro_pp`;
- `nivel_confianca_pct`;
- `turno`: `1º turno` ou `2º turno`;
- `tipo_cenario`: `Estimulada` ou `Espontânea`;
- `cenario`: identificador publicado, como `Cenário 1`, `Espontânea` ou `Único`;
- `adversario`;
- `nivel_geografico`;
- `geografia`;
- `segmento_tipo`;
- `segmento`;
- `amostra_segmento`;
- `lula_pct`;
- `adversario_pct`;
- `outros_candidatos_pct`: obrigatório no primeiro turno e igual a zero no segundo;
- `brancos_nulos_indecisos_pct`;
- `base_voto`: `Totais` ou `Validos`.

O histórico de Flávio e Renan fica unido nessa aba, preenchendo `adversario` com o nome correspondente. A versão entregue em 17/07/2026 contém 1.807 linhas em `Confrontos`: 1.138 de primeiro turno, 669 de segundo turno e 57 espontâneas, sempre separadas das estimuladas. Há 112 linhas por sexo e 185 por religião; os demais recortes publicados também são preservados. Não haverá `id_pesquisa`, `fonte_arquivo`, `fonte_aba`, `fonte_linha` nem `observacoes` para o operador preencher. A rastreabilidade será gerada automaticamente na leitura.

### 6.4 Inclusão de novo candidato

Para incluir Lula × candidato X, o operador adiciona linhas em `Confrontos` com o turno, o tipo de cenário, o cenário e `adversario = Candidato X`. Para incluir o mesmo confronto em São Paulo, usa `nivel_geografico = UF` e `geografia = SP`. Para uma abertura etária ou religiosa, usa `segmento_tipo = Idade` ou `Religiao` e a categoria publicada em `segmento`.

Nenhum desses casos exige nova aba ou código específico. O pipeline gera automaticamente `scenario_id`, `geography_id` e `segment_id` normalizados a partir dos campos preenchidos.

### 6.5 Aba `Institutos`

O cadastro visível deve continuar pequeno:

- `instituto`: nome canônico usado nos outputs;
- `aliases`: grafias equivalentes separadas por ponto e vírgula;
- `peso_legacy`: peso de qualidade usado pelo baseline, entre 0 e 1; vazio para instituto provisório;
- `situacao`: `Aprovado`, `Provisorio` ou `Inativo`.

Esses são os únicos campos que alguém poderá precisar manter ocasionalmente. Instituto desconhecido será cadastrado automaticamente como `Provisorio`, com `peso_legacy` vazio e aviso de validação; o pipeline aplicará um prior conservador configurado, sem gravar um peso inventado no Excel.

Versão metodológica, vigência, desempenho histórico, house effect, erro excedente, tamanho efetivo e peso efetivamente aplicado pertencem à camada técnica e serão gerados pelo pipeline. Mudanças nesses parâmetros devem ser versionadas e nunca reescrever silenciosamente outputs históricos.

### 6.6 Aba `Instrucoes`

É simultaneamente guia de preenchimento e fonte visível dos menus. Deve conter:

- exemplos nacionais, regionais, estaduais e demográficos;
- lista `Brasil`, cinco regiões e 27 UFs;
- faixas usuais de idade e renda;
- opções iniciais de sexo, escolaridade e outros segmentos;
- primeira célula vazia em cada lista para inclusão de uma nova categoria publicada;
- aviso para preservar exatamente o rótulo da pesquisa, sem harmonização manual;
- tratamento de valores ausentes e explicação de que IDs, fontes e métricas técnicas são automáticos.

As abas operacionais devem mostrar, acima dos cabeçalhos, uma instrução curta e grupos visuais. Em `Confrontos`, usar `DADOS DA PESQUISA`, `CENÁRIO E ADVERSÁRIO`, `ONDE?`, `PARA QUEM?` e `RESULTADOS`. O operador não deve precisar memorizar o significado das dimensões.

### 6.7 Regras das dimensões

- `nivel_geografico`: `Brasil`, `Regiao` ou `UF`;
- `geografia`: `Brasil`, `Sudeste`, `SP` ou outro código/nome controlado;
- `segmento_tipo`: `Total`, `Idade`, `Sexo`, `Escolaridade`, `Renda`, `Religiao` ou `Outro`;
- `segmento`: `Total` ou a categoria publicada, como `16-24`;
- Brasil/Total é o default para pesquisas nacionais sem abertura, mas deve ficar explícito em todas as linhas;
- uma linha só pode ser agregada com linhas da mesma combinação de produto, adversário, geografia, segmento e base de voto;
- vários recortes da mesma pesquisa não são observações independentes para um agregado nacional.

Os menus serão dependentes:

- `Brasil` → `Brasil`;
- `Regiao` → `Norte`, `Nordeste`, `Centro-Oeste`, `Sudeste` ou `Sul`;
- `UF` → uma das 27 siglas;
- `Total` → `Total`;
- `Idade`, `Renda`, `Sexo`, `Escolaridade` ou `Outro` → opções da coluna correspondente em `Instrucoes`.

As listas de segmento usam intervalos comuns apenas como atalhos. Se o instituto publicar outra faixa, o operador a acrescenta ao fim da lista correta e o menu cresce automaticamente. Intervalos como `16-24`, `18-24` e `16-29` permanecem distintos.

Sem pedir um ID ao operador, o pipeline criará dois identificadores técnicos: um `poll_group_id` para a pesquisa/onda-mãe e um `poll_id` para cada célula publicada. O agrupamento usará uma assinatura normalizada de instituto, datas disponíveis, amostra total, tipo e frequência; geografia, segmento, adversário, métrica e base de voto diferenciarão as células. Assinaturas incompletas ou ambíguas geram alerta de revisão, nunca uma união silenciosa.

O Excel será amigável ao operador; o dado de saída será amigável às máquinas. No Databricks, as dimensões serão preservadas como colunas e permitirão filtros sem criar novas tabelas por candidato ou recorte.

---

## 7. Cadastro, qualidade e efeitos de instituto

### 7.1 Objetivo

Incluir toda informação minimamente utilizável sem tratar como equivalentes pesquisas com evidências diferentes e sem transformar a planilha em um formulário metodológico.

### 7.2 Três dimensões que não devem virar uma única nota opaca

1. **Precisão:** amostra efetiva e margem de erro disponível.
2. **Viés sistemático ou house effect:** deslocamento médio do instituto em relação ao consenso comparável.
3. **Transparência:** disponibilidade de informações sobre amostragem, modo, ponderação, questionário e contratante.

House effect não é sinônimo de baixa qualidade. Um instituto pode deslocar a média de forma consistente e ainda ter baixa dispersão. Nesse caso, o modelo pode corrigir o nível estimado sem puni-lo como se fosse imprevisível. Erro excedente e instabilidade, por outro lado, reduzem sua influência.

### 7.3 Cadastro operacional versus registro técnico

O Excel contém apenas `instituto`, `aliases`, `peso_legacy` e `situacao`. O pipeline mantém um registro técnico por instituto e versão de metodologia, com:

- validade inicial e final;
- quantidade e recência da evidência;
- viés médio da margem Lula menos adversário;
- MAE, RMSE e erro excedente;
- house effect regularizado;
- tamanho efetivo estimado;
- peso aplicado em cada execução;
- indicadores de transparência, quando obtidos automaticamente.

O desempenho deve ser medido sobre margens, por contexto e sem vazamento temporal. Para avaliar 2022, por exemplo, a nota utilizada no backtest deve ser estimada apenas com informação anterior a 2022. Institutos com pouca história sofrem *shrinkage* para a média, evitando pesos extremos por amostra pequena.

### 7.4 Instituto novo e pesquisa incompleta

- instituto novo entra com `peso_legacy` vazio; o pipeline aplica prior conservador configurado e alerta;
- ausência de margem ou confiança gera alerta, não exclusão;
- ausência de amostra usa fallback conservador configurado e fica visível no relatório;
- pesquisas discrepantes permanecem como pontos e entram por método robusto;
- exclusão total exige duplicidade, impossibilidade numérica ou falha objetiva documentada.

### 7.5 Governança

- o operador não altera pesos durante a atualização rotineira;
- configurações e versões ficam congeladas por execução;
- toda revisão de peso ou correção de house effect precisa de backtest, data de vigência e aprovação;
- outputs preservam o valor bruto e o valor ajustado;
- a transparência pode gerar alerta ou teto de influência, mas não uma grande penalização arbitrária sem validação.

### 7.6 Perguntas que a liderança precisa decidir

- Quem aprova a promoção de uma metodologia?
- Qual período mínimo de execução paralela será exigido?
- Qual diferença em backtest é material para trocar o baseline?
- Qual fallback conservador será adotado quando amostra e margem estiverem ausentes?
- Com que frequência o cadastro técnico será recalibrado?

---

## 8. Metodologia estatística: estratégia de decisão

### 8.1 Modelo A — baseline oficial reproduzido

Reimplementar exatamente a fórmula executada pelo legado e validá-la contra golden files:

```text
peso = qualidade^0,50 × recencia^0,25 × amostra^0,25
```

Preservar janelas, cap de amostra em 5.000, tratamento de votos e intervalos encontrados no código antigo. A base limpa não deve ser convertida artificialmente em dados diários: uma onda semanal é uma observação semanal; a grade diária é um output do motor.

### 8.2 Modelo B — legado aperfeiçoado e explicável

Manter a média ponderada, mas testar como pacote auditável:

- tamanho efetivo `min(n_declarado, n_implícito_na_margem, cap)`;
- ponto médio do campo quando recuperável e divulgação como data de disponibilidade;
- covariância correta da avaliação líquida e da margem entre candidatos;
- uma linha por onda publicada;
- tamanho de amostra do segmento quando houver recorte;
- proibição de usar a margem total como se fosse margem do subgrupo;
- limite de contribuição por instituto/tracking;
- erro total com heterogeneidade e piso histórico;
- qualidade histórica com *shrinkage*;
- janela linear versus meia-vida escolhida por backtest.

Esse é o candidato preferencial à futura metodologia oficial por preservar a filosofia do legado e corrigir fragilidades objetivas.

### 8.3 Modelo C — challenger temporal robusto

Desenvolver separadamente um modelo temporal hierárquico com estado latente, efeitos de instituto, erro excedente, correlação de tracking e distribuição t-Student para reduzir a influência de outliers sem apagá-los. Sua primeira probabilidade oficializável é a de liderança atual. Previsão de vitória no dia da eleição continuará experimental até existir calibração suficiente.

### 8.4 Regra de promoção

O método recomendado deve equilibrar:

- erro em backtests;
- estabilidade diária;
- reação a mudanças reais;
- transparência;
- robustez a institutos discrepantes;
- facilidade de manutenção;
- capacidade de explicar o resultado à liderança.

Não se escolherá o método apenas porque ele produz a curva visualmente mais agradável.

---

## 9. Validações automáticas

### 9.1 Erros bloqueantes

- instituto ausente;
- data de referência inválida; se datas de campo forem enriquecidas automaticamente, início posterior ao fim;
- amostra negativa ou não numérica quando preenchida;
- percentual fora de 0 a 100;
- nível de confiança fora de faixa;
- base de votos não identificada quando necessária;
- adversário ausente em `Confrontos`;
- `nivel_geografico`, `geografia`, `segmento_tipo` ou `segmento` ausente;
- `nivel_geografico = Brasil` com `geografia` diferente de `Brasil`;
- `segmento_tipo = Total` com `segmento` diferente de `Total`;
- `amostra_segmento` maior que `amostra_total` quando ambas existirem;
- conflito entre resultados informados e sua soma;
- duplicata inequívoca.

### 9.2 Alertas não bloqueantes

- instituto não classificado;
- amostra ausente e fallback conservador aplicado;
- amostra do segmento ausente em recorte não total;
- recorte com poucas pesquisas ou apenas um instituto;
- margem de erro ausente;
- soma incompatível com as categorias publicadas ou com a nota de arredondamento da fonte;
- pesquisa muito antiga inserida posteriormente;
- valor muito distante das pesquisas próximas;
- possível duplicata;
- amostra excepcionalmente alta ou baixa;
- cenário preenchido parcialmente.

Alertas não devem alterar dados automaticamente. Devem solicitar revisão ou registrar uma decisão explícita.

---

## 10. Probabilidade de Lula ganhar

Há dois produtos diferentes. A **probabilidade de liderança atual** responde se Lula está à frente nas condições medidas hoje. A **probabilidade de vitória no dia da eleição** exige também modelar evolução futura. Misturar as duas coisas enfraqueceria a interpretação e criaria falsa precisão.

### Proposta para o MVP

- calcular a diferença agregada entre Lula e o adversário;
- calcular separadamente cada combinação de adversário, geografia e segmento;
- estimar a incerteza da diferença;
- transformar essa distribuição em probabilidade de Lula estar acima de 50% dos votos válidos ou acima do adversário, conforme a regra aprovada;
- publicar também intervalo, data de referência e versão metodológica;
- apresentar a probabilidade como estimativa condicional, nunca como certeza ou previsão definitiva da eleição.

### Antes de oficializar

- definir se “ganhar” significa liderar hoje ou vencer no dia da eleição;
- decidir como tratar indecisos, brancos e nulos;
- verificar se a incerteza inclui apenas erro amostral ou também dispersão entre institutos;
- calibrar o modelo em eleições passadas, quando houver dados;
- impedir probabilidades excessivamente confiantes quando existirem poucas pesquisas.
- não publicar probabilidade de um recorte sem cobertura mínima configurada.

No MVP, a recomendação é começar com **probabilidade de liderança nas condições atuais**. Uma previsão para o dia da eleição exige um modelo adicional de evolução temporal e não deve ser vendida como simples extensão da média.

---

## 11. Arquitetura conceitual

1. **Entrada:** Excel único, desenhado para digitação humana.
2. **Validação:** leitura, padronização e relatório de inconsistências.
3. **Transformação:** cálculo de avaliação líquida, votos válidos, cenário, geografia, segmento e formato interno comum.
4. **Institutos:** padronização por aliases, peso legacy e métricas técnicas calculadas automaticamente.
5. **Agregação:** aplicação da metodologia dentro de cada célula comparável `produto × adversario × geografia × segmento × base_voto`.
6. **Auditoria:** registro de parâmetros, dados utilizados e pesos.
7. **Saída:** gráficos, tabelas e resumo executivo.
8. **Arquivo histórico:** cópia datada dos resultados e da configuração.
9. **Publicação analítica:** arquivos normalizados e versionados para ingestão no Databricks.

Componentes devem ser independentes o suficiente para que uma mudança visual não altere cálculos e uma mudança metodológica não exija redesenhar o Excel.

---

## 12. Integração com Databricks

O Excel não deve ser a estrutura final dos dashboards. Ele é a interface de entrada. O pipeline transformará suas abas em tabelas estáveis, adequadas ao Databricks.

### Camadas propostas

- **Bronze — pesquisas brutas:** reprodução dos valores digitados, com aba de origem, data de carga e identificador da execução.
- **Silver — pesquisas padronizadas:** datas, percentuais, institutos, adversário, geografia, segmento, base de voto, qualidade e validações em formato longo.
- **Gold — resultados do agregador:** séries suavizadas, intervalos, probabilidade de liderança atual, pesos e indicadores prontos para dashboards; forecast eleitoral, quando existir, deve ficar separado e marcado como experimental.

### Tabelas mínimas

- `polls_raw`;
- `polls_standardized`;
- `institutes_registry`;
- `institutes_diagnostics`;
- `aggregates_timeseries`;
- `win_probability_timeseries`;
- `run_log`;
- `validation_issues`.

### Estratégia de carga

Na primeira versão, o pipeline poderá gerar CSV ou Parquet em pastas padronizadas para upload ao Databricks. Depois, a execução poderá gravar diretamente em uma área autorizada e atualizar tabelas Delta. A credencial e o ambiente não devem ficar embutidos no código.

Cada registro publicado deve conter:

- `run_id`;
- `data_processamento`;
- `versao_metodologia`;
- `poll_group_id` e `poll_id` gerados automaticamente;
- `cenario`;
- `adversario`;
- `nivel_geografico`;
- `geografia`;
- `segmento_tipo`;
- `segmento`;
- `data_referencia`;
- indicadores calculados;
- origem do dado.

Essa estrutura permite dashboards atualizados, comparação entre versões, auditoria e reconstrução histórica.

### Dashboards previstos

- evolução da avaliação do Governo Lula III;
- avaliação líquida;
- Lula × adversário com filtros de geografia e segmento;
- probabilidade de liderança atual por adversário/recorte e, separadamente, eventual forecast experimental;
- dispersão das pesquisas individuais;
- composição e peso das pesquisas no último agregado;
- qualidade, house effects e cobertura da base;
- alertas da última carga.

---

## 13. Entregáveis

### Produto

- arquivo-modelo de entrada;
- rotina única de atualização;
- motor de validação;
- motor de agregação;
- gráficos padronizados por produto, adversário, geografia e segmento;
- planilha de resultados;
- relatório de composição e pesos;
- histórico de execuções.

### Documentação

- manual de operação de uma página;
- dicionário de dados;
- nota metodológica;
- política de qualidade de institutos;
- catálogo de alertas e erros;
- procedimento de contingência;
- registro de decisões metodológicas.

### Garantia de qualidade

- testes das fórmulas;
- testes de validação;
- base fictícia de demonstração;
- backtest de 2022, se os dados forem recuperados;
- comparação paralela com o legado;
- checklist de aprovação da versão.

---

## 14. Plano de execução por fases

### Fase −1 — Inspeção somente leitura das planilhas legadas

**Objetivo:** compreender a estrutura real dos dados antes de definir ou implementar a nova planilha geral.

**Arquivos prioritários:**

- `input_agregador.xlsx`;
- `input_eleicao_2022.xlsx` ou `input_eleicao2022.xlsx`, conforme o nome encontrado no ambiente.

**Regra absoluta:** nesta fase, os arquivos devem ser tratados como evidência. O agente não pode editar, recalcular, corrigir, reformatar, salvar, renomear, mover ou sobrescrever as planilhas. Se uma ferramenta puder alterar metadados ou recalcular fórmulas ao abrir, deve-se trabalhar sobre uma cópia técnica descartável, preservando os originais e seus hashes.

**Inspeção obrigatória:**

- listar todas as abas, dimensões e tabelas;
- identificar cabeçalhos, tipos e unidades;
- localizar fórmulas, PROCVs, referências cruzadas e valores colados;
- mapear quais abas são fonte, intermediárias e outputs manuais;
- identificar colunas de instituto, datas, amostra, margem, confiança e resultados;
- distinguir pesquisas regulares, trackings e médias móveis;
- distinguir votos totais e válidos;
- localizar avaliação do Governo Lula III;
- localizar Lula × Flávio e outros confrontos existentes;
- identificar rankings e pesos de qualidade;
- procurar duplicidades, campos ausentes, nomes inconsistentes e mudanças de layout;
- registrar exemplos de linhas reais anonimizadas, se necessário;
- identificar o que pode ser migrado automaticamente e o que exige decisão humana.

**Entregáveis antes de qualquer implementação:**

1. inventário das duas planilhas;
2. diagrama das dependências entre abas;
3. dicionário de dados legado;
4. tabela de correspondência `origem → campo novo`;
5. lista de inconsistências e decisões pendentes;
6. proposta de planilha geral contendo `Lula3`, uma única aba `Confrontos` e dimensões geográficas/demográficas;
7. estratégia de migração inicial sem alterar os originais;
8. demonstração de como uma pesquisa nova será cadastrada em poucos minutos.

**Critério de desenho da nova planilha:** a estrutura final deve aproveitar os dados recuperáveis, reunir Flávio e Renan em `Confrontos` e permitir novo adversário, região, UF ou faixa etária apenas por novas linhas. Nenhuma facilidade visual pode comprometer rastreabilidade, votos totais/válidos ou compatibilidade com Databricks.

**Gate:** nenhuma arquitetura de ingestão, migração ou novo Excel será homologada antes da aprovação do mapeamento legado e do fluxo de atualização proposto.

### Fase 0 — Alinhamento e decisões

**Objetivo:** evitar construir antes de definir o que será considerado correto.

**Atividades:**

- confirmar usuários, destinatários e frequência de atualização;
- aprovar escopo do MVP;
- definir responsável metodológico;
- decidir critérios preliminares de qualidade;
- definir conceito de data da pesquisa;
- definir outputs esperados;
- inventariar bases históricas recuperáveis.

**Saída:** termo curto de decisões aprovado.

**Gate:** não iniciar implementação sem dono das decisões metodológicas.

### Fase 1 — Dados e protótipo operacional

**Objetivo:** provar que uma única base atende aos três produtos.

**Atividades:**

- desenhar o Excel mínimo;
- criar dicionário de dados;
- preencher uma base fictícia;
- validar o fluxo de cadastro com o operador;
- definir mensagens de erro;
- testar casos de pesquisa parcial.

**Saída:** modelo de entrada aprovado, ainda sem agregador oficial.

**Gate:** cadastrar uma pesquisa comum em poucos minutos, sem orientação externa.

### Fase 2 — Baseline estatístico reproduzível

**Objetivo:** reproduzir de modo limpo a lógica essencial do legado.

**Atividades:**

- implementar transformação e ponderação;
- centralizar parâmetros;
- gerar Lula III e todos os confrontos/recortes pelo mesmo motor;
- produzir memória de cálculo;
- testar fórmulas em exemplos controlados;
- comparar resultados com cálculos manuais.

**Saída:** primeira versão tecnicamente funcional.

**Gate:** todo número do último ponto pode ser reconstruído a partir da memória de cálculo.

### Fase 3 — Avaliação metodológica

**Objetivo:** escolher parâmetros e método com evidência.

**Atividades:**

- executar backtests históricos;
- testar sensibilidade a qualidade, tempo e amostra;
- estimar viés, MAE, RMSE, erro excedente e house effects com shrinkage;
- impedir vazamento temporal na avaliação dos institutos;
- comparar janela fixa e decaimento contínuo;
- simular inclusão de pesquisas fracas e outliers;
- testar concentração de tracking/instituto;
- documentar vantagens e limitações.

**Saída:** nota de recomendação metodológica para decisão da chefia.

**Gate:** aprovação formal do método e dos pesos.

### Fase 4 — Outputs e experiência operacional

**Objetivo:** transformar cálculo correto em produto utilizável.

**Atividades:**

- padronizar gráficos e legendas;
- criar relatório de validação;
- organizar arquivos por data, adversário, geografia e segmento;
- criar execução única;
- escrever manual de uma página;
- testar em outra máquina ou com outro usuário.

**Saída:** candidato à produção.

**Gate:** outra pessoa consegue atualizar o agregador apenas com o manual.

### Fase 5 — Execução paralela e homologação

**Objetivo:** reduzir risco de transição.

**Atividades:**

- rodar legado e novo modelo em paralelo;
- investigar divergências;
- registrar correções;
- obter aceite metodológico e operacional;
- congelar a primeira versão oficial.

**Saída:** versão 1.0 homologada.

**Gate:** liderança aceita resultados, limitações e procedimento de atualização.

### Fase 6 — Evolução controlada

**Objetivo:** melhorar sem transformar o sistema em novo legado.

**Possibilidades:**

- novos confrontos por configuração;
- correções por instituto;
- painel interativo;
- coleta semiautomática;
- distribuição automatizada;
- modelos temporais mais avançados.

Cada evolução deve ter hipótese, benefício esperado, teste e aprovação.

---

## 15. Critérios de sucesso

### Operacionais

- uma nova pesquisa exige somente uma nova linha;
- nenhuma cópia manual entre abas;
- nenhuma fórmula manual;
- nenhuma edição de código para atualizar dados;
- uma única execução produz todos os cenários;
- novo adversário, SP, Sudeste ou faixa etária entra sem nova aba;
- erros apontam campo e linha;
- outro operador consegue executar o processo.

### Metodológicos

- pesos e parâmetros documentados;
- institutos fracos incluídos de forma controlada;
- resultado reproduzível;
- memória de cálculo disponível;
- desempenho histórico comparado;
- limitações explicitadas nos outputs.

### Gerenciais

- tempo de atualização previsível;
- menor dependência de uma pessoa;
- novos adversários e recortes adicionados sem duplicação estrutural;
- explicação clara de mudanças relevantes no agregado;
- confiança para usar o material na tomada de decisão.

---

## 16. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Base histórica indisponível | limita backtests | recuperar outputs, usar dados públicos autorizados ou documentar a limitação |
| Peso de instituto mal calibrado | questionamento do resultado | baseline preservado, componentes separados, shrinkage, backtest sem vazamento e aprovação |
| Pesquisa fraca desloca a curva | leitura enganosa | peso mínimo testado, análise de sensibilidade e limite de concentração |
| Digitação incorreta | output incorreto | validações, listas e relatório antes do cálculo |
| Tracking domina a amostra | falsa precisão | identificar tracking e limitar/corrigir contribuição correlacionada |
| Subgrupo tratado como amostra total | falsa precisão em SP/região/idade | usar `amostra_segmento`, não herdar automaticamente a margem total e aplicar gate de cobertura |
| Faixas etárias incompatíveis | mistura de públicos diferentes | preservar rótulo original e agregar somente categorias harmonizadas por regra versionada |
| Modelo complexo demais | baixa manutenção | baseline simples e evolução somente com evidência |
| Mudança de escopo contínua | atraso | congelar MVP e manter backlog separado |
| Dependência do desenvolvedor | novo risco operacional | documentação, testes e homologação por segundo usuário |
| Dados confidenciais expostos | risco institucional | separação entre código e dados, regras de acesso e exclusão do versionamento |

---

## 17. Governança e responsabilidades

Devem existir, mesmo que acumulados pela mesma pessoa no início, quatro papéis claros:

- **Patrocinador:** define prioridade e aprova escopo.
- **Responsável metodológico:** aprova pesos, critérios e interpretações.
- **Operador:** cadastra pesquisas e executa a atualização.
- **Responsável técnico:** mantém validações, cálculos e outputs.

Mudanças devem ser classificadas:

- correção de dado;
- correção técnica;
- mudança visual;
- mudança metodológica.

Mudança metodológica exige registro, comparação com a versão anterior e aprovação. Resultados históricos não devem ser recalculados silenciosamente sem identificação de versão.

---

## 18. Decisões que precisam ser tomadas antes da construção

1. Qual data representa a pesquisa no agregado: fim do campo, ponto médio ou divulgação?
2. Quem aprova o `peso_legacy` inicial e sua eventual revisão?
3. Qual evidência mínima permite promover um instituto de `Provisorio` para `Aprovado`?
4. Qual informação mínima permite incluir uma pesquisa?
5. Tracking receberá tratamento diferente de pesquisa convencional?
6. Os confrontos serão divulgados em votos totais, válidos ou ambos?
7. Qual horizonte temporal será exibido nos gráficos?
8. Quem aprova mudanças metodológicas?
9. Quais outputs são efetivamente consumidos pela liderança?
10. Por quanto tempo legado e novo modelo rodarão em paralelo?
11. Qual cobertura mínima permite publicar curva e probabilidade de um recorte?
12. As faixas etárias serão mantidas como publicadas ou harmonizadas em categorias corporativas?

---

## 19. Proposta de apresentação à liderança

### Mensagem central

O projeto não busca apenas modernizar scripts. Busca reduzir risco operacional e transformar um processo pessoal e manual em uma ferramenta institucional, auditável e extensível.

### Narrativa sugerida

1. **Situação atual:** o agregador funciona, mas exige manipulação manual e conhecimento tácito.
2. **Nova necessidade:** mais cenários e inclusão de institutos heterogêneos aumentam a complexidade e o risco.
3. **Proposta:** base única, motor único, qualidade ponderada e auditoria completa.
4. **Benefício:** atualização simples, comparabilidade e capacidade de explicar cada resultado.
5. **Controle de risco:** MVP, backtest, execução paralela e aprovação por gates.
6. **Decisão pedida:** aprovação do escopo inicial e indicação do responsável metodológico.

---

## 20. Recomendação final

A solução mais coerente é uma reconstrução incremental, não uma extensão dos scripts separados. O legado deve servir como benchmark, não como restrição arquitetural.

O primeiro marco de sucesso não é um gráfico novo. É conseguir inserir uma pesquisa uma única vez e demonstrar, sem trabalho manual intermediário, como ela percorreu validação, ponderação, agregação e publicação.

Depois disso, a excelência virá da disciplina: medir, comparar, documentar e simplificar. O sistema será considerado pronto quando outra pessoa puder operá-lo, a liderança puder questioná-lo e cada resposta puder ser sustentada por dados e regras explícitas.

### Estudo metodológico associado

As alternativas de evolução, correções matemáticas, tratamento de tracking, house effects, probabilidade de liderança, forecast eleitoral e plano de backtests estão detalhados em `ESTUDO_METODOLOGICO_AGREGADOR.md`. O estudo estabelece o agregador antigo como baseline obrigatório e recomenda um processo de modelo oficial versus modelo desafiante.

### Especificação para implementação

O contrato de dados, arquitetura mínima, comandos, outputs, testes e critérios de aceite estão detalhados em `ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`. O texto pronto para iniciar o trabalho em outro agente está em `PROMPT_HANDOFF_CHAT_TRABALHO.md`.
