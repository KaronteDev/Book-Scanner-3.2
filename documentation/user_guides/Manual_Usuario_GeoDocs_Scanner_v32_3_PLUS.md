# 🧭 Manual de Uso — GeoDocs Scanner v32.3

### K-Dev / GeoDocs Research Suite

**Versión:** 32.3 Estable  
**Autor:** Equipo de Desarrollo K-Dev  
**Fecha de última revisión:** Octubre 2025  
**Licencia:** MIT / Uso académico permitido con atribución

---

## 1\. Introducción

**GeoDocs Scanner v32.3** es una aplicación desarrollada como parte del ecosistema **GeoDocs Research Suite**, orientada a la digitalización, corrección y análisis académico de documentos patrimoniales.  
Integra módulos de captura, procesamiento, OCR, anotación, validación y exportación con estándares académicos internacionales (IIIF, TEI-XML, Dublin Core, etc.).

### Objetivos principales

*   Facilitar la digitalización de documentos mediante cámara o escáner.
*   Aplanar y corregir la curvatura de páginas de libros u obras encuadernadas.
*   Automatizar el OCR y permitir su revisión ortográfica y contextual.
*   Permitir anotaciones geolocalizadas y vinculación con entidades (personas, lugares, fondos).
*   Sincronizar proyectos locales con el backend **GeoDocs REST API**.

---

## 2\. Requisitos del sistema

| Requisito | Descripción |
| --- | --- |
| **Sistema operativo** | Windows 10/11, Linux, macOS |
| **CPU** | Mínimo 4 núcleos (recomendado 8) |
| **RAM** | 8 GB mínimo (16 GB recomendado) |
| **Dependencias Python** | `opencv-python`, `pytesseract`, `tkinter`, `sqlite3`, `requests`, `pyttsx3`, `Pillow` |
| **OCR** | Tesseract OCR (instalado en el sistema) |
| **Conexión** | Requerida para sincronización con GeoDocs REST API |

---

## 3\. Interfaz principal

La interfaz inicial presenta dos opciones principales:

1.  **Modo Escáner** — captura de páginas, corrección óptica y OCR.
2.  **Modo Anotaciones** — gestión de anotaciones, topónimos y personajes.

Ambos módulos comparten la misma base de datos global y permiten trabajar de forma local o sincronizada con el servidor GeoDocs.

---

## 4\. Escaneo y procesamiento de imagen

### Captura

*   Admite cámaras USB o integradas, seleccionables desde el menú principal.
*   Incluye vista previa en tiempo real y control manual de disparo.
*   Detecta automáticamente si hay **una o dos páginas** abiertas.

### Corrección de curvatura

*   Detección de bordes mediante Canny y dilatación morfológica.
*   Aproximación poligonal con `approxPolyDP` para rectificar contornos.
*   Transformación afín para aplanar la imagen.
*   Remuestreo con mapa de distorsión precalculado.

### Limpieza automática

*   Detección y eliminación de dedos o soportes visibles.
*   Ajuste automático de brillo y contraste.
*   Opción de recorte automático al área del documento.

### Calibración de formato

*   Perfiles predeterminados: **A3, A4, A5 y A6**.
*   Guardado de parámetros por cámara y proyecto.

---

## 5\. OCR y postprocesado

### Proceso OCR

*   OCR automático multilingüe mediante **Tesseract**.
*   Ejecución por lotes para más de 20 páginas.
*   Comparación automática entre OCR original y corregido.

### Editor WYSIWYG

*   Corrección manual del texto reconocido.
*   Revisión ortográfica automática.
*   Subrayado de errores y sugerencias contextuales.

### Sincronización visual

*   Vista comparada con la imagen original.
*   Scroll sincronizado entre texto e imagen.
*   Alternancia entre vista “Imagen / OCR / Comparado”.

---

## 6\. Audio y accesibilidad

*   Sistema **TTS (Texto a voz)** integrado mediante `pyttsx3`.
*   Lectura del OCR original o corregido.
*   Controles de pausa, velocidad y voz (masculina/femenina).
*   Soporte de atajos de teclado:
    *   `Ctrl+R` — reproducir lectura.
    *   `Ctrl+P` — pausar.
    *   `Ctrl+S` — detener.

---

## 7\. Glosarios y abreviaturas

*   Base integrada de **abreviaturas académicas comunes**.
*   Importación de glosarios externos en **CSV, JSON o XML**.
*   Asistente de mapeado de campos al cargar el fichero.
*   Fusión y comparación (`merge/diff`) de glosarios existentes.
*   Plantillas configurables (APA, MLA, CSIC).

