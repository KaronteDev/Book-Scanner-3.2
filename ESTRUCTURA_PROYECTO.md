# Estructura del Proyecto GeoDocs Scanner

## 📁 Organización de Carpetas

```
Book Scanner 3.2/
│
├── 📂 config/                          # Archivos de configuración
│   ├── config.dev.json                 # Configuración desarrollo
│   ├── config.prod.json                # Configuración producción
│   ├── geodocs_config.json             # Config principal GeoDocs
│   ├── geodocs_api_map.json            # Mapeo de API
│   ├── ocr_config.json                 # Configuración OCR
│   ├── rest_config.json                # Configuración REST
│   ├── quality_scheduler.json          # Scheduler de calidad
│   └── camera_calibration.json         # Calibración de cámara
│
├── 📂 scripts/                         # Scripts de utilidad
│   ├── build/                          # Scripts de compilación
│   │   ├── build_exe.ps1
│   │   ├── build_installer.ps1
│   │   ├── build_installer_nsis.ps1
│   │   └── setup.py
│   ├── installers/                     # Archivos de instaladores
│   │   ├── installer.iss
│   │   ├── installer.nsi
│   │   ├── geodocs_scanner.spec
│   │   └── geodocs_scanner_portable.spec
│   ├── migrations/                     # Scripts de migración DB
│   │   ├── migrate_db.py
│   │   ├── migrate_schema_v3.py
│   │   └── migrate_versions.py
│   └── utilities/                      # Utilidades varias
│       ├── install_dependencies.py
│       ├── install_deps.ps1
│       └── run_coverage.py
│
├── 📂 documentation/                   # Documentación del proyecto
│   ├── user_guides/                    # Guías de usuario
│   │   ├── Manual_Usuario_GeoDocs_Scanner_v32_3_PLUS.md
│   │   └── GUIA_NUEVAS_FUNCIONALIDADES.md
│   ├── archived/                       # Documentación archivada
│   │   ├── CAMBIOS_MAPA.md
│   │   ├── EVALUACION_NAVEGADORES.md
│   │   ├── mejoras.md
│   │   └── ... (otros archivos históricos)
│   ├── QUICK_START.md
│   ├── INDEX.md
│   └── RESUMEN_EJECUTIVO.md
│
├── 📂 mobile_app/                      # Aplicación móvil Flutter
│   ├── lib/
│   ├── android/
│   ├── ios/
│   ├── pubspec.yaml
│   └── README_SETUP.md
│
├── 📂 gui/                             # Componentes GUI Tkinter
│   ├── advanced_search.py
│   ├── annotation_view.py
│   ├── capture_dialog.py
│   ├── export_view.py
│   └── ... (otros módulos GUI)
│
├── 📂 models/                          # Modelos de datos
├── 📂 modules/                         # Módulos funcionales
├── 📂 presenters/                      # Presentadores (MVP)
├── 📂 services/                        # Servicios (API, OCR, etc.)
│   └── mobile_api_server.py
├── 📂 views/                           # Vistas
├── 📂 utils/                           # Utilidades
├── 📂 plugins/                         # Sistema de plugins
│
├── 📂 web_viewer/                      # Visor web
│
├── 📂 tests/                           # Tests unitarios e integración
│   └── test_mobile_annotations_sync.py
│
├── 📂 docs/                            # Documentación Sphinx
├── 📂 docs_src/                        # Fuentes documentación
│
├── 📂 data/                            # Datos de la aplicación
│   ├── app_config.json
│   └── rest_config.json
│
├── 📂 assets/                          # Recursos (iconos, imágenes)
│   └── icons/
│
├── 📂 output/                          # Carpeta de salida consolidada
│   ├── output_scan/                    # Salida del escáner
│   └── output_tk/                      # Salida Tkinter
│
├── 📂 logs/                            # Logs del servidor móvil
│   └── mobile_server_*.log
│
├── 📂 build/                           # Archivos de compilación
├── 📂 build_deps/                      # Dependencias de build
├── 📂 dist/                            # Distribuciones compiladas
├── 📂 htmlcov/                         # Cobertura de tests HTML
│
├── 📂 old/                             # Versiones antiguas guardadas
│
├── 📂 papelera/                        # Archivos obsoletos (SAFE TO DELETE)
│   ├── legacy_scripts/                 # Scripts de conversión viejos
│   ├── old_tests/                      # Tests temporales antiguos
│   ├── old_versions/                   # Versiones anteriores de archivos
│   └── deprecated_docs/                # Documentación obsoleta
│
├── 🐍 main.py                          # Punto de entrada principal
├── 🐍 launcher.py                      # Lanzador/selector de módulos
├── 🐍 scanner_gui.py                   # Módulo de escaneo
├── 🐍 annotator_gui.py                 # Módulo de anotación
├── 🐍 start_mobile_server.py           # Servidor API móvil
├── 🐍 processor_queue.py               # Cola de procesamiento OCR
│
├── 📄 README.md                        # Documentación principal
├── 📄 requirements.txt                 # Dependencias Python
├── 📄 pytest.ini                       # Configuración pytest
├── 📄 .coveragerc                      # Configuración coverage
├── 📄 LICENSE                          # Licencia del proyecto
│
└── 🗄️ geodocs_scanner.db              # Base de datos principal

```

