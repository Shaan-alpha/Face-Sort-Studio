# ===================================================================
# Face Sort Studio - Run Script (PowerShell)
# ===================================================================
# Usage:  powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1
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

if (-not $env:FACE_SORT_DEBUG) {
    $env:FACE_SORT_DEBUG = "1"
}

Write-Host ""
Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host "|     Face Sort Studio - Starting        |" -ForegroundColor Cyan
Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Open the URL printed by Flask in your browser." -ForegroundColor White
Write-Host ""

python run.py