---

## 8\. Metadatos y proyectos

Cada proyecto almacena sus datos en carpetas independientes dentro del directorio raíz configurado en la base global `GeoDocs.db`.

### Campos principales

| Campo | Descripción |
| --- | --- |
| **Título del documento** | Nombre identificativo |
| **Autor** | Persona o entidad creadora |
| **Tipo documental** | Libro, revista, legajo, expediente, etc. |
| **Signatura** | Identificador archivístico |
| **Archivo** | Centro o institución |
| **Fondo** | Fondo documental asociado |
| **Tema** | Línea de investigación |
| **Etiquetas** | Palabras clave |
| **Fecha** | Año o rango temporal |

### Tablas complementarias

*   **Archivos:** nombre, dirección, contacto.
*   **Fondos:** nombre, descripción, archivo al que pertenece.

---

## 9\. Anotaciones y geolocalización

*   Creación de anotaciones georreferenciadas.
*   Enlace directo a **Topónimos** y **Personajes** del sistema GeoDocs.
*   Integración con mapas interactivos (Leaflet / ArcGIS JS API).
*   Cada anotación puede contener: texto, coordenadas, relación de entidad.

---

## 10\. Integración con GeoDocs REST API

### Autenticación

*   Mediante **JWT** (JSON Web Token).
*   Requiere configuración previa del archivo `rest_config.json` con:

### Endpoints principales

| Endpoint | Función |
| --- | --- |
| `/api/documentos` | Subida y descarga de proyectos |
| `/api/fondos` | Gestión de fondos documentales |
| `/api/personas` | Sincronización de entidades-persona |
| `/api/toponimos` | Sincronización de entidades-geográficas |

---

## 11\. Revisión y validación académica

Incluye el **Formulario de Validación Técnica v32.3**, disponible en PDF y Markdown.  
Cada módulo puede marcarse como **Correcto (✔)** o **Con incidencias (✖)** y añadir observaciones multilínea.

*   Firma digital del validador.
*   Generación automática del informe institucional.
*   Compatible con firma electrónica avanzada (PAdES).

---

## 12\. Exportación académica

El sistema soporta los principales formatos de exportación para investigación histórica:

| Formato | Descripción |
| --- | --- |
| **IIIF v3** | Estandar internacional para imágenes y metadatos. |
| **TEI-XML** | Text Encoding Initiative con estructura jerárquica. |
| **Dublin Core JSON-LD/XML** | Metadatos bibliográficos normalizados. |
| **GeoJSON** | Representación geográfica de anotaciones. |

Se genera un **bundle ZIP** con todos los formatos y su validación.

---

## 13\. Rendimiento y estabilidad

*   OCR por lotes optimizado con procesamiento paralelo.
*   Manejo seguro de memoria y CPU.
*   Reanudación automática tras interrupciones.
*   Registro de errores y auditoría en `logs/`.

---

## 14\. Mantenimiento y seguridad

*   Copias de seguridad automáticas de proyectos y base global.
*   Restauración desde el panel de administración.
*   Gestión de roles y permisos:
    *   **Básico:** solo lectura.
    *   **Investigador:** edición de OCR y anotaciones.
    *   **Experto:** validación académica.
    *   **Administrador:** acceso total y publicación REST.
*   Conexión cifrada (HTTPS).

---

## 15\. Anexo: comandos útiles

```
# Iniciar el escáner
python geodocs_scanner.py

# Crear un nuevo proyecto
python geodocs_scanner.py --new "Libro_Codice_1850"

# Sincronizar con servidor GeoDocs
python sync_rest.py --upload Proyecto_X

# Ejecutar OCR masivo
python ocr_batch.py --dir proyectos/Libro_Codice_1850

# Generar informe de validación
python export_validation.py --pdf
```

---

## 16\. Glosario técnico

| Término | Definición |
| --- | --- |
| **OCR** | Reconocimiento Óptico de Caracteres |
| **TTS** | Text-to-Speech (texto a voz) |
| **IIIF** | International Image Interoperability Framework |
| **TEI-XML** | Formato XML para codificación de textos académicos |
| **GeoJSON** | Formato estándar para datos geográficos |
| **REST API** | Interfaz para comunicación con el servidor |
| **JWT** | Token de autenticación seguro |
| **SQLite** | Base de datos ligera local |

---

**© K-Dev / GeoDocs Research Suite — GeoDocs Scanner v32.3 · Manual de Uso**

---

## 2.1. Instalación de entornos (Python venv / Conda)

### Opción A — `venv` (recomendada)

