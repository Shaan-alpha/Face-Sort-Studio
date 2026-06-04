# ===================================================================
# Face Sort Studio - Setup Script (PowerShell)
# ===================================================================
# Usage:  powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
# ===================================================================

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $root) { $root = Get-Location }

Set-Location $root

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python was not found on PATH. Install Python 3.11+ and try again." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host "|       Face Sort Studio - Setup         |" -ForegroundColor Cyan
Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create an isolated virtual environment and install into it
Write-Host "[1/3] Setting up virtual environment + dependencies ..." -ForegroundColor Yellow
$venvDir = Join-Path $root "venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    python -m venv $venvDir
}
& $venvPython -m pip install --upgrade pip --quiet
# `-e .` installs the pinned deps (setup.py reads requirements.txt) AND the
# `face-sort` console command, so this venv matches every documented path.
& $venvPython -m pip install -e $root --quiet
Write-Host "       Virtual environment ready (.\venv) and dependencies installed." -ForegroundColor Green

# Step 2: Create data directories
Write-Host "[2/3] Creating data directories ..." -ForegroundColor Yellow
$dirs = @("data\database", "data\jobs", "data\outputs", "data\models")
foreach ($d in $dirs) {
    $full = Join-Path $root $d
    if (-not (Test-Path $full)) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
    }
}
Write-Host "       Data directories ready." -ForegroundColor Green

# Step 3: Download DL models
Write-Host "[3/3] Checking deep-learning models ..." -ForegroundColor Yellow
$modelsDir = Join-Path $root "data\models"
& $venvPython -c "from face_sort.app.bootstrap import ensure_models_exist; ensure_models_exist(r'$modelsDir')"
Write-Host "       Models ready." -ForegroundColor Green

Write-Host ""
Write-Host "Setup complete! Run the app with:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1" -ForegroundColor White
Write-Host ""
