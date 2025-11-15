# 📚 GeoDocs Scanner v32.3 PLUS

**Sistema Avanzado de Digitalización y Anotación Documental**

GeoDocs Scanner es una aplicación de escritorio profesional para digitalizar, procesar, anotar y exportar documentos históricos y patrimoniales, con integración completa en el ecosistema GeoDocs Research Suite.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)

---

## ✨ Características Principales

### 📸 Módulo de Escaneo
- **Captura desde cámara** en tiempo real con vista previa
- **Corrección automática** de perspectiva y curvatura
- **Modo libro abierto** con división automática de páginas
- **Eliminación inteligente** de dedos y soportes
- **Calibración precisa** para formatos A3, A4, A5, A6
- **Mejora automática** de brillo, contraste y nitidez
- **Detección de rotación** y corrección automática

### 🔤 Módulo OCR
- Motor **Tesseract OCR** con soporte multiidioma (español, latín, inglés)
- **Preprocesamiento avanzado** para mejor precisión
- **Editor WYSIWYG** para correcciones manuales
- **Comparador visual** imagen ↔ texto con scroll sincronizado
- **Versionado automático** de OCR (original + correcciones)
- **Revisión ortográfica** integrada (language_tool_python)
- **Confianza por palabra** y estadísticas de calidad

### 🔊 Accesibilidad
- **Texto a voz** (TTS) con pyttsx3 (offline)
- Reproducción de OCR original o corregido
- Atajos de teclado:
  - `Ctrl+R` → Reproducir
  - `Ctrl+P` → Pausar
  - `Ctrl+Shift+P` → Detener
- Configuración de voz, velocidad y volumen
- Generación de audiolibros por página

### 📝 Anotaciones Académicas
- **Anotaciones sobre texto e imagen** con Web Annotation Model
- **Georreferenciación** de topónimos con coordenadas
- **Vinculación de entidades** (personas, lugares, eventos)
- **Integración con API REST** de GeoDocs
- **Exportación a formatos estándar** (TEI, GeoJSON)

### 📚 Glosarios y Abreviaturas
- **Importación** desde CSV, JSON, XML
- **Mapeo automático** de campos (abbr, expansion, context)
- **Expansión automática** en texto corregido
- **Múltiples ámbitos**: proyecto, tema, global
- **Diccionarios académicos** precargados

### 📦 Exportación Académica
- **Dublin Core** (JSON-LD, XML) para metadatos
- **IIIF Manifest 3.0** para interoperabilidad de imágenes
- **TEI-XML** para codificación académica de textos
- **GeoJSON** para datos geoespaciales
- **PDF/A-2** con OCR incrustado y metadatos XMP
- **Validación automática** de formatos

### 🗄️ Gestión de Proyectos
- **Base de datos global** (archivos, fondos, proyectos)
- **BD por proyecto** (páginas, OCR, anotaciones, glosarios)
- **Metadatos completos**: fondo documental, signatura, autor, fecha
- **Organización jerárquica**: Archivo → Fondo → Proyecto → Documentos

---

## 🚀 Instalación

### Requisitos Previos

1. **Python 3.10 o superior**
   ```bash
   python --version  # Verificar versión
   ```

