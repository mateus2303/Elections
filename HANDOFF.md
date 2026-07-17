# HANDOFF.md

## Status atual

A base operacional foi corrigida e está aprovada no escopo dos dados tabulares oriundos dos 23 PDFs aproveitados. Foram reconciliadas 1.302 linhas diretamente contra 109 páginas; o pipeline estatístico ainda não foi implementado neste diretório (`outputs/019f62ff-04df-7cd2-8754-a00774c248dd/`; verificação em 2026-07-16).

## Últimas mudanças

- Sem controle de versão; não há `git log` disponível (verificação local em 2026-07-16).
- 2026-07-15 — `Base_nova_limpa.xlsx` consolidada com seis abas, menus, cadastro de institutos, controle e auditoria (`outputs/019f62ff-04df-7cd2-8754-a00774c248dd/Base_nova_limpa.xlsx`).
- 2026-07-15 — Datas de `Lula3` e `Confrontos` padronizadas em `aaaa-mm-dd` e ordenadas cronologicamente (`Base_nova_limpa.xlsx`).
- 2026-07-15 — Pacote final recriado com a base e os quatro documentos de handoff (`Pacote_Agregador_Kinea.zip`).
- 2026-07-16 — A auditoria anterior de 0,52% foi identificada como inadequada para medir acurácia: ela tratava falta de vínculo linha→página como prova de erro. O artefato permanece apenas como diagnóstico histórico de rastreabilidade.
- 2026-07-16 — Reextraídos os 23 PDFs aproveitados: 318 linhas de `Lula3` e 984 de `Confrontos`. A reconciliação final retornou zero omissões, duplicatas semânticas, divergências numéricas e divergências de metadados.
- 2026-07-16 — Corrigidas 252 omissões de Lula × Renan, 246 células numéricas da Nexus, 21 duplicatas semânticas e metadados de Ipec, Futura, Nexus e Paraná Pesquisas.
- 2026-07-16 — Registradas regras permanentes: parser por cabeçalho, metadado por onda/PDF, expansão de todos os adversários, deduplicação semântica, soma literal das categorias e reauditoria após exportação.

## O que falta fazer

1. Levar `Pacote_Agregador_Kinea.zip` ao ambiente corporativo e seguir `PROMPT_HANDOFF_CHAT_TRABALHO.md`.
2. Inspecionar o legado e as planilhas `input_agregador` e `input_eleicao2022` sem alterá-las; produzir diagnóstico e matriz origem → destino (`PROMPT_HANDOFF_CHAT_TRABALHO.md`).
3. Recuperar fórmula, parâmetros e golden files do agregador antigo (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
4. Criar o projeto Python, testes, validações e Modelo A (`ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
5. Confirmar decisões metodológicas e dados de integração Databricks (`ESTUDO_METODOLOGICO_AGREGADOR.md`; `ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
6. Validar separadamente as séries legadas fora do escopo dos 23 PDFs reextraídos; o escopo PDF já está liberado.

## Como retomar rapidamente

1. Ler `AGENTS.md`, `PROJECT_CONTEXT.md`, `HANDOFF.md` e depois os quatro documentos de projeto.
2. Conferir os artefatos finais com:

```powershell
Get-ChildItem .\outputs\019f62ff-04df-7cd2-8754-a00774c248dd
```

3. Abrir e preencher somente `Base_nova_limpa.xlsx`; preservar os arquivos-fonte (`PROMPT_HANDOFF_CHAT_TRABALHO.md`).
4. Instalação do pipeline: A confirmar — projeto e dependências ainda não encontrados.
5. Comando de execução/teste: A confirmar — CLI e testes ainda não implementados.

## Checklist de validação

- [ ] Originais corporativos inspecionados somente em leitura e com hashes registrados.
- [ ] Diagnóstico e matriz origem → destino aprovados antes de alterações.
- [ ] Modelo A reproduz o legado dentro de tolerância acordada.
- [ ] Primeiro/segundo turno e espontânea/estimulada permanecem separados.
- [ ] Novo adversário, SP/Total, região/Total e Brasil/segmento funcionam sem nova aba.
- [ ] IDs, rastreabilidade, fallbacks e alertas são automáticos.
- [ ] Memória de pesos reconstrói o último ponto.
- [ ] Testes automatizados passam e erros bloqueantes impedem Gold.
- [ ] Contratos Bronze/Silver/Gold foram validados no Databricks.
- [ ] Nenhum dado confidencial ou credencial foi versionado.
- [x] Os 23 PDFs aproveitados foram reextraídos e reconciliados contra a base exportada.
- [x] Escopo PDF sem omissões, duplicatas semânticas, divergências numéricas ou de metadados.
- [ ] Séries legadas fora do escopo PDF foram homologadas no ambiente corporativo.

## Histórico curto de sessões

- 2026-07-16 — contexto persistente inicializado via init-context (Codex).
- 2026-07-16 — auditoria de acurácia concluída: planilha com `Resumo_Acuracia` e relatório final entregues; base mantida bloqueada para uso integral até validação das pendências (Codex).
- 2026-07-16 — segunda auditoria concluída por reextração direta dos PDFs; base corrigida e escopo PDF liberado, com a conclusão de 0,52% formalmente superada (Codex).
