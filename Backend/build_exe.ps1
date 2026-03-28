Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "Building machine-vision-backend.exe with PyInstaller..." -ForegroundColor Cyan

py -3 -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name "machine-vision-backend" `
  "main.py"

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller build failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
Write-Host "Executable: $PSScriptRoot\dist\machine-vision-backend.exe"
