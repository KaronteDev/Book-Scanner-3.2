
from pathlib import Path
import json, sqlite3

def _img_size(img_path):
    try:
        from PIL import Image
        with Image.open(img_path) as im:
            return im.width, im.height
    except Exception:
        return None, None

def export_iiif(db_path: str, document_id: int, out_dir: str, base_img_url: str = ""):
    con = sqlite3.connect(db_path); con.row_factory=sqlite3.Row
    doc = con.execute("SELECT id, title FROM document WHERE id=?", (document_id,)).fetchone()
    pages = con.execute("SELECT id, seq, processed_path FROM page WHERE document_id=? ORDER BY seq", (document_id,)).fetchall()
    con.close()
    canvases = []
    for p in pages:
        img_id = f"{base_img_url}/{Path(p['processed_path']).name}" if base_img_url else str(Path(p['processed_path']))
        w, h = _img_size(p["processed_path"]) if p["processed_path"] else (None, None)
        canvas_id = f"{base_img_url}/canvas/{p['seq']}" if base_img_url else f"canvas/{p['seq']}"
        anno_id = f"{base_img_url}/annotation/{p['seq']}" if base_img_url else f"annotation/{p['seq']}"
        canvases.append({
            "id": canvas_id,
            "type": "Canvas",
            "height": h or 0,
            "width": w or 0,
            "items": [{
                "id": anno_id,
                "type": "AnnotationPage",
                "items": [{
                    "id": f"{anno_id}#paint",
                    "type":"Annotation",
                    "motivation":"painting",
                    "body":{
                        "id": img_id,
                        "type":"Image",
                        "format": "image/jpeg"
                    },
                    "target": canvas_id
                }]
            }]
        })
    manifest = {
      "@context": "http://iiif.io/api/presentation/3/context.json",
      "id": f"{base_img_url}/manifest/{document_id}" if base_img_url else f"manifest/{document_id}",
      "type": "Manifest",
      "label": {"es": [doc['title'] if doc and doc['title'] else f"Documento {document_id}"]},
      "items": canvases
    }
    outp = Path(out_dir); outp.mkdir(parents=True, exist_ok=True)
    man_path = outp / f"iiif_manifest_doc_{document_id}.json"
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(man_path)


def validate_iiif(manifest_path: str):
    import json, os
    from pathlib import Path
    if not os.path.exists(manifest_path):
        return {"ok": False, "error": "manifest not found"}
    try:
        data = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    except Exception as ex:
        return {"ok": False, "error": f"json parse error: {ex}"}
    problems = []
    if data.get("type") != "Manifest":
        problems.append("type != Manifest")
    if "items" not in data or not isinstance(data["items"], list) or not data["items"]:
        problems.append("items (canvases) missing or empty")
    else:
        for i, cv in enumerate(data["items"], start=1):
            if cv.get("type") != "Canvas":
                problems.append(f"canvas {i}: type != Canvas")
            if "items" not in cv or not cv["items"]:
                problems.append(f"canvas {i}: items (AnnotationPage) missing")
            else:
                ap = cv["items"][0]
                if ap.get("type") != "AnnotationPage":
                    problems.append(f"canvas {i}: AnnotationPage type invalid")
                if "items" not in ap or not ap["items"]:
                    problems.append(f"canvas {i}: Annotation missing")
                else:
                    an = ap["items"][0]
                    if an.get("type") != "Annotation":
                        problems.append(f"canvas {i}: Annotation type invalid")
                    body = an.get("body", {})
                    if body.get("type") != "Image":
                        problems.append(f"canvas {i}: body.type != Image")
    return {"ok": len(problems)==0, "problems": problems}
