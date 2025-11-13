# 🔌 Sistema de Plugins - Book Scanner 3.2

El Book Scanner 3.2 incluye un sistema de plugins extensible que permite añadir funcionalidades personalizadas sin modificar el código core de la aplicación.

## 📁 Estructura

```
plugins/
├── __init__.py              # Inicialización del módulo
├── base_plugin.py           # Clase base abstracta
├── plugin_loader.py         # Cargador dinámico de plugins
├── example_plugin.py        # Plugin de ejemplo
├── plugins_config.json      # Configuración de plugins
└── README.md               # Este archivo
```

## 🚀 Crear un Plugin Personalizado

### 1. Crear archivo del plugin

Crea un nuevo archivo `.py` en la carpeta `plugins/`:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mi_plugin.py — Descripción de tu plugin
"""
from pathlib import Path
from typing import Dict, Any

from plugins.base_plugin import BasePlugin


class MiPlugin(BasePlugin):
    """Mi plugin personalizado"""
    
    @property
    def name(self) -> str:
        return "Mi Plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Descripción breve del plugin"
    
    @property
    def author(self) -> str:
        return "Tu Nombre"
    
    @property
    def requires(self) -> list:
        """Dependencias opcionales"""
        return ['pillow', 'numpy']  # Ejemplo
    
    def initialize(self, app_context: Dict[str, Any]) -> bool:
        """Inicializar plugin"""
        self.app_context = app_context
        self.root = app_context.get('root')
        self.base_path = app_context.get('base_path')
        
        # Tu código de inicialización aquí
        print(f"✓ {self.name} inicializado")
        return True
    
    def shutdown(self) -> None:
        """Limpiar recursos"""
        print(f"✓ {self.name} descargado")
```

### 2. Añadir funcionalidad

Implementa los métodos según necesites:

#### Items de Menú

```python
def get_menu_items(self) -> list:
    return [
        {
            'label': 'Mi Acción',
            'command': self.mi_accion,
            'icon': '🔧',
            'accelerator': 'Ctrl+M'
        }
    ]

def mi_accion(self):
    from tkinter import messagebox
    messagebox.showinfo("Mi Plugin", "Acción ejecutada!")
```

#### Procesar Imágenes

```python
def process_image(self, image_path: Path):
    """Procesar imagen capturada"""
    from PIL import Image
    
    # Cargar imagen
    img = Image.open(image_path)
    
    # Tu procesamiento aquí
    # Por ejemplo: convertir a escala de grises
    img_gray = img.convert('L')
    
    # Guardar (sobrescribir o nueva ruta)
    img_gray.save(image_path)
    
    return image_path
```

#### Procesar Texto OCR

```python
def process_ocr_text(self, text: str, metadata: Dict[str, Any] = None) -> str:
    """Limpiar/mejorar texto OCR"""
    import re
    
    # Ejemplo: eliminar múltiples espacios
    text = re.sub(r'\s+', ' ', text)
    
    # Ejemplo: corregir errores comunes
    text = text.replace('rn', 'm')
    text = text.replace('|', 'l')
    
    return text.strip()
```

#### Hooks de Eventos

```python
def on_project_opened(self, project_path: Path) -> None:
    """Llamado cuando se abre un proyecto"""
    print(f"Proyecto abierto: {project_path}")

def on_page_captured(self, page_path: Path, metadata: Dict[str, Any]) -> None:
    """Llamado cuando se captura una página"""
    print(f"Página capturada: {page_path}")

def on_ocr_completed(self, page_id: int, text: str) -> None:
    """Llamado cuando se completa el OCR"""
    print(f"OCR completado para página {page_id}")
```

## ⚙️ Configuración

Los plugins pueden guardar su configuración:

```python
def load_config(self, config: Dict[str, Any]) -> None:
    """Cargar configuración"""
    self.config = config or {}
    self.mi_opcion = self.config.get('mi_opcion', 'valor_por_defecto')

def save_config(self) -> Dict[str, Any]:
    """Guardar configuración"""
    return {
        'mi_opcion': self.mi_opcion,
        'enabled': self.enabled
    }

def get_settings_panel(self, parent):
    """Panel de configuración en UI"""
    import tkinter as tk
    from tkinter import ttk
    
    frame = ttk.Frame(parent, padding=10)
    
    ttk.Label(frame, text="Mi Opción:").pack()
    var = tk.StringVar(value=self.mi_opcion)
    ttk.Entry(frame, textvariable=var).pack()
    
    def guardar():
        self.mi_opcion = var.get()
    
    ttk.Button(frame, text="Guardar", command=guardar).pack()
    
    return frame
```

## 📋 API Completa de BasePlugin

### Propiedades Obligatorias

- `name` → Nombre del plugin
- `version` → Versión (formato x.y.z)
- `description` → Descripción breve

### Propiedades Opcionales

- `author` → Autor del plugin
- `requires` → Lista de dependencias Python

### Métodos del Ciclo de Vida

- `initialize(app_context)` → Inicializar (retornar True si exitoso)
- `shutdown()` → Limpiar recursos

### Métodos de Integración UI

- `get_menu_items()` → Items de menú
- `get_toolbar_buttons()` → Botones de toolbar
- `get_settings_panel(parent)` → Panel de configuración

### Métodos de Procesamiento

- `process_image(image_path)` → Procesar imagen
- `process_ocr_text(text, metadata)` → Procesar texto OCR

### Hooks de Eventos

- `on_project_opened(project_path)`
- `on_project_closed()`
- `on_page_captured(page_path, metadata)`
- `on_ocr_completed(page_id, text)`

### Métodos de Configuración

- `load_config(config)` → Cargar configuración
- `save_config()` → Guardar configuración

## 🎯 Ejemplos de Plugins Útiles

### 1. Plugin de Marca de Agua

```python
def process_image(self, image_path: Path):
    from PIL import Image, ImageDraw, ImageFont
    
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    # Añadir marca de agua
    text = "© Mi Archivo 2025"
    draw.text((10, 10), text, fill=(200, 200, 200, 128))
    
    img.save(image_path)
    return image_path
```

### 2. Plugin de Validación de Calidad

```python
def on_page_captured(self, page_path: Path, metadata: Dict[str, Any]):
    from PIL import Image
    import numpy as np
    
    img = Image.open(page_path)
    arr = np.array(img)
    
    # Calcular brillo promedio
    brightness = np.mean(arr)
    
    if brightness < 50:
        print(f"⚠️ Imagen muy oscura: {page_path}")
    elif brightness > 200:
        print(f"⚠️ Imagen muy clara: {page_path}")
```

### 3. Plugin de Auto-Corrección OCR

```python
def process_ocr_text(self, text: str, metadata: Dict[str, Any] = None) -> str:
    import language_tool_python
    
    # Corrector ortográfico
    tool = language_tool_python.LanguageTool('es')
    matches = tool.check(text)
    corrected = language_tool_python.utils.correct(text, matches)
    
    return corrected
```

## 🔧 Gestión de Plugins

### Habilitar/Deshabilitar

En `plugins_config.json`:

```json
{
  "Mi Plugin": {
    "enabled": true,
    "mi_configuracion": "valor"
  },
  "Otro Plugin": {
    "enabled": false
  }
}
```

### Desde Código

```python
from plugins import PluginLoader

loader = PluginLoader(plugins_dir)
loader.enable_plugin("Mi Plugin")
loader.disable_plugin("Otro Plugin")
```

## 📦 Distribución

Para distribuir tu plugin:

1. Comparte solo el archivo `.py`
2. Documenta dependencias en `requires`
3. Incluye README con instrucciones
4. El usuario solo debe copiar el archivo a `plugins/`

## 🐛 Debug

Para depurar plugins, habilita logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Los errores en plugins no detienen la aplicación, solo se loguean.

## 💡 Consejos

- ✅ Mantén plugins simples y enfocados
- ✅ Maneja excepciones para no romper la app
- ✅ Usa `self.enabled` para permitir deshabilitar funcionalidad
- ✅ Documenta bien la configuración requerida
- ❌ No modifiques archivos globales sin permiso
- ❌ No bloquees el hilo principal (usa threading si es necesario)
