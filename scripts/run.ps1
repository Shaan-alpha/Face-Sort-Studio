# ===================================================================
# Face Sort Studio - Run Script (PowerShell)
# ===================================================================
# Usage:  powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1
# ===================================================================

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $root) { $root = Get-Location }

Set-Location $root

# Prefer the project venv created by setup.ps1; fall back to PATH python.
$venvPython = Join-Path $root "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $pathPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pathPython) {
        Write-Host "Python was not found. Run scripts\setup.ps1 first, or install Python 3.11+." -ForegroundColor Red
        exit 1
    }
    Write-Host "No venv found (.\venv) - using PATH python. Run scripts\setup.ps1 for an isolated environment." -ForegroundColor Yellow
    $python = "python"
}

Write-Host ""
Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host "|     Face Sort Studio - Starting        |" -ForegroundColor Cyan
Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Your browser will open automatically; a tray icon appears once it's running." -ForegroundColor White
Write-Host ""

& $python run.py
