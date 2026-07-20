# Monitor de pesquisas eleitorais do TSE

## Escopo implementado

O MVP consulta os três recursos tabulares oficiais do conjunto `pesquisas-eleitorais-2026`, usando o arquivo consolidado `BRASIL` de cada ZIP. O arquivo principal usa `NR_PROTOCOLO_REGISTRO` como chave; contratantes e pagantes são relações 1:N.

Os pacotes documentais são registrados como referências oficiais de pacote. O MVP não baixa diariamente os ZIPs grandes de PDFs.

## Estado real validado em 2026-07-20

- 1.251 pesquisas no recurso principal.
- 1.282 linhas de contratantes.
- 1.282 linhas de pagantes.
- Geração principal: `20/07/2026 05:46:52`.
- Dez execuções completas posteriores à carga inicial terminaram com sucesso e zero novos/alterados na repetição.
- A planilha possui 1.251 linhas em `Base completa` e as oito abas operacionais previstas.
- A primeira tentativa teve falha de exportação por timezone em datetimes; o erro foi registrado, os dados foram preservados e a conversão foi corrigida antes da execução validada.
- Testes automatizados: `17 passed`, cobrindo idempotência, novidades, alterações campo a campo, duplicidade, falha de download, ZIP inválido, alteração de esquema, datas inválidas, Excel, alertas duplicados, observações manuais, filtros, janela de alertas e preservação do estado anterior.

## Limitações conhecidas

1. A fonte estruturada não possui coluna própria para margem de erro, confiança, avaliação de governo, cancelamento ou publicação efetiva. Margem/confiança permanecem no texto de `DS_PLANO_AMOSTRAL`.
2. A data permitida não confirma que o resultado foi divulgado.
3. Questionários, notas fiscais e detalhamentos são ZIPs de PDFs grandes; a referência do MVP aponta para o pacote oficial.
4. O PesqEle é uma contingência pública, mas a interface é dinâmica e não é tratada como API estável.
5. O envio SMTP não permite garantia matemática de exatamente uma entrega; eventos ambíguos ficam registrados para revisão.
6. CPF de pessoa física é mascarado nas tabelas normalizadas; o snapshot bruto permanece no diretório local de auditoria.

## Próxima fase

Criar adaptadores configuráveis para fontes públicas de publicação efetiva, com URL, título, data/hora, evidências, confiança e fila de revisão humana. Nenhum resultado percentual será extraído automaticamente de imagens ou gráficos.
