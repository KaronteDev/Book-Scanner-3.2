# Análisis de Bases de Datos SQLite en el Proyecto

## Bases de Datos Encontradas

### 1. **geodocs.db** (Base de datos GLOBAL)
- **Ubicación**: `data/geodocs.db`
- **Usada por**: 
  - `utils/db_manager.py` (función `init_global_db()`)
  - `scripts/migrations/migrate_versions.py`
  - `scripts/migrations/migrate_schema_v3.py`
  - `scripts/migrations/migrate_db.py`
  
- **Esquema (Tablas)**:
  - `archivos` - Instituciones/Repositorios (ISAD(G) 5.3)
  - `fondos` - Fondos documentales (ISAD(G), EAD)
  - `etiquetas` - Materias/Descriptores controlados
  - `proyectos` - Proyectos de digitalización (Dublin Core + ISAD(G))
  - `proyecto_etiquetas` - Tabla puente N:M
  - `settings` - Configuración de la aplicación (key/value)

- **Propósito**: Base de datos global/maestra que gestiona archivos, fondos documentales, proyectos de digitalización y configuración general del sistema. Sigue estándares archivísticos (ISAD(G), Dublin Core, EAD).

---

### 2. **geodocs_scanner.db** (Base de datos SCANNER)
- **Ubicación**: Raíz del proyecto (`geodocs_scanner.db`)
- **Usada por**:
  - `web_viewer/server.py` - Servidor Flask para visualización web
  - `scanner_gui.py` - Interfaz de escaneo
  - `processor_queue.py` - Cola de procesamiento OCR
  - `modules/scheduler.py`
  - Archivos legacy en `old/` y `papelera/`

- **Esquema (Tablas)**:
  - `project` - Proyectos de escaneo
  - `document` - Documentos escaneados
  - `page` - Páginas individuales con OCR
  - `annotation` - Anotaciones geográficas/metadata
  - `glossary` - Glosarios terminológicos
  - `glossary_term` - Términos de glosarios
  - `style_template` - Plantillas de estilo editorial
  - `abbrev_style` - Estilos de abreviaturas
  - `person` - Entidades de personas (prosopografía)
  - `place` - Entidades de lugares (geografía)
  - `version_history` - Historial de cambios
  - Otras tablas para revisiones, diff, publicación, TTS, etc.

- **Propósito**: Base de datos operacional del escáner y el visor web. Contiene datos de escaneo, OCR, anotaciones, glosarios, plantillas de estilo y toda la información editorial/operativa.

---

### 3. **project.db** (Base de datos POR PROYECTO)
- **Ubicación**: Dentro de cada carpeta de proyecto (`{proyecto}/project.db`)
- **Usada por**:
  - `utils/db_manager.py` (función `init_project_db()`)
  - Scripts de migración

- **Esquema (Tablas)**:
  - `document` - Metadatos del documento (Dublin Core extendido + METS)
  - `page` - Páginas/Folios (PREMIS Object Entity)
  - `structure` - Estructura lógica del documento
  - `annotation` - Anotaciones
  - `person` - Personas mencionadas
  - `place` - Lugares mencionados
  - `event` - Eventos
  - `technical_metadata` - Metadatos técnicos PREMIS
  - `preservation_event` - Eventos de preservación
  - `rights` - Información de derechos
  - `file_format` - Formatos de archivo
  - Otras tablas para relaciones entre entidades

- **Propósito**: Base de datos específica de cada proyecto individual, con metadatos detallados siguiendo estándares de preservación digital (Dublin Core, PREMIS, METS). Permite que cada proyecto sea autónomo.

---

### 4. **papelera/Prueba1/oo/project.db**
- **Ubicación**: `papelera/Prueba1/oo/project.db`
- **Estado**: Archivo de prueba/descartado en la papelera
- **Acción**: Puede eliminarse

---

## Análisis de Duplicidad y Propuesta de Unificación

### Problema Principal: Duplicidad entre `geodocs.db` y `geodocs_scanner.db`

Existen **DOS bases de datos globales** que causan confusión:

1. **geodocs.db** - Orientada a gestión archivística (ISAD(G), fondos, archivos)
2. **geodocs_scanner.db** - Orientada a operaciones de escaneo y edición

**Tablas duplicadas entre ambas**:
- `project` / `proyectos` - Ambas guardan información de proyectos
- `document` - Presente en ambas con esquemas diferentes

### Inconsistencias Detectadas

1. **Nomenclatura**: `proyectos` (geodocs.db) vs `project` (geodocs_scanner.db)
2. **Propósito mezclado**: geodocs.db es más "archivística", geodocs_scanner.db es más "operativa"
3. **Datos dispersos**: Los proyectos de escaneo están en scanner.db pero deberían registrarse en geodocs.db
4. **Sincronización**: No existe mecanismo para mantener coherencia entre ambas

---

## Propuesta de Unificación

### OPCIÓN 1: Unificar en una sola base de datos global ✅ RECOMENDADA

**Estructura propuesta**: `geodocs.db` (única base de datos global)

