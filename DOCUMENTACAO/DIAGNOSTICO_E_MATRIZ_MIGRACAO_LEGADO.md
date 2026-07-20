# Diagnóstico e matriz de migração do legado

Data da inspeção: 2026-07-17  
Escopo: scripts e planilhas em `codigos e planilhas legado/`.

## Preservação e inventário

As duas planilhas foram lidas somente para consulta, sem abertura em Excel, recálculo, salvamento ou alteração. Os hashes abaixo registram a fotografia anterior à adaptação dos caminhos nos scripts.

| Arquivo | SHA-256 original | Papel identificado |
|---|---|---|
| `2tLulaxFlavio.txt` | `a1412d146a64a95a03fc1123eacc24e268a0c76078740f18ae9992aacc7ef316` | Agregação de segundo turno, Lula × Flávio. |
| `avgeoic.txt` | `a014a0824b16bad1826eaf49094adce4cea34948b0e524a71599520d0e62175d` | Agregação das três séries de avaliação do governo. |
| `avliq2series.txt` | `3c209ce858daaae554a76a9942c4fd30c1b9c4e29ddf0d4160d4d2d33a74fbab` | Agregação de aprovação líquida em duas janelas. |
| `input_agregador.xlsx` | `e45dd3361b4da2bdb9ee2a2fef829f740dd38347f88bb6ff7c5bf05d2caaaeaa` | Dados e cadastros legados para avaliação do governo. |
| `input_eleicao_2022.xlsx` | `5dc880016260b03b11b17b9ca2febaaedfc9f6bb6a114d3fb20741473f1a9bf5` | Dados e cadastros legados para confrontos de segundo turno. |

Não foram encontrados arquivos de saída antigos que possam servir como *golden files*. Logo, a fórmula foi recuperada do código, mas a equivalência numérica histórica ainda dependerá de uma saída aprovada ou de uma execução anterior recuperada.

## Estrutura que alimenta os scripts

### Avaliação do governo

`input_agregador.xlsx` possui, entre outras, as abas de cadastros `Pindograma 2024`, `pollstergraph total pré-22` e `ranking kinea 2022`; de dados brutos `pesquisas regulares` e `tracking atlas`; e de consolidação `padrao e tracking mm7d`.

A aba efetivamente lida por `avgeoic.txt` e `avliq2series.txt` é `padrao e tracking mm7d`, com 367 observações entre 2023-01-08 e 2026-07-12. Ela reúne 186 pesquisas regulares e 181 pontos semanais do tracking Atlas já suavizados em 7 dias. Seus campos operacionais são `data`, `Instituto`, `Amostra`, `Índice Pindograma`, `Índice Pollstergraph`, rankings legados, `Ótimo/Bom`, `Regular`, `Ruim/Péssimo` e `aprov liq`.

O `Índice Pindograma` vem do campo normalizado invertido do cadastro `Pindograma 2024`; é o único índice de qualidade de fato usado pelos três scripts. O `Índice Pollstergraph` e os rankings são carregados nas planilhas, mas não afetam os cálculos Python encontrados.

### Lula × Flávio

`input_eleicao_2022.xlsx` contém abas de pesquisas padrão, tracking e combinações para Lula × Flávio e Lula × Tarcísio. `2tLulaxFlavio.txt` lê apenas `padrao e tracking mm7d válidos2`, com 220 observações entre 2025-06-11 e 2026-06-21.

Nessa aba, as colunas `Lula` e `Flavio` já representam votos válidos: os percentuais totais das pesquisas padrão foram previamente reescalados para somar 100 entre os dois candidatos. A coluna `Indecisos e Abstentos` é mantida, mas não participa do cálculo Python. As duas últimas colunas têm fórmulas e valores, porém não possuem cabeçalhos nem são usadas pelo script.

As planilhas legadas mantêm vínculos externos de Excel e valores em cache. A execução Python lê esses valores salvos; ela não atualiza nem resolve tais vínculos. Esses vínculos não devem ser reproduzidos no novo fluxo.

## Fórmula efetivamente executada (Modelo A legado)

Para cada data já existente na aba de entrada, o script seleciona observações com idade entre 0 e `janela_dias` inclusive. Não há grade diária independente: só há ponto quando existe data na planilha de entrada.

Para cada observação `i` elegível, o peso é:

```text
qualidade_i = Índice Pindograma_i
recencia_i  = 1 - idade_em_dias_i / janela_dias
amostra_i   = min(Amostra_i, 5000) / 5000

peso_i = qualidade_i^0,50 × recencia_i^0,25 × amostra_i^0,25
estimativa = Σ(peso_i × valor_i) / Σ(peso_i)
```

Os parâmetros recuperados são:

| Script | Métrica | Janela | Qualidade | Cap de amostra |
|---|---|---:|---|---:|
| `avgeoic.txt` | Ótimo/Bom, Regular e Ruim/Péssimo | 30 dias | Índice Pindograma | 5.000 |
| `avliq2series.txt` | aprovação líquida | 15 e 30 dias | Índice Pindograma | 5.000 |
| `2tLulaxFlavio.txt` | Lula e Flávio em votos válidos | 30 dias | Índice Pindograma | 5.000 |

O intervalo de 95% usa `1,96 × erro-padrão` e variâncias binomiais ponderadas por `alpha_i = peso_i / Σ(peso_i)`. Para aprovação líquida, o legado soma as variâncias de aprovação e reprovação; para as demais séries, usa a variância binomial da própria proporção. Os intervalos são limitados a `[0, 100]` para proporções e `[-100, 100]` para aprovação líquida.

## Comportamento e limitações observados

