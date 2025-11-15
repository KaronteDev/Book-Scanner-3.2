@echo off
REM GeoDocs Scanner - Inicio Rápido
REM Este script lanza la aplicación principal

echo.
echo ====================================
echo   GeoDocs Scanner v32.3 PLUS
echo ====================================
echo.

REM Verificar si existe el entorno virtual
if exist "venv\Scripts\activate.bat" (
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
) else (
    echo No se encontro entorno virtual.
    echo Usando Python del sistema...
)

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado
    echo Por favor instale Python 3.10 o superior
    pause
    exit /b 1
)

echo.
echo Iniciando GeoDocs Scanner...
echo.

REM Lanzar aplicación
python main.py

REM Si hay error, mostrar mensaje
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo iniciar la aplicacion
    echo Revise que todas las dependencias esten instaladas
    echo Ejecute: python setup.py
    pause
)
