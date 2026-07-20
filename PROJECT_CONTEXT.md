# PROJECT_CONTEXT.md

## Visão geral

O projeto reconstrói o agregador interno de pesquisas políticas para tornar a atualização simples, auditável e escalável: o operador preenche uma pesquisa uma única vez em Excel, e um pipeline futuro valida, pondera, agrega, gera gráficos e prepara dados para Databricks (`ROTEIRO_NOVO_AGREGADOR.md`).

## Objetivo de negócio/técnico

- Reduzir a operação recorrente a abrir `Base_nova_limpa.xlsx`, adicionar linhas publicadas, salvar e executar uma rotina única (`ROTEIRO_NOVO_AGREGADOR.md`).
- Produzir avaliação do Governo Lula III, confrontos Lula × adversário, probabilidade de Lula estar à frente hoje, gráficos, memória de pesos e tabelas auditáveis (`ROTEIRO_NOVO_AGREGADOR.md`).
- Aceitar novos adversários e recortes por Brasil, região, UF e segmento sem criar novas abas ou módulos (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Preparar contratos Bronze, Silver e Gold para dashboards no Databricks (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).

## Arquitetura e componentes principais

### Estado atual

- `ENTREGA_FINAL/Base_nova_limpa.xlsx`: base operacional consolidada com as abas `Lula3`, `Confrontos`, `Institutos`, `Controle`, `Instrucoes` e `Auditoria`, revalidada em 2026-07-17.
- `ENTREGA_FINAL/Pacote_Agregador_Kinea.zip`: pacote final com a base e os quatro documentos de handoff atualizados.
- `DOCUMENTACAO/`: contém roteiro, especificação, estudo metodológico e prompt para o chat do trabalho.
- `ARQUIVOS_ANTIGOS/auditoria_preliminar_2026-07-16/`: preserva a primeira auditoria e seu relatório apenas como histórico; não são artefatos operacionais.
- `README.md`: mapa simples da pasta e indicação inequívoca dos arquivos atuais.
- O MVP Python está em `src/agregador/`, com configuração em `config/` e testes sintéticos em `tests/`. Ele lê o Excel em modo somente leitura, gera IDs, validações, Modelo A oficial e Modelo B candidato isolado, memória de pesos, Bronze/Silver/Gold, relatórios e gráficos.
- `codigos e planilhas legado/`: contém três scripts históricos com caminhos locais adaptados e as duas planilhas-fonte preservadas. O diagnóstico e a matriz de migração estão em `DOCUMENTACAO/DIAGNOSTICO_E_MATRIZ_MIGRACAO_LEGADO.md`.

### Arquitetura-alvo

1. Excel único como entrada operacional, com `Lula3` e `Confrontos` como tabelas de fatos (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
2. Ingestão e padronização geram IDs e rastreabilidade sem trabalho manual (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
3. Validação separa erros bloqueantes de alertas e impede publicação Gold inválida (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
4. Motor metodológico versionado executa Modelo A, depois Modelos B e C em paralelo (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
5. Publicação gera gráficos, relatórios, CSV/Parquet e contratos Bronze/Silver/Gold (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).

## Decisões técnicas já tomadas

- 2026-07-15 — Um único Excel; separação por produto, não por candidato ou recorte (`ROTEIRO_NOVO_AGREGADOR.md`).
- 2026-07-15 — `Confrontos` reúne turno, tipo de cenário, cenário, adversário, geografia e segmento em colunas (`ROTEIRO_NOVO_AGREGADOR.md`).
- 2026-07-15 — Município está fora do escopo; Brasil, região e UF estão dentro (`ROTEIRO_NOVO_AGREGADOR.md`).
- 2026-07-15 — Segmentos iniciais: Total, Idade, Renda, Sexo, Escolaridade, Religião e Outro; preservar os rótulos publicados (`ROTEIRO_NOVO_AGREGADOR.md`).
- 2026-07-15 — `Institutos` mantém apenas `instituto`, `aliases`, `peso_legacy` e `situacao`; diagnósticos técnicos pertencem ao pipeline (`ROTEIRO_NOVO_AGREGADOR.md`).
- 2026-07-15 — Pesquisas fracas ou institutos novos permanecem na base com peso/prior conservador e alerta (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
- 2026-07-15 — Modelo A reproduz o legado; Modelo B melhora a abordagem; Modelo C é challenger temporal (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
- 2026-07-15 — A probabilidade inicial mede liderança atual, não vitória no dia da eleição (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
- 2026-07-15 — A base limpa evita repetição artificial semanal → diária como input; uma onda publicada é uma observação (`PROMPT_HANDOFF_CHAT_TRABALHO.md`).
- 2026-07-15 — Datas das abas operacionais usam `aaaa-mm-dd` e estão ordenadas do mais antigo ao mais novo (`ENTREGA_FINAL/Base_nova_limpa.xlsx`).
- 2026-07-16 — A primeira auditoria de acurácia classificou ausência de vínculo linha→página como erro do dado. Esse critério mede rastreabilidade, não acurácia numérica; portanto, o resultado de 0,52% não deve ser usado como estimativa de qualidade da base e foi superado pela reextração direta.
- 2026-07-16 — A primeira reextração dos 23 PDFs reconciliou somente 1.302 linhas e foi posteriormente considerada incompleta: a seleção por aberturas prioritárias deixou tabelas válidas fora do censo. O resultado foi superado pela revisão integral de 2026-07-17.
- 2026-07-17 — Os 23 PDFs aproveitados foram reextraídos integralmente, tabela por tabela. O contrato de cobertura final contém 1.738 linhas: 431 em `Lula3` e 1.307 em `Confrontos`; o XLSX reaberto apresentou 1.738/1.738 linhas, zero divergências célula a célula e zero erros de fórmula.
- 2026-07-17 — Foram recuperadas 422 linhas omitidas (72 Ipec, 41 PoderData, 245 Nexus e 64 Paraná Pesquisas), corrigidos 9 resultados com diferença de 0,1 p.p., 8 campos de amostra e 13 rótulos. Duas células publicadas explicitamente em branco foram preservadas como nulas.
- 2026-07-17 — Causas-raiz: lista restrita de segmentos prioritários; residual para forçar 100%; rótulos fragmentados pelo OCR; cópia da amostra total para recortes regionais; e filtro salvo que ocultava 1.356 linhas de `Confrontos`.
- 2026-07-17 — Regra preventiva: censo integral antes da extração, contrato de cobertura por PDF/onda/cenário/adversário, fallback obrigatório em `Outro`, soma literal por cabeçalhos sem residual, nulos explícitos, amostra do recorte somente quando publicada, dupla leitura com revisão visual e reconciliação após reabrir o XLSX.
- 2026-07-17 — Organização permanente: entrega atual em `ENTREGA_FINAL/`, documentos em `DOCUMENTACAO/`, histórico em `ARQUIVOS_ANTIGOS/` e proibição de pastas permanentes com UUID ou identificador opaco.
- 2026-07-17 — Fórmula observada do Modelo A legado: peso = `Índice Pindograma^0,50 × recência linear^0,25 × amostra limitada a 5.000^0,25`; os scripts usam janelas de 15 ou 30 dias e calculam pontos somente nas datas existentes. A reprodução deve manter esse comportamento isolado de melhorias futuras (`DIAGNOSTICO_E_MATRIZ_MIGRACAO_LEGADO.md`).
- 2026-07-18 — O Modelo A `legacy-baseline-1.0` foi reproduzido contra os outputs técnicos locais do legado: 317 pontos para cada série de avaliação e 161 para cada série Lula × Flávio, com diferença máxima de `2,85e-14` p.p. (precisão de ponto flutuante). A homologação corporativa continua pendente de golden files aprovados.
- 2026-07-18 — O Modelo B `model-b-candidate-0.1` foi implementado e mantido separado do baseline: meia-vida de 15 dias, janela de 90 dias, `n` efetivo conservador, shrinkage de qualidade, covariância multinomial para diferenças, piso de incerteza de 1,5 p.p. e teto de 35% por instituto. Como esse teto requer ao menos três institutos independentes, casos inviáveis recebem `evidencia_insuficiente_concentracao` e não geram probabilidade. O candidato aguarda backtest e aprovação.
- 2026-07-19 — O pacote de apresentação do Modelo A foi incorporado ao pipeline em `src/agregador/presentation.py`. Ele gera, sem nomes de candidatos fixados no código, séries de margem e intenção/não voto por adversário, comparação do último ponto, evidência por instituto com distinção entre regular e tracking, fotografias demográficas, mapa de composição do primeiro turno e avaliação do governo. A planilha `apresentacao/Resultados_Modelo_A.xlsx` é a saída executiva; `graficos_diagnostico/` permanece separado para conferência técnica. A entrega corrente fica em `ENTREGA_FINAL/RESULTADOS_ATUAIS/Modelo_A_Baseline_Oficial/`, com versões substituídas preservadas em `ARQUIVOS_ANTIGOS/EXECUCOES_PIPELINE/`.
- 2026-07-19 — A mesma apresentação foi habilitada para o Modelo B, sem misturar os agregados: `Resultados_Modelo_B.xlsx` inclui `Incerteza_Modelo_B`, `Probabilidade_Experimental` e intervalos experimentais nos gráficos de margem. O rótulo do modelo é explícito e o gate de cobertura usa o mínimo de três institutos definido no candidato. Probabilidades suprimidas permanecem como nulas com motivo; o B segue experimental.
- 2026-07-20 — Para transferência ao ambiente de trabalho, os códigos foram empacotados em `ENTREGA_FINAL/CODIGOS/`, com comandos e configurações separados para A e B e um único `MOTOR_COMUM/`. As configurações portáteis usam caminhos relativos; `Config.resolve_path` normaliza esses caminhos antes de publicar validações e resultados.

## Convenções e padrões

- Nomes de campos em `snake_case`; valores categóricos legíveis em Português-BR (`Base_nova_limpa.xlsx` e `ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Uma linha representa uma onda/célula publicada; recortes da mesma pesquisa compartilham `poll_group_id` futuro (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Agregar somente dentro da mesma combinação de produto, turno, cenário, adversário, geografia, segmento e base de voto (`PROMPT_HANDOFF_CHAT_TRABALHO.md`).
- Valores desconhecidos podem ficar vazios; o pipeline aplica fallback explícito e alerta (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Outputs devem carregar `run_id`, versão metodológica, origem e memória de pesos (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Código em Python, com entrada única `python -m agregador ...`; MVP implementado em `src/agregador/`, com instruções em `DOCUMENTACAO/MANUAL_EXECUCAO_AGREGADOR.md`. A apresentação é reproduzível a partir da base e não exige manutenção de uma lista de adversários.

## Dependências importantes

- Microsoft Excel ou leitor compatível para manutenção da base operacional (`Base_nova_limpa.xlsx`).
- Python: 3.12 ou superior, declarado em `pyproject.toml`.
- Bibliotecas: `pandas`, `numpy`, `openpyxl`, `matplotlib` e `PyYAML`; Parquet é emitido automaticamente quando houver engine compatível.
- Databricks: workspace, catálogo, schema, volume/storage, autenticação e política de execução A confirmar (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Git/CI: A confirmar; este diretório está sem controle de versão.

## Riscos e pontos de atenção

- A fórmula, pesos, janelas e cap efetivamente executados foram recuperados. Ainda faltam a decisão histórica formal para a data de referência e golden files aprovados para homologar numericamente o Modelo A (`DIAGNOSTICO_E_MATRIZ_MIGRACAO_LEGADO.md`).
- As planilhas legadas dependem de vínculos externos do Excel e de valores em cache; o novo pipeline não pode depender desses vínculos (`DIAGNOSTICO_E_MATRIZ_MIGRACAO_LEGADO.md`).
- Trackings e aberturas da mesma pesquisa são correlacionados e não podem multiplicar artificialmente a informação (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
- A margem de erro total não deve ser aplicada como margem de subgrupo; ausência de `amostra_segmento` exige fallback e alerta (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
- House effect, precisão e transparência são dimensões distintas; não condensar tudo em nota opaca (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
- Probabilidades por recorte exigem gates mínimos de cobertura e piso de incerteza (`PROMPT_HANDOFF_CHAT_TRABALHO.md`).
- O teto de 35% do Modelo B só é matematicamente viável com três ou mais institutos independentes; cobertura inferior é exibida, mas não recebe probabilidade nem status de evidência suficiente.
- Dados e caminhos corporativos podem ser confidenciais; não incluí-los em Git ou compartilhamentos não autorizados (`ROTEIRO_NOVO_AGREGADOR.md`).
- O escopo diretamente revalidado cobre 1.738 linhas tabulares inseridas a partir dos 23 PDFs aproveitados. Totais e séries legadas que não vieram desses PDFs continuam sujeitos à homologação corporativa separada; isso não invalida o escopo PDF já reconciliado.

## Backlog priorizado de próximos passos

1. Recuperar a decisão histórica para a data de referência e os golden files do legado, para homologar o baseline numérico (`DIAGNOSTICO_E_MATRIZ_MIGRACAO_LEGADO.md`).
2. Validar com a chefia as decisões metodológicas pendentes e os critérios de homologação (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
3. Homologar o Modelo A com golden files corporativos e a decisão formal sobre data de referência (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
4. Validar com o time os gates de cobertura e a regra definitiva de probabilidade de liderança.
5. Confirmar o ambiente Databricks e publicar os contratos Bronze/Silver/Gold no destino corporativo (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
7. Validar separadamente, no ambiente corporativo, as séries legadas fora do escopo dos 23 PDFs reextraídos.
8. Executar backtest walk-forward e definir critérios de aprovação do Modelo B antes de qualquer promoção; somente depois iniciar o challenger C (`ESTUDO_METODOLOGICO_AGREGADOR.md`).

## Monitor TSE

Em 2026-07-20 foi adicionado o pacote independente `src/monitor_tse/`. Ele acompanha os registros de pesquisas de 2026 sem escrever em `ENTREGA_FINAL/Base_nova_limpa.xlsx`. O estado mutável fica em `%LOCALAPPDATA%\MonitorPesquisasTSE`; a saída amigável fica em `ENTREGA_FINAL/MONITOR_TSE/monitor_pesquisas_tse.xlsx`.

Decisões do monitor:

- SQLite é a fonte de estado; o Excel é uma saída regenerável.
- `NR_PROTOCOLO_REGISTRO` é a chave oficial.
- Os CSVs consolidados `BRASIL` são usados; arquivos por UF não são concatenados.
- Os URLs dos três recursos tabulares são descobertos pelo catálogo CKAN do TSE, com fallback para os URLs CDN oficiais validados.
- `DT_DIVULGACAO` representa apenas permissão legal e permanece separada de publicação efetiva.
- Observações manuais são importadas da aba própria e mantidas em SQLite.
- O módulo de localização de publicação efetiva permanece desativado no MVP.
- A retenção de snapshots é configurável em `source.raw_retention_days` (padrão `0`, preservação indefinida); a janela de alertas usa `America/Sao_Paulo`.
- O pacote que deve ser enviado ao computador do trabalho fica em `ENTREGA_FINAL/MONITOR_TSE/`; o ponto de entrada é `run_monitor_tse.py` e o `output_dir` desse pacote é a própria pasta.

Última atualização: 2026-07-20 — Monitor TSE implementado e validado com fonte oficial atual; Modelos A e B continuam separados, com o A como baseline oficial e o B pendente de backtest/homologação.
