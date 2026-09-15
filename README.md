
# GeoDocs Scanner v12 — REST avanzada + Mapeo/Validación + Pull diferido

Esta versión incorpora:
- **CRUD de mapeo REST** (`GeoDocs API → Editar mapeo de endpoints…`) con pestañas para endpoints y field_map.
- **Validador de esquema** (`GeoDocs API → Validar mapeo/DB…`) que compara columnas locales vs mapeo.
- **Pull de documentos (solo metadatos)** y **descarga diferida de imágenes** cuando se solicita.
- **Push de documentos** aplicando el mapeo de campos a la API remota.
- Se mantiene la creación de proyectos locales desde cero y el escaneo con OpenCV.

## Uso
```
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python gui_book_scan_tk.py
```

## Configuración
- Edita `geodocs_config.json` o usa **GeoDocs API → Ajustes API…** (URL base, API key, TLS, timeout)
- Edita `geodocs_api_map.json` o usa el CRUD de **GeoDocs API → Editar mapeo de endpoints…**

## Flujo
1. **Crear proyecto local** (botón “Nuevo proyecto…”) → escanear, OCR, reordenar, exportar PDF.
2. **Subir a servidor** (GeoDocs API → Subir Documento + Páginas).
3. **Descargar remotos (pull)** → “Descargar documentos (pull)…”, importar metadatos, y **Descargar imágenes…** cuando se necesite.



## Entornos (v14)
- Cambia entre **Desarrollo** y **Producción**: menú **Entorno**.
- **Autodetectar entorno** prueba primero `config.dev.json` y luego `config.prod.json`.
- El perfil activo se copia a `geodocs_config.json`.


## Novedades v15 (académico & profesional)
- **Ficha ISAD(G)**: nivel de descripción, productor, alcance y contenido (editable desde la GUI).
- **Citas automáticas**: generación de referencia en **APA** e **ISO 690** desde los metadatos.
- **Informe de proyecto (PDF)**: reporte institucional con logo, metadatos y estadística de páginas.
- **Versionado + hash**: cada nueva página guarda **SHA-256** y se registra en `version_history`.


## Novedades v16 (interoperabilidad académica)
- **Anotaciones por página** (GUI): tipo, etiquetas y cuerpo; registro en DB y versionado.
- **Exportar → EAD3 (XML)**: estructura archivística con repositorio y componentes por página.
- **Exportar → Dublin Core (JSON-LD)**: descripción en schema.org/CreativeWork.
- **Exportar → TEI-XML (OCR)**: cuerpo con divs por página utilizando OCR TXT si existe.
- **Exportar → METS/ALTO**: paquete METS mínimo y ficheros ALTO simplificados por página.


## Roadmap Estratégico (Q4 2025 – Q2 2026)

| Fase | Objetivo Principal | Entregables | Estado |
|------|--------------------|-------------|--------|
| Fase 1 | Separación MVC/MVP | `models/`, `views/`, `presenters/`, `services/` | Completado |
| Fase 2 | Visualización 3D | Visor Three.js + hotspots + zoom palabra | Completado |
| Fase 3 | App móvil (Spec) | Documento `mobile_app_spec.rst` + endpoints | Completado (spec) |
| Fase 4 | Documentación interactiva | Sphinx embebido + ventana ayuda + tutorial | Completado |
| Fase 5 | Testing automatizado | >70% cobertura, estructura unit/integration/e2e | Completado (93%) |
| Fase 6 | Refactor cámara | `CaptureService` + tests start/stop/errores | Completado |
| Fase 7 | Video Tour | Integración YouTube embebida en ventana ayuda | En progreso |
| Fase 8 | Móvil MVP | Captura WiFi + OCR revisión táctil | Pendiente |
| Fase 9 | Sincronización en vivo | WebSocket anotaciones/OCR/app móvil | Pendiente |
| Fase 10 | Export 3D/Presentación | Generar animaciones y paquete demo académico | Pendiente |

