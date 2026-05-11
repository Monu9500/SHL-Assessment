@echo off
cd /d "%~dp0"
echo Starting API (fixes conda vs .venv automatically)...
echo Open: http://127.0.0.1:8000/health
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" start_api.py
) else (
  python start_api.py
  if errorlevel 1 py -3 start_api.py
)
