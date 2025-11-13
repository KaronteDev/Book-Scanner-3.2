# ⚡ QUICK START - Integración Rápida de Mejoras

## 🚀 5 Pasos para Integrar Todo

---

## 1️⃣ Migrar Base de Datos (1 minuto)

```powershell
# Ejecutar UNA SOLA VEZ
python migrate_versions.py
```

**Resultado**: Tabla `versions` creada en todas las bases de datos.

---

## 2️⃣ Importar Nuevos Módulos en main.py

Añade estos imports al inicio de `main.py`:

```python
from utils.keyboard_manager import KeyboardManager, setup_default_shortcuts
from gui.stats_panel import show_stats_panel
from gui.advanced_search import show_advanced_search
```

---

## 3️⃣ Inicializar Keyboard Manager

En el `__init__` de tu clase principal:

```python
class BookScannerApp:
    def __init__(self, root):
        self.root = root
        # ... tu código existente ...
        
        # Añadir al final del __init__:
        self._setup_keyboard_shortcuts()
    
    def _setup_keyboard_shortcuts(self):
        """Configurar atajos de teclado globales"""
        self.keyboard_manager = KeyboardManager(self.root)
        
        # Contexto con referencias a funciones
        app_context = {
            'root': self.root,
            'scanner': getattr(self, 'scanner_module', None),
            'export_func': getattr(self, 'export_project', None),
            'gallery_func': getattr(self, 'focus_gallery', None),
            'quality_func': getattr(self, 'filter_quality', None),
            'new_project_func': getattr(self, 'new_project', None),
            'open_project_func': getattr(self, 'open_project', None),
            'save_func': getattr(self, 'save_all', None),
            'rotate_func': getattr(self, 'rotate_selected_image', None),
            'delete_func': getattr(self, 'delete_selected_image', None),
            'search_func': self.open_advanced_search,
            'zoom_func': getattr(self, 'zoom_gallery', None)
        }
        
        setup_default_shortcuts(self.keyboard_manager, app_context)
        self.keyboard_manager.bind_all()
```

---

## 4️⃣ Añadir Menús

Añade un menú "Herramientas" con las nuevas funcionalidades:

```python
def _create_menu_bar(self):
    """Crear barra de menús (modifica tu función existente)"""
    menubar = tk.Menu(self.root)
    self.root.config(menu=menubar)
    
    # ... tus menús existentes (Archivo, Editar, etc.) ...
    
    # NUEVO: Menú Herramientas
    menu_tools = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Herramientas", menu=menu_tools)
    
    menu_tools.add_command(
        label="📊 Estadísticas del Proyecto",
        command=self.show_statistics,
        accelerator="Ctrl+I"
    )
    
    menu_tools.add_command(
        label="🔍 Búsqueda Avanzada",
        command=self.open_advanced_search,
        accelerator="Ctrl+F"
    )
    
    menu_tools.add_separator()
    
    menu_tools.add_command(
        label="⌨️ Atajos de Teclado",
        command=self.show_keyboard_help,
        accelerator="F1"
    )
```

---

## 5️⃣ Implementar Funciones de Menú

Añade estas funciones a tu clase principal:

```python
def show_statistics(self):
    """Mostrar panel de estadísticas"""
    if not hasattr(self, 'current_project_db') or not self.current_project_db:
        messagebox.showwarning(
            "Aviso",
            "Abre un proyecto primero para ver estadísticas"
        )
        return
    
    show_stats_panel(self.root, Path(self.current_project_db))

def open_advanced_search(self):
    """Abrir búsqueda avanzada multi-proyecto"""
    global_db_path = Path("data/geodocs.db")  # Ajusta tu ruta
    projects_root = Path("proyectos/")        # Ajusta tu ruta
    
    show_advanced_search(self.root, global_db_path, projects_root)

def show_keyboard_help(self):
    """Mostrar ventana de ayuda de atajos"""
    from utils.keyboard_manager import show_shortcuts_help
    show_shortcuts_help(self.keyboard_manager, self.root)
```

---

## ✅ ¡LISTO!

**Ya tienes integradas las 10 mejoras:**

1. ✅ Metadatos V3 → Ya funcionan automáticamente en metadata_manager
2. ✅ Rotación → Ya integrada en scanner_module
3. ✅ Diálogo de captura → Se activa automáticamente al capturar
4. ✅ Eliminación múltiple → Ya funciona en metadata_manager
5. ✅ Plugins → Sistema listo (crea tus plugins en `plugins/`)
6. ✅ Lazy loading → Ya activo automáticamente en galería
7. ✅ Versionado → Disponible después de migración
8. ✅ Atajos → Activos con keyboard_manager
9. ✅ Estadísticas → Accesible desde menú Herramientas
10. ✅ Búsqueda → Accesible desde menú Herramientas

---

## 🧪 Testing Rápido

```powershell
# 1. Ejecutar aplicación
python main.py

# 2. Probar atajos:
# - F1 → Ver lista de atajos
# - F5 → Capturar (muestra diálogo de metadatos)
# - Ctrl+F → Búsqueda avanzada

# 3. Probar menús:
# - Herramientas → Estadísticas
# - Herramientas → Búsqueda Avanzada

# 4. Probar galería:
# - Rotar imágenes con botones ↶↷⤾
# - Lazy loading (importa 100+ imágenes)
```

---

## 📝 Ajustes Opcionales

### Si usas nombres diferentes de variables:

Modifica el `app_context` en `_setup_keyboard_shortcuts()` con TUS nombres de funciones:

```python
app_context = {
    'scanner': self.MI_SCANNER,        # Ajusta nombre
    'export_func': self.MI_EXPORTAR,   # Ajusta nombre
    # ... etc
}
```

### Si tus rutas son diferentes:

Ajusta en `open_advanced_search()`:

```python
global_db_path = Path("TU_RUTA/geodocs.db")
projects_root = Path("TU_RUTA/proyectos/")
```

---

## ⚠️ Problemas Comunes

### "Module not found: keyboard_manager"
→ Verifica que `utils/keyboard_manager.py` existe

### "Shortcuts don't work"
→ Asegúrate de llamar `keyboard_manager.bind_all()`

### "Stats panel empty"
→ Abre un proyecto primero

### "Search shows no projects"
→ Verifica que `projects_root` apunta a carpeta correcta

---

## 🎉 ¡Ya está!

Con estos 5 pasos tienes todas las mejoras funcionando.

**Tiempo estimado de integración: 15-30 minutos**

Para más detalles, consulta:
- `GUIA_NUEVAS_FUNCIONALIDADES.md` → Uso de cada funcionalidad
- `MEJORAS_IMPLEMENTADAS_HOY.md` → Detalles técnicos
- `RESUMEN_EJECUTIVO.md` → Visión general del proyecto
