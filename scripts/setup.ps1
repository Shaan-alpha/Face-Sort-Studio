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
    Write-Host "Python was not found on PATH. Install Python 3.13+ and try again." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host "|       Face Sort Studio - Setup         |" -ForegroundColor Cyan
Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# Step 1: Install dependencies into the active Python environment
Write-Host "[1/3] Installing Python dependencies ..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
python -m pip install -r (Join-Path $root "requirements.txt") --quiet
Write-Host "       Dependencies installed." -ForegroundColor Green

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
python -c "from backend.app.bootstrap import ensure_models_exist; ensure_models_exist(r'$modelsDir')"
Write-Host "       Models ready." -ForegroundColor Green

Write-Host ""
Write-Host "Setup complete! Run the app with:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1" -ForegroundColor White
Write-Host ""
