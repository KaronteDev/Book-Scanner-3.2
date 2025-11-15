# Snippets de Código para Copy-Paste en GUI

## 📋 Instrucciones

Estos son fragmentos listos para copiar y pegar en `gui/metadata_manager.py`.

---

## 1️⃣ EditorProyecto - Añadir Variables (en `__init__`)

**Ubicación:** Línea ~909, después de `self.var_fecha = tk.StringVar()`

```python
# NUEVOS CAMPOS V3
self.var_abreviatura = tk.StringVar()
self.var_tipo_pub = tk.StringVar()
self.tipos_pub_data = []
```

---

## 2️⃣ EditorProyecto - Cargar Tipos de Publicación (en `__init__`)

**Ubicación:** Línea ~1000, antes de `self._load_archivos_fondos()`

```python
# Cargar tipos de publicación disponibles
try:
    self.tipos_pub_data = db.list_tipos_publicacion(self.base_path)
except Exception:
    self.tipos_pub_data = []
```

---

## 3️⃣ EditorProyecto - Añadir Campos en Formulario

**Ubicación:** Línea ~935, después del campo "Signatura"

```python
# Campo Abreviatura (NUEVO)
add_label("Abreviatura:")
abrev_frame = ttk.Frame(frm)
abrev_frame.grid(row=row, column=1, sticky='w', padx=6, pady=4)
ttk.Entry(abrev_frame, textvariable=self.var_abreviatura, width=15).pack(side=tk.LEFT)
ttk.Label(abrev_frame, text="(nivel 1: proyecto/archivo/fondo_signatura)", foreground="#666").pack(side=tk.LEFT, padx=(6,0))
row += 1

# Campo Tipo de Publicación (NUEVO)
add_label("Tipo de Publicación:")
tipo_pub_options = [f"{t['icono']} {t['nombre']}" for t in self.tipos_pub_data] if self.tipos_pub_data else []
self.cmb_tipo_pub = ttk.Combobox(frm, textvariable=self.var_tipo_pub, values=tipo_pub_options, state='readonly', width=48)
self.cmb_tipo_pub.grid(row=row, column=1, sticky='w', padx=6, pady=4)
if tipo_pub_options:
    self.cmb_tipo_pub.current(0)
row += 1
```

---

## 4️⃣ EditorProyecto - Método para Obtener ID de Tipo Publicación

**Ubicación:** Añadir método nuevo después de `_refresh_fondos`

```python
def _get_selected_tipo_pub_id(self) -> Optional[int]:
    """Obtener ID del tipo de publicación seleccionado"""
    if not hasattr(self, 'cmb_tipo_pub'):
        return None
    
    try:
        idx = self.cmb_tipo_pub.current()
        if idx >= 0 and idx < len(self.tipos_pub_data):
            return self.tipos_pub_data[idx]['id']
    except Exception:
        pass
    
    return None
```

---

## 5️⃣ EditorProyecto - Actualizar `_save()` para Incluir Nuevos Campos

**Ubicación:** Línea ~1150, en el dict `data`

**Reemplazar:**
```python
data = dict(
    titulo=titulo,
    signatura=signatura,
    tipo_documento=self.var_tipo.get().strip(),
    autor=self.var_autor.get().strip(),
    tema=self.var_tema.get().strip(),
    fecha=self.var_fecha.get().strip(),
    fondo_id=fid,
    etiqueta_ids=etiqueta_ids,
)
```

**Por:**
```python
data = dict(
    titulo=titulo,
    signatura=signatura,
    abreviatura=self.var_abreviatura.get().strip() or None,  # NUEVO
    tipo_publicacion_id=self._get_selected_tipo_pub_id(),    # NUEVO
    tipo_documento=self.var_tipo.get().strip(),
    autor=self.var_autor.get().strip(),
    tema=self.var_tema.get().strip(),
    fecha=self.var_fecha.get().strip(),
    fondo_id=fid,
    etiqueta_ids=etiqueta_ids,
)
```

---

## 6️⃣ EditorProyecto - Actualizar `_load_project()` para Cargar Nuevos Campos

**Ubicación:** Línea ~1085, después de cargar otros campos

```python
# Cargar abreviatura (NUEVO)
self.var_abreviatura.set(row.get('abreviatura') or '')

# Cargar tipo de publicación (NUEVO)
tipo_pub_id = row.get('tipo_publicacion_id')
if tipo_pub_id and hasattr(self, 'cmb_tipo_pub'):
    for i, t in enumerate(self.tipos_pub_data):
        if t['id'] == tipo_pub_id:
            self.cmb_tipo_pub.current(i)
            break
```

---

## 7️⃣ EditorArchivo - Añadir Campo Abreviatura

**Ubicación:** En construcción de formulario, después del campo "Siglas"

```python
# Campo Abreviatura (NUEVO)
lbl, entry, help_icon = create_field_with_help(
    content_frame,
    row,
    "Abreviatura:",
    FIELD_HELP.get('archivo_abreviatura', 'Código corto para carpetas (máx 6 caracteres)'),
    entry_var=self.var_abreviatura,
    entry_width=15
)
row += 1

# Etiqueta informativa
ttk.Label(content_frame, text="(Se genera automáticamente si se deja vacío)", foreground="#666").grid(
    row=row-1, column=2, sticky='w', padx=6
)
```

