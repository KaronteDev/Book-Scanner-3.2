# Papelera - Archivos Obsoletos

Esta carpeta contiene archivos que ya no se utilizan en el proyecto actual.

## Contenido

### legacy_scripts/
Scripts de conversión y corrección antiguos que fueron utilizados en versiones previas:
- convert_*.py - Scripts de conversión de código
- fix_*.py - Scripts de corrección automática
- fix_msgbox.ps1 - Script PowerShell de corrección

### old_tests/
Tests temporales y de debugging que ya no son necesarios:
- test_cache_simple.py
- test_map_performance.py
- test_render_debug.py
- test_tkinterweb*.py
- tmp_check_app.py

### old_versions/
Versiones anteriores de archivos principales:
- gui_book_scan_tk2.py - Versión antigua de GUI
- book_scan_core.py - Core antiguo
- app.py - Aplicación anterior
- ejemplo_integracion_gui.py - Ejemplo de integración

### Otros archivos temporales
- mapa.html - Archivo temporal de mapa
- launch.bat - Lanzador batch antiguo
- plantilla_archivos*.csv - Plantillas de prueba
- Prueba1/ - Carpeta de pruebas
- .venv-1/ - Entorno virtual antiguo

## Acción Recomendada

**Estos archivos pueden eliminarse de forma segura** si confirmas que:
1. No necesitas referencias históricas del código
2. Los tests antiguos no tienen lógica que necesites portar
3. Las versiones anteriores de GUI no contienen funcionalidad útil

Para eliminar toda la carpeta papelera:
```powershell
Remove-Item -Path "papelera" -Recurse -Force
```

**Fecha de reorganización:** 2025-11-14
