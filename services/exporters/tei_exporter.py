from lxml import etree
from pathlib import Path
from typing import Any


def export_tei(book: Any, path: str) -> str:
    """Genera TEI-XML básico con header y divs por página."""
    NSMAP = {None: "http://www.tei-c.org/ns/1.0"}
    tei = etree.Element("TEI", nsmap=NSMAP)
    header = etree.SubElement(tei, "teiHeader")
    file_desc = etree.SubElement(header, "fileDesc")
    title_stmt = etree.SubElement(file_desc, "titleStmt")
    etree.SubElement(title_stmt, "title").text = getattr(book, 'title', 'Sin título')
    publication_stmt = etree.SubElement(file_desc, "publicationStmt")
    etree.SubElement(publication_stmt, "p").text = "Generado por GeoDocs ExportService"
    source_desc = etree.SubElement(file_desc, "sourceDesc")
    etree.SubElement(source_desc, "p").text = "Capturas locales"

    text = etree.SubElement(tei, "text")
    body = etree.SubElement(text, "body")
    for idx, ref in enumerate(getattr(book, 'pages', [])):
        div = etree.SubElement(body, "div", attrib={"n": str(idx+1)})
        etree.SubElement(div, "p").text = f"Página {idx+1}: {ref}"
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(etree.tostring(tei, encoding="utf-8", pretty_print=True, xml_declaration=True))
    return str(p)