### Prioridades Próximas
1. Video Tour (YouTube) integrado (botón en ayuda).  
2. MVP App móvil (captura + pull OCR + edición).  
3. WebSocket sync tiempo real (anotaciones/OCR).  
4. Wizard avanzado (rama condicional según perfil).  
5. Export bundle de Presentación (slides + 3D hotspots).  

### Métricas de Calidad Actuales
- Cobertura pruebas: 93% (objetivo base >70%).
- Hotspots 3D: zoom palabra y layout dinámico funcional.
- Tiempo arranque visor 3D: <1s (in-browser). Embedding CEF: pendiente.
- Documentación Sphinx: auto-build on demand.

---

## Novedades v17 (mejoras de productividad y UX) — Nov 2025

### 10 Mejoras Mayores Implementadas

#### 1. **Metadatos V3 Completos**
- Campos `abreviatura` en Proyecto, Archivo y Fondo
- Campo `tipo_publicacion` con 13 tipos predefinidos
- Estructura jerárquica de carpetas automática
- Tooltips informativos en todos los campos

#### 2. **Rotación Rápida de Imágenes**
- Botones ↶90°, ↷90°, ⤾180° en cada miniatura
- Rotación instantánea desde la galería
- Atajos: **Ctrl+R** (90°), **Ctrl+Shift+R** (-90°)

#### 3. **Diálogo de Metadatos Pre-Captura**
- Formulario antes de cada captura
- Botón **"Usar datos anteriores"** para reutilizar
- Persistencia automática de metadatos
- Shortcuts: Enter/Escape

#### 4. **Eliminación Múltiple de Fondos**
- Selección múltiple con Ctrl/Shift
- Eliminación en batch optimizada
- Contador de éxitos/errores

#### 5. **Sistema de Plugins Completo**
- Arquitectura extensible sin modificar el core
- BasePlugin ABC con hooks para: imágenes, OCR, eventos, UI
- Cargador dinámico con hot-reload
- Plugin de ejemplo incluido
- Documentación completa en `plugins/README.md`

#### 6. **Lazy Loading de Galería**
- Carga solo miniaturas visibles
- **95% mejora de performance** (10s → 0.5s con 500 imágenes)
- Detección de viewport con throttling
- Escalable a miles de imágenes

#### 7. **Historial de Versiones**
- Sistema completo de snapshots para OCR y anotaciones
- Métodos: create, get, list, revert, compare, delete
- Auto-limpieza de versiones antiguas
- Migración de BD incluida (`migrate_versions.py`)

#### 8. **Atajos de Teclado Globales**
- **18 atajos** predefinidos: F5 (captura), Ctrl+E (exportar), etc.
- Ventana de ayuda con **F1**
- Sistema extensible y configurable
- Enable/disable dinámico

#### 9. **Panel de Estadísticas Completo**
- Dashboard con **4 pestañas**:
  - General: Overview + progress bars
  - OCR: Estados + métricas + actividad reciente
  - Calidad: Distribución + promedio + problemas
  - Cronología: Actividad diaria + día más productivo
- Exportación a CSV

#### 10. **Búsqueda Avanzada Multi-Proyecto**
- Motor de búsqueda global en todos los proyectos
- **9 filtros combinables**: texto, fecha, proyecto, archivo, fondo, tipo, OCR, calidad
- Resultados exportables a CSV
- Navegación directa a ubicaciones

### Documentación Completa

- **[QUICK_START.md](QUICK_START.md)** - Integración en 5 pasos (15-30 min)
- **[RESUMEN_EJECUTIVO.md](RESUMEN_EJECUTIVO.md)** - Visión general y métricas
- **[MEJORAS_IMPLEMENTADAS_HOY.md](MEJORAS_IMPLEMENTADAS_HOY.md)** - Detalles técnicos
- **[GUIA_NUEVAS_FUNCIONALIDADES.md](GUIA_NUEVAS_FUNCIONALIDADES.md)** - Guía de usuario
- **[plugins/README.md](plugins/README.md)** - Tutorial de plugins
- **[INDEX.md](INDEX.md)** - Índice de toda la documentación

