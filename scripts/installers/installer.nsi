; NSIS Script for GeoDocs Scanner
; Requires NSIS 3.x: https://nsis.sourceforge.io/

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

; --------------------------------
; Definitions
; --------------------------------
!define APPNAME "GeoDocs Scanner"
!define COMPANYNAME "GeoDocs"
!define DESCRIPTION "Sistema de escaneo y gestión de documentos geográficos"
!define VERSIONMAJOR 1
!define VERSIONMINOR 0
!define VERSIONBUILD 0
!define HELPURL "https://github.com/KaronteDev/Book-Scanner-3.2"
!define UPDATEURL "https://github.com/KaronteDev/Book-Scanner-3.2/releases"
!define ABOUTURL "https://github.com/KaronteDev/Book-Scanner-3.2"

!define VCREDIST_URL "https://aka.ms/vs/17/release/vc_redist.x64.exe"
!define TESSERACT_URL "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe"

; --------------------------------
; General
; --------------------------------
Name "${APPNAME}"
OutFile "dist\installer\GeoDocsScannerSetup.exe"
InstallDir "$PROGRAMFILES64\${APPNAME}"
InstallDirRegKey HKLM "Software\${APPNAME}" "InstallDir"
RequestExecutionLevel admin

; --------------------------------
; Interface Settings
; --------------------------------
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; --------------------------------
; Pages
; --------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\GeoDocsScanner.exe"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; --------------------------------
; Languages
; --------------------------------
!insertmacro MUI_LANGUAGE "Spanish"

; --------------------------------
; Variables
; --------------------------------
Var VCRedistNeeded
Var TesseractNeeded
Var VCRedistDownload
Var TesseractDownload

; --------------------------------
; Installer Sections
; --------------------------------
Section "GeoDocs Scanner" SecMain
    SectionIn RO
    
    SetOutPath "$INSTDIR"
    
    ; Copy main executable
    File "dist\GeoDocsScanner.exe"
    
    ; Copy all other files recursively
    File /r "dist\*.*"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\${APPNAME}"
    CreateShortcut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\GeoDocsScanner.exe"
    CreateShortcut "$SMPROGRAMS\${APPNAME}\Desinstalar ${APPNAME}.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\GeoDocsScanner.exe"
    
    ; Registry information for add/remove programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayIcon" "$INSTDIR\GeoDocsScanner.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "${COMPANYNAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "HelpLink" "${HELPURL}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "URLUpdateInfo" "${UPDATEURL}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "URLInfoAbout" "${ABOUTURL}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMajor" ${VERSIONMAJOR}
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMinor" ${VERSIONMINOR}
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoRepair" 1
    
    ; Store installation folder
    WriteRegStr HKLM "Software\${APPNAME}" "InstallDir" $INSTDIR
    
SectionEnd

; --------------------------------
; Uninstaller Section
; --------------------------------
Section "Uninstall"
    
    ; Remove files and uninstaller
    Delete "$INSTDIR\GeoDocsScanner.exe"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
    Delete "$SMPROGRAMS\${APPNAME}\Desinstalar ${APPNAME}.lnk"
    RMDir "$SMPROGRAMS\${APPNAME}"
    Delete "$DESKTOP\${APPNAME}.lnk"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
    DeleteRegKey HKLM "Software\${APPNAME}"
    
SectionEnd

; --------------------------------
; Functions
; --------------------------------

