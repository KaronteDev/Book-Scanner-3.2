#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import json
from pathlib import Path
from datetime import datetime
import sqlite3

def export_ead3_xml(db_path: Path, doc_id: int, out_path: Path):
    """Exporta un documento en formato EAD3 XML."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # Obtener metadatos del documento
    cur.execute("""
        SELECT d.id, d.title, d.autor, d.fecha_text, d.signatura,
               d.tema, d.tipo, d.lugar, d.idioma, d.derechos,
               d.resumen, d.nivel_descripcion, d.productor,
               d.alcance_y_contenido, a.nombre, f.nombre
        FROM document d
        LEFT JOIN archivo a ON a.id=d.archivo_id
        LEFT JOIN fondo f ON f.id=d.fondo_id
        WHERE d.id=?""", (doc_id,))
    row = cur.fetchone()
    if not row:
        con.close()
        return False
        
    (did, title, autor, fecha, signa, tema, tipo, lugar, idioma,
     derechos, resumen, nivel, productor, alcance, arch, fond) = row
    
    # Construir XML
    root = ET.Element("ead")
    archdesc = ET.SubElement(root, "archdesc")
    did_el = ET.SubElement(archdesc, "did")
    
    # Metadatos principales
    if title:
        ET.SubElement(did_el, "unittitle").text = title
    if signa:
        ET.SubElement(did_el, "unitid").text = signa
    if autor:
        ET.SubElement(did_el, "origination").text = autor
    if fecha:
        ET.SubElement(did_el, "unitdate").text = fecha
    if nivel:
        ET.SubElement(did_el, "physdesc").text = nivel
    if arch:
        ET.SubElement(did_el, "repository").text = arch
    if fond:
        ET.SubElement(did_el, "collection").text = fond
    if lugar:
        ET.SubElement(did_el, "geogname").text = lugar
    if idioma:
        ET.SubElement(did_el, "langmaterial").text = idioma
    if derechos:
        ET.SubElement(did_el, "accessrestrict").text = derechos
    
    # Scope and content
    scope = ET.SubElement(archdesc, "scopecontent")
    if alcance or resumen or tema:
        scope.text = " | ".join([x for x in [alcance, resumen, tema] if x])
    
    # Pages as components
    dsc = ET.SubElement(archdesc, "dsc")
    for (seq, path) in con.execute(
        """SELECT seq, processed_path
           FROM page
           WHERE document_id=?
           ORDER BY seq""", (doc_id,)):
        c = ET.SubElement(dsc, "c")
        ET.SubElement(c, "did")
        ET.SubElement(c, "unittitle").text = f"Página {seq:04d}"
        if path:
            ET.SubElement(c, "dao", {"href": path})
    
    # Write to file
    tree = ET.ElementTree(root)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    con.close()
    return True

def export_dc_jsonld(db_path: Path, doc_id: int, out_path: Path):
    """Exporta un documento en formato Dublin Core JSON-LD."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    cur.execute("""
        SELECT d.title, d.autor, d.fecha_text, d.signatura,
               d.tema, d.tipo, d.lugar, d.idioma, d.derechos,
               d.resumen, a.nombre, f.nombre
        FROM document d 
        LEFT JOIN archivo a ON a.id=d.archivo_id 
        LEFT JOIN fondo f ON f.id=d.fondo_id
        WHERE d.id=?""", (doc_id,))
    r = cur.fetchone()
    con.close()
    
    if not r:
        return False
        
    (title, autor, fecha, signa, tema, tipo, lugar, idioma,
     derechos, resumen, arch, fond) = r
    
    obj = {
        "@context": "http://schema.org",
        "@type": "CreativeWork",
        "name": title,
        "creator": autor,
        "dateCreated": fecha,
        "description": resumen or tema,
        "inLanguage": idioma,
        "locationCreated": lugar,
        "copyrightNotice": derechos,
        "identifier": signa,
        "genre": tipo,
        "provider": {
            "@type": "Organization",
            "name": arch
        },
        "isPartOf": {
            "@type": "Collection",
            "name": fond
        }
    }
    
    out_path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    return True

def export_tei_xml(db_path: Path, doc_id: int, out_path: Path):
    """Exporta un documento en formato TEI XML."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # Get document metadata
    cur.execute("""
        SELECT title, autor, fecha_text, lugar, idioma, resumen
        FROM document 
        WHERE id=?""", (doc_id,))
    doc = cur.fetchone()
    if not doc:
        con.close()
        return False
        
    title, autor, fecha, lugar, idioma, resumen = doc
    
    # Build XML
    root = ET.Element("TEI", {"xmlns":"http://www.tei-c.org/ns/1.0"})
    teiHeader = ET.SubElement(root, "teiHeader")
    
    # File description
    fileDesc = ET.SubElement(teiHeader, "fileDesc")
    titleStmt = ET.SubElement(fileDesc, "titleStmt")
    ET.SubElement(titleStmt, "title").text = title or ""
    if autor:
        ET.SubElement(titleStmt, "author").text = autor
    
    pubStmt = ET.SubElement(fileDesc, "publicationStmt")
    ET.SubElement(pubStmt, "publisher").text = "GeoDocs"
    
    sourceDesc = ET.SubElement(fileDesc, "sourceDesc")
    ET.SubElement(sourceDesc, "p").text = resumen or ""
    
    # Text with pages
    text = ET.SubElement(root, "text")
    body = ET.SubElement(text, "body")
    
    # Pages as divs with OCR
    for (seq, txt, pdf) in con.execute("""
        SELECT seq, ocr_txt_path, ocr_pdf_path
        FROM page
        WHERE document_id=?
        ORDER BY seq""", (doc_id,)):
        div = ET.SubElement(body, "div", {"n": str(seq)})
        if txt and Path(txt).exists():
            try:
                content = Path(txt).read_text(encoding="utf-8")
                ET.SubElement(div, "p").text = content
            except:
                ET.SubElement(div, "p").text = ""
        else:
            ET.SubElement(div, "p").text = ""
    
    ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)
    con.close()
    return True

