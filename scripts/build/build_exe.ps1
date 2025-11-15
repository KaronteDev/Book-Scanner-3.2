Param(
    [switch]$Clean,
    [string]$Spec = "geodocs_scanner.spec"
)

Write-Host "[GeoDocs] Building executable..."

if ($Clean) {
  Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
}

# Ensure venv active (assumes already activated externally)
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
  Write-Host "PyInstaller no encontrado. Instalando..."
  pip install pyinstaller | Out-Null
}

pyinstaller $Spec --noconfirm

if ($LASTEXITCODE -ne 0) {
  Write-Error "Error en PyInstaller"
  exit 1
}

Write-Host "Ejecutable generado en dist/" -ForegroundColor Green