1. Os scripts são independentes, com parâmetros e nomes fixos no próprio código; não há configuração única, CLI, testes ou memória de pesos.
2. `avgeoic.txt` e `avliq2series.txt` recebem pontos de tracking que já passaram por média móvel de 7 dias e os suavizam novamente na janela do agregador. Isso faz o tracking entrar como várias observações altamente correlacionadas.
3. A incerteza supõe independência entre observações e só cobre amostragem binomial. Ela não inclui correlação de tracking, efeito de instituto, incerteza dos pesos ou erro excedente.
4. A exclusão de valores ausentes é incompleta em `avgeoic.txt` e `2tLulaxFlavio.txt`: remove ausência apenas na métrica, não em qualidade ou amostra. Isso pode produzir resultado nulo se houver peso ausente.
5. A escolha de data é a data registrada no Excel; o legado não distingue data de campo, divulgação ou referência nem registra a decisão.
6. Há nomes e variáveis não usados, por exemplo `Índice Pollstergraph`, rankings, `sheet_1`, `sheet_2` e a importação de `norm`. Em `avliq2series.txt`, a aba de saída da janela de 30 dias é nomeada incorretamente como `Serie_Janela_100d`.
7. `2tLulaxFlavio.txt` possui título, candidatos, eixo vertical e nomes de arquivos fixos. Ele não é extensível a outro adversário, geografia ou segmento.
8. Não existe cálculo de probabilidade de liderança. Os intervalos exibidos não devem ser interpretados como previsão de vitória eleitoral.

Esses pontos não invalidam o Modelo A; eles definem o que precisa ser reproduzido de forma explícita e o que deverá ficar isolado como melhoria do Modelo B.

## Matriz origem → destino

| arquivo_origem | aba_origem | coluna_origem | significado | transformação para a nova base | aba_destino | coluna_destino | automatizável | observação |
|---|---|---|---|---|---|---|---|---|
| `input_agregador.xlsx` | `pesquisas regulares` | `data` | data da pesquisa | preservar como data real | `Lula3` | `data_referencia` | Sim | data de campo/publicação permanece indisponível quando não recuperável. |
| `input_agregador.xlsx` | `pesquisas regulares` | `Instituto` | instituto | normalizar pelo cadastro de aliases | `Lula3` | `instituto` | Sim | `Ipec`/`IPEC` exigem normalização por alias. |
| `input_agregador.xlsx` | `pesquisas regulares` | `Amostra` | amostra total | preservar número publicado | `Lula3` | `amostra_total` e `amostra_segmento` | Sim | para Total, a amostra do segmento repete a total. |
| `input_agregador.xlsx` | `pesquisas regulares` | `Ótimo/Bom`, `Regular`, `Ruim/Péssimo` | avaliação do governo | preservar percentuais publicados | `Lula3` | `otimo_bom_pct`, `regular_pct`, `ruim_pessimo_pct` | Sim | `aprov liq` deve ser derivado no pipeline. |
| `input_agregador.xlsx` | `tracking atlas` | dados diários e médias de 7 dias | tracking de avaliação | migrar somente a onda publicada; não usar média de 7 dias como nova fonte bruta | `Lula3` | campos equivalentes e `tipo_pesquisa=tracking` | Parcial | frequência deve refletir a publicação real; correlação será tratada no Modelo B. |
| `input_agregador.xlsx` | `Pindograma 2024` | `Nome`, `Normalizado Invertido` | peso de qualidade legado | normalizar nome e registrar peso | `Institutos` | `instituto`, `peso_legacy` | Sim | é o peso efetivamente usado pelo Modelo A. |
| `input_agregador.xlsx` | `pollstergraph total pré-22` | índice do instituto | indicador alternativo | não migrar para a entrada operacional; preservar em diagnóstico técnico, se necessário | futuro diagnóstico | campo técnico versionado | Sim | o código atual não o usa. |
| `input_eleicao_2022.xlsx` | `Lula vs Flavio padrao` | `data`, `Instituto`, `Amostra` | metadados do confronto | preservar e normalizar | `Confrontos` | `data_referencia`, `instituto`, `amostra_total`, `amostra_segmento` | Sim | nacional/total e pesquisa pontual. |
| `input_eleicao_2022.xlsx` | `Lula vs Flavio padrao` | `Lula`, `Flavio`, `Indecisos e Abstentos` | percentuais totais | preservar valores publicados | `Confrontos` | `lula_pct`, `adversario_pct`, `brancos_nulos_indecisos_pct`, `base_voto=Totais` | Sim | adversário é Flávio; outros candidatos são zero nesse confronto binário. |
| `input_eleicao_2022.xlsx` | `Lula vs Flavio tracking` | dados diários e média de 7 dias | tracking de confronto | migrar somente a observação publicada; manter tipo/frequência explícitos | `Confrontos` | campos equivalentes e `tipo_pesquisa=tracking` | Parcial | não transformar a média de 7 dias em novas ondas independentes. |
| `input_eleicao_2022.xlsx` | `padrao e tracking mm7d válidos2` | `Lula`, `Flavio` | insumo já convertido em votos válidos | derivar no Modelo A a partir de registros `Totais`, sem migrar como nova pesquisa | saída metodológica | valor analítico | Sim | é uma visão derivada do legado, não fonte operacional. |
| `input_eleicao_2022.xlsx` | vínculos externos e caches | índices e tracking importados | dependência de ambiente anterior | substituir por ingestão rastreável e cadastro local | pipeline | origem e diagnósticos | Sim | não preservar caminho corporativo nem vínculo externo. |

## Consequência para a próxima implementação

O Modelo A deve reproduzir separadamente: conversão para votos válidos quando aplicável, seleção da janela, pesos acima, média ponderada e intervalo legado. O Modelo B poderá corrigir a dependência entre ondas de tracking, a incerteza e a escolha da data de referência, mas sem substituir silenciosamente o baseline.
