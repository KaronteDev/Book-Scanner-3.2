Param(
  [string]$InstallerScript = "installer.iss",
  [switch]$Sign,
  [string]$CertPfx = "",
  [string]$CertPassword = "",
  [string]$TimestampUrl = "http://timestamp.digicert.com",
  [switch]$ReportOnly
)

Write-Host "[GeoDocs] Building installer..."

# Locate iscc (Inno Setup Compiler)
$possible = @(
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
  "${Env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "${Env:ProgramFiles}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ }

if (-not $possible) {
  Write-Warning "ISCC.exe no encontrado. Instala Inno Setup 6 para compilar el instalador."
  exit 1
}
$iscc = $possible[0]
Write-Host "Usando ISCC: $iscc"

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

& "$iscc" $InstallerScript
if ($LASTEXITCODE -ne 0) {
  Write-Error "Fallo compilando instalador"
  exit 1
}

$installerOut = Get-ChildItem dist/installer -Filter GeoDocsScannerSetup.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $installerOut) {
  Write-Warning "No se encontró instalador generado."
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
