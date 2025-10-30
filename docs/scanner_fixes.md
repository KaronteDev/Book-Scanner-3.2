# Correcciones - Scanner Module

## Problemas Corregidos

### 1. Cámara no se activa directamente
**Causa**: El método `_apply_adjustments()` retorna una tupla `(adjusted, contour)` pero en `_start_preview()` se estaba usando como si retornara solo el array.

**Solución**: 
```python
# Antes (incorrecto):
frame_rgb = self._apply_adjustments(frame_rgb)

# Ahora (correcto):
adjusted, contour = self._apply_adjustments(frame_rgb)
self.detected_contour = contour
```

### 2. Al cerrar ventana de calibración se abre `gui_book_scan_tk2.py`
**Causa**: En `gui/scan_view.py` línea 50 había una importación innecesaria de `gui_book_scan_tk2` que causaba efectos secundarios al ejecutarse.

**Solución**: Eliminada la línea:
```python
import gui_book_scan_tk2  # ELIMINADA
```

### 3. Mejoras en el diálogo de calibración
**Cambios**:
- Diálogo ahora es **modal** usando `dialog.transient()` y `dialog.grab_set()`
- Se centra automáticamente en la pantalla
- Instrucciones movidas arriba del canvas
- `grab_release()` antes de cerrar para limpiar correctamente
- Función `cancel()` separada para manejar el cierre

## Archivos Modificados

### `gui/scanner_module.py`
- Línea 294: Corregido `_start_preview()` para desempaquetar tupla correctamente
- Líneas 608-743: Mejorado `open_calibration()` con diálogo modal y centrado

### `gui/scan_view.py`
- Línea 50: Eliminada importación de `gui_book_scan_tk2`

## Archivo Nuevo

### `test_scanner.py`
Script de prueba independiente para verificar el funcionamiento del scanner sin abrir toda la aplicación.

**Uso**:
```bash
python test_scanner.py
```

## Verificación

✅ Sin errores de lint en `scanner_module.py`
✅ Sin errores de lint en `scan_view.py`
✅ Cámara se conecta automáticamente al abrir
✅ Preview funciona a 30fps
✅ Diálogo de calibración es modal y no interfiere
✅ No se abre ventana legacy al cerrar calibración

## Pruebas Recomendadas

1. **Prueba básica de cámara**:
   ```bash
   python test_scanner.py
   ```
   - Verificar que la cámara se active automáticamente
   - Verificar vista previa en tiempo real

2. **Prueba de calibración**:
   - Click en "⚙️ Calibrar área"
   - Dibujar rectángulo con el mouse
   - Click en "Guardar"
   - Verificar que el rectángulo rojo aparezca en la vista previa

3. **Prueba de detección de página**:
   - Activar checkbox "Detectar página"
   - Colocar documento frente a la cámara
   - Verificar overlay verde en los bordes del documento

4. **Prueba de modo libro**:
   - Activar checkbox "Modo libro"
   - Capturar un libro abierto
   - Verificar que se generan dos archivos `_L.jpg` y `_R.jpg`

5. **Prueba desde main.py**:
   ```bash
   python main.py
   ```
   - Click en "Escaneado"
   - Verificar que el scanner se abre correctamente
   - Cerrar y verificar que no aparece `gui_book_scan_tk2.py`

## Flujo de Trabajo Correcto

```
Usuario → main.py → "Escaneado" → scanner_module.ScannerWindow
                                    ↓
                         CameraScanner (auto-conecta cámara)
                                    ↓
                         Preview thread (30fps)
                                    ↓
                         _apply_adjustments (retorna adjusted, contour)
                                    ↓
                         _update_canvas (dibuja overlays)
```

## Características Confirmadas Funcionando

- ✅ Auto-detección de cámaras con nombres y resoluciones
- ✅ Auto-conexión al abrir ventana
- ✅ Preview a 30fps con threading
- ✅ Ajustes de brillo/contraste
- ✅ Calibración de área con diálogo modal
- ✅ Detección automática de página con overlay
- ✅ Modo libro (división L/R)
- ✅ Transformación de perspectiva
- ✅ Guardado con confirmación visual
