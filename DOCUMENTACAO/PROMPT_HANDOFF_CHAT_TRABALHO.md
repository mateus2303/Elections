# Prompt de handoff para o chat do trabalho

Copie o texto abaixo para iniciar a execução no ambiente corporativo. Anexe também os arquivos citados no fim.

---

Você será responsável por construir um novo agregador interno de pesquisas políticas. O objetivo operacional é simples: o usuário abre um único Excel, adiciona uma pesquisa ou onda publicada, fecha o arquivo e executa uma rotina única. Todo ID, rastreabilidade, padronização, cálculo, gráfico e exportação deve ser automático.

Não comece programando. Leia integralmente, nesta ordem:

1. `ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`
2. `ROTEIRO_NOVO_AGREGADOR.md`
3. `ESTUDO_METODOLOGICO_AGREGADOR.md`
4. `Base_nova_limpa.xlsx`

Depois, inspecione integralmente o repositório legado, arquivos de orientação, histórico Git, scripts, configurações, testes, Excels e outputs de referência. Localize especialmente o código canônico do agregador antigo, os parâmetros realmente executados e os golden files disponíveis. Preserve dados confidenciais e nunca os inclua no Git.

Antes de qualquer alteração, localize e inspecione `input_agregador.xlsx` e `input_eleicao_2022.xlsx`/`input_eleicao2022.xlsx`. A inspeção é estritamente somente leitura: não edite, recalcule, salve, corrija, reformate, renomeie, mova ou sobrescreva os originais. Registre os hashes antes de abrir. Se a ferramenta puder alterar o arquivo, use uma cópia descartável.

Mapeie abas, colunas, fórmulas, referências, trackings, votos totais/válidos, pesos, rankings e inconsistências. Entregue um diagnóstico factual e uma matriz completa `origem → destino`. Compare os achados com `Base_nova_limpa.xlsx`, que já possui `Lula3` e uma única aba `Confrontos`, reúne todos os adversários e remove repetições artificiais semana→dia. A versão entregue em 17/07/2026 contém 1.845 linhas em `Lula3` e 1.807 em `Confrontos`; o escopo diretamente revalidado contra 23 PDFs soma 1.738 linhas, sendo 431 de avaliação e 1.307 de confrontos. Em `Confrontos`, primeiro e segundo turnos, espontânea e estimulada, sexo e religião já aparecem em colunas e linhas próprias. Preserve faixas e geografias publicadas, sem transformar recortes ou adversários do mesmo cenário em pesquisas independentes. Não recrie dados diários como input; a série diária será output do motor.

## Regras operacionais obrigatórias

- Não peça ao operador `id_pesquisa`, `fonte_arquivo`, `fonte_aba`, `fonte_linha` ou `observacoes`.
- Gere `poll_group_id`, `poll_id`, arquivo, aba e linha automaticamente durante a leitura. `poll_group_id` deve reunir células da mesma pesquisa/onda sem exigir ID manual; use assinatura normalizada de instituto, datas disponíveis, amostra total, tipo e frequência, sinalizando qualquer ambiguidade.
- Não imponha coleta manual de metodologia que o time não manterá.
- Campos desconhecidos, como amostra, margem ou confiança, podem ficar vazios; aplique fallback conservador configurado, gere alerta e preserve a pesquisa.
- Não crie script, aba ou configuração específica por candidato. Novo adversário entra por novas linhas em `Confrontos`.
- Não crie `LulaxFlavio_SP`, `LulaxFlavio_Sudeste`, `LulaxFlavio_16a24` ou estruturas equivalentes.
- Uma linha representa uma pesquisa ou onda efetivamente publicada. Não replique tracking semanal em sete linhas.
- Não exclua uma pesquisa apenas por ser ruim, nova ou discrepante. Exclua apenas por regra objetiva documentada.
- Mantenha o projeto enxuto: poucos módulos com responsabilidades claras, sem versões paralelas, cópias desnecessárias ou arquivos auxiliares permanentes.

### Protocolo obrigatório para extração e revisão de PDFs

