Param(
  [switch]$InstallTesseract,
  [switch]$InstallVCRedist,
  [string]$WorkDir = "build_deps"
)

Write-Host "[GeoDocs] Comprobando dependencias opcionales..."
$wd = Resolve-Path $WorkDir -ErrorAction SilentlyContinue
if (-not $wd) { New-Item -ItemType Directory -Path $WorkDir | Out-Null; $wd = Resolve-Path $WorkDir }

function Download($Url, $Out) {
  Write-Host "Descargando $Url -> $Out"
  try {
    Invoke-WebRequest -Uri $Url -OutFile $Out -UseBasicParsing
  } catch {
    $errMsg = $_.Exception.Message
    Write-Warning "Fallo descargando ${Url}: $errMsg"
    return $false
  }
  return (Test-Path $Out)
}

# Tesseract check
if ($InstallTesseract) {
  if (Get-Command tesseract.exe -ErrorAction SilentlyContinue) {
    Write-Host "Tesseract ya instalado." -ForegroundColor Green
  } else {
    $tesUrl = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.1.20230401.exe"
    $tesOut = Join-Path $wd "tesseract-installer.exe"
    if (Download $tesUrl $tesOut) {
      Write-Host "Ejecutando instalador Tesseract (requiere interacción)" -ForegroundColor Yellow
      Start-Process -FilePath $tesOut -Wait
    }
  }
}

# VC++ Redistributable
if ($InstallVCRedist) {
  $vcKey = "HKLM:SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"
  try {
    $inst = (Get-ItemProperty -Path $vcKey -Name Installed -ErrorAction Stop).Installed
  } catch { $inst = 0 }
  if ($inst -eq 1) {
    Write-Host "VC++ Redistributable ya presente." -ForegroundColor Green
  } else {
    $vcUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    $vcOut = Join-Path $wd "vc_redist.x64.exe"
    if (Download $vcUrl $vcOut) {
      Write-Host "Instalando VC++ Redistributable..." -ForegroundColor Yellow
      Start-Process -FilePath $vcOut -ArgumentList "/install /quiet /norestart" -Wait
    }
  }
}

Write-Host "Proceso finalizado." -ForegroundColor Green
