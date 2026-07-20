@echo off
setlocal
cd /d "%~dp0\..\..\.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m monitor_tse run --config "config\monitor_tse.yaml"
) else (
  python -m monitor_tse run --config "config\monitor_tse.yaml"
)
exit /b %ERRORLEVEL%