- Antes de extrair valores, faça um censo integral de todas as tabelas e aberturas publicadas. Não trabalhe com lista restrita de páginas ou segmentos prioritários.
- Monte um contrato de cobertura por `PDF × onda × cenário × adversário`: conte todas as linhas esperadas e só libere a base quando `esperado = exportado`. Categoria válida sem taxonomia própria entra em `Outro`; nunca é descartada.
- Leia candidatos e respostas pelo cabeçalho semântico publicado. Some literalmente as categorias; nunca use residual para forçar 100% e nunca dependa da posição fixa das colunas.
- Preserve célula publicada em branco como nula; não converta branco em zero. Preencha `amostra_segmento` apenas quando o recorte for explicitamente publicado; não copie `amostra_total` para região ou segmento.
- Faça duas extrações independentes e revisão visual dirigida a cabeçalhos, rótulos quebrados pelo OCR, brancos, zeros e mudanças de layout. Divergência entre leituras exige retorno à página do PDF.
- Depois de salvar, reabra o XLSX, reconcilie novamente todas as linhas e células, verifique datas crescentes, erros de fórmula, filtros e linhas ocultas. A entrega deve abrir com as abas operacionais visíveis e utilizáveis.

## Escalabilidade de candidato, geografia e segmento

As duas abas operacionais são `Lula3` e `Confrontos`. Ambas contêm:

- `nivel_geografico`;
- `geografia`;
- `segmento_tipo`;
- `segmento`;
- `amostra_segmento`.

`Confrontos` também contém `turno`, `tipo_cenario`, `cenario`, `adversario`, `adversario_pct` e `outros_candidatos_pct`. Novo candidato, cenário, região, UF, faixa etária ou religião deve funcionar apenas por novas linhas. Município está fora do escopo. O pipeline gera automaticamente `scenario_id`, `geography_id` e `segment_id`.

O Excel deve ser autoexplicativo. Preserve as bandas visuais e, em `Confrontos`, os grupos `DADOS DA PESQUISA`, `CENÁRIO E ADVERSÁRIO`, `ONDE?`, `PARA QUEM?` e `RESULTADOS`. Implemente menus para turno/tipo/cenário e menus dependentes: `Brasil → Brasil`, `Regiao → cinco regiões`, `UF → 27 siglas`; `segmento_tipo → opções da coluna correspondente em Instrucoes`. A aba `Instrucoes` é a fonte visível das listas, sem nova aba técnica. Quando o operador acrescentar uma categoria na primeira célula vazia da lista correta, o menu deve crescer automaticamente.

As opções iniciais devem cobrir faixas usuais de idade e renda, sexo, escolaridade, religião (`Católico`, `Evangélico`) e outros segmentos. Elas são atalhos, não uma harmonização: preserve exatamente o rótulo publicado e mantenha separadas faixas incompatíveis como `16-24`, `18-24` e `16-29`.

Agregue somente dentro da mesma combinação `produto × turno × tipo_cenario × cenario × adversario × nivel_geografico × geografia × segmento_tipo × segmento × base_voto`. Nunca misture primeiro e segundo turnos ou espontânea e estimulada. No primeiro turno, some em `outros_candidatos_pct` as demais candidaturas publicadas e, em `brancos_nulos_indecisos_pct`, todas as categorias não candidatas publicadas. Nunca calcule esses campos como residual para forçar 100%; preserve a diferença de arredondamento da fonte. Linhas de adversários diferentes do mesmo cenário compartilham `poll_group_id` e não aumentam o peso da pesquisa. Para subgrupos, use `amostra_segmento`; não aplique a margem de erro da amostra total ao segmento. Sem amostra do segmento, preserve o ponto, use fallback conservador, gere alerta e aplique piso de incerteza.

Curva e probabilidade por recorte exigem gate configurável de pesquisas, institutos, recência e informação efetiva. Abaixo do gate, publique `evidencia_insuficiente`. Faixas etárias incompatíveis devem permanecer separadas até existir regra de harmonização aprovada e versionada.

## Cadastro de institutos

A aba `Institutos` deve conter somente quatro campos visíveis:

1. `instituto`
2. `aliases`
3. `peso_legacy`
4. `situacao`

Instituto desconhecido entra automaticamente como `Provisorio`, com `peso_legacy` vazio, alerta e participação por meio de prior conservador configurado no pipeline. Normalizar grafias e aliases antes do lookup. Alias ambíguo é erro bloqueante.

