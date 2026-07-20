# HANDOFF.md

## Status atual

Registro da sessão de 2026-07-17: legado inspecionado em modo somente leitura, com hashes das duas planilhas preservados. Os três scripts históricos tiveram somente os caminhos de entrada e saída adaptados ao próprio diretório e foram executados com sucesso no Python local. O diagnóstico, a fórmula recuperada e a matriz origem → destino estão em `DOCUMENTACAO/DIAGNOSTICO_E_MATRIZ_MIGRACAO_LEGADO.md`.

Registro da sessao de 2026-07-17: pasta de pesquisas eleitorais nacionais adicionada ao repositorio para sincronizacao com o GitHub.

Registro da sessao de 2026-07-17: reorganizacao local sincronizada com o repositorio GitHub; commit de sincronizacao pendente de envio.

A base operacional foi corrigida e está aprovada no escopo dos dados tabulares oriundos dos 23 PDFs aproveitados. Foram reconciliadas 1.738 linhas — 431 em `Lula3` e 1.307 em `Confrontos` — sem divergência conhecida após reabrir o XLSX. O pipeline estatístico MVP está implementado em `src/agregador/`; a planilha continua sendo a única entrada operacional.

## Últimas mudanças

- Sem controle de versão; não há `git log` disponível (verificação local em 2026-07-16).
- 2026-07-15 — `Base_nova_limpa.xlsx` consolidada com seis abas, menus, cadastro de institutos, controle e auditoria; arquivo atual em `ENTREGA_FINAL/Base_nova_limpa.xlsx`.
- 2026-07-15 — Datas de `Lula3` e `Confrontos` padronizadas em `aaaa-mm-dd` e ordenadas cronologicamente (`Base_nova_limpa.xlsx`).
- 2026-07-15 — Pacote final recriado com a base e os quatro documentos de handoff (`Pacote_Agregador_Kinea.zip`).
- 2026-07-16 — A auditoria anterior de 0,52% foi identificada como inadequada para medir acurácia: ela tratava falta de vínculo linha→página como prova de erro. O artefato permanece apenas como diagnóstico histórico de rastreabilidade.
- 2026-07-16 — A primeira reextração dos 23 PDFs cobriu 318 linhas de `Lula3` e 984 de `Confrontos`, mas a revisão integral seguinte demonstrou que o censo estava incompleto; esse resultado foi superado em 2026-07-17.
- 2026-07-16 — Corrigidas 252 omissões de Lula × Renan, 246 células numéricas da Nexus, 21 duplicatas semânticas e metadados de Ipec, Futura, Nexus e Paraná Pesquisas.
- 2026-07-16 — Registradas regras permanentes: parser por cabeçalho, metadado por onda/PDF, expansão de todos os adversários, deduplicação semântica, soma literal das categorias e reauditoria após exportação.
- 2026-07-17 — Censo integral dos 23 PDFs concluído: 1.738/1.738 linhas reconciliadas no arquivo reaberto, com zero diferenças célula a célula, datas crescentes, 13 nomes definidos preservados e nenhum erro de fórmula.
- 2026-07-17 — Recuperadas mais 422 linhas publicadas; corrigidos 9 resultados de 0,1 p.p., 8 campos de amostra e 13 rótulos. A acurácia numérica anterior à correção era 4.937/4.946 = 99,82%; o indicador de 15,6% era inadequado porque reprovava uma linha inteira por qualquer metadado faltante.
- 2026-07-17 — A aba `Confrontos` foi reconstruída no mesmo workbook para remover 1.356 linhas ocultas por filtro salvo; a entrega final mantém seis abas, tabela única de confrontos e menus até a linha 10.000.
- 2026-07-17 — Novas regras permanentes: censo integral, contrato `esperado × exportado`, fallback em `Outro`, nulos explícitos, amostra do recorte somente quando publicada, dupla leitura com revisão visual e validação após reabrir o XLSX.
- 2026-07-17 — Pasta reorganizada: entrega em `ENTREGA_FINAL/`, quatro documentos em `DOCUMENTACAO/`, auditoria superada em `ARQUIVOS_ANTIGOS/` e remoção das pastas com UUID e dos temporários vazios.
- 2026-07-17 — Legado identificado: `avgeoic.txt`, `avliq2series.txt` e `2tLulaxFlavio.txt` aplicam média geométrica com peso de qualidade Pindograma (0,50), recência (0,25), amostra limitada a 5.000 (0,25) e janelas de 15 ou 30 dias. Não foram encontrados golden files de saída.
- 2026-07-17 — As fontes `input_agregador.xlsx` e `input_eleicao_2022.xlsx` mantiveram os hashes originais após a execução. Foram gerados e conferidos o gráfico e os três workbooks de saída do legado, todos em `codigos e planilhas legado/`.
- 2026-07-17 — Criado `DOCUMENTACAO/DIAGNOSTICO_E_MATRIZ_MIGRACAO_LEGADO.md`; caminhos corporativos foram removidos dos três scripts em favor de caminhos relativos ao diretório do script.
- 2026-07-18 — Execução final do Modelo A em `saidas/execucao_2026-07-18_114131`: 16.762 pontos agregados, 231.256 contribuições de pesos, 3.342 registros de probabilidade experimental e 12 gráficos. Validação: 0 erros bloqueantes e 2.437 alertas preservados.
- 2026-07-18 — Regressão técnica contra os outputs locais do legado: três séries de avaliação (317 pontos cada) e Lula/Flávio em válidos (161 pontos cada) reproduzidas com diferença máxima de 2,85e-14 p.p. Esses outputs não substituem golden files corporativos aprovados.
- 2026-07-18 — Modelo B `model-b-candidate-0.1` implementado em rota isolada (`--model b`), sem alterar o Modelo A: meia-vida de 15 dias, janela de 90 dias, `n` efetivo conservador, shrinkage de qualidade, covariância para diferenças, piso de incerteza de 1,5 p.p. e teto de 35% por instituto. Casos com menos de três institutos independentes recebem `evidencia_insuficiente_concentracao`; permanecem visíveis, mas sem probabilidade.
- 2026-07-18 — Execução final do Modelo B em `saidas/execucao_2026-07-18_120342`: 16.762 pontos agregados, 639.708 contribuições de pesos, 3.342 registros de probabilidade experimental e 12 gráficos. Validação: 0 erros bloqueantes e 2.437 alertas. Todos os grupos de pesos somam 1 (erro máximo `3,33e-16`); 6.226 pontos têm evidência suficiente e 10.536 foram corretamente marcados com concentração insuficiente.
- 2026-07-19 — A saída oficial foi reorganizada para `ENTREGA_FINAL/RESULTADOS_ATUAIS/Modelo_A_Baseline_Oficial/`. O Modelo A foi executado novamente com o pacote genérico de apresentação: 18.434 linhas na planilha `apresentacao/Resultados_Modelo_A.xlsx`, 16 gráficos de apresentação, 18.433 agregados (incluindo `nao_voto_totais`) e 0 erros bloqueantes; os 2.437 alertas permanecem registrados. A aba `Aberturas` foi reduzida aos campos interpretáveis, e `evidencia_por_instituto.png` diferencia regular de tracking. O hash da entrada foi `eccbb8ef5e1488db61754a5df9bacbe7831b2992e6448761b46da06033516e7f`.
- 2026-07-20 — A fonte `1st_round_-_with_flavio-140720261102.xlsx` foi incorporada à aba `Confrontos`: 28 ondas semanais, 169 linhas para 10 adversários e datas de 2026-01-06 a 2026-07-13. `Flávio Bolsonaro` foi harmonizado para `Flávio`; os demais rótulos foram preservados. As categorias `Voto branco / nulo` e `Não sei` foram somadas literalmente; amostra, margem e confiança permaneceram nulas porque não constam na planilha-fonte. A base foi ordenada por data e a auditoria recebeu a origem, a regra e a ressalva do cenário inferido pelo nome do arquivo.
- 2026-07-20 — Validação pós-importação concluída com 0 erros bloqueantes e 2.606 alertas conservadores (principalmente ausência de amostra de recorte). A reconciliação independente encontrou 169/169 linhas, nenhum rótulo corrompido e somas entre 99,8% e 100,1% por arredondamento publicado. Backup anterior preservado em `ARQUIVOS_ANTIGOS/Base_nova_limpa_antes_atlas_1T_2026-07-20.xlsx`.

