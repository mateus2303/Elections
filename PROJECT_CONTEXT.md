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
- Pipeline, CLI, testes e configuração ainda não existem neste diretório (`rg --files` em 2026-07-17).

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

## Convenções e padrões

- Nomes de campos em `snake_case`; valores categóricos legíveis em Português-BR (`Base_nova_limpa.xlsx` e `ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Uma linha representa uma onda/célula publicada; recortes da mesma pesquisa compartilham `poll_group_id` futuro (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Agregar somente dentro da mesma combinação de produto, turno, cenário, adversário, geografia, segmento e base de voto (`PROMPT_HANDOFF_CHAT_TRABALHO.md`).
- Valores desconhecidos podem ficar vazios; o pipeline futuro aplica fallback explícito e alerta (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Outputs devem carregar `run_id`, versão metodológica, origem e memória de pesos (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Código-alvo em Python, com entrada única `python -m agregador ...`; estrutura ainda não implementada (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`; `rg --files` em 2026-07-16).

## Dependências importantes

- Microsoft Excel ou leitor compatível para manutenção da base operacional (`Base_nova_limpa.xlsx`).
- Python: versão A confirmar; nenhum `pyproject.toml` ou `requirements.txt` encontrado.
- Bibliotecas Python para planilhas, dados, gráficos e Parquet: A confirmar; nenhum manifesto encontrado.
- Databricks: workspace, catálogo, schema, volume/storage, autenticação e política de execução A confirmar (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Git/CI: A confirmar; este diretório está sem controle de versão.

## Riscos e pontos de atenção

- A fórmula realmente executada pelo legado, a data histórica usada e os golden files ainda precisam ser recuperados para homologar o Modelo A (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Trackings e aberturas da mesma pesquisa são correlacionados e não podem multiplicar artificialmente a informação (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
- A margem de erro total não deve ser aplicada como margem de subgrupo; ausência de `amostra_segmento` exige fallback e alerta (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
- House effect, precisão e transparência são dimensões distintas; não condensar tudo em nota opaca (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
- Probabilidades por recorte exigem gates mínimos de cobertura e piso de incerteza (`PROMPT_HANDOFF_CHAT_TRABALHO.md`).
- Dados e caminhos corporativos podem ser confidenciais; não incluí-los em Git ou compartilhamentos não autorizados (`ROTEIRO_NOVO_AGREGADOR.md`).
- O escopo diretamente revalidado cobre 1.738 linhas tabulares inseridas a partir dos 23 PDFs aproveitados. Totais e séries legadas que não vieram desses PDFs continuam sujeitos à homologação corporativa separada; isso não invalida o escopo PDF já reconciliado.

## Backlog priorizado de próximos passos

1. No ambiente corporativo, inspecionar em modo somente leitura o repositório legado, `input_agregador` e `input_eleicao2022`; registrar hashes, diagnóstico e matriz origem → destino (`PROMPT_HANDOFF_CHAT_TRABALHO.md`).
2. Recuperar a fórmula canônica, parâmetros, definição de data e golden files do legado (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
3. Validar com a chefia as decisões metodológicas pendentes e os critérios de homologação (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
4. Criar o projeto Python, configuração única, ingestão e validações com testes (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
5. Implementar e comparar o Modelo A com o legado antes de qualquer melhoria oficial (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
6. Gerar memória de pesos, gráficos e tabelas normalizadas; validar novo adversário e recortes (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
7. Confirmar o ambiente Databricks e publicar contratos Bronze/Silver/Gold (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
8. Validar separadamente, no ambiente corporativo, as séries legadas fora do escopo dos 23 PDFs reextraídos.
9. Implementar Modelo B e, somente depois, challenger C com backtest walk-forward (`ESTUDO_METODOLOGICO_AGREGADOR.md`).

Última atualização: 2026-07-17 — inclui censo integral dos 23 PDFs, reconciliação de 1.738 linhas, organização intuitiva da pasta e proibição de diretórios opacos.
