@echo off
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Backend Python environment is missing.
  pause
  exit /b 1
)
"backend\.venv\Scripts\python.exe" "start_project.py"
if errorlevel 1 pause