## 🎯 Archivos Principales

| Archivo | Propósito |
|---------|-----------|
| `main.py` | Punto de entrada principal de la aplicación |
| `launcher.py` | Selector de módulos (Escaneo/Anotación) con control del servidor móvil |
| `scanner_gui.py` | Interfaz de escaneo con cámara |
| `annotator_gui.py` | Interfaz completa de anotación y exportación |
| `start_mobile_server.py` | Servidor Flask-SocketIO para app móvil |
| `requirements.txt` | Todas las dependencias del proyecto |

## 🚀 Scripts Importantes

### Build y Despliegue
- `scripts/build/build_exe.ps1` - Compilar ejecutable
- `scripts/build/build_installer.ps1` - Crear instalador
- `scripts/installers/installer.iss` - Configuración Inno Setup

### Mantenimiento
- `scripts/migrations/migrate_*.py` - Migraciones de base de datos
- `scripts/utilities/install_dependencies.py` - Instalar dependencias opcionales
- `scripts/utilities/run_coverage.py` - Ejecutar análisis de cobertura

## 📝 Notas

### Papelera
La carpeta `papelera/` contiene archivos obsoletos que **pueden eliminarse** de forma segura:
- Scripts de conversión antiguos (`convert_*.py`, `fix_*.py`)
- Tests temporales y de debugging
- Versiones antiguas de GUI
- Archivos de ejemplo y pruebas

### Configuración
Todos los archivos de configuración están centralizados en `config/`:
- Usa `config.dev.json` para desarrollo
- Usa `config.prod.json` para producción
- `geodocs_config.json` es el archivo activo cargado por la app

### Output
Los directorios de salida están consolidados en `output/`:
- `output/output_scan/` - Imágenes capturadas
- `output/output_tk/` - Exportaciones y PDFs

### Logs
Los logs del servidor móvil se guardan automáticamente en `logs/` con timestamp.

## 🔄 Próximos Pasos de Limpieza

1. **Revisar y eliminar** la carpeta `papelera/` cuando confirmes que no necesitas esos archivos
2. **Considerar mover** `old/` a `papelera/old_versions/` si no se usa
3. **Limpiar** `.venv-1/` si existe (mover a papelera)
4. **Revisar** `Prueba1/` y moverlo a papelera si es código de prueba obsoleto

## 📚 Documentación

- **README.md** - Documentación principal con historial de versiones
- **documentation/QUICK_START.md** - Guía rápida de inicio
- **documentation/user_guides/** - Manuales de usuario detallados
- **mobile_app/README_SETUP.md** - Guía de setup de la app móvil
- **plugins/README.md** - Documentación del sistema de plugins
