
from pathlib import Path
import sqlite3, json

def export_geojson(db_path: str, document_id: int, out_dir: str):
    con = sqlite3.connect(db_path); con.row_factory=sqlite3.Row
    rows = con.execute("SELECT a.id, a.page_id, a.lat, a.lon, a.label, p.seq FROM annotations a LEFT JOIN page p ON p.id=a.page_id WHERE a.document_id=?", (document_id,)).fetchall()
    con.close()
    feats = []
    for r in rows or []:
        feats.append({
          "type":"Feature",
          "properties":{
            "id": r["id"], "page_id": r["page_id"], "page_seq": r["seq"], "label": r["label"], "document_id": document_id
          },
          "geometry":{"type":"Point","coordinates":[r["lon"], r["lat"]]}
        })
    gj = {"type":"FeatureCollection", "features": feats}
    outp = Path(out_dir); outp.mkdir(parents=True, exist_ok=True)
    path = outp / f"geo_doc_{document_id}.geojson"
    path.write_text(json.dumps(gj, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
