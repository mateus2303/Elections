param([string]$TaskName = "Monitor Pesquisas TSE")
$ErrorActionPreference = "Stop"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Tarefa removida (se existia): $TaskName"

