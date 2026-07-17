# AGENTS.md

## Ordem de leitura obrigatória

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `HANDOFF.md`
4. `README.md` — A confirmar; arquivo ainda não encontrado.

## Regras operacionais deste projeto

- Trabalhar e documentar em Português-BR, com linguagem objetiva e explicável ao time de análise (documentos `ROTEIRO_NOVO_AGREGADOR.md` e `PROMPT_HANDOFF_CHAT_TRABALHO.md`).
- Manter a entrega enxuta: não criar versões paralelas, cópias, abas ou arquivos auxiliares permanentes sem necessidade explícita (`PROMPT_HANDOFF_CHAT_TRABALHO.md`).
- Antes de alterar fontes legadas, inspecionar `input_agregador` e `input_eleicao2022` em modo somente leitura, registrar hashes e apresentar diagnóstico e matriz origem → destino (`PROMPT_HANDOFF_CHAT_TRABALHO.md`).
- Nunca pedir ao operador IDs, arquivo, aba, linha de origem ou observações; a rastreabilidade deve ser automática (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Novo candidato, geografia ou segmento entra por novas linhas em `Confrontos`, nunca por nova aba ou código específico (`ROTEIRO_NOVO_AGREGADOR.md`).
- Preservar datas do Excel como datas reais, exibidas em `aaaa-mm-dd`, e manter as abas operacionais em ordem cronológica crescente (`outputs/019f62ff-04df-7cd2-8754-a00774c248dd/Base_nova_limpa.xlsx`).
- Em primeiro turno, ler categorias pelo cabeçalho publicado e somar literalmente demais candidatos e respostas não candidatas; nunca usar residual para forçar 100% nem depender da posição fixa de colunas (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
- Não excluir pesquisas apenas por baixa qualidade ou divergência; aplicar regras objetivas, peso conservador e alertas (`ESTUDO_METODOLOGICO_AGREGADOR.md`).
- Implementar e homologar primeiro o Modelo A legado; manter Modelos B e C separados até backtest e aprovação (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Ao existir código, executar testes de unidade, integração e regressão previstos antes de declarar conclusão (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Não registrar dados confidenciais, planilhas reais, credenciais ou outputs sensíveis em controle de versão (`ROTEIRO_NOVO_AGREGADOR.md`).
- Padrão de commit: A confirmar (sem controle de versão).
- CI que bloqueia merge: A confirmar (não encontrado).
- Docker e deploy: A confirmar (não encontrado).
- Integração Databricks: contratos previstos; workspace, catálogo, schema, armazenamento e autenticação ainda precisam ser confirmados (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).

## Gatilhos de atualização obrigatória

- Ao final de qualquer sessão que altere código, dados finais ou decisões, atualizar `HANDOFF.md`.
- Ao final de tarefa que mude arquitetura, metodologia ou convenção, atualizar `PROJECT_CONTEXT.md`.
- Ao surgir nova diretriz de processo, atualizar `AGENTS.md` e registrar a data da mudança no `HANDOFF.md`.
- Não apagar o histórico curto de sessões; acrescentar uma nova linha por sessão relevante.

## Meta-regra

Este arquivo rege como trabalhar no projeto. Se houver conflito com uma instrução da sessão, avisar o usuário e pedir uma decisão antes de prosseguir.
