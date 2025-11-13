#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ejemplo_integracion_gui.py — Ejemplos de cómo integrar las nuevas funcionalidades en la GUI

Este archivo muestra fragmentos de código para integrar:
1. Campo Abreviatura en formularios
2. Combo de Tipo de Publicación
3. Botones de Rotación en galería
4. Detección de dedos/soportes
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# =============================================================================
# EJEMPLO 1: Añadir campo Abreviatura en formulario de Proyecto
# =============================================================================

def ejemplo_formulario_proyecto_con_abreviatura(parent_frame):
    """
    Añadir al EditorProyecto en metadata_manager.py
    Después de los campos existentes, añadir:
    """
    
    # En __init__, después de definir otras variables:
    var_abreviatura = tk.StringVar()
    
    # En la construcción del formulario, después de signatura:
    row = 0  # mantener el contador de fila
    
    # ... campos existentes ...
    
    # NUEVO: Abreviatura
    ttk.Label(parent_frame, text="Abreviatura:", width=20, anchor=tk.W).grid(
        row=row, column=0, sticky='w', padx=6, pady=4
    )
    ttk.Entry(parent_frame, textvariable=var_abreviatura, width=30).grid(
        row=row, column=1, sticky='w', padx=6, pady=4
    )
    ttk.Label(
        parent_frame, 
        text="ℹ️", 
        cursor="question_arrow",
        foreground="#666"
    ).grid(row=row, column=2, sticky='w', padx=2)
    # Tooltip: "Código corto nivel 1 de carpetas (ej: LEG1234). Estructura: proyecto/archivo/fondo_signatura"
    
    row += 1
    
    # Actualizar _save() para incluir abreviatura:
    """
    data = dict(
        titulo=titulo,
        signatura=signatura,
        abreviatura=self.var_abreviatura.get().strip() or None,  # NUEVO
        tipo_documento=self.var_tipo.get().strip(),
        ...
    )
    """


# =============================================================================
# EJEMPLO 2: Añadir combo de Tipo de Publicación en formulario de Proyecto
# =============================================================================

def ejemplo_formulario_proyecto_con_tipo_publicacion(parent_frame, base_path):
    """
    Añadir al EditorProyecto en metadata_manager.py
    """
    from utils import db_manager as db
    
    # En __init__:
    var_tipo_pub = tk.StringVar()
    tipos_pub_data = []  # almacenar los tipos para obtener ID después
    
    # Cargar tipos de publicación
    tipos_pub_data = db.list_tipos_publicacion(base_path)
    
    # En la construcción del formulario:
    row = 0
    
    ttk.Label(parent_frame, text="Tipo de Publicación:", width=20, anchor=tk.W).grid(
        row=row, column=0, sticky='w', padx=6, pady=4
    )
    
    # Combo con iconos
    tipo_pub_options = [
        f"{t['icono']} {t['nombre']}" for t in tipos_pub_data
    ]
    
    cmb_tipo_pub = ttk.Combobox(
        parent_frame,
        textvariable=var_tipo_pub,
        values=tipo_pub_options,
        state='readonly',
        width=28
    )
    cmb_tipo_pub.grid(row=row, column=1, sticky='w', padx=6, pady=4)
    
    # Seleccionar primer elemento por defecto
    if tipo_pub_options:
        cmb_tipo_pub.current(0)
    
    row += 1
    
    # En _save(), obtener el ID del tipo seleccionado:
    """
    tipo_pub_id = None
    if self.var_tipo_pub.get():
        # Obtener índice seleccionado
        idx = self.cmb_tipo_pub.current()
        if idx >= 0 and idx < len(self.tipos_pub_data):
            tipo_pub_id = self.tipos_pub_data[idx]['id']
    
    data = dict(
        ...
        tipo_publicacion_id=tipo_pub_id,  # NUEVO
        ...
    )
    """


# =============================================================================
# EJEMPLO 3: Botones de Rotación en Galería
# =============================================================================

def ejemplo_botones_rotacion_en_galeria(parent_frame, project_root, page_id, on_rotated_callback):
    """
    Añadir en scanner_module.py o en visor de imágenes
    """
    from modules.image_rotation import create_rotation_buttons_frame, rotate_page_with_db_update
    
    def on_rotate(angle):
        """Callback cuando se hace clic en un botón de rotación"""
        # Mostrar confirmación
        if not messagebox.askyesno(
            "Rotar Imagen",
            f"¿Rotar imagen {angle}° en sentido {'horario' if angle > 0 else 'antihorario'}?",
            parent=parent_frame
        ):
            return
        
        # Aplicar rotación
        success, msg = rotate_page_with_db_update(
            project_root=project_root,
            page_id=page_id,
            angle=angle,
            regenerate_thumbnail=True
        )
        
        if success:
            messagebox.showinfo("Rotación", msg, parent=parent_frame)
            # Callback para refrescar la vista
            if on_rotated_callback:
                on_rotated_callback()
        else:
            messagebox.showerror("Error", msg, parent=parent_frame)
    
    # Crear frame con botones
    rotation_frame = create_rotation_buttons_frame(
        parent=parent_frame,
        on_rotate_callback=on_rotate,
        padding=5
    )
    rotation_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
    
    return rotation_frame


