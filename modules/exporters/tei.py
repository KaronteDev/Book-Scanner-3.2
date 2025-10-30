
from lxml import etree
import sqlite3
from bs4 import BeautifulSoup
from pathlib import Path

def export_tei(db_path: str, document_id: int, out_dir: str, include_zones=False):
    con = sqlite3.connect(db_path); con.row_factory=sqlite3.Row
    doc = con.execute("SELECT id, title, author, date FROM document WHERE id=?", (document_id,)).fetchone()
    pages = con.execute("SELECT id, seq, ocr_html FROM page WHERE document_id=? ORDER BY seq", (document_id,)).fetchall()
    con.close()
    TEI = etree.Element("TEI", nsmap=None)
    teiHeader = etree.SubElement(TEI, "teiHeader")
    fileDesc = etree.SubElement(teiHeader, "fileDesc")
    titleStmt = etree.SubElement(fileDesc, "titleStmt")
    etree.SubElement(titleStmt, "title").text = (doc["title"] if doc and doc["title"] else f"Documento {document_id}")
    if doc and doc["author"]:
        etree.SubElement(titleStmt, "author").text = doc["author"]
    pubStmt = etree.SubElement(fileDesc, "publicationStmt")
    etree.SubElement(pubStmt, "p").text = "Generado por GeoDocs Scanner v32.3"
    sourceDesc = etree.SubElement(fileDesc, "sourceDesc")
    etree.SubElement(sourceDesc, "p").text = "Fuente: proyecto GeoDocs"
    text = etree.SubElement(TEI, "text"); body = etree.SubElement(text, "body")
    for p in pages:
        pb = etree.SubElement(body, "pb"); pb.set("n", str(p["seq"]))
        div = etree.SubElement(body, "div")
        html = p["ocr_html"] or ""
        soup = BeautifulSoup(html, "lxml")
        zones = soup.find_all(attrs={"data-zone": True}) if include_zones else []
        if zones:
            for el in zones:
                zone = (el.get("data-zone") or "").strip()
                zdiv = etree.SubElement(div, "div"); zdiv.set("type", zone)
                text_content = el.get_text(" ", strip=True)
                if zone == "footnote":
                    note = etree.SubElement(zdiv, "note"); note.set("place", "foot"); note.text = text_content
                elif zone == "quote":
                    q = etree.SubElement(zdiv, "q"); q.text = text_content
                else:
                    etree.SubElement(zdiv, "p").text = text_content
        plain = soup.get_text(" ", strip=True)
        if plain:
            etree.SubElement(div, "p").text = plain
    xml = etree.tostring(TEI, pretty_print=True, encoding="utf-8", xml_declaration=True)
    outp = Path(out_dir); outp.mkdir(parents=True, exist_ok=True)
    tei_path = outp / f"tei_doc_{document_id}.xml"
    tei_path.write_bytes(xml); return str(tei_path)
