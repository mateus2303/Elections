param(
  [string]$TaskName = "Monitor Pesquisas TSE",
  [string]$ProjectRoot = "",
  [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
  $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}
if ([string]::IsNullOrWhiteSpace($PythonPath)) {
  $candidate = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
  if (Test-Path -LiteralPath $candidate) { $PythonPath = $candidate } else { $PythonPath = (Get-Command python.exe).Source }
}
$configPath = Join-Path $ProjectRoot "config\monitor_tse.yaml"
if (-not (Test-Path -LiteralPath $configPath)) { throw "Configuração não encontrada: $configPath" }
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument "-m monitor_tse run --config `"$configPath`"" -WorkingDirectory $ProjectRoot
$morning = New-ScheduledTaskTrigger -Daily -At 08:00
$afternoon = New-ScheduledTaskTrigger -Daily -At 17:30
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($morning,$afternoon) -Settings $settings -Description "Monitora pesquisas eleitorais registradas no TSE" -Force | Out-Null
Write-Host "Tarefa instalada: $TaskName"
Write-Host "Projeto: $ProjectRoot"
Write-Host "Python: $PythonPath"

