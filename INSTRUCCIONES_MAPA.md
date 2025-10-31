# 🗺️ Guía del Sistema de Mapas - GeoDocs Scanner

## ✅ Sistema Configurado

El sistema de mapas está completamente funcional con:

- **Mapa Estático Interactivo** ✓ (Click para seleccionar, drag para mover, zoom con rueda)
- **Geocodificación Nominatim** ✓ (Búsqueda de direcciones)
- **OpenStreetMap Tiles** ✓ (Teselas de mapa)

> **Nota:** El mapa interactivo con Leaflet (tkinterweb) está deshabilitado porque no renderiza 
> correctamente en Python 3.14 para Windows. El mapa estático ofrece toda la funcionalidad necesaria.

---

## 🎯 Cómo Usar los Mapas

### 1️⃣ **Abrir el Editor de Archivo**

1. Ve a **Menú → Metadatos**
2. Selecciona la pestaña **"Archivos"**
3. Haz clic en **"➕ Nuevo"** o **"✏️ Editar"** un archivo existente

### 2️⃣ **Acceder al Mapa**

En el editor de archivo, busca el campo **"Coordenadas"** y haz clic en el botón:
- **🗺 Abrir mapa**

### 3️⃣ **Vista del Mapa Interactivo**

Se abrirá una ventana con un mapa completamente funcional:

#### 📍 **Barra Superior:**
- Campo de dirección (auto-rellenado)
- Control de Zoom (3-18)
- Botón **"Geocodificar"** - Busca coordenadas de la dirección

#### 🎮 **Controles de Navegación:**
- **⬅ ⬆ ➡ ⬇** - Botones de paneo
- **"Centrar en marcador"** - Vuelve al punto seleccionado

#### 🖱️ **Interacción con el Mapa:**
- **Click simple** → Selecciona coordenadas y coloca marcador
- **Drag (arrastrar)** → Mueve el mapa (pan)
- **Flechas del teclado** → Mueve el mapa
- **Rueda del ratón** → Zoom in/out
- **Redimensionar ventana** → El mapa se ajusta automáticamente

#### ℹ️ **Barra de Estado:**
Muestra las coordenadas actuales o errores de conexión

#### 🎯 **Botonera Inferior:**
- **"Usar estas coordenadas"** - Guarda la selección
- **"Cerrar"** - Cancela sin guardar

---

## 🔧 Solución de Problemas

### ❓ El mapa muestra "No se pudo cargar el mapa"

**Causas posibles:**
- Sin conexión a Internet (las teselas se descargan de tile.openstreetmap.org)
- PIL/Pillow no está instalado

**Solución:**
- Verifica tu conexión a Internet
- Si falta PIL: `pip install pillow`

**Causa:** Estás arrastrando el mapa en lugar de hacer click

**Solución:**
- Haz **click rápido** sin mover el ratón
- Si arrastras más de 5 píxeles, se interpreta como paneo del mapa
- El marcador rojo debe aparecer al hacer click

---

## 💡 Consejos de Uso

### 📍 Para máxima precisión:
1. Usa el botón **"Geocodificar"** para centrar el mapa en la dirección
2. Ajusta el zoom al nivel 16-18 para ver detalles
3. Haz **click directo** en el punto exacto (sin arrastrar)
4. El formato guardado es: `latitud,longitud` (6 decimales de precisión)

### 🌍 Búsqueda por dirección:
- Formato recomendado: `Calle, Ciudad, Provincia, País`
- Ejemplo: `Calle Mayor 1, Madrid, Madrid, España`
- Cuanto más completa, mejor resultado

### ⚡ Atajos de teclado:
- `←` `→` `↑` `↓` - Mover el mapa (paneo)
- Rueda del ratón - Zoom in/out
- Drag con ratón - Desplazar mapa
- Click sin arrastrar - Seleccionar coordenadas

---

## 📦 Dependencias

El sistema de mapas requiere:

```txt
# Requerido para el mapa estático
Pillow>=10.0.0

# Opcional: mejor interfaz visual
ttkbootstrap>=1.10.0
```

Para instalar todo de una vez:
```bash
pip install -r requirements.txt
```

---

## 🎉 ¡Listo para Usar!

Tu sistema de mapas está completamente configurado y funcional:

- 🗺️ **Mapa estático interactivo** con tiles de OpenStreetMap
- 📍 **Geocodificación** con Nominatim (búsqueda por direcciones)
- 🎯 **Click-to-select** para coordenadas precisas
- 🖱️ **Drag para paneo** y zoom con rueda del ratón
- ⌨️ **Controles de teclado** para navegación
- ⚡ **Interfaz rápida y responsiva**

**¡Feliz mapeo!** 🚀
