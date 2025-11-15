; Inno Setup script for GeoDocs Scanner
; Compile with Inno Setup Compiler (https://jrsoftware.org/isinfo.php)
; Requires Inno Download Plugin: https://mitrichsoftware.wordpress.com/inno-setup-tools/inno-download-plugin/

#include <idp.iss>

#define MyAppName "GeoDocs Scanner"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "GeoDocs"
#define MyAppExe "GeoDocsScanner.exe"

#define VCRedistURL "https://aka.ms/vs/17/release/vc_redist.x64.exe"
#define TesseractURL "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe"

[Setup]
AppId={{A3B9F7D2-7C6B-4F1F-9E12-GeoDocsScanner}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\GeoDocsScanner
DefaultGroupName=GeoDocs Scanner
DisableProgramGroupPage=yes
OutputDir=dist\installer
OutputBaseFilename=GeoDocsScannerSetup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\GeoDocsScanner.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\GeoDocs Scanner"; Filename: "{app}\{#MyAppExe}"
Name: "{group}\Desinstalar GeoDocs Scanner"; Filename: "{uninstallexe}"
Name: "{autodesktop}\GeoDocs Scanner"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear icono en el escritorio"; GroupDescription: "Opciones adicionales:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Ejecutar GeoDocs Scanner"; Flags: nowait postinstall skipifsilent

[Code]
var
  VCRedistNeeded: Boolean;
  TesseractNeeded: Boolean;

function VCRedistInstalled: Boolean;
var
  Installed: Cardinal;
begin
  Result := RegQueryDwordValue(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) and (Installed = 1);
end;

function TesseractInstalled: Boolean;
var
  TesseractPath: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\Tesseract-OCR', 'InstallDir', TesseractPath) or 
            RegQueryStringValue(HKCU, 'SOFTWARE\Tesseract-OCR', 'InstallDir', TesseractPath);
end;

function InitializeSetup: Boolean;
begin
  Result := True;
  VCRedistNeeded := not VCRedistInstalled;
  TesseractNeeded := not TesseractInstalled;
  
  if VCRedistNeeded then begin
    if MsgBox('Visual C++ Redistributable no está instalado.' + #13#10 + '¿Deseas descargarlo e instalarlo ahora?', mbConfirmation, MB_YESNO) = IDYES then begin
      idpAddFile('{#VCRedistURL}', ExpandConstant('{tmp}\vc_redist.x64.exe'));
    end else begin
      if MsgBox('Sin VC++ Redistributable la aplicación podría no funcionar.' + #13#10 + '¿Deseas continuar de todos modos?', mbConfirmation, MB_YESNO) = IDNO then begin
        Result := False;
      end;
    end;
  end;
  
  if TesseractNeeded and Result then begin
    if MsgBox('Tesseract OCR no está instalado (necesario para funcionalidad OCR).' + #13#10 + '¿Deseas descargarlo e instalarlo ahora?', mbConfirmation, MB_YESNO) = IDYES then begin
      idpAddFile('{#TesseractURL}', ExpandConstant('{tmp}\tesseract-setup.exe'));
    end else begin
      MsgBox('Podrás instalar Tesseract manualmente después desde:' + #13#10 + '{#TesseractURL}', mbInformation, MB_OK);
    end;
  end;
  
  idpDownloadAfter(wpReady);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  VCRedistPath, TesseractPath: String;
begin
  if CurStep = ssPostInstall then begin
    // Install VC++ Redistributable if downloaded
    VCRedistPath := ExpandConstant('{tmp}\vc_redist.x64.exe');
    if VCRedistNeeded and FileExists(VCRedistPath) then begin
      if MsgBox('¿Instalar Visual C++ Redistributable ahora?', mbConfirmation, MB_YESNO) = IDYES then begin
        Exec(VCRedistPath, '/install /quiet /norestart', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
      end;
    end;
    
    // Install Tesseract if downloaded
    TesseractPath := ExpandConstant('{tmp}\tesseract-setup.exe');
    if TesseractNeeded and FileExists(TesseractPath) then begin
      if MsgBox('¿Instalar Tesseract OCR ahora?', mbConfirmation, MB_YESNO) = IDYES then begin
        Exec(TesseractPath, '/S', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
      end;
    end;
  end;
end;
