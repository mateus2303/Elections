# Estudo metodológico para evolução do Agregador de Pesquisas Políticas

## Como preservar uma metodologia elogiada e melhorá-la com evidência

**Status:** estudo para decisão e desenho do projeto  
**Escopo:** avaliação do Governo Lula III e confrontos Lula × adversário, com aberturas nacionais, geográficas e demográficas quando publicadas  
**Data:** julho de 2026

---

## 1. Conclusão executiva

A metodologia antiga não deve ser descartada. Ela possui quatro virtudes importantes:

1. combina várias pesquisas em vez de reagir excessivamente a uma observação;
2. considera qualidade, recência e amostra;
3. limita o ganho de influência de amostras muito grandes;
4. é relativamente simples de explicar e auditar.

A recomendação é reconstruí-la primeiro como **Modelo Oficial de Referência**, reproduzindo seus resultados dentro de tolerância definida. As melhorias devem entrar de forma incremental e comparável. Nenhuma mudança metodológica deve ser oficializada apenas por parecer sofisticada ou produzir um gráfico visualmente melhor.

O principal espaço de melhoria não está necessariamente na média central. Está na medição da incerteza, no tratamento de trackings e pesquisas correlacionadas, na estimação da qualidade dos institutos e na separação entre:

- estimativa da opinião pública no presente;
- probabilidade de Lula estar à frente no presente;
- previsão de vitória no dia da eleição.

Esses são três produtos diferentes.

### Recomendação em uma frase

**Manter a curva antiga como baseline, corrigir primeiro as fragilidades objetivas, desenvolver em paralelo um modelo temporal com efeitos de instituto e só promover mudanças que vençam o baseline em backtests previamente definidos.**

### Proposta de evolução

- **Modelo A — Legado reproduzido:** fórmula atual, limpa, testada e auditável.
- **Modelo B — Legado aperfeiçoado:** mesma lógica de ponderação, com melhor data de referência, tamanho amostral efetivo, tratamento de tracking e incerteza total.
- **Modelo C — Desafiante temporal:** modelo de espaço de estados/Bayesiano com efeitos de instituto, usado inicialmente apenas para comparação.

O Modelo B é o candidato mais realista à primeira metodologia oficial do novo agregador. O Modelo C é a fronteira de evolução, não uma exigência para lançar o produto.

---

## 2. O que a metodologia antiga faz

Para cada data observada, entram as pesquisas realizadas dentro de uma janela retrospectiva. O peso bruto da pesquisa `i` é:

```text
peso_i = qualidade_i^0,50 × tempo_i^0,25 × amostra_i^0,25
```

Com:

```text
tempo_i   = 1 − atraso_i / janela
amostra_i = min(n_i, 5.000) / 5.000
```

A estimativa é:

```text
estimativa = Σ(peso_i × resultado_i) / Σ(peso_i)
```

Os pesos normalizados são:

```text
alpha_i = peso_i / Σ(peso_i)
```

E a variância usada no intervalo de confiança é construída, em linhas gerais, como:

```text
variância = Σ(alpha_i² × variância_amostral_i)
```

### Interpretação correta

Apesar do nome “média geométrica”, o resultado final não é uma média geométrica dos percentuais. O que é geométrico/multiplicativo é a composição do peso. Depois disso, os resultados das pesquisas são combinados por média aritmética ponderada.

Essa nomenclatura deve ser corrigida na documentação para evitar dúvidas, sem necessidade de mudar a fórmula.

---

## 3. Por que o baseline é bom

### 3.1 Evita dependência de uma única pesquisa

