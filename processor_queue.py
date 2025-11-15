
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
processor_queue.py - cola sencilla de procesamiento (OCR, ajustes).
Se ejecuta desde el módulo de escaneo o manualmente.
"""
import json, sqlite3, time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "data" / "geodocs.db"
OCR_CONF = BASE_DIR / "ocr_config.json"

def db():
    return sqlite3.connect(DB)

def load_conf():
    try:
        return json.loads(OCR_CONF.read_text(encoding="utf-8"))
    except Exception:
        return {"default_lang":"spa+eng","psm":3,"oem":3}

def do_ocr_for_page(row, conf):
    # row: (id, processed_path)
    pid, img = row
    if not img or not Path(img).exists():
        return None
    text = None
    try:
        import pytesseract
        from PIL import Image
        cfg = f'--psm {int(conf.get("psm",3))} --oem {int(conf.get("oem",3))}'
        lang = conf.get("default_lang","spa+eng")
        text = pytesseract.image_to_string(Image.open(img), lang=lang, config=cfg)
    except Exception as ex:
        text = None
    return text

def run_once(limit=10):
    conf = load_conf()
    with db() as con:
        cur = con.cursor()
        rows = list(cur.execute("SELECT id, processed_path FROM scanner_page WHERE IFNULL(status,'pending')!='done' ORDER BY id LIMIT ?", (limit,)))
        for r in rows:
            pid, _ = r
            cur.execute("UPDATE scanner_page SET status='processing' WHERE id=?", (pid,))
            con.commit()
            text = do_ocr_for_page(r, conf)
            if text is not None:
                cur.execute("UPDATE scanner_page SET ocr_text=?, status='done' WHERE id=?", (text, pid))
            else:
                cur.execute("UPDATE scanner_page SET status='error' WHERE id=?", (pid,))
            con.commit()

if __name__ == "__main__":
    # Ejecuta una pasada
    run_once(limit=50)
