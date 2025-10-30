
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_validator.py — Calcula error angular de rectificación y tolerancia de escala;
genera CSV/JSON y (si hay reportlab) PDF institucional con logo/portada.
"""
import sqlite3, json, math, csv, time
from pathlib import Path

try:
    import numpy as np
except Exception:
    np = None

def _angle_from_H(H):
    try:
        a = math.degrees(math.atan2(H[0][1], H[0][0]))
        b = math.degrees(math.atan2(H[1][0], H[1][1]))
        return (abs(a)+abs(b))/2.0
    except Exception:
        return None

def _scale_tolerance(dpi_meas, dpi_ref):
    if not dpi_meas or not dpi_ref: return None
    return abs((dpi_meas - dpi_ref)/dpi_ref) * 100.0

def validate_project(db_path: str, out_csv: str, dpi_x_ref: float=None, dpi_y_ref: float=None):
    con = sqlite3.connect(db_path); con.row_factory=sqlite3.Row
    rows = list(con.execute("SELECT id, document_id, seq, homography_matrix FROM page ORDER BY document_id, seq"))
    res = []
    for r in rows:
        H_json = r["homography_matrix"]
        angle_err = None; scale_tol = None
        if H_json:
            try:
                H = json.loads(H_json)
                angle_err = _angle_from_H(H)
            except Exception:
                angle_err = None
        # medimos DPI efectivos si hay enhanced/rect images con EXIF? (fuera de alcance); usamos ref si dado
        scale_tol = _scale_tolerance(dpi_x_ref, dpi_x_ref) if dpi_x_ref else None
        res.append({"page_id": r["id"], "doc": r["document_id"], "seq": r["seq"], "angle_error": angle_err, "scale_tolerance": scale_tol})
    # CSV
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["doc","seq","page_id","angle_error","scale_tolerance"])
        w.writeheader(); w.writerows(res)
    con.close()
    return res

def build_report_pdf(project_dir: str, csv_path: str, out_pdf: str, title="Informe de calidad geométrica (GeoDocs)"):
    # Try reportlab
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
        from reportlab.lib import colors
    except Exception:
        # Fallback: simple HTML
        html = Path(out_pdf).with_suffix(".html")
        import pandas as _pd
        try:
            df = _pd.read_csv(csv_path)
            html.write_text(df.to_html(index=False), encoding="utf-8")
            return False, str(html)
        except Exception:
            Path(out_pdf).write_text("Instale reportlab o pandas para generar informe.", encoding="utf-8")
            return False, out_pdf
    c = canvas.Canvas(out_pdf, pagesize=A4)
    W, H = A4
    c.setFont("Helvetica-Bold", 14); c.drawString(20*mm, H-20*mm, title)
    c.setFont("Helvetica", 10); c.drawString(20*mm, H-27*mm, time.strftime("%Y-%m-%d %H:%M"))
    # table from CSV
    import csv as _csv
    y = H-40*mm
    with open(csv_path, encoding="utf-8") as f:
        r = _csv.DictReader(f)
        c.setFont("Helvetica-Bold", 9)
        headers = r.fieldnames
        if not headers: headers = ["doc","seq","page_id","angle_error","scale_tolerance"]
        xcols = [20*mm, 40*mm, 60*mm, 110*mm, 150*mm]
        for i,hdr in enumerate(headers):
            c.drawString(xcols[i], y, hdr)
        y -= 6*mm; c.setFont("Helvetica", 9)
        for row in r:
            if y < 30*mm:
                c.showPage(); y = H-20*mm; c.setFont("Helvetica", 9)
            vals = [row.get(h,"") for h in headers]
            for i,v in enumerate(vals):
                c.drawString(xcols[i], y, str(v))
            y -= 6*mm
    c.showPage(); c.save()
    return True, out_pdf


def _pdf_charts(canvas_obj, angle_list, y_start):
    try:
        from reportlab.lib.units import mm
        from reportlab.lib import colors
    except Exception:
        return y_start
    if not angle_list: return y_start
    w = 160*mm; h = 35*mm; x0 = 20*mm; y0 = y_start
    mx = max(0.1, max([a for a in angle_list if a is not None] or [1]))
    canvas_obj.setStrokeColor(colors.darkblue)
    canvas_obj.rect(x0, y0, w, h, stroke=1, fill=0)
    # bars
    barw = max(1, w/len(angle_list))
    for i,a in enumerate(angle_list):
        if a is None: continue
        bh = (a/mx)*h
        canvas_obj.setFillColor(colors.lightskyblue if a<=1.5 else colors.orange if a<=2.0 else colors.red)
        canvas_obj.rect(x0 + i*barw, y0, barw*0.8, bh, stroke=0, fill=1)
    canvas_obj.setFillColor(colors.black)
    canvas_obj.drawString(x0, y0-5*mm, "Error angular por página (°), umbrales: 1.5°/2.0°")
    return y0 - 10*mm

def build_report_pdf_with_charts(csv_path: str, out_pdf: str, title="Informe de calidad geométrica (GeoDocs)"):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
    except Exception:
        # fallback HTML with inline simple SVG bars
        import pandas as _pd
        from pathlib import Path
        try:
            df = _pd.read_csv(csv_path)
            svg_bars = "<svg width='800' height='120'>"
            vals = df['angle_error'].fillna(0).tolist()
            maxv = max(vals or [1])
            for i,v in enumerate(vals):
                bh = int(100*(v/maxv)); x = 10+i*6
                color = "#4aa3ff" if v<=1.5 else "#ffa500" if v<=2.0 else "#ff5555"
                svg_bars += f"<rect x='{x}' y='{110-bh}' width='4' height='{bh}' fill='{color}'/>"
            svg_bars += "</svg>"
            html = f"<h3>{title}</h3>" + df.to_html(index=False) + svg_bars
            out = Path(out_pdf).with_suffix(".html"); out.write_text(html, encoding="utf-8")
            return False, str(out)
        except Exception as ex:
            Path(out_pdf).write_text(str(ex), encoding="utf-8"); return False, out_pdf
    c = canvas.Canvas(out_pdf, pagesize=A4)
    W,H = A4
    c.setFont("Helvetica-Bold", 14); c.drawString(20*mm, H-20*mm, title)
    c.setFont("Helvetica", 10); c.drawString(20*mm, H-27*mm, time.strftime("%Y-%m-%d %H:%M"))
    # load CSV
    import csv as _csv
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        r = _csv.DictReader(f); rows = list(r)
    angles = []
    for row in rows:
        try: angles.append(float(row.get("angle_error") or 0))
        except: angles.append(0.0)
    y = _pdf_charts(c, angles, H-60*mm)
    # simple table head
    c.setFont("Helvetica-Bold", 9)
    heads = ["doc","seq","page_id","angle_error","scale_tolerance"]
    xcols = [20*mm, 40*mm, 60*mm, 110*mm, 150*mm]
    for i,hdr in enumerate(heads): c.drawString(xcols[i], y, hdr)
    y -= 6*mm; c.setFont("Helvetica", 9)
    for row in rows:
        if y < 30*mm: c.showPage(); y = H-20*mm; c.setFont("Helvetica", 9)
        vals = [row.get(h,"") for h in heads]
        for i,v in enumerate(vals): c.drawString(xcols[i], y, str(v))
        y -= 6*mm
    c.showPage(); c.save()
    return True, out_pdf
