#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
finger_removal.py — Detección y eliminación de dedos y soportes en imágenes de documentos
"""
from pathlib import Path
from typing import Optional, List, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    cv2 = None
    np = None
    HAS_CV2 = False


def detect_fingers_and_supports(
    image_path: Path,
    return_mask: bool = False
) -> Tuple[bool, Optional[any]]:
    """
    Detectar dedos y soportes en imagen de documento.
    
    Estrategia:
    1. Detección de color de piel (rango HSV)
    2. Detección de objetos oscuros en bordes (soportes negros)
    3. Análisis de contornos en márgenes
    
    Args:
        image_path: Ruta de la imagen
        return_mask: Si retornar la máscara de detección
    
    Returns:
        (has_fingers: bool, mask: Optional[np.ndarray])
    """
    if not HAS_CV2:
        return False, None
    
    if not image_path.exists():
        return False, None
    
    try:
        # Cargar imagen
        img = cv2.imread(str(image_path))
        if img is None:
            return False, None
        
        h, w = img.shape[:2]
        
        # Crear máscara combinada
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        
        # 1. Detección de color de piel (dedos)
        skin_mask = detect_skin_color(img)
        if skin_mask is not None:
            combined_mask = cv2.bitwise_or(combined_mask, skin_mask)
        
        # 2. Detección de objetos oscuros en bordes (soportes)
        support_mask = detect_dark_edges(img)
        if support_mask is not None:
            combined_mask = cv2.bitwise_or(combined_mask, support_mask)
        
        # Verificar si hay detecciones significativas
        total_pixels = h * w
        detected_pixels = np.count_nonzero(combined_mask)
        detection_ratio = detected_pixels / total_pixels
        
        # Si más del 0.5% de la imagen son dedos/soportes
        has_detection = detection_ratio > 0.005
        
        if return_mask:
            return has_detection, combined_mask
        else:
            return has_detection, None
        
    except Exception as e:
        print(f"Error detectando dedos: {e}")
        return False, None


def detect_skin_color(img: any) -> Optional[any]:
    """
    Detectar regiones de color de piel en la imagen.
    
    Args:
        img: Imagen BGR de OpenCV
    
    Returns:
        Máscara binaria con regiones de piel
    """
    if not HAS_CV2:
        return None
    
    try:
        # Convertir a HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Rangos de color de piel en HSV (calibrado para luz natural)
        # Rango 1: tonos cálidos
        lower1 = np.array([0, 20, 70], dtype=np.uint8)
        upper1 = np.array([20, 255, 255], dtype=np.uint8)
        
        # Rango 2: tonos más oscuros
        lower2 = np.array([0, 15, 40], dtype=np.uint8)
        upper2 = np.array([25, 255, 255], dtype=np.uint8)
        
        # Crear máscaras
        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        
        # Combinar máscaras
        mask = cv2.bitwise_or(mask1, mask2)
        
        # Eliminar ruido (morfología)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Filtrar solo regiones en los bordes (donde suelen estar los dedos)
        h, w = mask.shape
        border_width = int(min(h, w) * 0.15)  # 15% de los bordes
        
        # Crear máscara de bordes
        edge_mask = np.zeros_like(mask)
        edge_mask[:border_width, :] = 255  # Borde superior
        edge_mask[-border_width:, :] = 255  # Borde inferior
        edge_mask[:, :border_width] = 255  # Borde izquierdo
        edge_mask[:, -border_width:] = 255  # Borde derecho
        
        # Aplicar máscara de bordes
        mask = cv2.bitwise_and(mask, edge_mask)
        
        return mask
        
    except Exception as e:
        print(f"Error en detección de piel: {e}")
        return None


def detect_dark_edges(img: any, threshold: int = 40) -> Optional[any]:
    """
    Detectar objetos oscuros en los bordes (soportes, marcos negros).
    
    Args:
        img: Imagen BGR de OpenCV
        threshold: Umbral de oscuridad (0-255)
    
    Returns:
        Máscara binaria con regiones oscuras en bordes
    """
    if not HAS_CV2:
        return None
    
    try:
        # Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        h, w = gray.shape
        border_width = int(min(h, w) * 0.1)  # 10% de los bordes
        
        # Crear máscara de regiones oscuras
        _, dark_mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
        
        # Crear máscara de bordes
        edge_mask = np.zeros_like(dark_mask)
        edge_mask[:border_width, :] = 255
        edge_mask[-border_width:, :] = 255
        edge_mask[:, :border_width] = 255
        edge_mask[:, -border_width:] = 255
        
        # Aplicar máscara de bordes
        result = cv2.bitwise_and(dark_mask, edge_mask)
        
        # Limpiar ruido
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel, iterations=1)
        
        return result
        
    except Exception as e:
        print(f"Error en detección de bordes oscuros: {e}")
        return None


def remove_fingers_inpainting(
    image_path: Path,
    output_path: Optional[Path] = None,
    auto_detect: bool = True,
    mask: Optional[any] = None
) -> bool:
    """
    Eliminar dedos y soportes usando inpainting de OpenCV.
    
    Args:
        image_path: Ruta de la imagen original
        output_path: Ruta de salida (None = sobrescribir)
        auto_detect: Si detectar automáticamente (True) o usar mask proporcionada
        mask: Máscara de regiones a eliminar (si auto_detect=False)
    
    Returns:
        True si se procesó correctamente
    """
    if not HAS_CV2:
        print("OpenCV no disponible")
        return False
    
    if not image_path.exists():
        print(f"Imagen no encontrada: {image_path}")
        return False
    
    try:
        # Cargar imagen
        img = cv2.imread(str(image_path))
        if img is None:
            return False
        
        # Obtener máscara
        if auto_detect:
            has_fingers, detected_mask = detect_fingers_and_supports(image_path, return_mask=True)
            if not has_fingers or detected_mask is None:
                print("No se detectaron dedos/soportes")
                return False
            mask = detected_mask
        
        if mask is None:
            print("No se proporcionó máscara")
            return False
        
        # Aplicar inpainting
        # Método TELEA (rápido) o NS (más preciso pero lento)
        inpainted = cv2.inpaint(img, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
        
        # Guardar resultado
        output = output_path or image_path
        cv2.imwrite(str(output), inpainted)
        
        return True
        
    except Exception as e:
        print(f"Error en inpainting: {e}")
        return False


def crop_to_content(
    image_path: Path,
    output_path: Optional[Path] = None,
    margin: int = 20
) -> bool:
    """
    Recortar imagen eliminando bordes vacíos (método alternativo al inpainting).
    
    Args:
        image_path: Ruta de la imagen
        output_path: Ruta de salida (None = sobrescribir)
        margin: Píxeles de margen a conservar
    
    Returns:
        True si se recortó correctamente
    """
    if not HAS_CV2:
        return False
    
    if not image_path.exists():
        return False
    
    try:
        # Cargar imagen
        img = cv2.imread(str(image_path))
        if img is None:
            return False
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Binarizar (Otsu automático)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return False
        
        # Obtener bounding box del contenido
        x, y, w, h = cv2.boundingRect(np.vstack(contours))
        
        # Aplicar margen
        h_img, w_img = img.shape[:2]
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(w_img - x, w + 2 * margin)
        h = min(h_img - y, h + 2 * margin)
        
        # Recortar
        cropped = img[y:y+h, x:x+w]
        
        # Guardar
        output = output_path or image_path
        cv2.imwrite(str(output), cropped)
        
        return True
        
    except Exception as e:
        print(f"Error en crop: {e}")
        return False
