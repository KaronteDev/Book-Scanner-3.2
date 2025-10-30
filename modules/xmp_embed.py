
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xmp_embed.py — Genera sidecar XMP con metadatos GeoDocs (calibración, DPI, H, métricas).
No requiere dependencias; guarda un .xmp junto a la imagen.
"""
from pathlib import Path
import json, datetime

XMP_TPL = """<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
 <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
  <rdf:Description xmlns:geodocs='https://geodocs.example/ns/1.0/'
    geodocs:generator='GeoDocs Scanner v30.6'
    geodocs:documentId='{doc_id}'
    geodocs:pageId='{page_id}'
    geodocs:dpix='{dpi_x}'
    geodocs:dpiy='{dpi_y}'
    geodocs:calibratedSize='{size}'
    geodocs:homography='{Hjson}'
    geodocs:avgConfidence='{avg_conf}'
    geodocs:visualScore='{visual_score}'
    geodocs:timestamp='{ts}'/>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>
"""

def write_xmp(image_path: str, meta: dict) -> str:
    p = Path(image_path)
    out = p.with_suffix(p.suffix + ".xmp")
    payload = XMP_TPL.format(
        doc_id = meta.get("document_id",""),
        page_id = meta.get("page_id",""),
        dpi_x = meta.get("dpi_x",""),
        dpi_y = meta.get("dpi_y",""),
        size = meta.get("calibrated_size",""),
        Hjson = (meta.get("homography_matrix") or "").replace('\n',''),
        avg_conf = meta.get("avg_confidence",""),
        visual_score = meta.get("visual_score",""),
        ts = datetime.datetime.utcnow().isoformat()+"Z"
    )
    out.write_text(payload, encoding="utf-8")
    return str(out)
