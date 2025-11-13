\- Hecho. Falta preguntar si se puede usar ttkbootstrap tema superhero

\- Hecho. Añadir configuración de todos los apartados del fichero app\_config.json separados por pestañas

Metadatos y proyectos

\- Hecho. Hay que generar una ventana de configuración global del programa que permita seleccionar la carpeta raíz de trabajo



\- Hecho. Al crear un proyecto se debe solicitar los datos del proyecto en el que se está trabajando además de

\### Campos principales



| Campo | Descripción |

| --- | --- |

| \*\*idproyecto\*\* | Id autonumérico |

| \*\*titulo\*\* | Nombre identificativo |

| \*\*autor\*\* | Persona o entidad creadora |

| \*\*tipo\*\* | Libro, revista, legajo, expediente, etc. |

| \*\*signatura\*\* | Identificador archivístico |

| \*\*archivo\*\* | Centro o institución |

| \*\*fondo\*\* | Fondo documental asociado |

| \*\*tema\*\* | Línea de investigación |

| \*\*etiquetas\*\* | Palabras clave |

| \*\*fecha\*\* | Año o rango temporal |



Hay que generar un crud accesible desde escaner y anotaciones para gestionar los metadatos del proyecto y un botón que acceda a un crud de archivos, fondos y etiquetas desde cada ventana de edición de metadatos, además de añadir una gestión específica de cada una de estas tablas en una opción del menú principal.



\### Tablas complementarias archivos y fondos



\*   \*\*archivos:\*\* idarchivo, nombre, dirección, contacto.

\*   \*\*fondos:\*\* idfondo, nombre, descripción, archivo al que pertenece.

\*   \*\*etiquetas:\*\* idetiqueta, nombre, descripción





El proyecto se almacenará en una carpeta cuyo nombre será formado por las siglas del Archivo y la signatura

Cada proyecto almacena sus datos en esas carpetas independientes dentro del directorio raíz que tiene que estar configurado en la base global `GeoDocs.db`.



##### Archivos Python NO USADOS (pueden eliminarse):

* Raíz del proyecto:
* app.py - Punto de entrada obsoleto (versión v12, actual es v32.3)
* annotator\_gui.py - Lanzador obsoleto que importa gui\_book\_scan\_tk (no se usa en main.py)
* book\_scan\_core.py - Módulo core obsoleto (referenciado solo en archivos old/)
* convert\_export\_only.py - Script de conversión temporal
* convert\_export\_v3.py - Script de conversión temporal
* convert\_messageboxes.py - Script de conversión temporal
* convert\_msgbox\_v2.py - Script de conversión temporal
* convert\_msgbox.py - Script de conversión temporal
* fix\_all\_messageboxes.py - Script de conversión temporal
* fix\_export\_syntax.py - Script de corrección temporal
* fix\_export.py - Script de corrección temporal
* gui\_book\_scan\_tk2.py - GUI monolítica antigua (reemplazada por módulos en gui/)
* launcher.py - Lanzador obsoleto (main.py es el actual)
* processor\_queue.py - Procesador de cola no integrado
* scanner\_gui.py - GUI de scanner standalone básica (reemplazada por scanner\_module.py)
* test\_single\_instance.py - Script de prueba
* test\_scanner.py - Script de prueba (útil pero no parte de producción)
* tmp\_check\_app.py - Script temporal de verificación







##### Pendiente



* Hecho. Crear importación csv de archivos
* Crear importación csv de fondos
