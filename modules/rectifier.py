
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rectifier.py — Normalización de perspectiva previa al OCR usando cuadrilátero de página.
- Detecta el contorno mayor cuasi-rectangular (la página)
- Warp a rectángulo destino; si hay DPI calibrados, intenta tamaño destino en mm reales
"""
from pathlib import Path
import json

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

def _approx_quad(cnt, eps_ratio=0.02):
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, eps_ratio*peri, True)
    if len(approx) == 4:
        return approx.reshape(-1,2)
    return None

def _order_points(pts):
    rect = np.zeros((4,2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def detect_page_quad(image_bgr):
    if cv2 is None:
        return None
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, None, iterations=2)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]
    for c in cnts:
        quad = _approx_quad(c, eps_ratio=0.02)
        if quad is not None and cv2.contourArea(c) > 3000:
            return _order_points(quad.astype("float32"))
    return None

def warp_to_rect(image_bgr, quad_pts, dpi_x=None, dpi_y=None):
    """
    Si hay DPI calibrados, usamos un tamaño destino aproximado en px por 10mm bloques,
    manteniendo la relación de aspecto del quad. En ausencia de DPI, se usa el tamaño del quad.
    """
    if cv2 is None:
        return image_bgr, None
    tl,tr,br,bl = quad_pts
    wA = np.linalg.norm(br - bl)
    wB = np.linalg.norm(tr - tl)
    hA = np.linalg.norm(tr - br)
    hB = np.linalg.norm(tl - bl)
    width = int(round(max(wA, wB)))
    height = int(round(max(hA, hB)))
    if dpi_x and dpi_y:
        # objetivo: bloques de ~10mm en X e Y para escalar a mm reales
        px_per_10mm_x = (dpi_x/25.4)*10.0
        px_per_10mm_y = (dpi_y/25.4)*10.0
        # redondear tamaño al múltiplo más cercano de 10mm
        width = int(max(200, round(width / px_per_10mm_x) * px_per_10mm_x))
        height = int(max(200, round(height / px_per_10mm_y) * px_per_10mm_y))
    dst = np.array([[0,0],[width-1,0],[width-1,height-1],[0,height-1]], dtype="float32")
    H = cv2.getPerspectiveTransform(quad_pts.astype("float32"), dst)
    warped = cv2.warpPerspective(image_bgr, H, (width, height))
    return warped, H

def rectify_image_to_mm(input_path: str, output_path: str, dpi_x=None, dpi_y=None):
    if cv2 is None:
        raise RuntimeError("OpenCV no disponible (rectifier)")
    img = cv2.imread(str(input_path))
    if img is None:
        raise RuntimeError("No se pudo leer la imagen para rectificar")
    quad = detect_page_quad(img)
    if quad is None:
        # fallback: copiar
        import shutil; shutil.copyfile(input_path, output_path); return output_path, None
    warped, H = warp_to_rect(img, quad, dpi_x, dpi_y)
    ok = cv2.imwrite(str(output_path), warped)
    if not ok:
        raise RuntimeError("No se pudo guardar la imagen rectificada")
    return output_path, H


def homography_sidecar(out_path: str, H):
    """Save homography to sidecar TXT and return JSON string."""
    try:
        import numpy as _np, json as _j
        side = out_path + "_H.txt"
        _np.savetxt(side, H)
        return _j.dumps(H.tolist())
    except Exception:
        return None
