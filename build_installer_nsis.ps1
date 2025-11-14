Param(
  [string]$InstallerScript = "installer.nsi",
  [switch]$Sign,
  [string]$CertPfx = "",
  [string]$CertPassword = "",
  [string]$TimestampUrl = "http://timestamp.digicert.com",
  [switch]$ReportOnly
)

Write-Host "[GeoDocs] Building NSIS installer..."

# Locate makensis (NSIS Compiler)
$possible = @(
  "C:\Program Files (x86)\NSIS\makensis.exe",
  "${Env:ProgramFiles(x86)}\NSIS\makensis.exe",
  "${Env:ProgramFiles}\NSIS\makensis.exe"
)

$makensis = $null
foreach ($path in $possible) {
  if (Test-Path $path) {
    $makensis = $path
    break
  }
}

if (-not $makensis) {
  $cmdPath = Get-Command makensis.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
  if ($cmdPath) {
    $makensis = $cmdPath
  }
}

if (-not $makensis) {
  Write-Warning "makensis.exe no encontrado. Instala NSIS 3.x desde https://nsis.sourceforge.io/"
  Write-Host "Alternativa: choco install nsis" -ForegroundColor Cyan
  exit 1
}
Write-Host "Usando makensis: $makensis"

# Check NSIS version
try {
  $nsisVersion = & $makensis /VERSION
  Write-Host "NSIS Version: $nsisVersion"
} catch {
  Write-Warning "No se pudo verificar la versión de NSIS"
}

# Report info about signtool if present (even if not signing)
$signtoolPaths = @(
  "$Env:ProgramFiles(x86)\Windows Kits\10\bin\x64\signtool.exe",
  "$Env:ProgramFiles(x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
  (Get-Command signtool.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique
if ($signtoolPaths) {
  $signtool = $signtoolPaths[0]
  $ver = (Get-Item $signtool).VersionInfo.FileVersion
  $sigHash = (Get-FileHash $signtool -Algorithm SHA256).Hash
  Write-Host "signtool detectado: $signtool (Version $ver SHA256=$sigHash)"
} else {
  Write-Warning "signtool no detectado (firma opcional no disponible)."
}

if ($ReportOnly) { Write-Host "Modo ReportOnly: no se construye instalador."; exit 0 }

# Create output directory
$outputDir = "dist\installer"
if (-not (Test-Path $outputDir)) {
  New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# Build installer
Write-Host "Compilando instalador con NSIS..." -ForegroundColor Cyan
& $makensis /V3 $InstallerScript
if ($LASTEXITCODE -ne 0) {
  Write-Error "Fallo compilando instalador"
  exit 1
}

$installerOut = Get-ChildItem $outputDir -Filter GeoDocsScannerSetup.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $installerOut) {
  Write-Warning "No se encontró instalador generado en $outputDir"
  exit 1
}
Write-Host "Instalador generado: $($installerOut.FullName)" -ForegroundColor Green

# Compute installer hash
$instHash = (Get-FileHash $installerOut.FullName -Algorithm SHA256).Hash
Write-Host "SHA256 instalador: $instHash"

if ($Sign) {
  if (-not $signtool) {
    Write-Warning "Firma solicitada pero signtool no disponible."
  } elseif (-not (Test-Path $CertPfx)) {
    Write-Warning "Certificado PFX no encontrado. Omite firma."
  } else {
    Write-Host "Firmando instalador..."
    $args = @("sign","/f",$CertPfx,"/p",$CertPassword,"/fd","sha256","/tr",$TimestampUrl,"/td","sha256",$installerOut.FullName)
    & $signtool $args
    if ($LASTEXITCODE -eq 0) {
      Write-Host "Firma OK" -ForegroundColor Green
      $postHash = (Get-FileHash $installerOut.FullName -Algorithm SHA256).Hash
      Write-Host "SHA256 post-firma: $postHash"
    } else {
      Write-Warning "Fallo firmando instalador"
    }
  }
}

Write-Host "`n=== Build completado ===" -ForegroundColor Green
Write-Host "Instalador: $($installerOut.FullName)"
Write-Host "SHA256: $instHash"
