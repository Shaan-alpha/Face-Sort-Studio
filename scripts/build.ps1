# Face Sort Studio - EXE Build Script
# =================================

$ProjectDir = Get-Location
$DistDir = Join-Path $ProjectDir "dist"
$BuildDir = Join-Path $ProjectDir "build"

Write-Host "`n[1/3] Cleaning previous builds..." -ForegroundColor Cyan
if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }

Write-Host "`n[2/3] Building Standalone EXE..." -ForegroundColor Cyan
Write-Host "This may take 1-2 minutes depending on your CPU." -ForegroundColor Gray

# PyInstaller Command:
# --onefile: Bundle into a single EXE
# --windowed: No console window (optional, but good for GUI apps)
# --add-data: Include static/templates from face_sort/app
# --name: Resulting file name
# --icon: (Optional) if you have one
# --collect-all: Ensure all submodules and package data are included

pyinstaller --noconfirm --onefile --windowed `
    --name "FaceSortStudio" `
    --add-data "face_sort/app/templates;face_sort/app/templates" `
    --add-data "face_sort/app/static;face_sort/app/static" `
    --collect-all "face_sort" `
    --hidden-import "flask" `
    --hidden-import "flask_sqlalchemy" `
    --hidden-import "cv2" `
    --hidden-import "pystray" `
    --hidden-import "PIL" `
    run.py

Write-Host "`n[3/3] Build Complete!" -ForegroundColor Green
Write-Host "Your portable app is located at: $DistDir\FaceSortStudio.exe" -ForegroundColor White
Write-Host "Note: The first time you run the EXE, it will still download the AI models to 'data/models'." -ForegroundColor Gray
