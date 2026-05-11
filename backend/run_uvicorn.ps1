# Works even under conda (base): delegates to backend/.venv.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Open: http://127.0.0.1:8000/health"
$Py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $Py) {
    & $Py .\start_api.py
} else {
    python .\start_api.py
}