# =============================================================================
# EJEMPLO 4: Botón de Detección y Limpieza de Dedos/Soportes
# =============================================================================

def ejemplo_deteccion_dedos_en_procesamiento(parent_frame, image_path):
    """
    Añadir en módulo de procesamiento por lotes o en visor de imagen
    """
    from modules.finger_removal import (
        detect_fingers_and_supports,
        remove_fingers_inpainting,
        crop_to_content
    )
    import cv2
    import numpy as np
    from PIL import Image, ImageTk
    
    def detectar_y_mostrar_preview():
        """Detectar dedos y mostrar máscara de preview"""
        has_fingers, mask = detect_fingers_and_supports(
            image_path=Path(image_path),
            return_mask=True
        )
        
        if not has_fingers:
            messagebox.showinfo(
                "Detección",
                "✅ No se detectaron dedos ni soportes en la imagen.",
                parent=parent_frame
            )
            return
        
        # Mostrar preview de la detección
        img = cv2.imread(str(image_path))
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Crear overlay con máscara en rojo semi-transparente
        overlay = img_rgb.copy()
        overlay[mask > 0] = [255, 0, 0]  # Rojo donde hay detección
        
        # Mezclar
        alpha = 0.4
        preview = cv2.addWeighted(img_rgb, 1 - alpha, overlay, alpha, 0)
        
        # Mostrar en ventana de preview
        mostrar_preview_dialog(preview, mask)
    
    def mostrar_preview_dialog(preview_img, mask):
        """Ventana de diálogo con preview y opciones"""
        dialog = tk.Toplevel(parent_frame)
        dialog.title("Detección de Dedos/Soportes")
        dialog.geometry("800x700")
        
        # Convertir a PhotoImage para mostrar
        pil_img = Image.fromarray(preview_img)
        # Redimensionar si es muy grande
        max_size = 750
        if pil_img.width > max_size or pil_img.height > max_size:
            pil_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        photo = ImageTk.PhotoImage(pil_img)
        
        # Canvas para mostrar imagen
        canvas = tk.Canvas(dialog, width=pil_img.width, height=pil_img.height)
        canvas.pack(padx=10, pady=10)
        canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        canvas.image = photo  # mantener referencia
        
        # Etiqueta explicativa
        ttk.Label(
            dialog,
            text="🔴 Regiones detectadas marcadas en rojo",
            font=("Arial", 10)
        ).pack(pady=5)
        
        # Botones de acción
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def aplicar_inpainting():
            """Aplicar limpieza con inpainting"""
            success = remove_fingers_inpainting(
                image_path=Path(image_path),
                mask=mask,
                auto_detect=False
            )
            
            if success:
                messagebox.showinfo(
                    "Limpieza",
                    "✅ Dedos/soportes eliminados correctamente",
                    parent=dialog
                )
                dialog.destroy()
            else:
                messagebox.showerror(
                    "Error",
                    "❌ No se pudo aplicar la limpieza",
                    parent=dialog
                )
        
        def aplicar_recorte():
            """Aplicar recorte automático"""
            success = crop_to_content(
                image_path=Path(image_path),
                margin=20
            )
            
            if success:
                messagebox.showinfo(
                    "Recorte",
                    "✅ Imagen recortada correctamente",
                    parent=dialog
                )
                dialog.destroy()
            else:
                messagebox.showerror(
                    "Error",
                    "❌ No se pudo recortar la imagen",
                    parent=dialog
                )
        
        ttk.Button(
            btn_frame,
            text="✨ Limpiar (Inpainting)",
            command=aplicar_inpainting
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="✂️ Recortar Bordes",
            command=aplicar_recorte
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Cancelar",
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=5)
        
        dialog.grab_set()
    
    # Botón para activar detección
    ttk.Button(
        parent_frame,
        text="🧹 Detectar y Limpiar Dedos/Soportes",
        command=detectar_y_mostrar_preview
    ).pack(pady=10)


# =============================================================================
# EJEMPLO 5: Persistir y Cargar Datos de Captura Anterior
# =============================================================================