```
geodocs.db/
├── Módulo Archivístico (ya existe)
│   ├── archivos
│   ├── fondos
│   ├── proyectos (renombrar a 'proyectos_archivisticos')
│   ├── etiquetas
│   └── proyecto_etiquetas
│
├── Módulo de Escaneo/Edición (migrar desde geodocs_scanner.db)
│   ├── scanner_project (proyectos de escaneo)
│   ├── scanner_document
│   ├── scanner_page
│   ├── annotation
│   ├── glossary
│   ├── glossary_term
│   ├── style_template
│   ├── abbrev_style
│   ├── person
│   ├── place
│   └── version_history
│
└── Módulo Común
    └── settings
```

**Ventajas**:
- ✅ Elimina duplicidad
- ✅ Centraliza configuración
- ✅ Facilita consultas cruzadas (ej: enlazar proyecto de escaneo con fondo archivístico)
- ✅ Backup/migración más simple
- ✅ Menor complejidad del código

**Desventajas**:
- ⚠️ Requiere migración de datos
- ⚠️ Posible acoplamiento excesivo

---

### OPCIÓN 2: Mantener separación pero clarificar roles

**Estructura propuesta**:

1. **geodocs.db** - Base de datos MAESTRA (solo lectura desde scanner)
   - Gestión de archivos, fondos, catálogo general
   - Proyectos archivísticos de alto nivel
   
2. **geodocs_scanner.db** → Renombrar a **geodocs_work.db** - Base de datos OPERATIVA
   - Todas las operaciones de escaneo/edición/OCR
   - Referencia a proyectos en geodocs.db mediante FK
   - Tablas de trabajo: pages, annotations, glossaries, etc.

**Ventajas**:
- ✅ Separación clara de responsabilidades
- ✅ geodocs.db puede ser "read-only" para el scanner
- ✅ Menor impacto en código existente

**Desventajas**:
- ⚠️ Sigue habiendo dos bases de datos
- ⚠️ Requiere sincronización entre ambas
- ⚠️ Complejidad adicional en consultas cruzadas

---

### OPCIÓN 3: Eliminar geodocs.db y usar solo geodocs_scanner.db ❌ NO RECOMENDADA

**Motivo**: Se perdería la estructura archivística bien diseñada (ISAD(G), fondos, archivos) que está en geodocs.db.

---

## Recomendación Final

### 🎯 **OPCIÓN 1: Unificar en geodocs.db**

**Plan de migración**:

1. **Fase 1**: Añadir tablas de scanner a `geodocs.db`
   - Migrar esquema de geodocs_scanner.db a geodocs.db con prefijos claros
   - Crear vistas de compatibilidad si es necesario

2. **Fase 2**: Migrar datos
   - Exportar datos de geodocs_scanner.db
   - Importar a geodocs.db con transformaciones necesarias
   - Crear Foreign Keys entre módulos (ej: scanner_project → fondo_id)

3. **Fase 3**: Actualizar código
   - Cambiar todas las referencias de `geodocs_scanner.db` a `geodocs.db`
   - Unificar funciones de conexión (eliminar duplicados)
   - Actualizar `web_viewer/server.py`, `scanner_gui.py`, `processor_queue.py`

4. **Fase 4**: Eliminar geodocs_scanner.db
   - Hacer backup antes de eliminar
   - Actualizar documentación

**Tiempo estimado**: 4-6 horas de trabajo

---

## Sobre project.db (bases de datos por proyecto)

**Mantener** - No debe unificarse con la base de datos global.

**Motivo**: 
- Cada proyecto es una unidad autónoma exportable
- Permite distribuir proyectos individuales sin llevar toda la base de datos global
- Sigue el patrón de "archivo por proyecto" común en sistemas de preservación digital
- Compatible con estándares como METS/PREMIS que esperan metadatos empaquetados

**Mejora sugerida**:
- Añadir campo `global_project_id` en project.db para enlazar con el registro en geodocs.db
- Esto permite mantener autonomía pero con referencia al sistema global

---

## Archivos a Modificar para Unificación

### Archivos principales que usan geodocs_scanner.db:
1. `web_viewer/server.py` - 40+ conexiones
2. `scanner_gui.py` - Interfaz principal
3. `processor_queue.py` - Cola OCR
4. `modules/scheduler.py` - Programador
5. Archivos legacy (pueden ignorarse o eliminarse)

### Archivos que usan geodocs.db:
1. `utils/db_manager.py` - Gestor principal
2. Scripts de migración en `scripts/migrations/`

### Cambio global necesario:
```python
# ANTES
DB = BASE_DIR / "geodocs_scanner.db"

# DESPUÉS
DB = BASE_DIR / "data" / "geodocs.db"
```

---

## Conclusión

La duplicidad actual entre `geodocs.db` y `geodocs_scanner.db` es problemática y debe resolverse. La **unificación en geodocs.db** es la mejor opción para:

- Reducir complejidad
- Centralizar datos
- Facilitar mantenimiento
- Mejorar coherencia del sistema

Las bases de datos `project.db` individuales deben **mantenerse separadas** ya que sirven un propósito diferente (autonomía de proyectos).