**No olvidar añadir en `__init__`:**
```python
self.var_abreviatura = tk.StringVar()
```

**Y en `_save()`:**
```python
abreviatura=self.var_abreviatura.get().strip() or None,
```

**Y en `_load()`:**
```python
self.var_abreviatura.set(row.get('abreviatura') or row.get('siglas', '')[:6] or '')
```

---

## 8️⃣ EditorFondo - Añadir Campo Abreviatura

Similar a EditorArchivo:

```python
# En __init__
self.var_abreviatura = tk.StringVar()

# En formulario, después de "Código de referencia"
lbl, entry, help_icon = create_field_with_help(
    content_frame,
    row,
    "Abreviatura:",
    "Código corto para carpetas (máx 4 caracteres)",
    entry_var=self.var_abreviatura,
    entry_width=10
)
row += 1

# En _save()
abreviatura=self.var_abreviatura.get().strip() or None,

# En _load()
self.var_abreviatura.set(row.get('abreviatura') or '')
```

---

## 9️⃣ Actualizar FIELD_HELP Dictionary

**Ubicación:** Línea ~170, en el diccionario `FIELD_HELP`

```python
# Añadir estas entradas:
'archivo_abreviatura': 'Código corto nivel 2 de carpetas (máx 6 caracteres, ej: AHN). Estructura: proyecto/archivo/fondo_signatura/',
'fondo_abreviatura': 'Código corto nivel 3 de carpetas (máx 4 caracteres, ej: CONS). Estructura: proyecto/archivo/fondo_signatura/',
'proyecto_abreviatura': 'Código corto nivel 1 de carpetas (máx 8 caracteres, ej: LEG1234). Estructura: proyecto/archivo/fondo_signatura/',
'proyecto_tipo_pub': 'Tipo de documento: libro, revista, manuscrito, mapa, fotografía, etc. Facilita la catalogación.',
```

---

## 🔟 Actualizar Listas/Tablas para Mostrar Abreviaturas

### Lista de Archivos - Añadir Columna

**Ubicación:** Línea ~645, en `_build_tab_archivos`

**Reemplazar:**
```python
cols = ("id","nombre","siglas","ciudad","provincia","pais","email","telefono")
```

**Por:**
```python
cols = ("id","nombre","siglas","abreviatura","ciudad","provincia","pais","email","telefono")
```

**Y añadir header:**
```python
headers = {
    "id":"ID",
    "nombre":"Nombre",
    "siglas":"Siglas",
    "abreviatura":"Abrev.",  # NUEVO
    "ciudad":"Ciudad",
    "provincia":"Provincia",
    "pais":"País",
    "email":"Email",
    "telefono":"Teléfono"
}
```

### Lista de Fondos - Añadir Columna

Similar para fondos en `_build_tab_fondos`:

```python
cols = ("id","nombre","archivo","siglas","abreviatura","descripcion","periodo_inicio","periodo_fin")

headers = {
    # ... existentes ...
    "abreviatura":"Abrev.",  # NUEVO
    # ... resto ...
}
```

### Lista de Proyectos - Actualizar

En `main.py` o donde se muestra la lista de proyectos:

```python
# Añadir columna abreviatura y tipo_publicacion
cols = ("id","titulo","abreviatura","signatura","tipo_pub","fondo","fecha")

# En el loop de población:
for p in projects:
    tipo_pub_txt = ""
    if p.get('tipo_publicacion_id'):
        tipo_data = db.get_tipo_publicacion(base_path, p['tipo_publicacion_id'])
        if tipo_data:
            tipo_pub_txt = f"{tipo_data['icono']} {tipo_data['nombre']}"
    
    tree.insert("", "end", values=(
        p['id'],
        p['titulo'],
        p.get('abreviatura', ''),  # NUEVO
        p.get('signatura', ''),
        tipo_pub_txt,              # NUEVO
        p.get('fondo_nombre', ''),
        p.get('fecha', '')
    ))
```

---

## Verificación Final

Después de aplicar los cambios, verificar:

1. ✅ Formulario de Archivo muestra campo "Abreviatura"
2. ✅ Formulario de Fondo muestra campo "Abreviatura"
3. ✅ Formulario de Proyecto muestra:
   - Campo "Abreviatura"
   - Combo "Tipo de Publicación" con iconos
4. ✅ Al guardar proyecto, carpeta se crea en: `archivo/fondo/proyecto_signatura/`
5. ✅ Listas muestran columna "Abrev." para archivos/fondos/proyectos
6. ✅ Tooltips (ℹ️) muestran ayuda contextual

---

## Imports Necesarios

Asegurarse de que estos imports estén al inicio de `metadata_manager.py`:

```python
from typing import Optional, Dict, Any, List, Tuple  # Añadir si falta
from utils import db_manager as db
from utils import app_config
```

---

**¡Listo para integrar!** 🚀

Copiar y pegar estos snippets en los lugares indicados y las nuevas funcionalidades estarán disponibles en la GUI.
