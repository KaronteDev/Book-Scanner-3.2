# 🧠 Prompt Maestro — Solicitud de Implementación Completa de GeoDocs Scanner Avanzado

> ⚙️ **Objetivo:**  
Desarrollar una aplicación de escritorio en **Python (3.10 o superior)** con **OpenCV, Tkinter, Pillow, pytesseract y SQLite**, destinada a **digitalizar, procesar y anotar documentos y libros escaneados**, con integración directa en el ecosistema **GeoDocs Research Suite**.

---

## 🔧 Requisitos técnicos generales

- Lenguaje: **Python 3.10+**  
- Interfaz gráfica: **Tkinter + ttkbootstrap / Calcite style**  
- OCR: **Tesseract OCR** vía `pytesseract`  
- Voz: **TTS con pyttsx3**  
- Corrección ortográfica: **language_tool_python**  
- Almacenamiento: **SQLite (proyectos + global)**  
- Imagen: **OpenCV + Pillow**  
- API REST: **requests**  
- Geolocalización: **tkmapview** o **folium**

El proyecto debe ser **modular, mantenible y orientado a investigación académica**.

---

## 📁 Estructura de proyecto

/geodocs_scanner/
├─ main.py
├─ gui/
│ ├─ scan_view.py
│ ├─ annotation_view.py
│ └─ widgets/
├─ data/
│ ├─ geodocs.db
│ ├─ rest_config.json
│ └─ camera_profiles.json
├─ utils/
│ ├─ ocr_tools.py
│ ├─ image_cleaner.py
│ ├─ rest_api.py
│ └─ tts_manager.py
├─ assets/
│ └─ icons/
└─ README.md

---

## 📸 1. Escaneo y procesamiento de imágenes

**Objetivo:**  
Capturar páginas de libros o documentos desde cámara, corregir curvatura y perspectiva, limpiar artefactos y mejorar calidad.

**Funciones:**
- Detección automática de cámaras.  
- Vista previa en tiempo real (OpenCV + Tkinter).  
- Captura de imágenes con tecla **ESPACIO** o botón.  
- Modo **libro abierto** (división automática en dos mitades).  
- Corrección de **curvatura y perspectiva** con OpenCV.  
- **Eliminación automática de dedos o soportes de página**.  
- Ajuste de **brillo**, **contraste** y **nitidez**.  
- Soporte de calibración **A3, A4, A5, A6**.  
- Guardado en `/paginas/` con nombre `YYYYMMDD_HHMMSS_[anverso/reverso].jpg`.  
- Asociación automática al proyecto activo.

---

## 🧾 2. OCR (Reconocimiento de texto)

**Requisitos:**
- Motor Tesseract (`pytesseract`).  
- OCR por página o por lotes.  
- Procesamiento multilenguaje (`spa`, `lat`, `eng`).  
- Corrección automática de inclinación.  
- Limpieza y binarización previas.  
- Guardado de resultados en:
  - `ocr_original`
  - `ocr_corregido`
  - `ocr_versions` (histórico)
- **Comparador OCR**: Imagen original ↔ Texto OCR (scroll sincronizado).  
- Editor **WYSIWYG** para corrección manual.  
- Revisión ortográfica automática tras cada OCR (si activado).  

---

## 🧠 3. Texto a voz (TTS) y accesibilidad

- Integrar **pyttsx3** (funciona sin conexión).  
- Reproducir el OCR original o corregido.  
- Atajos de teclado:
  - `Ctrl+R` → Reproducir
  - `Ctrl+P` → Pausar
  - `Ctrl+Shift+P` → Detener
- Configurable (voz, velocidad, volumen).  
- Compatible con revisión ortográfica en ejecución.

---

## 🧩 4. Glosarios y abreviaturas

- Importación desde CSV, JSON o XML.  
- Mapeo automático de campos: `abbr`, `expansion`, `context`, `notes`.  
- Almacenamiento en tabla `glosario`.  
- Expansión automática de abreviaturas en OCR corregido.  
- Exportación opcional de glosario editado.

---

## 🌐 5. Integración REST con GeoDocs

- Archivo `rest_config.json` con `base_url` y `JWT`.  
- Endpoints:
  - `POST /api/documentos` → subida de metadatos y OCR.  
  - `GET /api/documentos` → carga de proyectos remotos.  
- Sincronización bidireccional local–servidor.  
- Detección de conexión y validación de token.  
- CRUD de configuración REST editable desde GUI.

---

## 🗺️ 6. Anotaciones y geolocalización

- Vista separada del escáner.  
- Anotaciones ligadas a texto o región de imagen.  
- Integración con topónimos y personajes de GeoDocs REST.  
- Georreferenciación en mapa interactivo (`tkmapview`).  
- Exportación a **GeoJSON**, **TEI-XML** o **IIIF Canvas**.  

---

## 🧱 7. Base de datos global (geodocs.db)

Tablas:
- `archivos` (nombre, dirección, contacto, email, teléfono)  
- `fondos` (nombre, descripción, archivo_id)  
- `proyectos` (metadatos y carpeta raíz)  

Cada proyecto tiene su propia DB (`project.db`) con:
- `paginas`  
- `ocr_versions`  
- `glosario`  

---

## 💬 8. Interfaz gráfica

- Separación en **dos pantallas principales**:
  1. Escáner  
  2. Anotaciones / OCR  
- Selector inicial para elegir módulo.  
- Diseño **profesional y accesible** (Open Sans, colores neutros).  
- Tooltips, estado de cámara y progreso OCR.  
- Soporte para teclado completo.  
- Persistencia de configuraciones.  

---

## ✍️ 9. Funcionalidades académicas avanzadas

- Exportación en formatos **Dublin Core**, **IIIF Manifest**, **TEI-XML**, **GeoJSON**.  
- Asociación de cada documento a **fondo documental** y **archivo histórico**.  
- Inclusión de campos académicos en metadatos:
  - fondo, archivo, signatura, autor, fecha, tema, etiquetas, tipo documental.  
- Validación mediante formulario institucional editable en PDF.  

---

## ⚙️ 10. Accesibilidad y mantenimiento

- Texto a voz integrado (offline).  
- Corrección ortográfica.  
- Revisión visual del OCR.  
- Log de errores.  
- Configuración editable de entorno (`TESSERACT_CMD`, `GEODOCS_BASE_URL`, etc.).  
- Modo de depuración.  
- Compatible con empaquetado (`.exe`, `.deb`, `.app`).  

---

## 🧾 11. Documentación y manual

- Generar `README.md` con instrucciones, dependencias, variables de entorno y atajos.  
- Incluir manual de uso en formato **Markdown y HTML** con:
  - Instalación
  - Uso del escáner
  - Procesamiento OCR
  - Edición y anotaciones
  - Configuración REST
  - Exportaciones académicas

---

## 🧭 12. Objetivo final

> Desarrollar una aplicación completa y académicamente profesional, integrada en la **GeoDocs Research Suite**, capaz de esca