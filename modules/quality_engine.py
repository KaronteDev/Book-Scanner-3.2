
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quality_engine.py — Lote automático de control de calidad OCR + visual.
- Recorre páginas del proyecto (o toda la DB si no se pasa doc_id)
- Calcula métricas visuales/textuales básicas y guarda overlay si es posible
- Inserta registros en audit_log
"""
from pathlib import Path
import sqlite3, json, time, re

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

DB = None  # set at runtime
BASE_DIR = None

def set_env(db_path: Path, base_dir: Path):
    global DB, BASE_DIR
    DB, BASE_DIR = Path(db_path), Path(base_dir)

def db():
    return sqlite3.connect(DB)

def _ensure_columns():
    with db() as con:
        con.execute("ALTER TABLE page ADD COLUMN visual_score REAL"); 
    # ignore if already exists
    with db() as con:
        con.execute("ALTER TABLE page ADD COLUMN ocr_error_map TEXT")
    with db() as con:
        con.execute("ALTER TABLE page ADD COLUMN avg_confidence REAL")
    with db() as con:
        con.execute("ALTER TABLE page ADD COLUMN last_quality_check TEXT")
    with db() as con:
        con.execute("ALTER TABLE page ADD COLUMN visual_issues INTEGER")

def _avg_conf_from_text(txt: str) -> float:
    # Heurística mínima si no hay hOCR: penaliza si hay muchos signos raros
    if not txt:
        return 0.0
    weird = len(re.findall(r'[^0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ¿?¡!,.:\-\s]', txt))
    ratio = 1.0 - min(0.5, weird / max(1, len(txt)))
    return round(60 + 40*ratio, 2)  # 60..100

def analyze_page_basic(image_path: Path, ocr_text: str):
    # Si OpenCV está disponible, genera overlay simple (sin hOCR real)
    avg_conf = _avg_conf_from_text(ocr_text)
    visual_score = avg_conf  # placeholder
    overlay_path = None
    if cv2 and image_path and image_path.exists():
        img = cv2.imread(str(image_path))
        if img is not None:
            overlay = img.copy()
            alpha = 0.35
            # Dibujar una banda de color según score global (demo)
            color = (0,255,0) if avg_conf>90 else (0,255,255) if avg_conf>75 else (0,0,255)
            h, w = img.shape[:2]
            cv2.rectangle(overlay, (0,0), (w, int(0.07*h)), color, -1)
            blended = cv2.addWeighted(overlay, alpha, img, 1-alpha, 0)
            overlay_path = str(image_path).rsplit('.',1)[0] + "_errors.jpg"
            cv2.imwrite(overlay_path, blended)
    error_map = {"zones": [], "avg_conf": avg_conf, "critical": 0}
    return avg_conf, visual_score, overlay_path, error_map

def run_quality_batch(doc_id: int = None, limit: int = None):
    _ensure_columns()
    start = time.time()
    processed = 0
    with db() as con:
        con.row_factory = sqlite3.Row
        q = "SELECT p.id, p.document_id, p.seq, p.processed_path, p.ocr_text FROM page p"
        args = []
        if doc_id is not None:
            q += " WHERE p.document_id=?"
            args.append(doc_id)
        q += " ORDER BY p.document_id, p.seq"
        if limit:
            q += " LIMIT ?"; args.append(limit)
        rows = list(con.execute(q, tuple(args)))
    for r in rows:
        pid = r["id"]
        img = Path(r["processed_path"]) if r["processed_path"] else None
        # Rectifier: apply perspective normalization with calibrated DPI if available
        rectified = None
        dpi_x = dpi_y = None
        try:
            # read calibration.json at project root
            from pathlib import Path as _P
            proj = _P(__file__).resolve().parents[1]
            cal = proj / 'calibration.json'
            if cal.exists():
                import json as _j
                c = _j.loads(cal.read_text(encoding='utf-8'))
                dpi_x = c.get('dpi_x'); dpi_y = c.get('dpi_y')
            if img and img.exists():
                from modules.rectifier import rectify_image_to_mm
                out_rect = str(img).rsplit('.',1)[0] + '_rect.jpg'
                rectified, _H = rectify_image_to_mm(str(img), out_rect, dpi_x, dpi_y)
                # store homography as sidecar + for DB
                try:
                    from modules.rectifier import homography_sidecar
                    H_json = homography_sidecar(out_rect, _H) if _H is not None else None
                except Exception:
                    H_json = None
                img = _P(rectified)
        except Exception:
            pass
        txt = r["ocr_text"] or ""
        avg_conf, visual_score, overlay_path, error_map = analyze_page_basic(img, txt)
        try:
            from modules.image_enhancer import enhance_image
            if img and img.exists():
                out_enh = str(img).rsplit('.',1)[0] + '_enhanced.jpg'
                enh_path, meta = enhance_image(str(img), out_enh, None, None, {})
            else:
                enh_path, meta = None, None
        except Exception:
            enh_path, meta = None, None
        with db() as con:
            cur = con.cursor()
            cur.execute("""UPDATE page 
                           SET avg_confidence=?, visual_score=?, ocr_error_map=?, last_quality_check=datetime('now'), visual_issues=?, enhanced_image_path=?, enhancement_method=?, homography_matrix=? 
                           WHERE id=?""",
                        (avg_conf, visual_score, json.dumps(error_map, ensure_ascii=False), 0, enh_path, (meta or {}).get('method') if meta else None, H_json, pid))
            cur.execute("""INSERT INTO audit_log(action, user, role, page_id, details) 
                           VALUES (?,?,?,?,?)""",
                        ("batch_quality_analysis", "system", None, pid, json.dumps({"avg_conf":avg_conf,"visual_score":visual_score})))
            con.commit()
        processed += 1
    elapsed = round(time.time()-start, 2)
    return {"processed": processed, "seconds": elapsed}
