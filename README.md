# Agregador de pesquisas políticas

## Onde está cada coisa

- `ENTREGA_FINAL/`: contém somente a planilha operacional atual e o pacote para levar ao ambiente da Kinea.
- `DOCUMENTACAO/`: roteiro, especificação, estudo metodológico e prompt de handoff.
- `ARQUIVOS_ANTIGOS/`: materiais históricos preservados apenas para consulta, acompanhados de explicação.
- `AGENTS.md`, `PROJECT_CONTEXT.md` e `HANDOFF.md`: contexto interno para continuar o projeto sem perder decisões.

## Arquivos para usar

1. Para atualizar pesquisas, abra `ENTREGA_FINAL/Base_nova_limpa.xlsx`.
2. Para transferir código e resultados ao computador do trabalho, use `ENTREGA_FINAL/Pacote_Agregador_Kinea.zip` e leve junto `ENTREGA_FINAL/Base_nova_limpa.xlsx`.
3. Para continuar a implementação, comece por `DOCUMENTACAO/PROMPT_HANDOFF_CHAT_TRABALHO.md`.

Depois de executar o pipeline, a entrega oficial do Modelo A fica em `ENTREGA_FINAL/RESULTADOS_ATUAIS/Modelo_A_Baseline_Oficial/` e o candidato experimental em `ENTREGA_FINAL/RESULTADOS_ATUAIS/Modelo_B_Candidato_Experimental/`. Abra o workbook correspondente; os gráficos em `apresentacao/graficos/` são gerados automaticamente para todos os adversários publicados, sem alterar o código quando novos nomes forem adicionados.

Para transferir os códigos ao computador do trabalho, use `ENTREGA_FINAL/CODIGOS/`. A pasta contém comandos separados para os dois modelos e o motor compartilhado. As instruções estão em `ENTREGA_FINAL/CODIGOS/README.md`.

## Execução do agregador

O pipeline Python está em `src/agregador/`. O Modelo A é o baseline oficial; o Modelo B é candidato experimental e roda separadamente com `python -m agregador run --config config/agregador.yaml --model b`. O manual operacional e os comandos de validação, execução e backtest estão em `DOCUMENTACAO/MANUAL_EXECUCAO_AGREGADOR.md`.

Não use os arquivos de `ARQUIVOS_ANTIGOS` como base operacional.

## Monitor de pesquisas do TSE

O monitor fica separado do agregador estatístico e não altera `ENTREGA_FINAL/Base_nova_limpa.xlsx`.
Ele mantém o estado principal em SQLite, preserva snapshots dos CSVs oficiais e gera
`ENTREGA_FINAL/MONITOR_TSE/monitor_pesquisas_tse.xlsx`.

Para transferir o monitor ao computador do trabalho, envie a pasta autônoma
`ENTREGA_FINAL/MONITOR_TSE/`. Dentro dela, execute `python run_monitor_tse.py`.

### Instalação e validação

Com Python 3.12 ou superior:

```powershell
python -m pip install -e .
python -m monitor_tse validate-config --config config/monitor_tse.yaml
python -m monitor_tse init-db --config config/monitor_tse.yaml
```

Credenciais de e-mail ficam em variáveis de ambiente. O arquivo `.env.example` documenta os nomes; não versionar um `.env` real.

### Execução manual

Forma simples, para compartilhar com o trabalho:

```powershell
python run_monitor_tse.py
```

Esse arquivo consulta o TSE e atualiza `ENTREGA_FINAL/MONITOR_TSE/monitor_pesquisas_tse.xlsx`.
Também é possível informar outro arquivo de configuração:

```powershell
python run_monitor_tse.py --config config/monitor_tse.yaml
```

Forma equivalente usando o módulo:

```powershell
python -m monitor_tse run --config config/monitor_tse.yaml
```

O banco, snapshots e logs ficam por padrão em `%LOCALAPPDATA%\MonitorPesquisasTSE`. A planilha é gerada em `ENTREGA_FINAL/MONITOR_TSE`. O primeiro carregamento cria uma linha de base e não envia um e-mail com todos os registros; novidades posteriores podem ser alertadas quando `alerts.email_enabled` estiver ativado.

`source.raw_retention_days` controla a retenção dos snapshots brutos; o padrão `0` preserva os arquivos indefinidamente.

### Agendamento no Windows

Execute em um PowerShell com o ambiente Python preparado:

```powershell
.\scripts\windows\instalar_tarefa.ps1
```

A tarefa usa verificações às 08:00 e 17:30, ignora instâncias simultâneas e tenta novamente após falhas. Para remover:

```powershell
.\scripts\windows\remover_tarefa.ps1
```

Para uma execução sem o Agendador, use `scripts\windows\executar_monitor_tse.bat`. O histórico técnico fica no SQLite e em `%LOCALAPPDATA%\MonitorPesquisasTSE\logs\monitor_tse.log`.

### Semântica da divulgação

`DT_DIVULGACAO` é somente a data a partir da qual a divulgação é permitida pelo TSE. O sistema mantém esse campo separado de qualquer publicação efetivamente localizada. O módulo de verificação externa permanece desativado no MVP.