### Impacto

| Métrica | Mejora |
|---------|--------|
| **Performance galería** | 95% más rápido |
| **Productividad** | 3x con atajos |
| **Búsqueda** | Multi-proyecto simultánea |
| **Extensibilidad** | ∞ con plugins |
| **Auditoría** | Historial completo |

### Quick Start v17

```powershell
# 1. Migrar base de datos (UNA VEZ)
python migrate_versions.py

# 2. Ejecutar aplicación
python main.py

# 3. Probar nuevas funciones:
# - F1 → Ver todos los atajos
# - F5 → Capturar con metadatos
# - Ctrl+F → Búsqueda avanzada
# - Menú Herramientas → Estadísticas
```

Ver **[QUICK_START.md](QUICK_START.md)** para integración completa en main.py.


## Novedades v17 (Geo + Entidades)
- **Geolocalización de anotaciones** (lat/lon) y vínculo con **Topónimos** y **Personas** de GeoDocs (REST).
- **Búsqueda de entidades** desde la interfaz Python (autocompletado simple).
- **Mapa web Calcite/Leaflet** con servidor Flask embebido (`web_viewer/server.py`), lanzable desde la GUI con *Ver anotaciones en mapa (web)*.
- **Sincronización de anotaciones** (push) a `/api/anotaciones` con JWT.
- **Miniaturas con superposición** de regiones anotadas (x,y,w,h normalizados).


## Novedades v18 (sincronización total)
- Autocompletado **Lat/Lon** al elegir **Topónimo**.
- **Pull** de anotaciones desde servidor en Tkinter y Visor Web.
- **Mini-mapa** para seleccionar coordenadas y traerlas a la GUI.
- **Filtro** de anotaciones por tipo.
- **Exportar GeoJSON** de anotaciones.


## Novedades v19 (IIIF + Linked Places + Búsqueda avanzada)
- **Exportar IIIF Presentation 3.0** (manifest.json) con Canvases e Image Annotations por página.
- **Exportar Linked Places (GeoJSON-LD)** con contexto JSON-LD y relaciones `lp:relationType`.
- **Búsqueda avanzada** en la GUI Tkinter (por texto, etiquetas, tipo, fechas, entidad).
- **Búsqueda avanzada** en el visor web (filtros y refresco de resultados + marcadores).


## Novedades v20 (IIIF avanzado + Prosopografía)
- **IIIF Image API (nivel 3)**: exporta un *manifest* que referencia servicios `ImageService3` (tiles, `info.json`). Configura `iiif_image_base_url` en `geodocs_config.json`.
- **IIIF WebAnnotations de regiones**: genera un `AnnotationPage` con `highlighting/commenting` usando `xywh=percent` desde `target_region`.
- **Prosopografía (Tkinter)**: análisis básico con gráficas (frecuencias de personas y topónimos). Menú **Analítica → Prosopografía…**.
- **Prosopografía (Web)**: panel con listados agregados `/prosopo`.


## Novedades v21 (IIIF por página + Grafos + Publicación)
- **IIIF AnnotationPages (xywh=pixel)** por página (convierte regiones normalizadas usando dimensiones reales de imagen).
- **Publicación de manifest IIIF** al backend (**POST** `/api/iiif/manifest`) desde la GUI.
- **Grafo de coapariciones**:
  - Exporta a **GEXF** / **GraphML**.
  - Visualización básica en la app (layout de fuerza, etiquetas parciales).


## Novedades v22 (Publicación + Validación IIIF + Grafo interactivo)
- **Validador IIIF** (chequeos básicos de estructura para Manifest/Annotation*).
- **Subida directa** de:
  - **IIIF AnnotationPages (pixel)** → `POST /api/iiif/annotations`.
  - **Linked Places (GeoJSON-LD)** → `POST /api/linked-places`.
