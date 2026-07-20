$ErrorActionPreference = "Stop"

$motor = (Resolve-Path (Join-Path $PSScriptRoot "..\MOTOR_COMUM")).Path
$config = (Resolve-Path (Join-Path $PSScriptRoot "config\agregador.yaml")).Path
$env:PYTHONPATH = Join-Path $motor "src"

python -m agregador validate --config $config --model b
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m agregador run --config $config --model b
exit $LASTEXITCODE
