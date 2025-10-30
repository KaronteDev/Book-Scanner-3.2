
from pathlib import Path
import sqlite3, json

DC_CONTEXT = {
  "@context": {
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/"
  }
}

def export_dc(db_path: str, document_id: int, out_dir: str, to_xml: bool=False):
    con = sqlite3.connect(db_path); con.row_factory=sqlite3.Row
    d = con.execute("SELECT * FROM document WHERE id=?", (document_id,)).fetchone()
    con.close()
    data = {
      "dc:title": d["title"] if d and d["title"] else f"Documento {document_id}",
      "dc:creator": d["author"] if d and "author" in d.keys() else None,
      "dcterms:date": d["date"] if d and "date" in d.keys() else None,
      "dc:type": d["doc_type"] if d and "doc_type" in d.keys() else None,
      "dc:identifier": d["signature"] if d and "signature" in d.keys() else None
    }
    outp = Path(out_dir); outp.mkdir(parents=True, exist_ok=True)
    if to_xml:
      from lxml import etree
      root = etree.Element("metadata", nsmap={"dc":"http://purl.org/dc/elements/1.1/","dcterms":"http://purl.org/dc/terms/"})
      for k,v in data.items():
        if v is None: continue
        ns, tag = k.split(":")
        el = etree.SubElement(root, "{http://purl.org/dc/%s/}%s" % ("elements/1.1" if ns=="dc" else "terms", tag))
        el.text = str(v)
      xml = etree.tostring(root, pretty_print=True, encoding="utf-8", xml_declaration=True)
      path = outp / f"dc_doc_{document_id}.xml"
      path.write_bytes(xml); return str(path)
    else:
      obj = dict(DC_CONTEXT)
      obj.update(data)
      path = outp / f"dc_doc_{document_id}.jsonld"
      path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
      return str(path)