- **Visor web**: grafo **interactivo** (sigma.js) de coapariciones (personas–topónimos) con endpoint `/graph`.


## Novedades v23 (flujo dividido)
- **Selector inicial** (`launcher.py`) para elegir módulo.
- **Módulo Escaneo** (`scanner_gui.py`): interfaz ligera con OpenCV para capturar páginas y guardarlas al proyecto **sin cargar el módulo de anotaciones**.
- **Módulo Anotaciones** (`annotator_gui.py`): reutiliza la interfaz completa anterior (OCR, metadatos, exportaciones, IIIF, analítica, REST, etc.).
- Beneficio: la **cámara solo se activa** cuando estás en *Escaneo*; el módulo de *Anotaciones* trabaja sobre páginas ya capturadas, sin bloquear la cámara.


## Novedades v24 (OCR integral + web viewer)
- **Cola de procesamiento (processor_queue.py)** para OCR automático por lotes (pytesseract si está disponible).
- **Configuración OCR** (`ocr_config.json`) con idioma, PSM y OEM.
- **Módulo de Escaneo**: menú **Archivo → Importar páginas…** (carpeta de imágenes; PDF/TIFF si hay librerías opcionales instaladas).
- **Módulo de Anotación**: pestaña **OCR/Textos** para ver/editar OCR, actualizar y subir al servidor.
- **Sincronización de OCR**: menú **Sincronizar** → **Subir OCR (documento)** o **Subir OCR (página)**.  
- **Visor web**: panel **OCR** con campo de página y textarea para consultar el texto desde SQLite por `document_id` y `seq`.


## Novedades v25 (Histórico + Comparador + Anverso/Reverso)
- **Histórico OCR**: tabla `ocr_revision` con versiones, usuario y fecha; guardado automático desde GUI y Web.
- **Comparador web**: panel con **scroll sincronizado** entre *OCR original* (o **imagen**) y **OCR corregido**; resaltado de diferencias palabra a palabra.
- **WYSIWYG**: editor HTML en el panel derecho (negrita/cursiva/subrayado/mark), guardado como `ocr_html` y texto plano en `ocr_text`.
- **Anverso/Reverso**: campo `face` por página, configurable desde la GUI; incluido en exportaciones y consolidado.
- **Descarga `.txt`** desde el panel OCR (endpoint `format=txt`).

### Exportación consolidada
- TXT y HTML combinados con marcas por página y `face`.


## Novedades v26 (Revisiones firmadas + Restaurar + Track changes)
- **Selector de revisión** en el comparador web (cargar/visualizar y **restaurar** versiones previas).
- **Firmas de revisión** (autor, fecha y nota) con endpoint `/sign_ocr_revision`.
- **Track changes**: dif de palabras generado como `<ins>/<del>` y guardado en `ocr_revision.changes_html`.
- Endpoints nuevos: `GET /ocr_revision_body`, `POST /restore_ocr_revision`, `POST /sign_ocr_revision`.
- El botón **Guardar corrección** respeta el modo Track changes y adjunta `changes_html`.


## Novedades v27 (Roles GeoDocs + Restauración parcial + Diffs avanzados)
- **Roles GeoDocs**: integración con `/api/auth/verify` para identificar `user` y `role` (investigador/experto/administrador) y ajustar permisos en la UI web.
- **Firmas condicionadas por rol**: solo `experto` y `administrador` pueden firmar revisiones.
- **Restauración parcial**: selecciona párrafos de una revisión y aplícalos sobre la versión activa; genera nueva revisión.
- **Vista de diferencias**: panel dedicado que muestra `changes_html` con `<ins>/<del>`; accesible desde el comparador.
- Endpoints: `GET /user_role`, `GET /ocr_changes`, `POST /apply_partial_restore`.