A agregação reduz o ruído idiossincrático de levantamentos individuais. A literatura de polling reconhece que combinar pesquisas tende a produzir uma leitura mais informativa do que observar cada pesquisa isoladamente, embora não elimine vieses compartilhados. Uma revisão técnica sobre polling destaca justamente que o pooling pode melhorar a precisão, mas uma média ingênua não resolve erros sistemáticos comuns entre institutos ([Public Opinion Quarterly](https://academic.oup.com/poq/article/75/5/962/1830219)).

### 3.2 Pondera dimensões relevantes

Qualidade, recência e amostra são fatores defensáveis. Uma pesquisa recente deve refletir melhor o estado atual; uma amostra maior tende a ter menor erro amostral; e institutos com evidência histórica melhor podem receber mais confiança.

### 3.3 O cap de amostra é prudente

Limitar a influência de amostras declaradas muito grandes protege contra falsa precisão. O tamanho nominal não captura sozinho desenho amostral, ponderação, não resposta ou seleção. Pesquisa sobre erro total encontrou erro observado aproximadamente duas vezes maior do que o sugerido por margens amostrais usuais, além de componente de erro comum a pesquisas da mesma eleição ([Shirani-Mehr et al., JASA](https://ideas.repec.org/a/taf/jnlasa/v113y2018i522p607-614.html)).

### 3.4 É explicável

Para uso executivo, uma metodologia auditável tem valor próprio. A liderança pode compreender por que uma pesquisa ganhou ou perdeu peso. Um modelo mais complexo só é superior se melhorar resultados sem destruir a capacidade de explicação e manutenção.

---

## 4. Onde estão as limitações

## 4.1 A janela de 30 dias cria um corte artificial

Uma pesquisa com 29 dias participa; no dia seguinte pode sair integralmente. Embora o peso temporal já se aproxime de zero no limite, a regra ainda depende de datas discretas e gera diferenças conforme a grade de cálculo.

**Melhoria candidata:** decaimento exponencial ou meia-vida. Exemplo:

```text
peso_tempo = 0,5^(idade_dias / meia_vida_dias)
```

Com meia-vida de 15 dias, uma pesquisa perde metade do peso a cada 15 dias, mas não desaparece abruptamente. A meia-vida é intuitiva e pode ser calibrada por backtest.

Isso não significa que o decaimento exponencial vencerá. A janela antiga deve permanecer como concorrente.

## 4.2 A data da pesquisa precisa ser definida

Usar data de divulgação pode tratar como “nova” uma pesquisa cujo campo terminou vários dias antes. Usar apenas o fim do campo ignora a distribuição das entrevistas.

**Recomendação:** usar o ponto médio do campo como data estatística da observação e manter a divulgação como data de disponibilidade. Em backtests em tempo real, uma pesquisa somente pode entrar a partir da divulgação, evitando uso de informação que ainda não existia.

Isso resolve duas perguntas distintas:

- “a que momento da opinião pública esta pesquisa se refere?” — ponto médio do campo;
- “quando o analista poderia conhecê-la?” — data de divulgação.

## 4.3 O tamanho nominal pode superestimar a precisão

O cálculo atual usa `n`, limitado a 5.000. Mas pesquisas com ponderação, cotas, painéis ou desenhos complexos podem ter tamanho efetivo menor.

**Melhoria candidata:** calcular um `n_efetivo` conservador:

```text
n_efetivo = min(n_declarado, n_implícito_na_margem_de_erro, cap)
```

Para margem `m` expressa como proporção e confiança de 95%, usando o pior caso `p=0,5`:

```text
n_implícito ≈ 1,96² × 0,25 / m²
```

O projeto brasileiro `agregR` documenta abordagem semelhante: compara amostra declarada com amostra implícita na margem de erro e usa a figura conservadora para definir o erro de cada candidato ([agregR](https://rnmag.github.io/agregR/)). Essa é uma referência brasileira útil, mas sua proposta deve ser testada independentemente antes de adoção.

## 4.4 O intervalo atual captura apenas parte da incerteza

O intervalo binomial supõe que o principal erro vem da seleção aleatória de respondentes. Na prática, pesquisas também compartilham erros de não resposta, cobertura, questionário, provável eleitor, ponderação e modo de coleta. Esses erros não necessariamente se cancelam.

Estudo com 4.221 pesquisas encontrou erro total maior do que o implícito nas margens divulgadas e um componente de viés comum por eleição ([Shirani-Mehr et al.](https://ideas.repec.org/a/taf/jnlasa/v113y2018i522p607-614.html)). A AAPOR também ressalta que diferentes estratégias de amostragem, coleta, ponderação e modelagem do eleitorado podem produzir diferenças relevantes, e que transparência metodológica é um sinal importante de qualidade ([AAPOR](https://aapor.org/polling-accuracy/)).

**Consequência:** somar muitas pesquisas pode estreitar demais a banda se todas compartilharem o mesmo erro.

**Melhoria candidata:** decompor a incerteza em:

```text
erro total = erro amostral + heterogeneidade entre pesquisas
           + incerteza temporal + incerteza comum histórica
```

O nome do output também deve mudar de “IC 95%” para algo mais preciso, como “intervalo de incerteza de 95%”, caso ele incorpore componentes modelados além da amostragem.

## 4.5 A variância da avaliação líquida precisa considerar covariância

Se Ótimo/Bom e Ruim/Péssimo são categorias mutuamente exclusivas da mesma pergunta, não são independentes. Em um modelo multinomial:

```text
Cov(A, R) = −p_A × p_R / n
```

Logo:

```text
Var(A − R) = Var(A) + Var(R) − 2Cov(A,R)
```

Como a covariância é negativa, assumir independência tende a subestimar a variância da diferença. Uma forma equivalente é:

```text
Var(A − R) = [p_A + p_R − (p_A − p_R)²] / n
```

Essa é uma correção matemática objetiva e deve ser testada como parte do Modelo B.

Se aprovação e desaprovação vierem de outra pergunta, ainda deve ser confirmado se são categorias da mesma distribuição antes de aplicar a fórmula.

## 4.6 Confrontos também possuem dependência entre candidatos

Lula e adversário são respostas da mesma pesquisa. Calcular incerteza para cada um isoladamente e depois tratá-los como independentes pode produzir uma incerteza incorreta para a diferença.

O indicador decisório deve ser modelado diretamente:

```text
margem_lula = Lula − adversário
```

Quando as categorias são mutuamente exclusivas, a covariância multinomial deve entrar no cálculo. Em votos válidos normalizados, a transformação também precisa propagar a incerteza.

## 4.7 Tracking não equivale a pesquisas independentes

Médias móveis de tracking compartilham entrevistas entre dias consecutivos. Tratar cada dia como uma pesquisa nova multiplica artificialmente a informação e estreita intervalos.

**Opções, da mais simples à mais completa:**

1. usar apenas ondas não sobrepostas;
2. reduzir o peso de ondas sobrepostas;
3. limitar a contribuição total de um instituto em cada janela;
4. modelar explicitamente a correlação do tracking.

Para o MVP, a terceira alternativa oferece boa relação entre ganho e complexidade. O modelo desafiante pode incorporar correlação explícita.

## 4.8 Frequência de publicação pode dominar a curva

Um instituto que publica diariamente pode receber muito mais peso agregado do que outro que publica mensalmente, mesmo sem oferecer informação independente equivalente.

**Melhoria candidata:** cap de contribuição por instituto/janela ou normalização por cluster instituto-tracking. O cap deve atuar depois dos pesos individuais e antes da normalização final.

## 4.9 A nota de qualidade não deve ser absoluta nem instável

Uma nota baseada em poucos resultados históricos pode punir demais um instituto por acaso. Um instituto novo tampouco deve receber nota extrema.

**Melhoria candidata:** shrinkage para a média:

```text
qualidade_ajustada = credibilidade × desempenho_observado
                   + (1 − credibilidade) × média_dos_institutos
```

A credibilidade cresce com o número de eleições, pesquisas e variedade de contextos avaliados. Isso reduz overfitting e torna o peso de institutos novos conservador, mas não arbitrário.

O histórico deve separar, quando possível:

- eleição nacional e subnacional;
- primeiro e segundo turnos;
- distância até a eleição;
- tipo de pergunta;
- possível mudança relevante de metodologia.

O desempenho deve ser calculado prioritariamente sobre a **margem entre os candidatos**, não sobre o percentual isolado de cada nome. Os diagnósticos mínimos por instituto são:

- viés médio assinado da margem;
- MAE e RMSE;
- erro excedente ao explicado pela amostra;
- quantidade de pesquisas, eleições e contextos;
- recência da evidência;
- estabilidade depois de mudanças de método.

Esses números não podem usar o futuro. Em um backtest de 2022, a avaliação do instituto deve ser estimada apenas com dados anteriores a 2022. Depois que a eleição termina, a nova evidência pode alimentar a versão seguinte. Esse cuidado evita *data leakage* e rankings artificialmente bons.

### 4.9.1 Precisão, house effect e transparência são dimensões distintas

Não se recomenda condensar tudo em uma nota única sem expor os componentes:

1. **Precisão** informa quanto ruído a observação provavelmente contém.
2. **House effect** informa deslocamento sistemático relativo ao consenso comparável.
3. **Transparência** informa se desenho, modo, amostragem, ponderação, questionário e contratante podem ser auditados.

A [Transparency Initiative da AAPOR](https://aapor.org/standards-and-ethics/transparency-initiative/) e suas [boas práticas](https://aapor.org/standards-and-ethics/best-practices/) oferecem um checklist útil. Entretanto, transparência não deve receber uma grande penalização numérica arbitrária antes de provar relação com desempenho. No primeiro momento, ela funciona melhor como alerta, exigência de revisão ou teto prudencial de influência.

### 4.9.2 Marca do instituto não basta

O mesmo instituto pode mudar modo de coleta, painel, ponderação ou público-alvo. O registro técnico deve tratar `instituto + versão de metodologia + período de validade` como unidade de governança. O operador não preencherá isso pesquisa por pesquisa: o pipeline ou o responsável metodológico mantém a versão quando houver uma mudança comprovada.

## 4.10 House effects são diferentes de qualidade

Um instituto pode ser consistentemente dois pontos mais favorável a um candidato e ainda assim apresentar baixa dispersão. Isso é um **efeito de casa**, não necessariamente baixa qualidade.

Jackman propôs pooling temporal com correção para diferenças sistemáticas entre organizações ([Jackman, 2005](https://www.tandfonline.com/doi/abs/10.1080/10361140500302472)). Modelos posteriores também incluem efeitos próprios de instituto e erro não amostral.

**Melhoria candidata:** estimar desvios relativos por instituto somente quando houver sobreposição suficiente com outras casas. Aplicar regularização forte para institutos com poucos dados.

O modelo não consegue identificar simultaneamente “verdade” e viés absoluto de todos os institutos sem uma âncora. Portanto, house effects durante a campanha são normalmente desvios relativos ao consenso, não prova de que um instituto está errado.

## 4.11 Outliers não devem ser excluídos por conveniência

Uma pesquisa discrepante pode representar erro ou mudança real. Apagá-la porque “parece errada” induz herding e deixa a série artificialmente estável. A literatura alerta que herding reduz a dispersão observada e pode criar falsa confiança ([Government and Opposition](https://www.cambridge.org/core/journals/government-and-opposition/article/twilight-of-the-polls-a-review-of-trends-in-polling-accuracy-and-the-causes-of-polling-misses/E479293C0A401A275D27BE46B4EDC998)).

**Recomendação:** manter o ponto bruto, sinalizar a discrepância e usar método robusto:

- distribuição t-Student no modelo de observação;
- heterogeneidade entre pesquisas;
- limite de influência;
- análise com e sem a observação.

Excluir só por regra objetiva: duplicidade, impossibilidade numérica, falta de informação mínima ou problema comprovado.

## 4.12 Recortes geográficos e demográficos não são novas pesquisas

Resultados de Brasil, Sudeste, SP e faixas etárias publicados pela mesma pesquisa compartilham questionário, campo, desenho e parte ou toda a amostra. Eles devem ser armazenados como células diferentes do mesmo levantamento, não como pesquisas independentes adicionais.

Os principais riscos são:

- aplicar ao subgrupo a margem de erro divulgada para a amostra total;
- atribuir a cada recorte o peso integral da pesquisa;
- combinar faixas etárias com limites incompatíveis;
- usar recortes para estreitar artificialmente o agregado Brasil/Total;
- publicar probabilidade para uma célula com uma única pesquisa ou instituto.

**Regra:** cada curva é calculada dentro da combinação `adversario × geografia × segmento × base_voto`. O recorte usa `amostra_segmento` quando disponível. Se ela estiver ausente, o ponto continua visível, mas recebe fallback conservador e alerta. A margem total não deve ser reinterpretada como margem do subgrupo.

No Modelo C, poderá existir *partial pooling* entre regiões ou faixas etárias, mas o compartilhamento de informação precisa ser explícito, regularizado e validado fora da amostra. Não se deve reconstruir o Brasil pela média simples das regiões nem uma população total pela média simples das idades.

---

## 5. Melhorias propostas por nível

## Nível 0 — Reproduzir e proteger o legado

### Objetivo

Garantir que a reconstrução não perca a metodologia elogiada.

### Mudanças

- centralizar a fórmula;
- registrar todos os parâmetros;
- corrigir nomenclatura;
- usar os mesmos pesos, janelas e cap;
- gerar memória de cálculo pesquisa por pesquisa;
- criar testes com casos conhecidos;
- comparar outputs antigos e novos.

### Critério de aceite

Diferença máxima previamente acordada entre séries antigas e novas, explicada apenas por arredondamento, datas ou correções de dados.

### Recomendação

Obrigatório. Esse é o primeiro marco técnico.

## Nível 1 — Melhorias seguras e interpretáveis

### Pacote 1A: datas e entrada

- ponto médio do campo como referência estatística;
- divulgação como data de disponibilidade;
- distinção entre totais e válidos;
- validação de escalas de avaliação;
- identificação de tracking.

### Pacote 1B: precisão

- tamanho amostral efetivo conservador;
- covariância correta para avaliação líquida;
- covariância correta para margem entre candidatos;
- piso de incerteza histórica;
- cap por instituto/tracking.
- tamanho efetivo específico do segmento;
- gate mínimo de pesquisas e institutos por recorte;
- preservação da dependência entre células da mesma pesquisa.

### Pacote 1C: pesos

- comparar janela atual com meia-vida;
- qualidade com shrinkage;
- peso provisório para instituto novo;
- análise de sensibilidade dos expoentes 50/25/25.
- diagnóstico separado de viés, dispersão e transparência;
- backtest sem vazamento temporal para pesos de instituto.

### Recomendação

Esse deve ser o foco do primeiro ciclo de melhoria. Mantém a filosofia antiga e corrige fragilidades demonstráveis.

## Nível 2 — Modelo de efeitos aleatórios e house effects

### Estrutura

Tratar cada pesquisa como observação com:

```text
resultado = opinião_latente_na_data
          + efeito_relativo_do_instituto
          + erro_amostral
          + erro_extra
```

O erro extra captura heterogeneidade que o binomial não explica. Efeitos de instituto são regularizados, reduzindo correções extremas quando há poucos dados.

### Benefícios

- bandas mais realistas;
- menor falsa precisão;
- distinção entre viés relativo e ruído;
- inclusão mais natural de institutos fracos;
- peso emergente da incerteza, não apenas de nota manual.

### Riscos

- identificabilidade;
- poucos dados por instituto;
- explicação mais difícil;
- necessidade de diagnóstico e monitoramento.

### Recomendação

Construir como challenger após o baseline e o pacote seguro.

## Nível 3 — Modelo temporal de espaço de estados

Modelos dinâmicos tratam a opinião real como estado latente que evolui ao longo do tempo. As pesquisas são medições ruidosas desse estado. Jackman e Linzer são referências importantes: Jackman combina polls ao longo da campanha e estima house effects; Linzer utiliza um modelo Bayesiano dinâmico com random walk e pooling ([Jackman](https://www.tandfonline.com/doi/abs/10.1080/10361140500302472); [Linzer](https://ideas.repec.org/a/taf/jnlasa/v108y2013i501p124-134.html)).

### Modelo conceitual

```text
estado_t = estado_(t−1) + inovação_t
pesquisa_i = estado_na_data_i + house_effect_instituto + erro_i
```

### Benefícios

- série diária contínua;
- tratamento probabilístico da evolução;
- separação entre mudança real e ruído;
- propagação coerente de incerteza;
- simulação direta de probabilidades.

### Riscos

- prior de volatilidade influencia a suavização;
- modelo pode parecer preciso sem estar calibrado;
- maior custo de implementação, execução e manutenção;
- resultados dependem de diagnósticos de convergência e validação posterior.

Pesquisa recente mostra que modelos temporais podem evitar confundir mudança de preferência com erro de polling ao estimar bias e variância ([JRSS A, 2024](https://academic.oup.com/jrsssa/article/188/2/566/7720791)).

### Recomendação

Manter como modelo desafiante. Só promovê-lo se superar o Modelo B e permanecer operacionalmente sustentável.

---

## 6. Probabilidade de Lula ganhar

## 6.1 Três perguntas diferentes

### A. Qual é a intenção agregada hoje?

Resultado da curva de pesquisas.

### B. Qual é a probabilidade de Lula estar à frente hoje?

Derivada da distribuição da margem atual:

```text
P(Lula > adversário | pesquisas disponíveis)
```

### C. Qual é a probabilidade de Lula vencer no dia da eleição?

Exige adicionar incerteza futura:

```text
P(vitória na eleição | pesquisas, tempo restante, volatilidade e erro histórico)
```

Quanto mais distante da eleição, maior deve ser a incerteza futura. A probabilidade C não pode ser obtida apenas aplicando uma função normal ao intervalo da média atual.

## 6.2 Produto inicial recomendado

Publicar primeiro a **probabilidade de liderança atual**, com esse nome. Ela deve vir da distribuição conjunta de Lula e adversário ou, preferencialmente, da distribuição direta da margem.

## 6.3 Forecast eleitoral futuro

Só lançar após:

- backtests em várias eleições;
- estimação de volatilidade até o pleito;
- erro comum histórico;
- regra para indecisos;
- calibração probabilística;
- amostra suficiente de eleições e confrontos.

Modelos como o de Linzer combinam dinâmica temporal e informação histórica; versões mais completas também combinam fundamentos com polls ([HDSR/MIT Press](https://hdsr.mitpress.mit.edu/pub/nw1dzd02/release/2)). Isso é conceitualmente diferente de um agregador descritivo e deve ter governança própria.

## 6.4 Evitar probabilidades extremas

Erros de pesquisas são correlacionados e possuem componentes não amostrais. Ignorar isso produz 99% quando a evidência real talvez justifique muito menos. O intervalo preditivo precisa incorporar um piso de erro total.

---

## 7. Avaliação do Governo Lula III

Avaliação de governo difere de intenção de voto porque não há “resultado eleitoral final” que revele diariamente a verdade. Portanto, o modelo deve priorizar descrição do estado atual, não previsão.

### Cuidados específicos

- não misturar Ótimo/Bom com Aprova sem identificar a pergunta;
- não misturar Ruim/Péssimo com Desaprova;
- controlar mudanças de redação;
- separar abrangências e populações diferentes;
- identificar séries de tracking;
- manter Regular quando fizer parte da escala;
- calcular índices líquidos apenas dentro de perguntas comparáveis.

### Possível estrutura

Produzir duas famílias, quando houver dados:

1. `Ótimo/Bom – Ruim/Péssimo`;
2. `Aprova – Desaprova`.

Elas podem aparecer no mesmo dashboard, mas não devem ser fundidas em uma única série sem estudo de calibração entre escalas.

### Como validar sem ground truth diário

- previsão de pesquisas futuras deixadas de fora;
- estabilidade a revisões;
- cobertura de uma nova pesquisa pelo intervalo anterior;
- análise de resíduos por instituto;
- consistência entre janelas;
- detecção de quebras após eventos políticos conhecidos, sem calibrar o modelo para “contar uma história”.

---

## 8. Recortes geográficos e demográficos

### 8.1 Modelo de dados

A unidade observada é uma pesquisa/onda para uma célula de análise:

```text
produto × turno × tipo_cenario × cenario × adversario
        × nivel_geografico × geografia × segmento_tipo × segmento × base_voto
```

Exemplos válidos e separados:

- Lula × Flávio | Brasil | Total;
- Lula × Flávio | SP | Total;
- Lula × Flávio | Sudeste | Total;
- Lula × Flávio | Brasil | Idade 16–24;
- Lula × Renan | SP | Idade 25–34.

O núcleo legado nacional é classificado como `Brasil / Brasil / Total / Total`. A base de referência entregue em 15/07/2026 possui 56 aberturas de avaliação e, em `Confrontos`, 371 linhas de segundo turno e 157 de primeiro turno. Há 11 linhas espontâneas classificadas como parciais/baixo risco; elas são preservadas, mas devem receber alerta e tratamento conservador. Grafias equivalentes podem ser normalizadas, mas limites diferentes não são combinados.

O pipeline deve gerar um `poll_group_id` para a pesquisa/onda-mãe e um `poll_id` para cada célula. O primeiro é uma assinatura normalizada de instituto, datas disponíveis, amostra total, tipo e frequência; o segundo acrescenta produto, adversário, geografia, segmento, métrica e base de voto. Assim, o operador não preenche IDs, mas o modelo ainda reconhece que vários recortes pertencem ao mesmo levantamento. Assinaturas ambíguas devem ser sinalizadas e nunca unidas silenciosamente.

### 8.2 Turno e cenário

`1º turno` e `2º turno` são produtos estatísticos distintos. `Estimulada` e `Espontânea` também não podem compartilhar curva, tendência ou probabilidade. O campo `cenario` separa listas alternativas testadas dentro da mesma pesquisa.

No primeiro turno, cada linha compara Lula com um adversário do mesmo cenário. `outros_candidatos_pct` é a soma literal das demais candidaturas publicadas; `brancos_nulos_indecisos_pct` é a soma literal das categorias não candidatas. Nunca use residual para forçar 100%: com várias categorias arredondadas, a soma pode divergir de 100% e deve permanecer igual à fonte. As linhas do mesmo levantamento e cenário compartilham `poll_group_id`; repetir Lula diante de vários adversários não multiplica a evidência da pesquisa. No segundo turno, `cenario = Único` e `outros_candidatos_pct = 0`.

### 8.3 Geografia

`nivel_geografico` evita ambiguidades entre Brasil, região e UF. `geografia` guarda o código ou nome controlado. Brasil/Total não deve absorver SP ou Sudeste. Se uma pesquisa publica somente SP, ela informa a curva de SP, não a curva nacional. Município foi retirado do escopo para reduzir complexidade operacional sem prejudicar os recortes prioritários.

### 8.4 Idade e outros segmentos

O campo `segmento_tipo` aceita `Total`, `Idade`, `Sexo`, `Escolaridade`, `Renda`, `Religiao` e `Outro`. `segmento` preserva a categoria publicada. Para religião, os menus iniciais são `Católico` e `Evangélico`; a base atual tem estrutura pronta, mas zero observações porque a fonte recebida não publicou essa abertura.

Faixas `16-24`, `18-24` e `16-29` não são equivalentes. A primeira entrega deve mantê-las separadas. Uma harmonização futura só pode combinar categorias quando existirem microdados, pesos populacionais ou regra estatística defensável e versionada.

### 8.5 Tamanho de amostra e incerteza

- `amostra_total` descreve o levantamento completo;
- `amostra_segmento` descreve a célula publicada;
- para Total, os dois valores coincidem quando conhecidos;
- para recorte, a incerteza deve usar `amostra_segmento`;
- sem amostra do segmento, aplicar fallback conservador, alerta e piso de incerteza;
- a margem de erro total não pode ser copiada como margem do segmento.

### 8.6 Cobertura mínima

O dashboard pode exibir pontos brutos com pouca informação, mas curva e probabilidade precisam de gate configurado. O gate deve considerar, no mínimo:

- número de pesquisas;
- número de institutos;
- recência;
- amostra efetiva;
- concentração em um único tracking.

Abaixo do gate, o output deve dizer `evidencia_insuficiente` em vez de fabricar uma probabilidade.

### 8.7 Tratamento nos três modelos

- **Modelo A:** aplica a fórmula legada separadamente em cada célula, sem empréstimo entre células.
- **Modelo B:** adiciona tamanho efetivo do segmento, piso de erro, cap por instituto/tracking e gates de cobertura.
- **Modelo C:** pode usar modelo hierárquico com *partial pooling* entre geografias/segmentos, usando `poll_group_id` para preservar a identificação de cada célula e a correlação da pesquisa-mãe.

### 8.8 Implicação operacional

Uma única aba `Confrontos` substitui abas por candidato, turno e recorte. Novo candidato, cenário, SP, Sudeste, faixa etária ou religião entra por novas linhas. No Databricks, as mesmas colunas viram filtros do dashboard. Essa estrutura é mais escalável e, ao mesmo tempo, reduz arquivos, abas e scripts.

---

## 9. Como incluir pesquisas de menor qualidade

O objetivo é inclusão responsável, não equivalência.

### 9.1 Regra proposta

Toda pesquisa com informação mínima entra na base e aparece como ponto bruto. Sua influência no agregado depende de:

- qualidade histórica regularizada;
- precisão efetiva;
- recência;
- redundância com ondas do mesmo tracking;
- heterogeneidade residual;
- completude e transparência.

O ponto bruto nunca é apagado. O valor ajustado, quando houver correção de house effect, deve ser armazenado em campo separado. Assim, o dashboard e a memória de cálculo conseguem mostrar exatamente quanto veio do dado e quanto veio do modelo.

### 9.2 Peso legacy versus peso empírico

No Modelo A, usar o `peso_legacy` já herdado e aprovado como parte da reprodução. No Modelo B, o sistema deve produzir evidência empírica:

- erro histórico;
- viés relativo;
- dispersão residual;
- quantidade de observações;
- estabilidade por tipo de eleição;
- quantidade e recência da evidência;
- intervalo de incerteza da própria avaliação do instituto.

A decisão final pode combinar regra humana e evidência estatística, mas os componentes precisam permanecer visíveis. Um instituto com viés estável pode ter seu valor corrigido sem receber a mesma penalização de um instituto com erro excessivo e imprevisível.

### 9.3 Instituto novo

Na operação, recebe `peso_legacy` vazio, situação `Provisorio` e alerta, sem bloquear a atualização. O pipeline aplica um prior conservador configurado, próximo da média e com incerteza maior, sem escrever um número arbitrário no Excel. Isso é preferível a peso zero ou confiança máxima. À medida que acumula evidência, sua avaliação é atualizada por *shrinkage*.

### 9.4 Informações oficiais disponíveis

O TSE mantém dados abertos de pesquisas eleitorais, incluindo conjuntos referentes a 2022, 2024 e 2026, que podem ajudar a recuperar metadados e formar base histórica ([Dados Abertos do TSE](https://dadosabertos.tse.jus.br/dataset/?_tags_limit=0&groups=pesquisas-eleitorais&license_id=cc-by&res_format=CSV)). O registro eleitoral também existe para permitir verificação de metodologia, amostragem e coleta ([TSE](https://temasselecionados.tse.jus.br/temas-selecionados/pesquisa-eleitoral/registro)).

Isso abre uma frente futura de enriquecimento sem exigir que o operador digite todos os campos manualmente.

### 9.5 Cadastro mínimo no Excel

A aba visível de institutos deve conter somente:

| Campo | Função |
|---|---|
| `instituto` | nome canônico |
| `aliases` | grafias equivalentes separadas por `;` |
| `peso_legacy` | reprodução do baseline |
| `situacao` | `Aprovado`, `Provisorio` ou `Inativo` |

Todo o restante é calculado ou mantido tecnicamente: vigência, versão de método, desempenho histórico, house effect, erro excedente, tamanho efetivo, transparência e peso final. Essa separação impede que a melhoria metodológica aumente a carga de preenchimento diário.

### 9.6 Tracking, sobreposição e concentração

Um instituto não deve dominar apenas por publicar mais. No Modelo B, os pesos individuais são calculados primeiro, depois a contribuição total do instituto/tracking recebe um teto e somente então ocorre a normalização. No Modelo C, a correlação pode ser modelada explicitamente. Evidência metodológica sobre sobreposição amostral reforça que amostras compartilhadas podem induzir dependência e falsa precisão ([Journal of Economic Surveys](https://onlinelibrary.wiley.com/doi/full/10.1111/joes.12633)).

---

## 10. Plano de backtest

## 10.1 Princípio

O teste deve reproduzir o que seria conhecido em cada data. Não se pode usar resultado eleitoral, pesquisas divulgadas depois ou nota de instituto calculada com a própria eleição que está sendo prevista.

Isso exige **walk-forward validation**:

1. escolher uma data histórica;
2. usar somente informações disponíveis até ela;
3. gerar estimativa e probabilidade;
4. avançar no tempo;
5. repetir para todas as eleições e datas.

## 10.2 Modelos comparados

- A0: legado exato;
- A1: legado com correções matemáticas;
- B1: decaimento contínuo;
- B2: `n_efetivo` e cap por instituto;
- B3: erro extra/efeitos aleatórios;
- C1: espaço de estados sem house effects;
- C2: espaço de estados com house effects regularizados.

Os pacotes devem ser testados isoladamente e combinados. Caso contrário, não será possível saber qual mudança gerou o ganho.

## 10.3 Bases históricas

Prioridade:

- segundo turno presidencial de 2022;
- primeiro turno de 2022 para testar múltiplas categorias;
- eleições anteriores com dados comparáveis;
- eleições subnacionais apenas como análise complementar;
- avaliação de governo para validação preditiva de pesquisas futuras.

O artigo “Election polls in Brazil: Trends and performance” compara mais de duas mil pesquisas brasileiras de 2012 a 2020 e pode orientar a construção da avaliação histórica ([Estudos Avançados/USP](https://revistas.usp.br/eav/en/article/view/205985)).

## 10.4 Métricas para estimativas pontuais

- MAE da margem Lula − adversário;
- RMSE da margem;
- viés médio assinado;
- erro do último agregado antes da eleição;
- erro por horizonte: 7, 15, 30, 60 e 90 dias;
- estabilidade/revisão entre dias;
- erro por instituto e modalidade, se disponível.
- erro por nível geográfico e tipo de segmento, sem misturar células;

MAE é mais robusto; RMSE penaliza erros grandes. Ambos devem ser apresentados.

## 10.5 Métricas para intervalos

- cobertura de 50%, 80%, 90% e 95%;
- largura média;
- cobertura por horizonte;
- weighted interval score ou CRPS, se o modelo produzir distribuição completa;
- frequência de pesquisas futuras fora do intervalo previsto.

Um intervalo sempre enorme terá boa cobertura e pouca utilidade; um intervalo estreito terá aparência de precisão e pode falhar. Cobertura e largura precisam ser avaliadas juntas.

## 10.6 Métricas para probabilidades

- Brier score;
- log loss, com proteção contra 0%/100%;
- gráfico de calibração;
- resolução/discriminação;
- calibração por faixa de probabilidade;
- comparação com baseline simples.

O Brier score é uma regra própria: incentiva probabilidades honestas e penaliza excesso de confiança. Ainda assim, eleições são eventos correlacionados e a amostra histórica é pequena; os resultados precisam vir com incerteza, não como ranking definitivo.

## 10.7 Testes de estresse

- inserir uma pesquisa 8 pontos fora do consenso;
- adicionar dez ondas correlacionadas do mesmo tracking;
- remover o maior instituto;
- alterar uma nota de qualidade;
- simular instituto novo;
- reduzir todas as amostras efetivas;
- atrasar a divulgação;
- trocar janela por meia-vida;
- cenário com poucas pesquisas;
- cenário com pesquisas divididas em dois clusters.
- recorte de idade sem amostra do segmento;
- uma única pesquisa para SP;
- faixas etárias incompatíveis entre institutos;
- dez recortes da mesma pesquisa sem permitir que aumentem o peso nacional;

O resultado deve mudar de forma compreensível e sem falsa precisão.

---

## 11. Critérios para promover uma melhoria

Uma mudança só passa a oficial se cumprir todos os critérios relevantes:

1. melhora ou não deteriora materialmente os backtests;
2. possui intervalos melhor calibrados;
3. não cria instabilidade operacional;
4. é explicável aos usuários;
5. funciona com pouca informação;
6. não depende de dados indisponíveis no fluxo real;
7. possui teste automatizado;
8. registra versão e parâmetros;
9. foi executada em paralelo;
10. recebeu aprovação metodológica.

Se os resultados forem mistos, o legado permanece oficial.

---

## 12. Recomendação metodológica inicial

## 12.1 Curva central

Começar com a filosofia atual:

```text
peso = qualidade^a × recência^b × precisão^c
```

Comparar:

- recência linear em janela versus meia-vida;
- `n` truncado versus `n_efetivo`;
- qualidade fixa versus qualidade regularizada;
- ausência versus cap de contribuição por instituto.

Os expoentes 0,50/0,25/0,25 permanecem como baseline, não como verdade definitiva.

## 12.2 Intervalo

Substituir o intervalo puramente binomial por:

```text
variância total = variância amostral ponderada
                + heterogeneidade estimada
                + piso histórico de erro comum
```

No curto prazo, o piso pode ser estimado por backtest. No modelo desafiante, pode ser inferido hierarquicamente.

## 12.3 Tracking

Identificar explicitamente e limitar a contribuição total dentro da janela. Não usar cada média móvel como observação independente plena.

## 12.4 House effects

Exibir primeiro como diagnóstico. Aplicar correção no resultado oficial somente após dados suficientes e validação fora da amostra.

## 12.5 Probabilidade

Publicar inicialmente probabilidade de liderança atual. Manter previsão eleitoral futura como produto experimental.

---

## 13. Plano de trabalho recomendado

### Etapa 1 — Reconstrução fiel

- implementar fórmula antiga;
- criar testes;
- produzir memória de pesos;
- recuperar resultados conhecidos;
- definir tolerância de reprodução.

### Etapa 2 — Base histórica

- recuperar planilhas internas;
- baixar metadados públicos do TSE quando útil;
- padronizar pesquisas de eleições anteriores;
- registrar data de disponibilidade;
- congelar dataset de backtest.

### Etapa 3 — Correções objetivas

- covariâncias;
- `n_efetivo`;
- tracking;
- concentração por instituto;
- piso de erro total.
- amostra e incerteza específicas de segmento;
- gates de cobertura por recorte;

### Etapa 4 — Torneio de modelos

- executar walk-forward;
- gerar métricas e gráficos;
- documentar ganhos e perdas;
- escolher Modelo B.

### Etapa 5 — Challenger

- modelo de espaço de estados;
- house effects regularizados;
- distribuição de margem;
- probabilidade de liderança;
- execução paralela.

### Etapa 6 — Governança

- versão metodológica;
- relatório de mudanças;
- aprovação;
- publicação no Databricks;
- monitoramento de calibração.

---

## 14. O que pode ser adiantado sem as planilhas internas

1. fechar o dicionário de dados;
2. formalizar matematicamente o baseline;
3. criar casos sintéticos de teste;
4. estruturar o pipeline de backtest;
5. definir métricas e gates;
6. baixar e avaliar dados públicos do TSE;
7. preparar o esquema Bronze/Silver/Gold;
8. criar o registro de versões metodológicas;
9. definir perguntas para a chefia;
10. construir um protótipo com dados fictícios.

Assim, quando as planilhas chegarem, o trabalho se concentra em mapear os dados e validar, não em decidir a arquitetura do zero.

---

## 15. Decisões necessárias da liderança

1. O produto quer medir o presente ou prever a eleição?
2. A probabilidade publicada será de liderança atual ou vitória eleitoral?
3. Qual nível de complexidade é sustentável depois da transição de área?
4. Quem aprova notas de institutos?
5. Qual diferença em relação ao legado é tolerável?
6. Quais eleições poderão ser usadas para backtest?
7. O modelo oficial pode mudar durante o ciclo eleitoral?
8. Como comunicar revisões históricas?
9. Qual tratamento institucional dar a pesquisas muito fracas?
10. Quem será o dono permanente do produto?
11. Qual número mínimo de pesquisas e institutos permite publicar uma curva por recorte?
12. Faixas etárias diferentes serão preservadas ou harmonizadas, e por qual regra?

---

## 16. Posição final

O agregador antigo merece ser preservado como referência porque resolve bem o problema operacional e possui uma lógica intuitiva. Porém, elogio histórico não elimina a necessidade de medir onde ele acerta e onde expressa confiança excessiva.

A melhoria mais importante não é substituir uma média ponderada por uma “caixa-preta”. É construir um sistema em que:

- a curva central seja estável e responsiva;
- pesquisas fracas entrem sem dominar;
- trackings não sejam contados várias vezes;
- diferenças entre institutos sejam reconhecidas;
- intervalos expressem erro total, não apenas amostral;
- probabilidades sejam calibradas;
- toda mudança possa ser comparada ao baseline.

Se o modelo mais sofisticado não provar seu valor, o baseline permanece. Essa disciplina é o que transforma uma boa metodologia herdada em uma metodologia institucionalmente confiável.

---

## Referências principais

- [AAPOR — Polling Accuracy](https://aapor.org/polling-accuracy/)
- [AAPOR — Transparency Initiative](https://aapor.org/standards-and-ethics/transparency-initiative/)
- [AAPOR — Best Practices for Survey Research](https://aapor.org/standards-and-ethics/best-practices/)
- [AAPOR — Disclosure Standards](https://aapor.org/standards-and-ethics/disclosure-standards/)
- [AAPOR — 2024 Pre-Election Polling Evaluation](https://aapor.org/announcements/2024-pre-election-polling-report/)
- [Shirani-Mehr et al. — Disentangling Bias and Variance in Election Polls](https://ideas.repec.org/a/taf/jnlasa/v113y2018i522p607-614.html)
- [Jackman — Pooling the Polls over an Election Campaign](https://www.tandfonline.com/doi/abs/10.1080/10361140500302472)
- [Linzer — Dynamic Bayesian Forecasting of Presidential Elections](https://ideas.repec.org/a/taf/jnlasa/v108y2013i501p124-134.html)
- [Bias and Excess Variance in Election Polling](https://academic.oup.com/jrsssa/article/188/2/566/7720791)
- [Hierarchical Bayesian estimation of house effects](https://arts.units.it/handle/11368/2996107)
- [Sample overlap and dependence](https://onlinelibrary.wiley.com/doi/full/10.1111/joes.12633)
- [Polling Bias and Undecided Voter Allocations](https://academic.oup.com/jrsssa/article/182/2/467/7070181)
- [Evolution of Election Polling in the United States](https://academic.oup.com/poq/article/75/5/962/1830219)
- [The Twilight of the Polls?](https://www.cambridge.org/core/journals/government-and-opposition/article/twilight-of-the-polls-a-review-of-trends-in-polling-accuracy-and-the-causes-of-polling-misses/E479293C0A401A275D27BE46B4EDC998)
- [Updated Dynamic Bayesian Forecasting Model — HDSR/MIT Press](https://hdsr.mitpress.mit.edu/pub/nw1dzd02/release/2)
- [Election Polls in Brazil: Trends and Performance](https://revistas.usp.br/eav/en/article/view/205985)
- [TSE — Dados Abertos de Pesquisas Eleitorais](https://dadosabertos.tse.jus.br/dataset/?_tags_limit=0&groups=pesquisas-eleitorais&license_id=cc-by&res_format=CSV)
- [TSE — Registro de Pesquisas Eleitorais](https://temasselecionados.tse.jus.br/temas-selecionados/pesquisa-eleitoral/registro)
- [agregR — Bayesian State-Space Aggregation of Brazilian Presidential Polls](https://rnmag.github.io/agregR/)
