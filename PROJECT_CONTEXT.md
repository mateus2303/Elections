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

- `Base_nova.xlsx` e `2nd_round_lula_vs_renan_santos-140720261102.xlsx`: fontes locais preservadas no diretório (`rg --files` em 2026-07-16).
- `outputs/019f62ff-04df-7cd2-8754-a00774c248dd/Base_nova_limpa.xlsx`: base operacional consolidada com as abas `Lula3`, `Confrontos`, `Institutos`, `Controle`, `Instrucoes` e `Auditoria` (arquivo XLSX analisado em 2026-07-16).
- `outputs/019f62ff-04df-7cd2-8754-a00774c248dd/Pacote_Agregador_Kinea.zip`: pacote final com a base e os quatro documentos de handoff (arquivo ZIP analisado em 2026-07-16).
- `outputs/019f6b82-269f-7810-bd1c-76fd20504089/auditoria_erros_extracao_pdf.xlsx`: auditoria em nível de campo com `Resumo_Acuracia`, 6.795 campos do período 2025-01-01 a 2026-07-15, log de erros, gravidade, metodologia e manifesto SHA-256 de 163 PDFs (gerado e validado em 2026-07-16).
- `outputs/019f6b82-269f-7810-bd1c-76fd20504089/relatorio_revisao_acuracia_extracao_original.docx`: relatório final com metodologia, tabela completa de acurácia, interpretação, pendências e regras preventivas (cinco páginas renderizadas e revisadas em 2026-07-16).
- Quatro documentos definem visão, especificação, metodologia e execução no ambiente corporativo (`ROTEIRO_NOVO_AGREGADOR.md`, `ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`, `ESTUDO_METODOLOGICO_AGREGADOR.md`, `PROMPT_HANDOFF_CHAT_TRABALHO.md`).
- Pipeline, CLI, testes, configuração e README ainda não existem neste diretório (`rg --files` em 2026-07-16).

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
- 2026-07-15 — Datas das abas operacionais usam `aaaa-mm-dd` e estão ordenadas do mais antigo ao mais novo (`outputs/019f62ff-04df-7cd2-8754-a00774c248dd/Base_nova_limpa.xlsx`).
- 2026-07-16 — A primeira auditoria de acurácia classificou ausência de vínculo linha→página como erro do dado. Esse critério mede rastreabilidade, não acurácia numérica; portanto, o resultado de 0,52% não deve ser usado como estimativa de qualidade da base e foi superado pela reextração direta.
- 2026-07-16 — Os 23 PDFs que alimentaram a base foram reextraídos de forma independente em 109 páginas tabulares. O escopo final reconciliado contém 1.302 linhas: 318 em `Lula3` e 984 em `Confrontos`, sem omissão, duplicata semântica, divergência numérica ou de metadado (`Base_nova_limpa.xlsx`; validação local em 2026-07-16).
- 2026-07-16 — Causas dos erros corrigidos: deduplicação por rótulo literal; metadado associado por instituto/mês em vez da onda; leitura por posição fixa após mudança de layout da Nexus; filtro que emitia somente um adversário; e uso de residual para forçar 100%.
- 2026-07-16 — Regra preventiva: interpretar cabeçalhos, vincular metadados à onda/PDF, expandir todos os adversários publicados, deduplicar por chave semântica e reconciliar `esperado × exportado` antes da liberação. Somar categorias publicadas e preservar diferenças de arredondamento; nunca forçar 100% por residual.

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
- O escopo diretamente revalidado cobre os dados tabulares inseridos a partir dos 23 PDFs aproveitados. Totais e séries legadas que não vieram desses PDFs continuam sujeitos à homologação corporativa separada; isso não invalida o escopo PDF já reconciliado.

## Backlog priorizado de próximos passos

1. No ambiente corporativo, inspecionar em modo somente leitura o repositório legado, `input_agregador` e `input_eleicao2022`; registrar hashes, diagnóstico e matriz origem → destino (`PROMPT_HANDOFF_CHAT_TRABALHO.md`).
2. Recuperar a fórmula canônica, parâmetros, definição de data e golden files do legado (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
3. Validar com a chefia as decisões metodológicas pendentes e os critérios de homologação (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
4. Criar README, projeto Python, configuração única, ingestão e validações com testes (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
5. Implementar e comparar o Modelo A com o legado antes de qualquer melhoria oficial (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
6. Gerar memória de pesos, gráficos e tabelas normalizadas; validar novo adversário e recortes (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
7. Confirmar o ambiente Databricks e publicar contratos Bronze/Silver/Gold (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
8. Validar separadamente, no ambiente corporativo, as séries legadas fora do escopo dos 23 PDFs reextraídos.
9. Implementar Modelo B e, somente depois, challenger C com backtest walk-forward (`ESTUDO_METODOLOGICO_AGREGADOR.md`).

Última atualização: 2026-07-16 — inclui reextração independente dos 23 PDFs aproveitados, correção da base e regras preventivas de extração.
