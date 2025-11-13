#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
image_rotation.py — Utilidades para rotar imágenes y actualizar metadatos
"""
from pathlib import Path
from typing import Optional, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from utils import db_manager as db


def rotate_image_file(
    image_path: Path,
    angle: int,
    save_as: Optional[Path] = None
) -> bool:
    """
    Rotar archivo de imagen.
    
    Args:
        image_path: Ruta de la imagen
        angle: Ángulo de rotación (90, 180, 270 grados)
        save_as: Ruta donde guardar (None = sobrescribir original)
    
    Returns:
        True si se rotó correctamente
    """
    if not HAS_PIL:
        print("PIL no disponible")
        return False
    
    if not image_path.exists():
        print(f"Imagen no encontrada: {image_path}")
        return False
    
    try:
        # Cargar imagen
        img = Image.open(image_path)
        
        # Normalizar ángulo (PIL usa antihorario, necesitamos horario)
        angle = angle % 360
        
        # Convertir a rotación PIL (inverso)
        if angle == 90:
            pil_angle = 270
        elif angle == 180:
            pil_angle = 180
        elif angle == 270:
            pil_angle = 90
        else:
            pil_angle = 0
        
        # Rotar
        if pil_angle != 0:
            img_rotated = img.rotate(pil_angle, expand=True)
        else:
            img_rotated = img
        
        # Guardar
        output_path = save_as or image_path
        img_rotated.save(output_path)
        
        return True
        
    except Exception as e:
        print(f"Error rotando imagen: {e}")
        return False


def rotate_page_with_db_update(
    project_root: Path,
    page_id: int,
    angle: int,
    regenerate_thumbnail: bool = True
) -> Tuple[bool, str]:
    """
    Rotar página y actualizar BD y thumbnail.
    
    Args:
        project_root: Ruta raíz del proyecto
        page_id: ID de página en project.db
        angle: Ángulo de rotación (90, 180, 270)
        regenerate_thumbnail: Si regenerar el thumbnail
    
    Returns:
        (success: bool, message: str)
    """
    try:
        success = db.rotate_page_image(project_root, page_id, angle)
        
        if success:
            return True, f"Imagen rotada {angle}° correctamente"
        else:
            return False, "No se pudo rotar la imagen"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def detect_page_orientation(image_path: Path) -> int:
    """
    Detectar orientación de página usando OCR o análisis de contornos.
    
    Returns:
        Ángulo de corrección necesario (0, 90, 180, 270)
    """
    # TODO: Implementar detección automática de orientación
    # Opciones:
    # 1. Usar tesseract con --psm 0 (OSD - Orientation and Script Detection)
    # 2. Análisis de características visuales (líneas de texto, histogramas)
    # 3. CNN pre-entrenada para detección de orientación
    
    # Por ahora retornar 0 (sin corrección)
    return 0


def auto_correct_orientation(
    image_path: Path,
    save_corrected: bool = True
) -> Tuple[int, bool]:
    """
    Detectar y corregir automáticamente la orientación de una imagen.
    
    Args:
        image_path: Ruta de la imagen
        save_corrected: Si guardar la imagen corregida
    
    Returns:
        (angle_applied: int, success: bool)
    """
    angle = detect_page_orientation(image_path)
    
    if angle == 0:
        return 0, True
    
    if save_corrected:
        success = rotate_image_file(image_path, angle)
        return angle, success
    else:
        return angle, False


def create_rotation_buttons_frame(
    parent,
    on_rotate_callback,
    **kwargs
) -> 'tk.Frame':
    """
    Crear frame con botones de rotación.
    
    Args:
        parent: Widget padre
        on_rotate_callback: Función callback(angle: int)
        **kwargs: Argumentos adicionales para el Frame
    
    Returns:
        Frame con botones
    """
    import tkinter as tk
    try:
        import ttkbootstrap as ttk
    except ImportError:
        from tkinter import ttk
    
    frame = ttk.Frame(parent, **kwargs)
    
    ttk.Label(frame, text="🔄 Rotar:").pack(side=tk.LEFT, padx=(0, 6))
    
    ttk.Button(
        frame,
        text="↶ 90°",
        command=lambda: on_rotate_callback(270),  # Antihorario
        width=8
    ).pack(side=tk.LEFT, padx=2)
    
    ttk.Button(
        frame,
        text="↷ 90°",
        command=lambda: on_rotate_callback(90),  # Horario
        width=8
    ).pack(side=tk.LEFT, padx=2)
    
    ttk.Button(
        frame,
        text="⤾ 180°",
        command=lambda: on_rotate_callback(180),
        width=8
    ).pack(side=tk.LEFT, padx=2)
    
    return frame
