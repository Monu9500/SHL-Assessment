# Create/update backend\.venv and start Uvicorn.
# IMPORTANT: Uses .venv\python.exe explicitly — never uses conda "python" on PATH after venv exists.
param(
  [ValidateSet("127.0.0.1", "0.0.0.0")]
  [string]$ListenHost = "127.0.0.1",
  [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "TIP: Browse http://127.0.0.1:8000/health  (never http://0.0.0.0:8000)" -ForegroundColor Yellow
Write-Host ""

$Py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
  Write-Host "Creating .venv with: python -m venv .venv"
  python -m venv .venv
  if (-not (Test-Path $Py)) {
    throw "Could not create .venv. Install Python 3.12 from python.org and ensure 'python' works."
  }
}

if (-not $SkipInstall) {
  Write-Host "Installing dependencies into .venv (first time can take several minutes)..."
  & $Py -m pip install -U pip wheel
  & $Py -m pip install -r requirements.txt
}

Write-Host ""
Write-Host "Using interpreter: $Py"
Write-Host "Starting uvicorn on ${ListenHost}:8000 (Ctrl+C to stop)"
if ($ListenHost -eq "0.0.0.0") {
  Write-Host "On this PC open: http://127.0.0.1:8000 — not 0.0.0.0"
}

# --reload subprocess inherits the same exe when spawned by uvicorn (must be started with this interpreter)
& $Py -m uvicorn app.main:app --reload --host $ListenHost --port 8000