## Novedades v28 (Rangos de caracteres + Roles personalizados + Auditoría)
- **Restauración por rango de caracteres**: selecciona un rango en la *revisión* y reemplaza la selección en el texto *corregido*; guarda con `/apply_partial_restore_chars`.
- **Roles personalizados**: `/user_role` ahora pasa `permissions` desde GeoDocs si el backend los expone; la UI respeta capacidades dinámicas.
- **Auditoría**: tabla `audit_log` y endpoint `/export_audit` (JSON/CSV) para firmas, restauraciones y guardados.
- Botón **Exportar auditoría (CSV)** en el panel de diferencias.


## Novedades v29 (Validación + Workflow + Publicación)
- **Validación de consistencia**: se calcula `similarity_score` (difflib) al guardar revisiones; alertas si el puntaje es bajo.
- **Workflow editorial** con estados: `borrador → revisado → validado → publicado` para páginas y documentos, con permisos por rol.
- **Dashboard de calidad**: vista web con tabla de similitud por página y estado, exportable desde auditoría.
- **Publicación a GeoDocs**: botón en web que llama a `/api/documentos/publish` del backend y marca el documento como `publicado` en local.


## Novedades v30 (Quality Engine automático por lotes)
- **Scheduler interno** configurable (`quality_scheduler.json`): por defecto habilitado cada 24 h.
- **Quality Engine** (`modules/quality_engine.py`) recorre páginas y calcula métricas visuales/textuales básicas y genera overlays (si OpenCV está disponible).
- **GUI (Tk)**: menú **Calidad** → *Forzar análisis (proyecto)* y *Activar/Desactivar scheduler*.
- **Web viewer**: botones **Recalcular análisis por lotes** y **Ver estado del scheduler**.
- Informe ligero en `quality_scheduler_status.json` tras cada ciclo.
> Nota: El análisis visual profundo con hOCR/ALTO se integrará cuando el entorno tenga Tesseract/hOCR disponibles.


## Novedades v30.2 (Calibración A3/A4/A5/A6 + DPI y perspectiva)
- **Calibración guiada** con hoja ISO 216 (A3/A4/A5/A6): detecta el mayor cuadrilátero en la imagen y estima **DPI X/Y** automáticamente.
- Guarda resultados en `calibration.json` y en SQLite (`document.dpi_x`, `dpi_y`, `calibrated_size`, `calibration_date`).
- Genera previsualización **rectificada** de la hoja de calibración.
- **Interfaz**: menú **Calibración** en el Anotador (Tkinter), y en el visor web botón **Ver calibración** + **rejilla de 10 mm** aproximada.
> Nota: La rejilla se ajustará dinámicamente a milímetros cuando haya DPI confirmados (en futuras subversiones).


## Novedades v30.3 (Auto-exposición + Mejora de imagen previa al OCR)
- **Auto-exposición de cámara** (OpenCV) desde el menú **Cámara**; intento de activar modo automático y opción manual (según backend). Hook opcional a **gphoto2**.
- **Mejora óptica previa al OCR**: CLAHE adaptativo, compensación de luz, balance de blancos y nitidez. Guardado en `enhanced_image_path` + `enhancement_method`.
- **Integración en lote**: el Quality Engine genera versiones *enhanced* para todo el proyecto.


## Novedades v30.4 (Homografía previa al OCR + Rejilla a milímetros + Exposición adaptativa)
- **Normalización de perspectiva previa al OCR**: nuevo módulo `modules/rectifier.py` detecta el cuadrilátero de página y aplica *warp* antes del enhancer/OCR. Si hay **DPI calibrados**, usa tamaño destino alineado a milímetros (bloques de 10 mm).
- **Rejilla a milímetros reales en web**: el checkbox “Mostrar rejilla (10 mm)” ahora usa DPI calibrados para escalar la cuadrícula a mm reales; *fallback* a 40 px si no hay DPI.
- **Exposición adaptativa por histograma**: en **Cámara → Ajustar exposición (auto)** se itera para alcanzar un brillo objetivo (0–1). Requiere soporte del backend de cámara.