```
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Opción B — Conda

```
conda create -n geodocs32 python=3.11
conda activate geodocs32
pip install -r requirements.txt
```

> **Nota:** Para usar GPU en OCR avanzado, instale el paquete CUDA/cuDNN adecuado y el backend compatible.

## 2.2. Variables de entorno (ENV)

Defina estas variables si su sistema no detecta las rutas automáticamente:

| Variable | Propósito | Ejemplo |
| --- | --- | --- |
| `TESSDATA_PREFIX` | Ruta a los datos de idiomas de Tesseract | `/usr/share/tesseract-ocr/4.00/tessdata` |
| `TESSERACT_CMD` | Ruta al ejecutable de Tesseract | `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| `GEODOCS_BASE_URL` | URL base del backend GeoDocs | `https://api.geodocs.es` |
| `GEODOCS_JWT` | Token JWT de autenticación | `eyJhbGciOi...` |
| `OPENCV_LOG_LEVEL` | Nivel de log de OpenCV | `ERROR` / `INFO` |
| `OMP_NUM_THREADS` | Hilos de BLAS/OpenMP (rendimiento) | `4` |

**Ejemplo (Linux/macOS):**

```
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata
export TESSERACT_CMD=/usr/bin/tesseract
export GEODOCS_BASE_URL=https://api.geodocs.es
export GEODOCS_JWT=eyJ...
```

## 2.3. Ficheros de configuración locales

| Archivo | Ubicación | Descripción |
| --- | --- | --- |
| `rest_config.json` | Carpeta del usuario o del proyecto | Persistencia de `base_url` y `token` JWT |
| `geodocs.db` | Raíz de la suite | Base de datos global de proyectos |
| `project.db` | Carpeta de cada proyecto | Datos, páginas, OCR y anotaciones del proyecto |
| `camera_profiles.json` | Carpeta del usuario | Perfiles de cámara (resolución, A3/A4/A5/A6) |
| `glossary/` | Carpeta del proyecto | Glosarios importados (CSV/XML/JSON) |

**Ejemplo** `**rest_config.json**`**:**

```
{
  "base_url": "https://api.geodocs.es",
  "token": "eyJhbGciOi..."
}
```

## 2.4. Perfiles de cámara y calibración (A3/A4/A5/A6)

*   Seleccione el perfil en la pantalla de **Escaneo**.
*   Cada perfil guarda: resolución, ROI, balance de blancos, exposición.
*   Los perfiles se guardan en `camera_profiles.json` y pueden exportarse/importarse.

---

### 7.1. Glosarios — Formatos soportados y mapeo

**CSV:** primera fila encabezados. Campos sugeridos: `abbr`, `expansion`, `context`, `notes`.  
**JSON:** array de objetos con los mismos campos.  
**XML:** raíz `<glossary>` con hijos `<entry>`.

**Ejemplo CSV:**

```
abbr,expansion,context,notes
ibid.,ibidem,Citas,Bibliografía
cf.,confer,Comparación,Usar en notas al pie
etc.,et cetera,Listas,Evitar en títulos
```

**Mapeo de campos:** al importar, asigne columnas → `Abreviatura`, `Expansión`, `Contexto`, `Notas`.  
Reglas: **primera mención expandida**, excepciones `keep_as_is`, `expand_always`.

---

## Anexo A. Atajos de teclado (completos)

| Acción | Atajo |
| --- | --- |
| Guardar cambios | `Ctrl+S` |
| Abrir proyecto | `Ctrl+O` |
| Nuevo proyecto | `Ctrl+N` |
| Revisión de cambios | `Ctrl+D` |
| Reproducir TTS | `Ctrl+R` |
| Pausar TTS | `Ctrl+P` |
| Detener TTS | `Ctrl+Shift+P` |
| OCR por lotes | `Ctrl+B` |
| Exportar | `Ctrl+E` |
| Cambiar módulo (Escaneo/Anotación) | `F6` |

## Anexo B. Solución de problemas

*   **Tesseract no encontrado** → Configure `TESSERACT_CMD` y `TESSDATA_PREFIX`.
*   **OCR con caracteres raros** → Verifique idioma instalado (`spa.traineddata`).
*   **Cámara no detectada** → Revise permisos del SO y drivers; pruebe con `v4l2-ctl` (Linux).
*   **Publicación falla (401)** → JWT caducado; regenere token.
*   **Exportación IIIF inválida** → Revise rutas `base_img_url` y estructura de canvases.

```
{
  "base_url": "https://api.geodocs.es",
  "token": "eyJhbGciOiJI..."
}
```