def export_mets_alto(db_path: Path, doc_id: int, out_dir: Path):
    """Exporta un documento en formato METS/ALTO."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # METS file
    mets = ET.Element("mets")
    fileSec = ET.SubElement(mets, "fileSec")
    filesEl = ET.SubElement(fileSec, "fileGrp", {"USE": "OCR"})
    
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""
        SELECT seq, processed_path, ocr_txt_path
        FROM page
        WHERE document_id=?
        ORDER BY seq""", (doc_id,))
    rows = cur.fetchall()
    
    # Process each page
    for seq, img_path, ocr_path in rows:
        # ALTO file for this page
        alto = ET.Element("alto", 
            {"xmlns":"http://www.loc.gov/standards/alto/ns-v4#"})
        layout = ET.SubElement(alto, "Layout")
        page = ET.SubElement(layout, "Page", {"ID": f"p{seq}"})
        textblock = ET.SubElement(page, "PrintSpace")
        
        # Get OCR text if available
        if ocr_path and Path(ocr_path).exists():
            try:
                text = Path(ocr_path).read_text(encoding="utf-8")
            except:
                text = ""
        else:
            text = ""
            
        # Create text blocks
        tb = ET.SubElement(textblock, "TextBlock", {"ID": f"tb{seq}"})
        tl = ET.SubElement(tb, "TextLine", {"ID": f"tl{seq}"})
        ET.SubElement(tl, "String", {"CONTENT": text[:10000]})
        
        # Save ALTO file
        alto_path = out_dir / f"alto_{seq:04d}.xml"
        ET.ElementTree(alto).write(alto_path, encoding="utf-8",
                                 xml_declaration=True)
        
        # Add to METS
        ET.SubElement(filesEl, "file",
                     {"ID": f"f{seq}", "SEQ": str(seq)}).text = str(alto_path)
    
    # Save METS file
    mets_path = out_dir / "mets.xml"
    ET.ElementTree(mets).write(mets_path, encoding="utf-8",
                              xml_declaration=True)
    con.close()
    return True