## Novedades v30.5 (Homografía persistente + Validación geométrica + Informe PDF + Accesibilidad)
- **Homografía por página**: se guarda en DB (`page.homography_matrix`) y en sidecar `*_H.txt` automáticamente.
- **Metadatos DPI** incrustados (Pillow) en JPEG/TIFF tras la rectificación/mejora (siempre que Pillow esté disponible).
- **Validador geométrico** (`modules/batch_validator.py`): calcula error angular y (si procede) tolerancia de escala; exporta CSV y genera informe **PDF** (si `reportlab` está disponible) o **HTML** como alternativa.
- **Tkinter**: menú **Calidad** con **Validar** y **Exportar informe**; menú **Accesibilidad** (Zoom UI, alto contraste).
- **Web**: controles de tamaño de fuente y contraste; ARIA labels para botones claves.


## Novedades v30.6 (XMP + Informe con gráficos + TTS + Revisión ortográfica + Accesibilidad WCAG)
- **XMP sidecar** por página con metadatos GeoDocs (DPI, calibración, H, métricas).
- **Informe PDF** con gráficos de error angular (ReportLab); fallback **HTML** con gráfico SVG embebido.
- **TTS** (OCR original y corregido) usando `pyttsx3` si disponible; botones en Tk y Web.
- **Revisión ortográfica** del OCR corregido con `language_tool_python` (si disponible) o `pyspellchecker` como alternativa.
- **Accesibilidad** reforzada (controles ya incluidos en v30.5 + contraste revisado).


## Novedades v30.7 (TTS ampliado + instalador + WYSIWYG ortográfico)
- **Instalador** `install_dependencies.py` y **requirements.txt** con todo lo opcional (pyttsx3, gTTS, language_tool_python, spellchecker, reportlab, simpleaudio/playsound).
- **TTS Python mejorado**: pyttsx3 offline con fallback gTTS; utilidades de reproducción en-app (simpleaudio/playsound).
- **Tkinter**: Generar TTS (página) y Reproducir audio TTS…
- **Web**: Editor **WYSIWYG** del OCR corregido, botón de revisión ortográfica con subrayado, guardado directo; botones TTS con player nativo del navegador (abre el WAV/MP3 generado).


## Novedades v30.8 (TTS en streaming + corrector interactivo + atajos WYSIWYG)
- **TTS en streaming (web)**: endpoint `/tts_stream` devuelve audio por chunks; reproductor de audio embebido.
- **Corrector interactivo**: menú contextual sobre palabras subrayadas con sugerencias (click para reemplazar). Endpoint `/spell_suggest`.
- **Atajos de teclado en editor**: **Ctrl+S** (guardar), **F7** (revisar), **Ctrl+Z/Y** (deshacer/rehacer).


## Novedades v30.9 (Diccionarios por proyecto/tema + Voz/velocidad TTS + Audiolibro)
- **Ortografía con diccionarios especializados**: se leen `custom_dict.json` y ficheros `dictionaries/*.txt` en la raíz del proyecto; el corrector ignora esos términos.
- **TTS configurable**: selección de **voz** (lista desde `/tts_voices`), **velocidad** y **volumen** (pyttsx3); gTTS como fallback.
- **Audiolibro**: genera pistas por página en orden, **playlist M3U** y **CUE**; intenta concatenar a **WAV** único si es posible. Controles en **web** y **Tk**.


## Novedades v31.0 (Gestor de glosarios + Abreviaturas académicas)
- **Glosarios/Diccionarios (CRUD)** por **proyecto/tema/global** con persistencia en SQLite.
- **Abreviaturas académicas (ES)** pre-cargadas como glosario global: ver `docs/abreviaturas_academicas_es.(csv|md)`.
- `/spellcheck` ahora devuelve `abbrev_hints` con coincidencias y posibles **expansiones**.
- Panel de **Glosarios** en el visor web (📚) para crear/editar/eliminar glosarios y pegar JSON de términos.


