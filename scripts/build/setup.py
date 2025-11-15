#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup.py — Automated setup script for GeoDocs Scanner
"""
import os
import sys
import subprocess
import platform
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def check_python_version():
    """Check Python version"""
    print_header("Verificando versión de Python")
    
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ ERROR: Se requiere Python 3.10 o superior")
        print("   Por favor actualice Python desde https://www.python.org/downloads/")
        return False
    
    print("✓ Versión de Python correcta")
    return True


def check_tesseract():
    """Check if Tesseract is installed"""
    print_header("Verificando Tesseract OCR")
    
    try:
        result = subprocess.run(
            ['tesseract', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✓ {version_line}")
            return True
        else:
            print("❌ Tesseract no encontrado")
            return False
    
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Tesseract no está instalado")
        print_installation_instructions()
        return False


def print_installation_instructions():
    """Print Tesseract installation instructions"""
    system = platform.system()
    
    print("\n📥 Instrucciones de instalación de Tesseract OCR:\n")
    
    if system == "Windows":
        print("Windows:")
        print("  1. Descargar desde: https://github.com/UB-Mannheim/tesseract/wiki")
        print("  2. Instalar en: C:\\Program Files\\Tesseract-OCR\\")
        print("  3. Agregar al PATH o configurar TESSERACT_CMD")
    
    elif system == "Linux":
        print("Linux:")
        print("  sudo apt update")
        print("  sudo apt install tesseract-ocr")
        print("  sudo apt install tesseract-ocr-spa tesseract-ocr-lat")
    
    elif system == "Darwin":
        print("macOS:")
        print("  brew install tesseract")
        print("  brew install tesseract-lang")
    
    print()


def install_dependencies():
    """Install Python dependencies"""
    print_header("Instalando dependencias de Python")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ ERROR: No se encontró requirements.txt")
        return False
    
    print(f"Instalando desde: {requirements_file}\n")
    
    try:
        subprocess.check_call([
            sys.executable,
            '-m',
            'pip',
            'install',
            '--upgrade',
            'pip'
        ])
        
        subprocess.check_call([
            sys.executable,
            '-m',
            'pip',
            'install',
            '-r',
            str(requirements_file)
        ])
        
        print("\n✓ Dependencias instaladas correctamente")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERROR al instalar dependencias: {e}")
        return False


def create_directories():
    """Create necessary directories"""
    print_header("Creando directorios")
    
    base = Path(__file__).parent
    
    directories = [
        base / "data",
        base / "proyectos",
        base / "temp",
        base / "logs",
        base / "exports",
        base / "assets" / "icons"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ {directory.relative_to(base)}")
    
    print("\n✓ Directorios creados")
    return True


def initialize_database():
    """Initialize global database"""
    print_header("Inicializando base de datos")
    
    try:
        from utils.db_manager import init_global_db
        
        base_path = Path(__file__).parent
        init_global_db(base_path)
        
        print("✓ Base de datos global inicializada")
        return True
    
    except Exception as e:
        print(f"❌ ERROR al inicializar base de datos: {e}")
        return False


def check_optional_dependencies():
    """Check optional dependencies"""
    print_header("Verificando dependencias opcionales")
    
    optional = {
        'ttkbootstrap': 'Mejora de interfaz gráfica',
        'psutil': 'Información del sistema',
        'requests': 'Cliente API REST'
    }
    
    for package, description in optional.items():
        try:
            __import__(package)
            print(f"✓ {package}: {description}")
        except ImportError:
            print(f"⚠ {package}: {description} (no instalado)")
    
    print()


def create_desktop_shortcut():
    """Create desktop shortcut (Windows only)"""
    if platform.system() != "Windows":
        return
    
    print_header("Crear acceso directo")
    
    response = input("¿Desea crear un acceso directo en el escritorio? (s/n): ")
    
    if response.lower() == 's':
        try:
            import win32com.client
            
            desktop = Path.home() / "Desktop"
            shortcut_path = desktop / "GeoDocs Scanner.lnk"
            target = Path(__file__).parent / "main.py"
            
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{target}"'
            shortcut.WorkingDirectory = str(Path(__file__).parent)
            shortcut.IconLocation = sys.executable
            shortcut.save()
            
            print(f"✓ Acceso directo creado en: {shortcut_path}")
        
        except Exception as e:
            print(f"⚠ No se pudo crear acceso directo: {e}")
            print("  Puede ejecutar: python main.py")


def print_summary():
    """Print setup summary"""
    print_header("Instalación Completada")
    
    print("GeoDocs Scanner v32.3 PLUS está listo para usar!\n")
    print("📖 Para iniciar la aplicación:")
    print("   python main.py\n")
    print("📚 Documentación:")
    print("   Ver README_NUEVO.md para guía completa\n")
    print("⌨️ Atajos útiles:")
    print("   F1: Ayuda")
    print("   Ctrl+Q: Salir")
    print("   ESPACIO: Capturar (en módulo de escaneo)\n")
    print("🔧 Configuración:")
    print("   - Tesseract: Configurar TESSERACT_CMD si es necesario")
    print("   - API REST: Editar data/rest_config.json")
    print("   - Aplicación: Editar data/app_config.json\n")
    print("=" * 60)


def main():
    """Main setup function"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         GeoDocs Scanner v32.3 PLUS - Instalación         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    success = True
    
    # Check Python version
    if not check_python_version():
        success = False
        input("\nPresione Enter para salir...")
        sys.exit(1)
    
    # Check Tesseract
    tesseract_ok = check_tesseract()
    if not tesseract_ok:
        print("\n⚠ ADVERTENCIA: Tesseract no está disponible")
        print("  El OCR no funcionará hasta que lo instale")
        response = input("\n¿Desea continuar de todos modos? (s/n): ")
        if response.lower() != 's':
            sys.exit(0)
    
    # Install dependencies
    if not install_dependencies():
        success = False
    
    # Create directories
    if not create_directories():
        success = False
    
    # Initialize database
    if not initialize_database():
        success = False
    
    # Check optional dependencies
    check_optional_dependencies()
    
    # Create shortcut
    create_desktop_shortcut()
    
    # Print summary
    if success:
        print_summary()
    else:
        print_header("Instalación Completada con Advertencias")
        print("⚠ Algunos componentes no se instalaron correctamente")
        print("  Revise los errores anteriores y corrija los problemas\n")
    
    input("\nPresione Enter para salir...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Instalación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        input("\nPresione Enter para salir...")
        sys.exit(1)
