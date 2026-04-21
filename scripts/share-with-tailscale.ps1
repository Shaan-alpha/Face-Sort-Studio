# ===================================================================
# Face Sort Studio - Share With Tailscale (PowerShell)
# ===================================================================
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\share-with-tailscale.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\share-with-tailscale.ps1 -Private
# ===================================================================

param(
    [int]$Port = 8000,
    [switch]$Private
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $root) { $root = Get-Location }

Set-Location $root

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python was not found on PATH. Install Python first and rerun this script." -ForegroundColor Red
    exit 1
}

$tailscale = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $tailscale) {
    Write-Host "Tailscale was not found on PATH." -ForegroundColor Red
    Write-Host "Install Tailscale, sign in, then rerun this script." -ForegroundColor Yellow
    exit 1
}

try {
    & $tailscale.Source status | Out-Null
} catch {
    Write-Host "Tailscale is installed, but it does not appear to be signed in yet." -ForegroundColor Red
    Write-Host "Open Tailscale, sign in, then rerun this script." -ForegroundColor Yellow
    exit 1
}

$serverUrl = "http://127.0.0.1:$Port/"
$serverReady = $false
$sharedModeReady = $false

try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $serverUrl -TimeoutSec 2
    $serverReady = $true
    $sharedModeReady = $response.Content -match "Shared mode"
} catch {
    $serverReady = $false
}

if ($serverReady -and -not $sharedModeReady) {
    Write-Host "A local server is already running on port $Port, but not in shared mode." -ForegroundColor Red
    Write-Host "Stop that server first, then rerun this script so the safe public-share mode is enabled." -ForegroundColor Yellow
    exit 1
}

if (-not $serverReady) {
    Write-Host ""
    Write-Host "+----------------------------------------+" -ForegroundColor Cyan
    Write-Host "|   Face Sort Studio - Shared Launch     |" -ForegroundColor Cyan
    Write-Host "+----------------------------------------+" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Starting the Flask app in a new PowerShell window..." -ForegroundColor Yellow

    $escapedRoot = $root.Replace("'", "''")
    $serverCommand = (
        "& { " +
        "Set-Location '$escapedRoot'; " +
        "`$env:FACE_SORT_PUBLIC_SHARE_MODE='1'; " +
        "`$env:FACE_SORT_DEBUG='0'; " +
        "`$env:FACE_SORT_PORT='$Port'; " +
        "python run.py" +
        " }"
    )

    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $serverCommand
    ) | Out-Null

    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $serverUrl -TimeoutSec 2
            $serverReady = $true
            $sharedModeReady = $response.Content -match "Shared mode"
            if ($sharedModeReady) { break }
        } catch {
            $serverReady = $false
        }
    }

    if (-not $serverReady -or -not $sharedModeReady) {
        Write-Host "The app did not become ready on $serverUrl." -ForegroundColor Red
        Write-Host "Check the new PowerShell window for startup errors, then rerun this script." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "Using the already running shared app on $serverUrl" -ForegroundColor Green
}

Write-Host ""
if ($Private) {
    Write-Host "Starting a private Tailscale share..." -ForegroundColor Cyan
    Write-Host "Only devices in your tailnet will be able to open it." -ForegroundColor White
    Write-Host ""
    & $tailscale.Source serve $Port
} else {
    Write-Host "Starting a public Tailscale Funnel..." -ForegroundColor Cyan
    Write-Host "Keep this window open while the app is shared." -ForegroundColor White
    Write-Host ""
    & $tailscale.Source funnel $Port
}