2. **Tesseract OCR**
   - Windows: Descargar desde [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - Linux: `sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-lat`
   - macOS: `brew install tesseract tesseract-lang`

3. **Cámara compatible** (USB, webcam integrada o cámara IP)

### Instalación de Dependencias

```bash
# Clonar o descargar el repositorio
cd "Book Scanner 3.2"

# Crear entorno virtual (recomendado)
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Configuración de Variables de Entorno

Crear archivo `.env` o configurar en el sistema:

```bash
# Tesseract OCR (Windows)
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Base URL de GeoDocs API (opcional)
set GEODOCS_API_URL=https://api.geodocs.local

# Modo debug
set DEBUG=0
```

---

## 📖 Uso

### Inicio Rápido

```bash
# Lanzar aplicación principal
python main.py
```

Se abrirá el **selector de módulos** donde puedes elegir:
- 📸 **Módulo de Escaneo**
- 📝 **Módulo de Anotación y OCR**
- 📦 **Módulo de Exportación**

### Flujo de Trabajo Típico

#### 1. Crear Proyecto

1. Abrir **Módulo de Escaneo**
2. Clic en **"Configurar Proyecto"**
3. Completar metadatos:
   - Título del proyecto
   - Signatura archivística
   - Tipo de documento (libro, manuscrito, legajo, etc.)
   - Autor, fecha, tema
   - Fondo documental y archivo

#### 2. Escanear Documentos

1. Seleccionar cámara en el menú desplegable
2. Ajustar calibración (tecla `C`)
3. Configurar opciones:
   - Formato de papel (A3, A4, A5, A6)
   - Auto-corrección de perspectiva
   - Eliminación de dedos
   - Modo libro abierto
4. Capturar páginas (tecla `ESPACIO` o botón)
5. Las imágenes se guardan automáticamente en `proyecto/paginas/`

#### 3. Procesamiento OCR

1. Abrir **Módulo de Anotación**
2. Seleccionar proyecto
3. Navegar por páginas
4. Ejecutar OCR (tecla `F5` o botón)
5. Revisar y corregir texto en pestaña "OCR Corregido"
6. Usar comparador visual para verificación
7. Guardar correcciones (`Ctrl+S`)

#### 4. Anotación Académica

1. En pestaña **"Anotaciones"**:
   - Crear anotaciones sobre regiones de texto
   - Vincular entidades (personas, lugares)
   - Añadir notas académicas
2. En pestaña **"Glosario"**:
   - Importar glosarios de abreviaturas
   - Expandir abreviaturas en texto corregido

#### 5. Exportación

1. Abrir **Módulo de Exportación**
2. Seleccionar proyecto
3. Elegir formatos:
   - Dublin Core para repositorios
   - IIIF Manifest para visualizadores web
   - TEI-XML para edición crítica
   - GeoJSON para análisis espacial
   - PDF/A para preservación
4. Exportar individual o en lote

---

## ⌨️ Atajos de Teclado

### Globales
| Atajo | Acción |
|-------|--------|
| `F1` | Ayuda |
| `F5` | Recargar/Actualizar |
| `Ctrl+Q` | Salir |
| `Ctrl+S` | Guardar |

### Módulo de Escaneo
| Atajo | Acción |
|-------|--------|
| `ESPACIO` | Capturar imagen |
| `C` | Calibrar cámara |
| `P` | Configurar proyecto |
| `ESC` | Cerrar vista previa |

### Módulo de Anotación
| Atajo | Acción |
|-------|--------|
| `Ctrl+R` | Reproducir TTS |
| `Ctrl+P` | Pausar TTS |
| `Ctrl+Shift+P` | Detener TTS |
| `F5` | Ejecutar OCR |
| `Ctrl+S` | Guardar corrección |
| `F7` | Revisar ortografía |

---

## 🔧 Configuración

### Archivo: `data/rest_config.json`

```json
{
  "api_base_url": "https://api.geodocs.local",
  "verify_tls": true,
  "timeout_sec": 20,
  "auth": "jwt",
  "jwt_token": "YOUR_JWT_TOKEN_HERE",
  "iiif_image_base_url": "https://iiif.geodocs.local/iiif/"
}
```

### Archivo: `camera_calibration.json`

```json
{
  "cam_0_proyecto1": {
    "paper_format": "A4",
    "dpi": 300,
    "corners": [[100, 100], [900, 100], [900, 700], [100, 700]],
    "auto_crop": true,
    "remove_fingers": true
  }
}
```

### Archivo: `ocr_config.json`

```json
{
  "default_lang": "spa",
  "psm_mode": 3,
  "languages": ["spa", "lat", "eng"],
  "preprocess": true,
  "auto_rotate": true,
  "denoise": true
}
```

---

## 📂 Estructura de Proyecto

```
proyecto_ejemplo/
├── project.db              # Base de datos del proyecto
├── metadata.json           # Metadatos del proyecto
├── paginas/                # Imágenes capturadas
│   ├── 20250101_120000_anverso.jpg
│   ├── 20250101_120005_reverso.jpg
│   └── ...
├── thumbnails/             # Miniaturas
│   └── ...
├── ocr/                    # Resultados OCR
│   ├── page_001_original.txt
│   ├── page_001_corrected.txt
│   └── ...
├── annotations/            # Anotaciones
│   └── annotations.json
├── glossaries/             # Glosarios
│   └── abbreviations.csv
├── exports/                # Exportaciones
│   ├── dc_export.jsonld
│   ├── manifest.json
│   ├── tei_export.xml
│   ├── annotations.geojson
│   └── document.pdf
└── audio/                  # Audiolibros (TTS)
    └── audiobook.m3u
```

---

## 🔌 API REST de GeoDocs

### Endpoints Disponibles

```python
from utils.rest_api import get_api_client

api = get_api_client('data/rest_config.json')

# Buscar lugares
places = api.search_places("Madrid", limit=10)

# Buscar personas
persons = api.search_persons("Alfonso X", limit=10)

# Crear anotación
annotation = api.create_annotation(doc_id=1, data={
    "type": "Annotation",
    "body": {"value": "Nota académica"},
    "target": {"selector": {"type": "TextPositionSelector"}}
})

# Geocodificación
coords = api.geocode("Plaza Mayor, Madrid")
```

---

## 🧪 Testing

```bash
# Ejecutar tests unitarios
python -m pytest tests/

# Test de OCR
python -m utils.ocr_tools --test

# Test de TTS
python -m utils.tts_manager --test
```

---

## 📊 Formatos Soportados

### Entrada
- **Imágenes**: JPG, PNG, TIFF, BMP
- **Glosarios**: CSV, JSON, XML
- **Configuración**: JSON

### Salida
- **Imágenes**: JPG (alta calidad), PNG
- **Texto**: TXT, HTML, hOCR
- **Metadatos**: JSON-LD, XML
- **Documentos**: PDF/A-2
- **Audio**: WAV, MP3 (vía gTTS)
- **Manifiestos**: IIIF 3.0, TEI-XML
- **Geodatos**: GeoJSON

---

## 🤝 Contribución

Las contribuciones son bienvenidas. Por favor:

1. Fork del repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Agregar funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

---

## 📝 Changelog

### v32.3 PLUS (2025-01-30)
- ✨ Arquitectura modular reorganizada (/gui, /utils, /data)
- 🎯 Selector de módulos centralizado
- 🗄️ Sistema de base de datos global + por proyecto
- 🔊 Gestor TTS mejorado con threading
- 🌐 Cliente REST API completo
- 📦 Módulos de exportación académica
- 📖 Documentación completa

### v32.3 (anterior)
- Escáner con corrección de perspectiva
- OCR con Tesseract
- TTS básico
- Exportadores iniciales

---

## 🐛 Solución de Problemas

### Tesseract no encontrado

**Error**: `TesseractNotFoundError`

**Solución**:
```bash
# Windows
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# O configurar en utils/ocr_tools.py
```

### Cámara no detectada

**Solución**:
1. Verificar permisos de cámara en Windows (Configuración → Privacidad)
2. Probar con diferentes índices de cámara (0, 1, 2)
3. Verificar que no esté en uso por otra aplicación

### Problemas con TTS

**Solución**:
```bash
# Instalar voces adicionales en Windows
# Panel de control → Voz → Agregar idiomas

# Linux: instalar espeak
sudo apt install espeak espeak-data
```

---

## 📄 Licencia

MIT License - Ver archivo `LICENSE` para detalles.

---

## 👥 Autores

**GeoDocs Research Team**
- Desarrollo principal: [Tu nombre]
- Contribuidores: Ver `CONTRIBUTORS.md`

---

## 📧 Contacto

- **Email**: geodocs@example.com
- **Web**: https://geodocs.local
- **Issues**: GitHub Issues

---

## 🙏 Agradecimientos

- **Tesseract OCR** por el motor de reconocimiento
- **OpenCV** por procesamiento de imágenes
- **IIIF Consortium** por estándares de interoperabilidad
- **TEI Consortium** por estándares de codificación de textos
- Comunidad Python por las excelentes bibliotecas

---

**GeoDocs Scanner** - Preservando el patrimonio documental con tecnología de vanguardia 📚✨