## O que falta fazer

1. Levar `ENTREGA_FINAL/Pacote_Agregador_Kinea.zip` ao ambiente corporativo e seguir `DOCUMENTACAO/PROMPT_HANDOFF_CHAT_TRABALHO.md`.
2. Recuperar golden files e a decisão histórica para a data de referência, para homologar numericamente o Modelo A (`DOCUMENTACAO/DIAGNOSTICO_E_MATRIZ_MIGRACAO_LEGADO.md`).
3. Homologar o Modelo A com golden files corporativos e a decisão histórica da data de referência.
4. Confirmar decisões metodológicas e dados de integração Databricks (`DOCUMENTACAO/ESTUDO_METODOLOGICO_AGREGADOR.md`; `DOCUMENTACAO/ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
5. Validar separadamente as séries legadas fora do escopo dos 23 PDFs reextraídos; o escopo PDF já está liberado.
6. Rodar e avaliar o backtest do Modelo B antes de promovê-lo; até lá, manter `legacy-baseline-1.0` como única série oficial.

## Como retomar rapidamente

1. Ler `AGENTS.md`, `PROJECT_CONTEXT.md`, `HANDOFF.md` e depois os quatro documentos de projeto.
2. Conferir os artefatos finais com:

```powershell
Get-ChildItem .\ENTREGA_FINAL
```

3. Abrir e preencher somente `ENTREGA_FINAL/Base_nova_limpa.xlsx`; preservar os arquivos-fonte (`DOCUMENTACAO/PROMPT_HANDOFF_CHAT_TRABALHO.md`).
4. Instalação do pipeline: `python -m pip install -e .`.
5. Execução/teste do baseline: `python -m agregador validate --config config/agregador.yaml` e `python -m agregador run --config config/agregador.yaml`. A planilha do A fica em `ENTREGA_FINAL/RESULTADOS_ATUAIS/Modelo_A_Baseline_Oficial/apresentacao/Resultados_Modelo_A.xlsx`.
6. Modelo B experimental: `python -m agregador run --config config/agregador.yaml --model b`; conferir `methodology_version` e nunca misturar a saída com a do Modelo A.

## Checklist de validação

- [x] Fontes legadas locais inspecionadas somente em leitura e com hashes registrados em `DOCUMENTACAO/DIAGNOSTICO_E_MATRIZ_MIGRACAO_LEGADO.md`.
- [ ] Diagnóstico e matriz origem → destino aprovados antes de alterações.
- [ ] Modelo A reproduz o legado dentro de tolerância acordada.
- [x] Regressão técnica contra outputs locais do legado executada com diferença de ponto flutuante; homologação corporativa por golden file ainda pendente.
- [x] Testes sintéticos passam e erros bloqueantes impedem Gold na execução da base operacional.
- [x] Modelo B candidato executado em rota separada, com teto de concentração verificável; backtest e homologação ainda pendentes.
- [ ] Primeiro/segundo turno e espontânea/estimulada permanecem separados.
- [ ] Novo adversário, SP/Total, região/Total e Brasil/segmento funcionam sem nova aba.
- [ ] IDs, rastreabilidade, fallbacks e alertas são automáticos.
- [ ] Memória de pesos reconstrói o último ponto.
- [ ] Testes automatizados passam e erros bloqueantes impedem Gold.
- [ ] Contratos Bronze/Silver/Gold foram validados no Databricks.
- [ ] Nenhum dado confidencial ou credencial foi versionado.
- [x] Os 23 PDFs aproveitados foram reextraídos integralmente e 1.738/1.738 linhas foram reconciliadas contra a base exportada e reaberta.
- [x] Escopo PDF sem omissões, duplicatas semânticas, divergências numéricas ou de metadados.
- [ ] Séries legadas fora do escopo PDF foram homologadas no ambiente corporativo.

## Histórico curto de sessões

- 2026-07-16 — contexto persistente inicializado via init-context (Codex).
- 2026-07-16 — auditoria de acurácia concluída: planilha com `Resumo_Acuracia` e relatório final entregues; base mantida bloqueada para uso integral até validação das pendências (Codex).
- 2026-07-16 — segunda auditoria concluída por reextração direta dos PDFs; base corrigida e escopo PDF liberado, com a conclusão de 0,52% formalmente superada (Codex).
- 2026-07-17 — terceira auditoria integral concluída: cobertura ampliada de 1.302 para 1.738 linhas, erros residuais corrigidos, causas-raiz registradas e XLSX reaberto validado sem divergências (Codex).
- 2026-07-17 — estrutura de pastas simplificada e documentada; somente entrega atual, documentação ativa e histórico identificado foram mantidos (Codex).
- 2026-07-17 — legado inspecionado, documentado e executado localmente; fontes preservadas, caminhos portáveis aplicados e outputs verificados (Codex).
- 2026-07-17 — MVP Python criado em `src/agregador/`, com `pyproject.toml`, configuração em `config/`, testes sintéticos e manual em `DOCUMENTACAO/MANUAL_EXECUCAO_AGREGADOR.md`. Implementa leitura somente leitura, IDs, validação, Modelo A, votos válidos, memória de pesos, Bronze/Silver/Gold, relatórios, gráficos e backtest simples. A validação da base passou sem erros bloqueantes e com 2.437 alertas preservados. Testes sintéticos: 3/3 aprovados. A execução completa funcionou; antes da pausa, o código foi otimizado para não repetir payload bruto em `poll_weights.csv`. Retomar executando o comando final, conferindo a saída e removendo apenas as execuções temporárias desta sessão (Codex).
- 2026-07-18 — retomada concluída: execução final validada, memória de pesos conferida contra o agregado, gráficos revisados e regressão técnica do Modelo A aprovada contra os outputs locais do legado (Codex).
- 2026-07-18 — As quatro pastas de execução anteriores em `saidas/` são temporárias desta implementação; a remoção automática foi bloqueada pela política do ambiente. A entrega corrente é exclusivamente `saidas/execucao_2026-07-18_114131/`; remover as quatro pastas de 2026-07-17 quando o ambiente permitir (Codex).
- 2026-07-18 — Modelo B candidato implementado, testado (5/5) e executado com saída final em `saidas/execucao_2026-07-18_120342/`. O Modelo A segue em `saidas/execucao_2026-07-18_114131/`. As demais pastas de `saidas/` desta data são execuções intermediárias/validação e não devem ser usadas como entrega; a limpeza continua dependente da política do ambiente (Codex).
- 2026-07-19 — Pacote genérico de apresentação do Modelo A implementado, testado (5/5) e executado. A saída corrente e legível está em `ENTREGA_FINAL/RESULTADOS_ATUAIS/Modelo_A_Baseline_Oficial/`; não usar as antigas pastas `saidas/` como entrega.
- 2026-07-19 — A execução antiga `saidas/execucao_2026-07-17_173613` foi movida para `ARQUIVOS_ANTIGOS/EXECUCOES_PIPELINE/Execucao_Intermediaria_2026-07-17`; a pasta operacional `saidas/` ficou sem conteúdo e pode ser ignorada caso o OneDrive não permita removê-la.
- 2026-07-19 — Pacote genérico de apresentação do Modelo B implementado, testado (5/5) e executado em rota separada. Conferir `ENTREGA_FINAL/RESULTADOS_ATUAIS/Modelo_B_Candidato_Experimental/apresentacao/Resultados_Modelo_B.xlsx`; não misturar com o workbook do A.
- 2026-07-20 — Códigos portáteis foram organizados em `ENTREGA_FINAL/CODIGOS/`: `Modelo_A_Baseline_Oficial/`, `Modelo_B_Candidato_Experimental/` e `MOTOR_COMUM/`. As duas configurações usam caminhos relativos à `ENTREGA_FINAL`; validação portátil do A e do B passou com código 0. O pacote ZIP foi atualizado para levar os dois workbooks e o código.
- 2026-07-20 — A base ficou disponível após o fechamento do Excel. O ZIP transferível foi recriado para incluir `Base_nova_limpa.xlsx`, os códigos portáteis, os resultados dos Modelos A e B e a documentação; a versão histórica incompleta permanece em `ARQUIVOS_ANTIGOS/` apenas como registro.
- 2026-07-19 — O Modelo B foi executado novamente após a integração da apresentação: entrega em `ENTREGA_FINAL/RESULTADOS_ATUAIS/Modelo_B_Candidato_Experimental/`, workbook `apresentacao/Resultados_Modelo_B.xlsx`, 17 gráficos, 18.434 linhas no workbook, 18.433 agregados, 3.343 linhas de probabilidade experimental, 0 erros bloqueantes e 2.437 alertas. A saída registra `model-b-candidate-0.1`; Flávio tem 4 institutos e atende o gate do B, enquanto Renan tem 1 e permanece com evidência insuficiente.
- 2026-07-20 — Monitor TSE implementado em `src/monitor_tse/`, separado do agregador. Inclui SQLite local, snapshots dos três CSVs oficiais, histórico de versões, diffs, Excel, e-mail configurável e scripts do Agendador do Windows.
- 2026-07-20 — Fonte oficial 2026 validada em modo live: 1.251 pesquisas, 1.282 contratantes, 1.282 pagantes; geração principal `20/07/2026 05:46:52`. Dez execuções válidas de repetição terminaram com código 0 e zero novidades/alterações; a última confirmou a descoberta pelo catálogo CKAN com fallback CDN.
- 2026-07-20 — Testes do conjunto monitor + agregador: 17/17 aprovados, incluindo retries limitados, ZIP inválido, alteração de esquema, filtro de período e deduplicação da janela de alertas. O workbook `ENTREGA_FINAL/MONITOR_TSE/monitor_pesquisas_tse.xlsx` foi reaberto e conferido visualmente; as oito abas operacionais foram geradas. A primeira falha de exportação por timezone foi registrada e corrigida antes da validação final.
- 2026-07-20 — Ajustes finais: descoberta CKAN com fallback foi mantida, filtros de período e retenção opcional de snapshots foram documentados, e os alertas passaram a calcular a janela no fuso `America/Sao_Paulo`.
- 2026-07-20 — O alerta de e-mail não despeja a carga inteira na primeira execução: a linha de base alimenta a planilha/SQLite, e os e-mails posteriores usam novidades, alterações, janela de divulgação ou heartbeat.
- 2026-07-20 — O pacote transferível foi consolidado em `ENTREGA_FINAL/MONITOR_TSE/`, com `run_monitor_tse.py`, `src/monitor_tse/`, configuração, scripts Windows, testes, documentação e workbook. A execução foi validada a partir da própria pasta, com código 0 e 12 testes do pacote aprovados.
- 2026-07-20 — Atualização Atlas concluída e documentada; ao retomar, regenerar os workbooks de apresentação dos Modelos A e B se a intenção for refletir as novas pesquisas nos gráficos. A base operacional já está pronta para essa execução.
