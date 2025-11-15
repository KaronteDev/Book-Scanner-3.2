# Guía de Importación Masiva de Archivos desde CSV

## Descripción

Esta funcionalidad permite importar múltiples archivos (instituciones) desde un archivo CSV, facilitando la carga masiva de datos.

## Uso

### 1\. Generar Plantilla

1.  Abrir el módulo **"📁 Proyectos y Metadatos"**
2.  Ir a la pestaña **"🏛 Archivos"**
3.  Hacer clic en el botón **"📄 Plantilla CSV"**
4.  Guardar el archivo en la ubicación deseada

### 2\. Rellenar el CSV

Abrir el archivo CSV con un editor de hojas de cálculo (Excel, LibreOffice Calc) o un editor de texto.

**IMPORTANTE**: El archivo debe usar **punto y coma (;)** como separador.

#### Campos disponibles:

| Campo | Obligatorio | Descripción | Ejemplo |
| --- | --- | --- | --- |
| `nombre` | ✓ | Nombre oficial de la institución | Archivo Histórico Provincial de Madrid |
| `siglas` |   | Siglas o acrónimo | AHPM |
| `codigo_identificacion` |   | Código oficial (ISIL, etc.) | ES-28079-AHPM |
| `tipo_institucion` |   | Tipo de institución | Archivo Público, Biblioteca, Museo |
| `direccion_completa` |   | Dirección postal completa | Calle de Ramón de la Cruz, 28 |
| `ciudad` |   | Ciudad | Madrid |
| `provincia` |   | Provincia o región | Madrid |
| `pais` |   | País | España |
| `contacto_responsable` |   | Nombre del responsable | Juan Pérez García |
| `email` |   | Correo electrónico | info@ahpm.es |
| `telefono` |   | Teléfono de contacto | +34 91 234 5678 |
| `url_web` |   | Página web oficial | https://www.ahpm.es |
| `horario_atencion` |   | Horario de atención al público | Lunes a Viernes: 9:00-14:00 |
| `condiciones_acceso` |   | Condiciones de acceso | Acceso libre previa solicitud |
| `coordenadas_geograficas` |   | Coordenadas GPS (lat,lon) | 40.4168,-3.7038 |
| `notas` |   | Notas adicionales | Archivo fundado en 1850 |

### 3\. Importar el CSV

1.  En la pestaña **"🏛 Archivos"**, hacer clic en **"📥 Importar CSV"**
2.  Seleccionar el archivo CSV rellenado
3.  **Elegir el carácter separador**:
    *   **Punto y coma (;)** - Por defecto, recomendado
    *   **Coma (,)** - CSV estándar internacional
    *   **Barra vertical (|)** - Alternativa cuando hay comas en los datos
    *   **Tabulación (TAB)** - Para archivos TSV
4.  El sistema procesará el archivo y mostrará un resumen:
    *   Número de archivos importados exitosamente
    *   Lista de errores (si los hubiera)

## Formato del Archivo

*   **Codificación**: UTF-8 con BOM (UTF-8-SIG)
*   **Separador**: Configurable (punto y coma, coma, barra vertical o tabulación)
*   **Primera fila**: Encabezados (no modificar)
*   **Filas siguientes**: Datos de cada archivo

## Separadores Disponibles

### Punto y coma (;) - Recomendado

*   **Ventaja**: Compatible con Excel en español
*   **Uso**: Cuando los datos contienen comas
*   **Ejemplo**: `Madrid;España;+34 91 234 5678`

### Coma (,) - Estándar

*   **Ventaja**: Estándar internacional CSV
*   **Uso**: Cuando los datos no contienen comas
*   **Ejemplo**: `Madrid,España,+34 91 234 5678`

### Barra vertical (|)

*   **Ventaja**: Raramente aparece en los datos
*   **Uso**: Cuando los datos contienen comas y punto y coma
*   **Ejemplo**: `Madrid|España|+34 91 234 5678`

### Tabulación (TAB)

*   **Ventaja**: Invisible, formato TSV
*   **Uso**: Archivos exportados desde bases de datos
*   **Ejemplo**: `Madrid[TAB]España[TAB]+34 91 234 5678`

## Ejemplo de Registro

```
nombre;siglas;codigo_identificacion;tipo_institucion;direccion_completa;ciudad;provincia;pais;contacto_responsable;email;telefono;url_web;horario_atencion;condiciones_acceso;coordenadas_geograficas;notas
Archivo Histórico Provincial de Madrid;AHPM;ES-28079-AHPM;Archivo Público;Calle de Ramón de la Cruz, 28;Madrid;Madrid;España;Juan Pérez García;info@ahpm.es;+34 91 234 5678;https://www.ahpm.es;Lunes a Viernes: 9:00-14:00;Acceso libre previa solicitud;40.4168,-3.7038;Archivo fundado en 1850
```

## Validaciones

*   El campo **nombre** es obligatorio
*   Las filas vacías se omiten automáticamente
*   Si hay errores, se muestra un informe detallado

## Recomendaciones

1.  **Probar primero**: Importar un CSV pequeño de prueba antes de importar muchos registros
2.  **Revisar el formato**: Asegurarse de que el separador sea punto y coma (;)
3.  **Codificación correcta**: Guardar el archivo en UTF-8 para caracteres especiales (ñ, tildes)
4.  **Backup**: Hacer una copia de seguridad de la base de datos antes de importaciones masivas

## Archivos de Ejemplo

*   **plantilla\_archivos.csv**: Plantilla con 3 ejemplos reales listos para usar

## Solución de Problemas

### Error: "nombre es obligatorio"

*   Asegurarse de que la columna `nombre` tenga valor en todas las filas

### Error al leer CSV

*   Verificar que el separador seleccionado coincida con el del archivo
*   Si el archivo usa punto y coma (;), seleccionar "Punto y coma" en el diálogo
*   Si el archivo usa comas (,), seleccionar "Coma" en el diálogo

### Caracteres extraños (�, ã, etc.)

*   Guardar el archivo CSV con codificación UTF-8 con BOM
*   En Excel: "Guardar como" → "CSV UTF-8 (delimitado por comas)"
*   Luego cambiar el separador si es necesario

### Columnas desalineadas

*   El separador seleccionado no coincide con el del archivo
*   Abrir el archivo en un editor de texto y verificar qué carácter separa las columnas
*   Seleccionar el separador correcto al importar

### Datos incompletos en una columna

*   Si los datos contienen el mismo carácter que el separador, usar otro separador
*   Ejemplo: Si hay comas en direcciones, usar punto y coma (;) como separador

## Compatibilidad

*   Compatible con archivos generados por Excel, LibreOffice Calc, Google Sheets
*   Funciona en Windows, Linux y macOS