# AGENTS.md

## Ordem de leitura obrigatória

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `HANDOFF.md`
4. `README.md`

## Regras operacionais deste projeto

- Trabalhar e documentar em Português-BR, com linguagem objetiva e explicável ao time de análise (documentos em `DOCUMENTACAO/`).
- Manter a entrega enxuta: não criar versões paralelas, cópias, abas ou arquivos auxiliares permanentes sem necessidade explícita (`DOCUMENTACAO/PROMPT_HANDOFF_CHAT_TRABALHO.md`).
- Usar nomes de pastas compreensíveis; nunca criar diretórios permanentes identificados apenas por UUID, hash ou código opaco. Entrega atual fica em `ENTREGA_FINAL/` e histórico em `ARQUIVOS_ANTIGOS/`.
- Antes de alterar fontes legadas, inspecionar `input_agregador` e `input_eleicao2022` em modo somente leitura, registrar hashes e apresentar diagnóstico e matriz origem → destino (`DOCUMENTACAO/PROMPT_HANDOFF_CHAT_TRABALHO.md`).
- Nunca pedir ao operador IDs, arquivo, aba, linha de origem ou observações; a rastreabilidade deve ser automática (`DOCUMENTACAO/ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Novo candidato, geografia ou segmento entra por novas linhas em `Confrontos`, nunca por nova aba ou código específico (`DOCUMENTACAO/ROTEIRO_NOVO_AGREGADOR.md`).
- Preservar datas do Excel como datas reais, exibidas em `aaaa-mm-dd`, e manter as abas operacionais em ordem cronológica crescente (`ENTREGA_FINAL/Base_nova_limpa.xlsx`).
- Em primeiro turno, ler categorias pelo cabeçalho publicado e somar literalmente demais candidatos e respostas não candidatas; nunca usar residual para forçar 100% nem depender da posição fixa de colunas (`DOCUMENTACAO/ESTUDO_METODOLOGICO_AGREGADOR.md`).
- Antes de extrair valores, fazer censo integral de todas as tabelas e aberturas publicadas no PDF; não limitar a leitura a páginas ou segmentos prioritários.
- Aplicar contrato de cobertura por PDF/onda/cenário/adversário: contar as linhas publicadas e reconciliar `esperado × exportado` antes de liberar a base. Segmento válido sem categoria própria entra em `Outro`, nunca é descartado.
- Preservar célula publicada em branco como nula; nunca inferir zero. Preencher `amostra_segmento` somente quando o recorte for explicitamente publicado, sem herdar `amostra_total`.
- Em extrações de PDF, combinar duas leituras independentes com conferência visual de cabeçalhos, quebras de rótulo, brancos e zeros; depois reabrir o XLSX exportado e repetir a reconciliação.
- Entregar as abas operacionais sem filtros ativos ou linhas ocultas; a conferência visual deve mostrar dados e menus utilizáveis ao abrir o arquivo.
- Não excluir pesquisas apenas por baixa qualidade ou divergência; aplicar regras objetivas, peso conservador e alertas (`DOCUMENTACAO/ESTUDO_METODOLOGICO_AGREGADOR.md`).
- Implementar e homologar primeiro o Modelo A legado; manter Modelos B e C separados até backtest e aprovação (`DOCUMENTACAO/ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Ao existir código, executar testes de unidade, integração e regressão previstos antes de declarar conclusão (`DOCUMENTACAO/ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
- Não registrar dados confidenciais, planilhas reais, credenciais ou outputs sensíveis em controle de versão (`DOCUMENTACAO/ROTEIRO_NOVO_AGREGADOR.md`).
- Padrão de commit: A confirmar (sem controle de versão).
- CI que bloqueia merge: A confirmar (não encontrado).
- Docker e deploy: A confirmar (não encontrado).
- Integração Databricks: contratos previstos; workspace, catálogo, schema, armazenamento e autenticação ainda precisam ser confirmados (`DOCUMENTACAO/ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).

## Gatilhos de atualização obrigatória

- Ao final de qualquer sessão que altere código, dados finais ou decisões, atualizar `HANDOFF.md`.
- Ao final de tarefa que mude arquitetura, metodologia ou convenção, atualizar `PROJECT_CONTEXT.md`.
- Ao surgir nova diretriz de processo, atualizar `AGENTS.md` e registrar a data da mudança no `HANDOFF.md`.
- Não apagar o histórico curto de sessões; acrescentar uma nova linha por sessão relevante.

## Meta-regra

Este arquivo rege como trabalhar no projeto. Se houver conflito com uma instrução da sessão, avisar o usuário e pedir uma decisão antes de prosseguir.
