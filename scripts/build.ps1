# ===================================================================
# Face Sort Studio - EXE Build Script (PowerShell)
# ===================================================================
# Usage:  powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
# Builds dist\FaceSortStudio.exe using the project venv created by setup.ps1.
# ===================================================================

$ProjectDir = Split-Path -Parent $PSScriptRoot
if (-not $ProjectDir) { $ProjectDir = Get-Location }
Set-Location $ProjectDir

$DistDir  = Join-Path $ProjectDir "dist"
$BuildDir = Join-Path $ProjectDir "build"

# Prefer the project venv (setup.ps1); fall back to PATH python.
$venvPython = Join-Path $ProjectDir "venv\Scripts\python.exe"
if (Test-Path $venvPython) { $py = $venvPython } else { $py = "python" }

# Run a native command and fail only on a non-zero exit code. (Tools like pip
# print notices to stderr on success; under ErrorActionPreference='Stop' that
# stderr would otherwise abort the script, so we check $LASTEXITCODE instead.)
function Invoke-Checked {
    param([Parameter(Mandatory)][string[]]$CommandArgs)
    & $CommandArgs[0] @($CommandArgs[1..($CommandArgs.Count - 1)])
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Command failed (exit $LASTEXITCODE): $($CommandArgs -join ' ')" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n[1/4] Ensuring app + build dependencies ..." -ForegroundColor Cyan
# `-e .` guarantees the app's runtime deps (incl. pystray + Pillow for the tray)
# are present so PyInstaller can bundle them; pyinstaller is the build tool itself.
Invoke-Checked @($py, '-m', 'pip', 'install', '-e', $ProjectDir, '--quiet')
Invoke-Checked @($py, '-m', 'pip', 'install', 'pyinstaller', '--quiet')

Write-Host "`n[2/4] Cleaning previous builds ..." -ForegroundColor Cyan
if (Test-Path $DistDir)  { Remove-Item -Recurse -Force $DistDir -ErrorAction SilentlyContinue }
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue }

Write-Host "`n[3/4] Building standalone EXE (1-2 minutes) ..." -ForegroundColor Cyan
Invoke-Checked @(
    $py, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed',
    '--name', 'FaceSortStudio',
    '--add-data', 'face_sort/app/templates;face_sort/app/templates',
    '--add-data', 'face_sort/app/static;face_sort/app/static',
    '--collect-all', 'face_sort',
    '--hidden-import', 'flask',
    '--hidden-import', 'flask_sqlalchemy',
    '--hidden-import', 'cv2',
    '--hidden-import', 'pystray',
    '--hidden-import', 'PIL',
    'run.py'
)

Write-Host "`n[4/4] Build complete!" -ForegroundColor Green
Write-Host "Your portable app is at: $DistDir\FaceSortStudio.exe" -ForegroundColor White
Write-Host "Note: on first launch the EXE downloads the ~37 MB AI models to data\models (one-time)." -ForegroundColor Gray