Function .onInit
    ; Check for 64-bit Windows
    ${IfNot} ${RunningX64}
        MessageBox MB_OK|MB_ICONSTOP "Esta aplicación requiere Windows de 64 bits."
        Abort
    ${EndIf}
    
    ; Initialize variables
    StrCpy $VCRedistNeeded "0"
    StrCpy $TesseractNeeded "0"
    StrCpy $VCRedistDownload "0"
    StrCpy $TesseractDownload "0"
    
    ; Check VC++ Redistributable
    Call CheckVCRedist
    Pop $0
    ${If} $0 == "0"
        StrCpy $VCRedistNeeded "1"
        MessageBox MB_YESNO "Visual C++ Redistributable no está instalado.$\n¿Deseas descargarlo e instalarlo?" IDYES vcredist_yes IDNO vcredist_no
        vcredist_yes:
            StrCpy $VCRedistDownload "1"
            Goto vcredist_end
        vcredist_no:
            MessageBox MB_YESNO "Sin VC++ Redistributable la aplicación podría no funcionar.$\n¿Deseas continuar de todos modos?" IDNO 0 IDYES vcredist_end
            Abort
        vcredist_end:
    ${EndIf}
    
    ; Check Tesseract
    Call CheckTesseract
    Pop $0
    ${If} $0 == "0"
        StrCpy $TesseractNeeded "1"
        MessageBox MB_YESNO "Tesseract OCR no está instalado (necesario para funcionalidad OCR).$\n¿Deseas descargarlo e instalarlo?" IDYES tesseract_yes IDNO tesseract_no
        tesseract_yes:
            StrCpy $TesseractDownload "1"
            Goto tesseract_end
        tesseract_no:
            MessageBox MB_OK "Podrás instalar Tesseract manualmente después desde:$\n${TESSERACT_URL}"
        tesseract_end:
    ${EndIf}
    
    ; Download dependencies if requested
    ${If} $VCRedistDownload == "1"
        DetailPrint "Descargando Visual C++ Redistributable..."
        NSISdl::download "${VCREDIST_URL}" "$TEMP\vc_redist.x64.exe"
        Pop $0
        ${If} $0 != "success"
            MessageBox MB_OK|MB_ICONEXCLAMATION "Error descargando VC++ Redistributable: $0"
            StrCpy $VCRedistDownload "0"
        ${EndIf}
    ${EndIf}
    
    ${If} $TesseractDownload == "1"
        DetailPrint "Descargando Tesseract OCR..."
        NSISdl::download "${TESSERACT_URL}" "$TEMP\tesseract-setup.exe"
        Pop $0
        ${If} $0 != "success"
            MessageBox MB_OK|MB_ICONEXCLAMATION "Error descargando Tesseract: $0"
            StrCpy $TesseractDownload "0"
        ${EndIf}
    ${EndIf}
    
FunctionEnd

Function .onInstSuccess
    ; Install VC++ Redistributable if downloaded
    ${If} $VCRedistDownload == "1"
        MessageBox MB_YESNO "¿Instalar Visual C++ Redistributable ahora?" IDYES install_vcredist IDNO skip_vcredist
        install_vcredist:
            DetailPrint "Instalando Visual C++ Redistributable..."
            ExecWait '"$TEMP\vc_redist.x64.exe" /install /quiet /norestart'
            Delete "$TEMP\vc_redist.x64.exe"
        skip_vcredist:
    ${EndIf}
    
    ; Install Tesseract if downloaded
    ${If} $TesseractDownload == "1"
        MessageBox MB_YESNO "¿Instalar Tesseract OCR ahora?" IDYES install_tesseract IDNO skip_tesseract
        install_tesseract:
            DetailPrint "Instalando Tesseract OCR..."
            ExecWait '"$TEMP\tesseract-setup.exe" /S'
            Delete "$TEMP\tesseract-setup.exe"
        skip_tesseract:
    ${EndIf}
FunctionEnd

Function CheckVCRedist
    ; Check for VC++ Redistributable 2015-2022 (v14.x)
    Push $0
    ClearErrors
    ReadRegDWORD $0 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Installed"
    ${If} ${Errors}
        Push "0"
    ${Else}
        ${If} $0 == 1
            Push "1"
        ${Else}
            Push "0"
        ${EndIf}
    ${EndIf}
    Pop $0
FunctionEnd

Function CheckTesseract
    ; Check for Tesseract in registry
    Push $0
    ClearErrors
    ReadRegStr $0 HKLM "SOFTWARE\Tesseract-OCR" "InstallDir"
    ${If} ${Errors}
        ClearErrors
        ReadRegStr $0 HKCU "SOFTWARE\Tesseract-OCR" "InstallDir"
        ${If} ${Errors}
            Push "0"
        ${Else}
            Push "1"
        ${EndIf}
    ${Else}
        Push "1"
    ${EndIf}
    Pop $0
FunctionEnd