def ejemplo_persistencia_captura(parent_frame, base_path):
    """
    Añadir en formulario de captura del scanner
    """
    from utils import db_manager as db
    
    # Variables del formulario (ejemplo)
    var_signatura = tk.StringVar()
    var_autor = tk.StringVar()
    var_fecha = tk.StringVar()
    # ... otras variables
    
    def cargar_datos_anteriores():
        """Cargar datos de la última captura"""
        settings = db.get_last_capture_settings(base_path)
        
        if settings:
            var_signatura.set(settings.get('signatura', ''))
            var_autor.set(settings.get('autor', ''))
            var_fecha.set(settings.get('fecha', ''))
            # ... otros campos
            
            messagebox.showinfo(
                "Datos Cargados",
                "✅ Datos de captura anterior cargados.\nModifica solo la signatura u otros campos necesarios.",
                parent=parent_frame
            )
        else:
            messagebox.showinfo(
                "Sin Datos",
                "No hay datos de captura anterior guardados.",
                parent=parent_frame
            )
    
    def guardar_captura_y_persistir():
        """Al guardar captura, persistir configuración"""
        # Recopilar datos del formulario
        settings = {
            'signatura': var_signatura.get(),
            'autor': var_autor.get(),
            'fecha': var_fecha.get(),
            # ... otros campos
        }
        
        # Guardar para próxima vez
        db.save_capture_settings(base_path, settings)
        
        # Continuar con el guardado normal...
        # (lógica de captura existente)
    
    # Botón para cargar datos anteriores
    ttk.Button(
        parent_frame,
        text="🔄 Usar Datos Anteriores",
        command=cargar_datos_anteriores
    ).pack(side=tk.LEFT, padx=5)
    
    # Nota: Al guardar captura, llamar guardar_captura_y_persistir()


# =============================================================================
# EJEMPLO 6: Añadir Campo Abreviatura en Editor de Archivo
# =============================================================================

def ejemplo_editor_archivo_con_abreviatura(parent_frame):
    """
    Añadir campo abreviatura en EditorArchivo de metadata_manager.py
    """
    
    # En __init__, después de otras variables:
    var_abreviatura = tk.StringVar()
    
    # En construcción de formulario, después de siglas:
    row = 0
    
    # Campo Siglas (existente)
    # ...
    
    # NUEVO: Abreviatura
    ttk.Label(parent_frame, text="Abreviatura:", width=20, anchor=tk.W).grid(
        row=row, column=0, sticky='w', padx=6, pady=4
    )
    ttk.Entry(parent_frame, textvariable=var_abreviatura, width=15).grid(
        row=row, column=1, sticky='w', padx=6, pady=4
    )
    ttk.Label(parent_frame, text="(6 caracteres máx.)", foreground="#666").grid(
        row=row, column=2, sticky='w', padx=6
    )
    row += 1
    
    # Validación en _save():
    """
    abreviatura = self.var_abreviatura.get().strip().upper()
    if len(abreviatura) > 6:
        messagebox.showwarning(
            "Abreviatura",
            "La abreviatura no puede tener más de 6 caracteres",
            parent=self
        )
        return
    
    # Si no se proporciona, se genera automáticamente en create_archivo
    data = dict(
        ...
        abreviatura=abreviatura or None,
        ...
    )
    """


# =============================================================================
# NOTAS DE INTEGRACIÓN
# =============================================================================

"""
INTEGRACIÓN EN METADATA_MANAGER.PY:

1. EditorProyecto.__init__:
   - Añadir: self.var_abreviatura = tk.StringVar()
   - Añadir: self.var_tipo_pub = tk.StringVar()
   - Añadir: self.tipos_pub_data = []

2. EditorProyecto - construcción de formulario:
   - Después de signatura: añadir campo abreviatura (ver ejemplo 1)
   - Después de tipo_documento: añadir combo tipo_publicacion (ver ejemplo 2)

3. EditorProyecto._save():
   - Añadir a dict data:
     abreviatura=self.var_abreviatura.get().strip() or None,
     tipo_publicacion_id=self._get_selected_tipo_pub_id(),

4. EditorProyecto._load_project():
   - Añadir:
     self.var_abreviatura.set(row.get('abreviatura') or '')
     # Seleccionar tipo_publicacion en combo

5. EditorArchivo y EditorFondo:
   - Añadir campo abreviatura similar a ejemplo 6


INTEGRACIÓN EN SCANNER_MODULE.PY:

1. En vista de imagen ampliada:
   - Añadir botones de rotación (ver ejemplo 3)
   - Al rotar, actualizar thumbnail en galería

2. En menú de procesamiento:
   - Añadir botón "Detectar dedos/soportes" (ver ejemplo 4)
   - Mostrar preview antes de aplicar

3. En formulario de captura:
   - Cargar datos anteriores al iniciar (ver ejemplo 5)
   - Guardar datos al capturar


PRUEBAS RECOMENDADAS:

1. Crear proyecto con abreviatura y tipo_publicacion
2. Verificar estructura de carpetas generada
3. Rotar imagen en galería y verificar actualización
4. Probar detección de dedos en imagen de prueba
5. Guardar captura y verificar que siguiente usa datos previos
"""


if __name__ == "__main__":
    print(__doc__)
    print("\n" + "="*80)
    print("Ver código fuente para ejemplos detallados de integración")
    print("="*80)
