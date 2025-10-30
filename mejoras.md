## **Mejoras implementadas ✓**

### **1\. Detección mejorada de dedos**

*   **YCrCb + HSV**: Detección dual usando dos espacios de color para mayor precisión
*   **Filtrado por área**: Elimina ruido, solo detecta regiones entre 0.1% y 15% del área total
*   **Morfología avanzada**: Operaciones de cierre/apertura más agresivas con kernels más grandes
*   **Dilatación de máscara**: Expande las áreas detectadas para cubrir mejor los bordes
*   **Filtrado de contornos**: Solo mantiene contornos significativos (dedos reales)

### **2\. Calibrador visual interactivo**

**Características:**

*   **Vista previa en tiempo real**: Muestra feed de la cámara a 30 FPS
*   **Rectángulo de calibración ajustable**: Arrastra las 4 esquinas para definir el área de captura
*   **Adaptación automática al formato**: Al seleccionar A3/A4/A5/A6, el rectángulo ajusta su aspect ratio
*   **Cálculo de DPI en tiempo real**: Muestra DPI actual basado en dimensiones físicas vs píxeles
*   **Información de resolución**: Muestra dimensiones en píxeles del área seleccionada

**Panel de control:**

*   Formatos de papel con dimensiones (A3: 297x420mm, A4: 210x297mm, etc.)
*   Selector de DPI objetivo (150, 200, 300, 400, 600)
*   Opciones de procesamiento automático
*   Botones: Guardar, Restablecer, Cancelar

**Persistencia:**

*   Guarda área calibrada en [camera\_calibration.json](vscode-file://vscode-app/m:/Users/Recursos/AppData/Local/Programs/Microsoft%20VS%20Code/resources/app/out/vs/code/electron-browser/workbench/workbench.html)
*   Identificador único por cámara + proyecto
*   Carga automática al conectar cámara calibrada

### **3\. Aplicación del área calibrada**

*   **Recorte inteligente**: Al capturar, primero recorta al área calibrada antes de procesar
*   **Procesamiento optimizado**: Solo procesa el área de interés, más rápido
*   **DPI correctos**: Mantiene la relación píxel/mm según calibración

**Flujo de trabajo:**

1.  Usuario abre "Calibrar"
2.  Arrastra esquinas del rectángulo verde sobre el documento
3.  Ajusta formato y DPI
4.  Guarda calibración
5.  Todas las capturas posteriores usan automáticamente esa área

**Ventajas:**

*   ✓ Elimina fondos y elementos no deseados
*   ✓ Optimiza resolución según formato del documento
*   ✓ Reduce tamaño de archivo
*   ✓ Procesamiento más rápido (menos píxeles)