def export_project_report(db_path: Path, doc_id: int, out_pdf: Path,
                         logo_path: Path=None):
    """Genera un informe PDF del proyecto."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
    except Exception:
        raise
        
    c = canvas.Canvas(str(out_pdf), pagesize=A4)
    W, H = A4
    y = H - 2*cm
    
    # Header with logo
    if logo_path and logo_path.exists():
        try:
            c.drawImage(str(logo_path), 2*cm, y-1.5*cm,
                       width=2*cm, height=1.5*cm,
                       preserveAspectRatio=True, mask='auto')
        except:
            pass
            
    c.setFont("Helvetica-Bold", 16)
    c.drawString(4.4*cm, y-0.5*cm, "GeoDocs — Informe de Proyecto")
    y -= 2.2*cm
    
    # Load document metadata
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""
        SELECT d.title, d.autor, d.fecha_text, d.tipo,
               d.signatura, d.tema, d.etiquetas, d.lugar,
               d.idioma, d.derechos, a.nombre, f.nombre,
               p.base_dir, d.resumen
        FROM document d
        LEFT JOIN project p ON p.id=d.project_id
        LEFT JOIN archivo a ON a.id=d.archivo_id
        LEFT JOIN fondo f ON f.id=d.fondo_id
        WHERE d.id=?""", (doc_id,))
    row = cur.fetchone()
    
    if not row:
        con.close()
        return False
        
    (title, autor, fecha, tipo, signatura, tema, etiquetas,
     lugar, idioma, derechos, archivo_nombre, fondo_nombre,
     base_dir, resumen) = row
    
    # Summary block
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, "Resumen")
    c.setFont("Helvetica", 10)
    y -= 0.6*cm
    
    text = c.beginText(2*cm, y)
    text.textLines(resumen or "-")
    c.drawText(text)
    
    y -= (min(6, (len((resumen or '').split())//20)+1))*0.5*cm
    y -= 0.4*cm
    
    # Metadata block
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, "Metadatos")
    y -= 0.6*cm
    c.setFont("Helvetica", 10)
    
    meta_lines = [
        ("Título", title),
        ("Autor", autor),
        ("Fecha", fecha),
        ("Tipo", tipo),
        ("Archivo", archivo_nombre),
        ("Fondo", fondo_nombre),
        ("Signatura", signatura),
        ("Tema", tema),
        ("Etiquetas", etiquetas),
        ("Lugar", lugar),
        ("Idioma", idioma),
        ("Derechos", derechos),
        ("Carpeta", base_dir)
    ]
    
    for k,v in meta_lines:
        c.drawString(2*cm, y, f"{k}: {v or '-'}")
        y -= 0.45*cm
        if y < 4*cm:
            c.showPage()
            y = H - 2*cm
    
    # Stats
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, "Estadísticas")
    y -= 0.6*cm
    c.setFont("Helvetica", 10)
    
    cur.execute("""
        SELECT COUNT(*),
               SUM(CASE WHEN ocr_txt_path IS NOT NULL THEN 1 ELSE 0 END)
        FROM page
        WHERE document_id=?""", (doc_id,))
    n_pages, n_ocr = cur.fetchone()
    
    c.drawString(2*cm, y, f"Páginas: {n_pages or 0} | OCR: {n_ocr or 0}")
    y -= 0.5*cm
    
    # Thumbnails (just list filenames)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, "Páginas")
    y -= 0.6*cm
    c.setFont("Helvetica", 9)
    
    for (seq, processed_path, hashv) in cur.execute("""
        SELECT seq, processed_path, hash_sha256
        FROM page
        WHERE document_id=?
        ORDER BY seq""", (doc_id,)):
        c.drawString(2*cm, y,
            f"{seq:04d} — {processed_path or '(sin archivo)'}  [{hashv or 'sin hash'}]")
        y -= 0.38*cm
        if y < 2*cm:
            c.showPage()
            y = H - 2*cm
    
    con.close()
    c.showPage()
    c.save()
    return True