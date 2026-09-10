# Handoff

## 2026-09-10

- Coletadas pesquisas de segundo turno do IBOPE/Ipec em `PESQUISAS_IBOPE_IPEC_SEGUNDO_TURNO`, com arquivos de 2002, 2006, 2010, 2014, 2018 e 2022.
- Coletadas pesquisas nacionais do CNT/MDA em `PESQUISAS_CNT_MDA_SEGUNDO_TURNO`, com rodadas de 2014, 2018 e 2022.
- PDFs conferidos com leitura de estrutura; páginas HTML foram mantidas somente quando eram a fonte pública verificável do resultado.
- Corrigido o arquivo da rodada CNT/MDA 125 de 2014: a notícia inicialmente baixada não correspondia à rodada; foi substituída por artigo correspondente ao registro BR-01139/2014.
- O TSE foi usado como catálogo e conferência de registros; os resultados vieram dos relatórios dos institutos ou de páginas públicas de divulgação.
- Para a seleção histórica de governador(a), foi feito censo do CESOP nas 216 combinações UF/ano (1994, 1998, 2002, 2006, 2010, 2014, 2018 e 2022), consultando variações de localidade e todas as páginas de resultados. Foram normalizados 1.111 registros únicos de Datafolha, IBOPE e Ipec, com 1.110 links de Tabelas públicos.
- Criada a pasta `PESQUISAS_GOVERNADOR_TABELAS_SELECIONADAS`, contendo 237 PDFs: uma tabela por instituto × UF × ano disponível, escolhida pela pesquisa mais próxima do primeiro turno ou do segundo turno quando existente. A pasta contém somente PDFs de Tabelas, sem questionários, fichas técnicas ou microdados.
- As escolhas com data exata foram priorizadas; 30 escolhas antigas tinham apenas mês/ano no CESOP e foram identificadas como aproximações. A classificação de 2006 foi corrigida para considerar Alagoas no primeiro turno. O caso CESOP/IBOPE 01241/TO/1998 vinha em ZIP e teve somente `TF_01241.pdf` extraído para a entrega.
- Para presidente, foi feita a varredura completa das 39 páginas do catálogo nacional do CESOP (388 registros). Criada a pasta `PESQUISAS_PRESIDENTE_NACIONAIS_SELECIONADAS`, com 19 PDFs: Datafolha 1994–2022 (8), IBOPE 1994–2018 (7, incluindo o relatório nacional de 2014), Ipec 2022 (1) e CNT/MDA 2014, 2018 e 2022 (3). Foram escolhidas as rodadas mais próximas do turno aplicável, com prioridade às pesquisas explicitamente marcadas como véspera; todos os PDFs finais foram validados e conferidos visualmente.
