# Monitor de pesquisas eleitorais do TSE

Este é um pacote autônomo para executar o monitor no computador do trabalho.
Ele consulta os recursos oficiais do TSE, mantém histórico em SQLite e gera a
planilha `monitor_pesquisas_tse.xlsx`.

## Instalação inicial

Abra o PowerShell nesta pasta e execute uma vez:

```powershell
python -m pip install -e ".[test]"
python -m monitor_tse validate-config --config config/monitor_tse.yaml
```

Se o computador tiver mais de uma versão do Python, use o mesmo executável nos
dois comandos.

## Execução recorrente

Sempre que quiser atualizar os dados, execute:

```powershell
python run_monitor_tse.py
```

Também é possível executar diretamente pelo módulo:

```powershell
python -m monitor_tse run --config config/monitor_tse.yaml
```

O arquivo produzido fica em:

```text
monitor_pesquisas_tse.xlsx
```

O banco e os snapshots ficam, por padrão, em:

```text
%LOCALAPPDATA%\MonitorPesquisasTSE
```

## E-mail

Copie `.env.example` para `.env`, preencha as credenciais SMTP e altere:

```yaml
alerts:
  email_enabled: true
```

Nunca grave senha no código ou no YAML.

## Agendamento do Windows

Para instalar duas execuções diárias às 08:00 e 17:30:

```powershell
.\scripts\windows\instalar_tarefa.ps1
```

Para remover:

```powershell
.\scripts\windows\remover_tarefa.ps1
```

## Testes

```powershell
python -m pytest -q tests
```

## Semântica importante

`DT_DIVULGACAO` é a data a partir da qual a divulgação é permitida pelo TSE.
Ela não confirma que os resultados foram publicados. O monitor de publicação
efetiva permanece desativado nesta versão.

O Excel é uma saída regenerável; o SQLite é a fonte permanente do histórico.
Observações manuais são preservadas e reaplicadas na exportação.
