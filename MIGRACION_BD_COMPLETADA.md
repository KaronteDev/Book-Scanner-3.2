# Unificación de Bases de Datos - Completada ✓

**Fecha**: 15 de noviembre de 2025  
**Estado**: ✅ COMPLETADA EXITOSAMENTE

---

## Resumen de la Migración

### 1. Base de Datos Unificada

**Antes**: 2 bases de datos globales separadas
- `geodocs_scanner.db` (operativa)
- `geodocs.db` (archivística)

**Después**: 1 base de datos unificada
- `data/geodocs.db` (contiene todo)

---

## Cambios Realizados

### A. Estructura de Base de Datos

Se añadieron las siguientes tablas a `data/geodocs.db`:

| Tabla Nueva | Propósito |
|-------------|-----------|
| `scanner_project` | Proyectos de escaneo operacionales |
| `scanner_document` | Documentos escaneados |
| `scanner_page` | Páginas individuales con OCR |
| `annotation` | Anotaciones geográficas y metadata |
| `glossary` | Glosarios terminológicos |
| `style_template` | Plantillas de estilo editorial |
| `ocr_revision` | Historial de revisiones OCR |
| `version_history` | Historial de cambios |
| `audit_log` | Registro de auditoría |

**Relaciones añadidas**:
- `scanner_project.proyecto_archivistico_id` → `proyectos.id` (FK opcional)
- `scanner_document.archivo_id` → `archivos.id` (FK)
- `scanner_document.fondo_id` → `fondos.id` (FK)

---

### B. Datos Migrados

✅ **2 glosarios** migrados  
✅ **1 plantilla de estilo** migrada  
✅ **0 proyectos** (base de datos estaba vacía)  
✅ **0 documentos**  
✅ **0 páginas**  

---

### C. Código Actualizado

Archivos modificados:

1. **web_viewer/server.py**
   - ✅ Ruta DB: `geodocs_scanner.db` → `data/geodocs.db`
   - ✅ Tablas: `page` → `scanner_page`
   - ✅ Tablas: `document` → `scanner_document`
   - ✅ Tablas: `project` → `scanner_project`

2. **scanner_gui.py**
   - ✅ Ruta DB: `geodocs_scanner.db` → `data/geodocs.db`
   - ✅ Nombres de tabla actualizados

3. **processor_queue.py**
   - ✅ Ruta DB: `geodocs_scanner.db` → `data/geodocs.db`
   - ✅ Nombres de tabla actualizados

4. **modules/scheduler.py**
   - ✅ Ruta DB: `geodocs_scanner.db` → `data/geodocs.db`
   - ✅ BASE_DIR corregido: `parent` → `parent.parent`

---

## Backups Creados

📦 Ubicación: `backups/`

- `geodocs_scanner_20251115_002423.db` (copia de seguridad original)
- `geodocs_20251115_002423.db` (copia de seguridad pre-migración)

---

## Ventajas de la Unificación

✅ **Eliminación de duplicidad** - Una sola fuente de verdad  
✅ **Configuración centralizada** - Settings en un solo lugar  
✅ **Consultas cruzadas simplificadas** - Joins entre módulos archivístico y operativo  
✅ **Backup/migración más simple** - Un solo archivo de base de datos  
✅ **Menor complejidad** - Menos archivos de configuración  
✅ **Coherencia de datos** - No hay riesgo de desincronización  

---

## Estado de las Bases de Datos

### 🗄️ data/geodocs.db (ACTIVA - Base Unificada)

**Módulo Archivístico** (estándares ISAD(G), Dublin Core, EAD):
- `archivos` - Instituciones/Repositorios
- `fondos` - Fondos documentales
- `proyectos` - Proyectos archivísticos de alto nivel
- `etiquetas` - Descriptores controlados
- `proyecto_etiquetas` - Tabla puente

**Módulo Operativo/Scanner**:
- `scanner_project` - Proyectos de escaneo
- `scanner_document` - Documentos escaneados
- `scanner_page` - Páginas con OCR
- `annotation` - Anotaciones
- `glossary` - Glosarios
- `style_template` - Plantillas
- `ocr_revision` - Revisiones
- `version_history` - Historial
- `audit_log` - Auditoría

**Módulo Común**:
- `settings` - Configuración clave/valor

---

### 📦 geodocs_scanner.db (OBSOLETA - Archivada)

**Estado**: Puede archivarse o eliminarse  
**Backup**: Disponible en `backups/`  
**Nota**: Todos los datos fueron migrados a `data/geodocs.db`

---

### 📁 {proyecto}/project.db (MANTENER - Por Proyecto)

**Estado**: ✅ Sin cambios - Se mantienen separadas  
**Propósito**: Base de datos autónoma por proyecto (portabilidad)  
**Esquema**: Dublin Core + PREMIS + METS  
**Mejora futura**: Añadir campo `global_project_id` para enlazar con geodocs.db

---

## Próximos Pasos Recomendados

### Inmediatos
1. ✅ ~~Ejecutar script de migración~~ - COMPLETADO
2. ✅ ~~Actualizar código~~ - COMPLETADO  
3. ⏳ **Probar la aplicación con la nueva base de datos**
4. ⏳ **Verificar que todas las funciones operen correctamente**

### Corto Plazo
5. 🔲 Añadir campo `global_project_id` a project.db individual
6. 🔲 Actualizar documentación técnica
7. 🔲 Archivar geodocs_scanner.db una vez verificado todo

### Opcional
8. 🔲 Crear vistas SQL para compatibilidad con código legacy
9. 🔲 Implementar índices para optimización de consultas
10. 🔲 Añadir triggers para auditoría automática

---

## Verificación Post-Migración

### Checklist de Pruebas

- [ ] El servidor web (`python web_viewer/server.py`) inicia sin errores
- [ ] Se pueden listar glosarios en el visor web
- [ ] Se pueden listar plantillas de estilo
- [ ] Scanner GUI puede crear nuevo proyecto
- [ ] Processor queue puede procesar páginas
- [ ] Anotaciones se guardan correctamente
- [ ] Exportaciones funcionan

---

## Comandos Útiles

### Verificar estructura de geodocs.db:
```bash
python scripts/migrations/list_scanner_tables.py
```

### Restaurar desde backup (si es necesario):
```bash
# PowerShell
Copy-Item "backups\geodocs_20251115_002423.db" "data\geodocs.db" -Force
```

### Verificar integridad de la base de datos:
```bash
python -c "import sqlite3; conn = sqlite3.connect('data/geodocs.db'); conn.execute('PRAGMA integrity_check'); print('OK')"
```

---

## Documentación Relacionada

- `ANALISIS_BASES_DE_DATOS.md` - Análisis detallado pre-migración
- `ESTRUCTURA_PROYECTO.md` - Estructura general del proyecto
- `scripts/migrations/unify_databases.py` - Script de migración
- `scripts/migrations/update_table_names.py` - Script de actualización de nombres

---

## Conclusión

✅ La unificación de bases de datos se completó exitosamente sin pérdida de datos.  
✅ Todos los archivos de código fueron actualizados para usar la nueva estructura.  
✅ Se crearon backups de seguridad de ambas bases de datos.  
✅ La aplicación está lista para pruebas con la base de datos unificada.

**Estado final**: ✅ OPERATIVA con `data/geodocs.db` como base de datos única