Precisão, house effect, transparência, desempenho histórico, erro excedente, tamanho efetivo e peso aplicado não são preenchidos no Excel. O pipeline deve calculá-los e versioná-los em tabelas técnicas. House effect não é baixa qualidade: ajuste sistemático e dispersão residual devem permanecer separados. Use *shrinkage* para institutos com pouca história e impeça vazamento temporal nos backtests.

## Estratégia metodológica obrigatória

1. **Modelo A — baseline oficial:** reproduza a fórmula e o comportamento efetivamente executados pelo legado, inclusive pesos, expoentes, janelas, cap de 5.000, votos válidos e intervalos. Valide contra golden files.
2. **Modelo B — legado aperfeiçoado:** mesma filosofia de média ponderada, com tamanho efetivo total e do segmento, covariâncias, uma linha por onda, teto por instituto/tracking, gates de cobertura, erro total, qualidade regularizada e janela/meia-vida escolhida por backtest.
3. **Modelo C — challenger:** modelo temporal hierárquico robusto com estado latente, efeitos de instituto, erro excedente, correlação de tracking, t-Student para outliers e eventual *partial pooling* explícito entre geografias/segmentos.

Nenhuma melhoria substitui o Modelo A silenciosamente. Modelos B ou C só podem ser promovidos após backtest walk-forward, critérios definidos antes do teste, intervalos calibrados, execução paralela, documentação e aprovação.

A probabilidade oficial inicial é `P(Lula estar à frente hoje)`. Não chame isso de previsão de vitória no dia da eleição. Forecast eleitoral deve permanecer experimental até incorporar evolução temporal, erro histórico e calibração suficiente.

## Ordem de execução

1. Produza o diagnóstico factual do repositório e das planilhas, sem alterar nada.
2. Liste decisões resolvidas, lacunas e bloqueios reais.
3. Entregue a matriz `origem → destino` e confirme o layout operacional mínimo.
4. Identifique a fórmula realmente executada e os golden files.
5. Apresente plano de implementação por fases e critérios de aceite.
6. Só após aprovação do diagnóstico, implemente fundação, validações e Modelo A.
7. Teste com dados sintéticos, dados atuais e referências antigas.
8. Teste explicitamente 1º/2º turno, espontânea/estimulada, candidato X, SP/Total, Sudeste/Total, Brasil/Idade, Brasil/Religiao e segmento sem amostra divulgada.
9. Gere memória de cálculo que reconstrua o último ponto pesquisa por pesquisa e recorte por recorte.
10. Prepare tabelas Bronze/Silver/Gold para Databricks, preservando adversário, geografia e segmento e incluindo `institutes_registry` e `institutes_diagnostics`.
11. Implemente Modelos B e C separadamente, sem alterar o oficial.

Não faça suposições silenciosas. Se uma decisão bloquear apenas a homologação, implemente a estrutura configurável, registre a pendência e continue nas partes não bloqueadas. Pergunte somente quando a escolha mudar materialmente o resultado e não puder ser descoberta no repositório.

Antes de declarar conclusão, apresente:

- diagnóstico do legado e hashes dos originais;
- matriz de migração;
- arquitetura final;
- decisões metodológicas e parâmetros;
- testes executados e resultados;
- comparação com o baseline;
- exemplos de outputs e memória de cálculo;
- contrato Bronze/Silver/Gold para Databricks;
- riscos e pendências;
- manual de execução para outro operador.

Comece agora apenas pela leitura, inspeção somente leitura, diagnóstico, mapeamento e plano. Não altere arquivos até apresentar esses quatro itens.

---

## Anexos necessários

- `ESPECIFICACAO_MESTRE_IMPLEMENTACAO.md`
- `ROTEIRO_NOVO_AGREGADOR.md`
- `ESTUDO_METODOLOGICO_AGREGADOR.md`
- `Base_nova_limpa.xlsx`
- código legado;
- `input_agregador.xlsx` e `input_eleicao_2022.xlsx`/`input_eleicao2022.xlsx`, se autorizados;
- outputs antigos usados como referência;
- informações do ambiente Databricks, quando disponíveis.
