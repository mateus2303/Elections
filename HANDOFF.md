# HANDOFF.md

## Status atual

Registro da sessao de 2026-07-17: pasta de pesquisas eleitorais nacionais adicionada ao repositorio para sincronizacao com o GitHub.

Registro da sessao de 2026-07-17: reorganizacao local sincronizada com o repositorio GitHub; commit de sincronizacao pendente de envio.

A base operacional foi corrigida e está aprovada no escopo dos dados tabulares oriundos dos 23 PDFs aproveitados. Foram reconciliadas 1.738 linhas — 431 em `Lula3` e 1.307 em `Confrontos` — sem divergência conhecida após reabrir o XLSX. A entrega atual está em `ENTREGA_FINAL/`; o pipeline estatístico ainda não foi implementado neste diretório (verificação em 2026-07-17).

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

## O que falta fazer

1. Levar `ENTREGA_FINAL/Pacote_Agregador_Kinea.zip` ao ambiente corporativo e seguir `DOCUMENTACAO/PROMPT_HANDOFF_CHAT_TRABALHO.md`.
2. Inspecionar o legado e as planilhas `input_agregador` e `input_eleicao2022` sem alterá-las; produzir diagnóstico e matriz origem → destino (`DOCUMENTACAO/PROMPT_HANDOFF_CHAT_TRABALHO.md`).
3. Recuperar fórmula, parâmetros e golden files do agregador antigo (`DOCUMENTACAO/ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
4. Criar o projeto Python, testes, validações e Modelo A (`DOCUMENTACAO/ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
5. Confirmar decisões metodológicas e dados de integração Databricks (`DOCUMENTACAO/ESTUDO_METODOLOGICO_AGREGADOR.md`; `DOCUMENTACAO/ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`).
6. Validar separadamente as séries legadas fora do escopo dos 23 PDFs reextraídos; o escopo PDF já está liberado.

## Como retomar rapidamente

1. Ler `AGENTS.md`, `PROJECT_CONTEXT.md`, `HANDOFF.md` e depois os quatro documentos de projeto.
2. Conferir os artefatos finais com:

```powershell
Get-ChildItem .\ENTREGA_FINAL
```

3. Abrir e preencher somente `ENTREGA_FINAL/Base_nova_limpa.xlsx`; preservar os arquivos-fonte (`DOCUMENTACAO/PROMPT_HANDOFF_CHAT_TRABALHO.md`).
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
- [x] Os 23 PDFs aproveitados foram reextraídos integralmente e 1.738/1.738 linhas foram reconciliadas contra a base exportada e reaberta.
- [x] Escopo PDF sem omissões, duplicatas semânticas, divergências numéricas ou de metadados.
- [ ] Séries legadas fora do escopo PDF foram homologadas no ambiente corporativo.

## Histórico curto de sessões

- 2026-07-16 — contexto persistente inicializado via init-context (Codex).
- 2026-07-16 — auditoria de acurácia concluída: planilha com `Resumo_Acuracia` e relatório final entregues; base mantida bloqueada para uso integral até validação das pendências (Codex).
- 2026-07-16 — segunda auditoria concluída por reextração direta dos PDFs; base corrigida e escopo PDF liberado, com a conclusão de 0,52% formalmente superada (Codex).
- 2026-07-17 — terceira auditoria integral concluída: cobertura ampliada de 1.302 para 1.738 linhas, erros residuais corrigidos, causas-raiz registradas e XLSX reaberto validado sem divergências (Codex).
- 2026-07-17 — estrutura de pastas simplificada e documentada; somente entrega atual, documentação ativa e histórico identificado foram mantidos (Codex).