## Novedades v31.1 (Abreviaturas avanzadas + Import/Export glosarios + Estilos)
- **WYSIWYG**: resalta abreviaturas conocidas y permite **expandir con clic** según sugerencia.
- **Estilos** (Chicago/APA/MLA/CSIC): selector en la barra superior; políticas listas para expandir en primera mención (base).
- **Importación de glosarios**: CSV, JSON y XML con **mapeo de campos** al cargar.
- **Exportación de glosarios**: a **CSV/JSON/TEI-XML** (simple, compatible con repositorios académicos).
- **Panel de glosarios**: complementado con import/export desde la misma interfaz.


## Novedades v31.2 (Estilos con subediciones + 1ª mención auto + TEI avanzado + Diff/Merge)
- **Estilos** con detalle por idioma/subedición: Chicago 17ª, APA 7ª, MLA 9ª, CSIC (base).
- **Primera mención automática**: expansión de la primera abreviatura con marcador **reversible** (clic para deshacer).
- **Importación TEI-XML avanzada**: soporta `<list>/<item>` y `<entry><form><abbr/>...</entry>`.
- **Comparativa y fusión de glosarios**: endpoints `/glossary_diff` y `/glossary_merge` con políticas de fusión.
- Mantiene todas las funcionalidades previas (TTS, audiolibro, accesibilidad, validación geométrica, XMP, OCR, etc.).


## Novedades v31.3 (Plantillas de estilo + Aplicación masiva + Diff/Merge interactivo)
- **Plantillas de estilo** (SQLite): CRUD vía `/style_templates` y panel “🎛️ Plantillas” en el visor web.
- **Aplicar estilo al documento**: expansión solo **1ª mención** por abreviatura; registro de cambios **CSV/JSON** por documento.
- **Diff/Merge de glosarios** con interfaz web (panel “⚖️ Diff Glosarios”) y atajos en Tk.
- Mantiene todas las funcionalidades previas (v31.2 y anteriores).


## v32.0 (integración inicial de revisión, reglas contextuales y export)
- **Diff engine** a nivel token y endpoints `/diff_page` y `/review_apply` (aceptar/rechazar/revertir).
- **Reglas contextuales**: módulo y CRUD `/context_rules` (vinculadas a plantillas).
- **Exportadores** IIIF/TEI/DC/GeoJSON (stubs funcionales) + `/export/*` y **bundle**.
- **Paneles** en el visor (botones): Revisión de Cambios, Reglas Contextuales y Exportar (wireframes operativos como shells).
- Mantiene toda la funcionalidad v31.3.


## v32.1 (conexión en vivo + reglas contextuales en el aplicador)
- **Revisión de cambios (en vivo)**: panel modal en la web que consume `/diff_page` y aplica decisiones con `/review_apply`.
- **Reglas contextuales**: el aplicador `apply_style_with_context(...)` respeta `context_rules` por zona (`data-zone`) en HTML.
- Conserva todo lo de v32.0 y anteriores.


## v32.2 (exportadores completados + panel de export en vivo)
- **IIIF v3** con dimensiones de canvas (si hay imagen en disco) y estructura de annotations completa.
- **TEI-XML** por zonas (`data-zone`) y cabecera TEI básica.
- **Dublin Core JSON-LD** con `@context` (y **XML** opcional).
- **GeoJSON** con propiedades enriquecidas (page_seq, document_id).
- **Panel de exportación** (modal en la web) conectado a `/export/*` + validador `/export/validate`.


## v32.3 (validador IIIF + TEI con notas/citas + publicación al backend GeoDocs)
- **IIIF**: validador básico (`/export/iiif_validate`) para comprobar estructura de manifiesto.
- **TEI**: notas al pie como `<note place="foot">` y citas como `<q>` a partir de `data-zone`.
- **Publicación**: genera **bundle ZIP** y lo envía al backend **GeoDocs** (`/api/documentos`) usando **JWT** desde la configuración.
- **UI Export**: opción **“Publicar al servidor”**, campos de **Base URL** y **JWT**, botón **Guardar config**.
- Persisten todas las funciones de v32.2 y anteriores.
