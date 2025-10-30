
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calibration.py — Calibración guiada con hoja A3/A4/A5/A6 para estimar DPI y corregir perspectiva.
- Detecta el contorno cuadrilátero más grande (la hoja estándar sobre el plano)
- Estima DPI (pix/mm) a partir de dimensiones reales (ISO 216) y guarda en JSON y SQLite.
- Devuelve matriz de homografía para aplanado (opcional) y grid para overlay.
"""
from pathlib import Path
import json, math, sqlite3, datetime

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

ISO_SIZES_MM = {
    "A3": (420.0, 297.0),
    "A4": (297.0, 210.0),
    "A5": (210.0, 148.0),
    "A6": (148.0, 105.0),
}

def _approx_quad(cnt, eps_ratio=0.02):
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, eps_ratio*peri, True)
    if len(approx) == 4:
        return approx.reshape(-1,2)
    return None

def _order_points(pts):
    # order as tl, tr, br, bl
    rect = np.zeros((4,2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def detect_sheet_quad(image_bgr):
    """Return ordered quad (tl,tr,br,bl) in pixel coords or None"""
    if cv2 is None:
        return None
    img = image_bgr.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, None, iterations=2)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]
    for c in cnts:
        quad = _approx_quad(c, eps_ratio=0.02)
        if quad is not None and cv2.contourArea(c) > 5000:
            return _order_points(quad.astype("float32"))
    return None

def estimate_dpi_from_quad(image_bgr, quad_pts, size_name):
    """Compute DPIx,DPIy using known ISO size; returns dpi_x,dpi_y and homography to rect"""
    Wmm, Hmm = ISO_SIZES_MM[size_name]  # width,height in mm (landscape orientation expectation)
    # Compute pixel width/height along quad
    tl,tr,br,bl = quad_pts
    px_w = (np.linalg.norm(tr-tl) + np.linalg.norm(br-bl)) / 2.0
    px_h = (np.linalg.norm(bl-tl) + np.linalg.norm(br-tr)) / 2.0
    # Choose orientation that best matches aspect ratio
    mm_w, mm_h = Wmm, Hmm
    if px_h > px_w and Hmm < Wmm:  # portrait
        mm_w, mm_h = Hmm, Wmm
    # DPI = pixels / inches ; inches = mm / 25.4
    dpi_x = px_w / (mm_w/25.4)
    dpi_y = px_h / (mm_h/25.4)
    # Homography to a rect of mm_w x mm_h scaled to pixels at same dpi
    dst_w = int(round(dpi_x * (mm_w/25.4)))
    dst_h = int(round(dpi_y * (mm_h/25.4)))
    dst = np.array([[0,0],[dst_w-1,0],[dst_w-1,dst_h-1],[0,dst_h-1]], dtype="float32")
    H = cv2.getPerspectiveTransform(quad_pts.astype("float32"), dst)
    return dpi_x, dpi_y, H, (dst_w, dst_h)

def apply_homography(image_bgr, H, size_px):
    if cv2 is None:
        return image_bgr
    w,h = size_px[0], size_px[1]
    warped = cv2.warpPerspective(image_bgr, H, (w,h))
    return warped

def save_calibration(project_dir: Path, doc_id: int, dpi_x: float, dpi_y: float, size_name: str, db_path: Path):
    project_dir = Path(project_dir)
    calib = {
        "document_id": doc_id,
        "dpi_x": round(float(dpi_x),2),
        "dpi_y": round(float(dpi_y),2),
        "size": size_name,
        "date": datetime.datetime.utcnow().isoformat()+"Z"
    }
    (project_dir/"calibration.json").write_text(json.dumps(calib, ensure_ascii=False, indent=2), encoding="utf-8")
    # Persist to SQLite
    con = sqlite3.connect(str(db_path)); cur = con.cursor()
    cur.execute("UPDATE document SET dpi_x=?, dpi_y=?, calibrated_size=?, calibration_date=datetime('now') WHERE id=?", (calib["dpi_x"], calib["dpi_y"], size_name, doc_id))
    con.commit(); con.close()
    return calib

def run_calibration(image_path: str, size_name: str, project_dir: str, db_path: str, doc_id: int):
    assert size_name in ISO_SIZES_MM, "Tamaño no soportado"
    if cv2 is None:
        raise RuntimeError("OpenCV no disponible para calibración")
    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError("No se pudo leer la imagen para calibración")
    quad = detect_sheet_quad(img)
    if quad is None:
        raise RuntimeError("No se detectó un cuadrilátero de hoja. Asegúrese de capturar la A3/A4/A5/A6 completa.")
    dpi_x, dpi_y, H, dst_size = estimate_dpi_from_quad(img, quad, size_name)
    calib = save_calibration(Path(project_dir), doc_id, dpi_x, dpi_y, size_name, Path(db_path))
    # generar previsualización rectificada opcional
    try:
        warped = apply_homography(img, H, dst_size)
        out = Path(project_dir) / f"calibration_rect_{size_name}.jpg"
        cv2.imwrite(str(out), warped)
        calib["rectified_preview"] = str(out)
    except Exception:
        pass
    return calib
