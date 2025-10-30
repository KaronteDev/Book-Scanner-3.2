#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, sqlite3
from pathlib import Path
from flask import Flask, send_from_directory, request, jsonify
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DB = BASE_DIR / "geodocs_scanner.db"
CONF = BASE_DIR / "geodocs_config.json"

app = Flask(__name__, static_folder=str(BASE_DIR / "web_viewer"))

def cfg():
    return json.loads(CONF.read_text(encoding="utf-8"))

def headers():
    h={"Content-Type":"application/json"}
    c = cfg()
    tok = c.get("jwt_token") or ""
    if tok: h["Authorization"] = f"Bearer {tok}"
    return h

@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/static/<path:p>")
def static_files(p):
    return send_from_directory(app.static_folder, p)

@app.get("/annotations")
def annotations():
    doc_id = request.args.get("document_id", type=int)
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    
q = request.args.get("q","").strip()
tags = request.args.get("tags","").strip()
typ = request.args.get("type","").strip()
dfrom = request.args.get("from","").strip()
dto = request.args.get("to","").strip()
sql = "SELECT * FROM annotation WHERE document_id=?"
args = [doc_id]
if q: sql += " AND body LIKE ?"; args.append(f"%{q}%")
if tags: sql += " AND IFNULL(tags,'') LIKE ?"; args.append(f"%{tags}%")
if typ: sql += " AND type=?"; args.append(typ)
if dfrom: sql += " AND IFNULL(created_at,'') >= ?"; args.append(dfrom)
if dto: sql += " AND IFNULL(created_at,'') <= ?"; args.append(dto)
sql += " ORDER BY id DESC"
rows = list(con.execute(sql, args))

    con.close()
    return jsonify({"annotations":[dict(r) for r in rows]})

@app.post("/sync_annotations")
def sync_annotations():
    data = request.get_json(force=True) or {}
    doc_id = int(data.get("document_id"))
    # send local annotations to remote
    c = cfg()
    base = (c.get("api_base_url") or "").rstrip("/")
    ep = base + "/api/anotaciones"
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    cur = con.cursor()
    rows = list(cur.execute("SELECT * FROM annotation WHERE document_id=?", (doc_id,)))
    payload = {"document_id": doc_id, "annotations": [dict(r) for r in rows]}
    r = requests.post(ep, headers=headers(), json=payload, timeout=int(c.get("timeout_sec",20)), verify=bool(c.get("verify_tls",True)))
    r.raise_for_status()
    return jsonify({"status":"ok","pushed":len(rows)})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

@app.get("/pick")
def pick():
    html = '''<!doctype html><html><head>
    <meta charset="utf-8"><title>Elegir coordenadas</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>html,body,#map{height:100%;margin:0}</style>
    </head><body>
    <div id="map"></div>
    <script>
    var m=L.map('map').setView([28.4682,-16.2546],10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(m);
    function send(lat,lon){
      fetch('/set_coords', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({lat:lat, lon:lon})});
      alert('Coordenadas guardadas: '+lat+', '+lon);
    }
    m.on('click', function(e){ send(e.latlng.lat, e.latlng.lng); });
    </script>
    </body></html>'''
    return html

@app.post("/set_coords")
def set_coords():
    data = request.get_json(force=True) or {}
    lat = float(data.get("lat")); lon = float(data.get("lon"))
    (BASE_DIR / "web_viewer" / "last_coords.json").write_text(json.dumps({"lat": lat, "lon": lon}), encoding="utf-8")
    return jsonify({"ok": True, "lat": lat, "lon": lon})

@app.get("/pull_annotations")
def pull_annotations():
    doc_id = int(request.args.get("document_id"))
    c = cfg(); base = (c.get("api_base_url") or "").rstrip("/")
    url = base + "/api/anotaciones"
    r = requests.get(url, headers=headers(), params={"document_id": doc_id}, timeout=int(c.get("timeout_sec",20)), verify=bool(c.get("verify_tls",True)))
    r.raise_for_status()
    data = r.json()
    anns = data.get("annotations", data if isinstance(data, list) else [])
    con = sqlite3.connect(DB)
    cur = con.cursor()
    for a in anns:
        cur.execute("""SELECT id FROM annotation WHERE document_id=? AND IFNULL(page_id,'')=IFNULL(?, '') AND IFNULL(body,'')=IFNULL(?, '') AND IFNULL(type,'')=IFNULL(?, '')""", (doc_id, a.get("page_id"), a.get("body"), a.get("type")))
        row = cur.fetchone()
        if row:
            cur.execute("""UPDATE annotation SET latitude=?, longitude=?, toponimo_id=?, persona_id=?, tags=?, target_region=?, updated_at=datetime('now') WHERE id=?""", (a.get("latitude"), a.get("longitude"), a.get("toponimo_id"), a.get("persona_id"), a.get("tags"), a.get("target_region"), row[0]))
        else:
            cur.execute("""INSERT INTO annotation (document_id,page_id,user,type,tags,body,target_region,latitude,longitude,toponimo_id,persona_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""", (doc_id, a.get("page_id"), a.get("user","remote"), a.get("type"), a.get("tags"), a.get("body"), a.get("target_region"), a.get("latitude"), a.get("longitude"), a.get("toponimo_id"), a.get("persona_id")))
    con.commit(); con.close()
    return jsonify({"status":"ok","pulled":len(anns)})


@app.get("/prosopo")
def prosopo():
    doc_id = int(request.args.get("document_id"))
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    persons = list(con.execute("SELECT persona_id, COUNT(*) c FROM annotation WHERE document_id=? AND persona_id IS NOT NULL GROUP BY persona_id ORDER BY c DESC", (doc_id,)))
    places = list(con.execute("SELECT toponimo_id, COUNT(*) c FROM annotation WHERE document_id=? AND toponimo_id IS NOT NULL GROUP BY toponimo_id ORDER BY c DESC", (doc_id,)))
    con.close()
    return jsonify({
        "persons":[{"id": r["persona_id"], "count": r["c"]} for r in persons],
        "places":[{"id": r["toponimo_id"], "count": r["c"]} for r in places]
    })


@app.get("/graph")
def graph():
    doc_id = int(request.args.get("document_id"))
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    rows = list(con.execute("SELECT page_id, persona_id, toponimo_id FROM annotation WHERE document_id=?", (doc_id,)))
    con.close()
    # Build nodes/edges (simple person-place co-occurrence)
    nodes = {}; edges = []; idx = 0
    per_by_page = {}
    top_by_page = {}
    from collections import defaultdict, Counter
    per_by_page = defaultdict(set); top_by_page = defaultdict(set)
    for r in rows:
        pid=r["page_id"]
        if r["persona_id"]: per_by_page[pid].add(f"person:{r['persona_id']}")
        if r["toponimo_id"]: top_by_page[pid].add(f"place:{r['toponimo_id']}")
    weight = Counter()
    for pid in per_by_page:
        for u in per_by_page[pid]:
            nodes.setdefault(u, {"key":u, "label":u, "size":3, "color":"#2b83ba"})
            for v in top_by_page.get(pid, []):
                nodes.setdefault(v, {"key":v, "label":v, "size":3, "color":"#abdda4"})
                weight[(u,v)] += 1
    for k,w in weight.items():
        u,v = k
        edges.append({"key": f"{u}--{v}", "source":u, "target":v, "size": max(1.0, float(w))})
    return jsonify({"nodes": list(nodes.values()), "edges": edges})


@app.get("/ocr_text")
def ocr_text():
    from flask import make_response
    doc_id = int(request.args.get("document_id"))
    seq = request.args.get("seq", type=int)
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    if seq is not None:
        r = con.execute("SELECT ocr_text FROM page WHERE document_id=? AND seq=?", (doc_id, seq)).fetchone()
    else:
        r = con.execute("SELECT ocr_text FROM page WHERE document_id=? ORDER BY seq LIMIT 1", (doc_id,)).fetchone()
    con.close()
    txt = (r["ocr_text"] if r and r["ocr_text"] else "")
    if request.args.get('format')=='txt':
        resp = make_response(txt)
        resp.headers['Content-Type'] = 'text/plain; charset=utf-8'
        resp.headers['Content-Disposition'] = f'attachment; filename=page_{seq:04d}.txt'
        return resp
    return jsonify({"ocr_text": txt})


@app.get("/page_image")
def page_image():
    doc_id = int(request.args.get("document_id")); seq = int(request.args.get("seq"))
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT processed_path FROM page WHERE document_id=? AND seq=?", (doc_id, seq)).fetchone()
    con.close()
    if not r or not r["processed_path"] or not Path(r["processed_path"]).exists():
        return "Not found", 404
    from flask import send_file
    return send_file(r["processed_path"])

@app.get("/ocr_revisions")
def ocr_revisions():
    doc_id = int(request.args.get("document_id")); seq = int(request.args.get("seq"))
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    pr = con.execute("SELECT id FROM page WHERE document_id=? AND seq=?", (doc_id, seq)).fetchone()
    if not pr: 
        con.close(); 
        return jsonify({"revisions":[]})
    pid = pr["id"]
    rows = list(con.execute("SELECT id, version, user, created_at FROM ocr_revision WHERE page_id=? ORDER BY version", (pid,)))
    con.close()
    return jsonify({"revisions":[dict(r) for r in rows]})

@app.post("/save_ocr_revision")
def save_ocr_revision():
    data = request.get_json(force=True) or {}
    doc_id = int(data.get("document_id")); seq = int(data.get("seq"))
    ocr_text = data.get("ocr_text") or ""
    ocr_html = data.get("ocr_html") or ""
    user = data.get("user") or "web-user"
    con = sqlite3.connect(DB); cur = con.cursor()
    pr = cur.execute("SELECT id FROM page WHERE document_id=? AND seq=?", (doc_id, seq)).fetchone()
    if not pr: 
        con.close(); 
        return jsonify({"ok": False, "error":"page not found"}), 404
    pid = pr[0]
    rv = cur.execute("SELECT IFNULL(MAX(version),0)+1 FROM ocr_revision WHERE page_id=?", (pid,)).fetchone()[0]
    cur.execute("INSERT INTO ocr_revision(page_id, version, user, ocr_text, ocr_html) VALUES (?,?,?,?,?)", (pid, rv, user, ocr_text, ocr_html))
    cur.execute("INSERT INTO audit_log(action, user, role, page_id, revision_id, details) VALUES (?,?,?,?,?,?)", ("save_revision", user, None, pid, cur.lastrowid, json.dumps({})))
    # also update current page
    cur.execute("UPDATE page SET ocr_text=?, ocr_html=?, status='done' WHERE id=?", (ocr_text, ocr_html, pid))
    con.commit(); con.close()
    return jsonify({"ok": True, "version": rv})


@app.get("/ocr_revision_body")
def ocr_revision_body():
    rid = int(request.args.get("revision_id"))
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT id, page_id, version, user, created_at, ocr_text, ocr_html, changes_html, signed, signed_at, signature FROM ocr_revision WHERE id=?", (rid,)).fetchone()
    con.close()
    if not r: return jsonify({"error":"not found"}), 404
    return jsonify({k: r[k] for k in r.keys()})

@app.post("/restore_ocr_revision")
def restore_ocr_revision():
    data = request.get_json(force=True) or {}
    rid = int(data.get("revision_id"))
    con = sqlite3.connect(DB); cur = con.cursor()
    r = cur.execute("SELECT page_id, ocr_text, ocr_html FROM ocr_revision WHERE id=?", (rid,)).fetchone()
    if not r:
        con.close(); return jsonify({"ok": False, "error":"revision not found"}), 404
    page_id, txt, html = r
    cur.execute("UPDATE page SET ocr_text=?, ocr_html=?, status='done' WHERE id=?", (txt, html, page_id))
    con.commit(); con.close()
    return jsonify({"ok": True})

@app.post("/sign_ocr_revision")
def sign_ocr_revision():
    data = request.get_json(force=True) or {}
    rid = int(data.get("revision_id"))
    author = (data.get("user") or "web-editor").strip()
    note = (data.get("signature") or "").strip()
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("UPDATE ocr_revision SET signed=1, signed_at=datetime('now'), signature=? , user=? WHERE id=?", (note, author, rid))
    cur.execute("INSERT INTO audit_log(action, user, role, page_id, revision_id, details) VALUES (?,?,?,?,?,?)", ("sign_revision", author, None, None, rid, json.dumps({"note":note})))
    con.commit(); con.close()
    return jsonify({"ok": True})


@app.get("/user_role")
def user_role():
    import requests, json as _json
    # Try to verify against GeoDocs backend using geodocs_config.json
    cfg_path = Path(__file__).resolve().parents[1] / "geodocs_config.json"
    role = "investigador"; user = "local-user"
    try:
        import requests, json as _json
        cfg = _json.loads(cfg_path.read_text(encoding="utf-8"))
        api = (cfg.get("api_base_url") or "").rstrip("/")
        token = cfg.get("jwt") or cfg.get("token") or ""
        if api and token:
            r = requests.get(api + "/api/auth/verify", headers={"Authorization": f"Bearer {token}"}, timeout=6, verify=cfg.get("verify_ssl", True))
            if r.ok:
                j = r.json()
                user = j.get("user") or user
                role = j.get("role") or role
                perms = j.get("permissions") or {}
    except Exception:
        pass
    try:
        perms
    except NameError:
        perms = {}
    return jsonify({"user": user, "role": role, "permissions": perms})


@app.get("/ocr_changes")
def ocr_changes():
    rid = int(request.args.get("revision_id"))
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT changes_html FROM ocr_revision WHERE id=?", (rid,)).fetchone()
    con.close()
    ch = r["changes_html"] if r and r["changes_html"] else ""
    return jsonify({"changes_html": ch})

@app.post("/apply_partial_restore")
def apply_partial_restore():
    data = request.get_json(force=True) or {}
    rid = int(data.get("revision_id"))
    doc_id = int(data.get("document_id"))
    seq = int(data.get("seq"))
    indices = data.get("indices") or []  # list of paragraph indices to apply
    # Fetch target revision body and current page
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    pr = con.execute("SELECT id, ocr_text, ocr_html FROM page WHERE document_id=? AND seq=?", (doc_id, seq)).fetchone()
    rr = con.execute("SELECT ocr_text, ocr_html FROM ocr_revision WHERE id=?", (rid,)).fetchone()
    if not pr or not rr:
        con.close()
        return jsonify({"ok": False, "error": "page or revision not found"}), 404
    page_id = pr["id"]
    base_html = pr["ocr_html"] or (pr["ocr_text"] or "")
    rev_html = rr["ocr_html"] or (rr["ocr_text"] or "")
    # Split into paragraphs - naive split by </p> else by double newline
    import re
    def split_par(html):
        if "</p>" in html:
            parts = [p + "</p>" for p in re.split(r"</p>", html) if p.strip()!=""]
            parts = [re.sub(r"^\s*<p[^>]*>", "", p) for p in parts]  # strip leading <p>
            return parts
        else:
            return [pp for pp in re.split(r"\n\n+", html) if pp.strip()!=""]
    base_parts = split_par(base_html)
    rev_parts  = split_par(rev_html)
    # Align lengths
    L = max(len(base_parts), len(rev_parts))
    base_parts += [""] * (L - len(base_parts))
    rev_parts  += [""] * (L - len(rev_parts))
    # Apply selected indices
    for i in indices:
        if 0 <= i < L:
            base_parts[i] = rev_parts[i]
    merged_html = "".join([f"<p>{p}</p>" for p in base_parts])
    # Save as new revision and update page
    cur = con.cursor()
    cur.execute("UPDATE page SET ocr_html=?, ocr_text=?, status='done' WHERE id=?", (re.sub(r"<[^>]+>", "", merged_html), merged_html, page_id))
    rv = cur.execute("SELECT IFNULL(MAX(version),0)+1 FROM ocr_revision WHERE page_id=?", (page_id,)).fetchone()[0]
    cur.execute("INSERT INTO ocr_revision(page_id, version, user, ocr_text, ocr_html, changes_html) VALUES (?,?,?,?,?,?)",
                (page_id, rv, "web-editor", re.sub(r"<[^>]+>", "", merged_html), merged_html, None))
    cur.execute("INSERT INTO audit_log(action, user, role, page_id, revision_id, details) VALUES (?,?,?,?,?,?)", ("partial_restore_paragraphs", "web-editor", None, page_id, cur.lastrowid, json.dumps({"indices":indices})))
    con.commit(); con.close()
    return jsonify({"ok": True, "version": rv})


@app.post("/apply_partial_restore_chars")
def apply_partial_restore_chars():
    data = request.get_json(force=True) or {}
    doc_id = int(data.get("document_id")); seq = int(data.get("seq"))
    final_text = data.get("final_text") or ""
    final_html = data.get("final_html") or ""
    user = (data.get("user") or "web-editor").strip()
    role = (data.get("role") or "investigador").strip()
    con = sqlite3.connect(DB); cur = con.cursor()
    pr = cur.execute("SELECT id FROM page WHERE document_id=? AND seq=?", (doc_id, seq)).fetchone()
    if not pr:
        con.close(); return jsonify({"ok": False, "error":"page not found"}), 404
    pid = pr[0]
    cur.execute("UPDATE page SET ocr_text=?, ocr_html=?, status='done' WHERE id=?", (final_text, final_html or final_text, pid))
    rv = cur.execute("SELECT IFNULL(MAX(version),0)+1 FROM ocr_revision WHERE page_id=?", (pid,)).fetchone()[0]
    cur.execute("INSERT INTO ocr_revision(page_id, version, user, ocr_text, ocr_html) VALUES (?,?,?,?,?)",
                (pid, rv, user, final_text, final_html or final_text))
    # audit
    cur.execute("INSERT INTO audit_log(action, user, role, page_id, revision_id, details) VALUES (?,?,?,?,?,?)",
                ("partial_restore_chars", user, role, pid, cur.lastrowid, json.dumps({"doc_id":doc_id,"seq":seq})))
    con.commit(); con.close()
    return jsonify({"ok": True, "version": rv})


@app.get("/export_audit")
def export_audit():
    fmt = request.args.get("format","json")
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    rows = list(con.execute("SELECT * FROM audit_log ORDER BY created_at DESC"))
    con.close()
    if fmt=="csv":
        import io, csv
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(rows[0].keys() if rows else ["id","action","user","role","page_id","revision_id","details","created_at"])
        for r in rows:
            w.writerow([r[k] for k in r.keys()])
        from flask import make_response
        resp = make_response(out.getvalue())
        resp.headers["Content-Type"]="text/csv; charset=utf-8"
        resp.headers["Content-Disposition"]="attachment; filename=audit_log.csv"
        return resp
    else:
        return jsonify([dict(r) for r in rows])


@app.post("/check_similarity")
def check_similarity():
    data = request.get_json(force=True) or {}
    doc_id = int(data.get("document_id"))
    seq = int(data.get("seq"))
    text_corr = (data.get("text") or "").strip()
    import difflib, sqlite3
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    baser = con.execute("SELECT ocr_text FROM page WHERE document_id=? AND seq=?", (doc_id, seq)).fetchone()
    base = (baser["ocr_text"] if baser and baser["ocr_text"] else "").strip()
    score = difflib.SequenceMatcher(None, base, text_corr).ratio() if (base and text_corr) else 0.0
    con.close()
    return jsonify({"score": score})


VALID_STATES = ["borrador","revisado","validado","publicado"]

@app.post("/change_state")
def change_state():
    data = request.get_json(force=True) or {}
    level = data.get("level","page")  # 'page' or 'document'
    state = data.get("state","borrador")
    if state not in VALID_STATES:
        return jsonify({"ok": False, "error": "invalid state"}), 400
    # role check
    role_info = requests.get(request.host_url.rstrip("/") + "/user_role").json()
    role = role_info.get("role","investigador")
    allowed = {
        "borrador": ["investigador","experto","administrador"],
        "revisado": ["investigador","experto","administrador"],
        "validado": ["experto","administrador"],
        "publicado": ["administrador"]
    }
    if role not in allowed[state]:
        return jsonify({"ok": False, "error": "forbidden"}), 403
    con = sqlite3.connect(DB); cur = con.cursor()
    if level == "page":
        doc_id = int(data.get("document_id")); seq = int(data.get("seq"))
        pr = cur.execute("SELECT id FROM page WHERE document_id=? AND seq=?", (doc_id, seq)).fetchone()
        if not pr: con.close(); return jsonify({"ok": False, "error": "page not found"}), 404
        pid = pr[0]
        cur.execute("UPDATE page SET review_state=? WHERE id=?", (state, pid))
        cur.execute("INSERT INTO audit_log(action, user, role, page_id, details) VALUES (?,?,?,?,?)", ("change_state_page", role_info.get("user"), role, pid, json.dumps({"state":state})))
    else:
        doc_id = int(data.get("document_id"))
        dr = cur.execute("SELECT id FROM document WHERE id=?", (doc_id,)).fetchone()
        if not dr: con.close(); return jsonify({"ok": False, "error": "document not found"}), 404
        cur.execute("UPDATE document SET workflow_state=? WHERE id=?", (state, doc_id))
        cur.execute("INSERT INTO audit_log(action, user, role, details) VALUES (?,?,?,?)", ("change_state_document", role_info.get("user"), role, json.dumps({"doc_id":doc_id,"state":state})))
    con.commit(); con.close()
    return jsonify({"ok": True, "state": state})


@app.get("/ocr_quality_dashboard")
def ocr_quality_dashboard():
    doc_id = request.args.get("document_id", type=int)
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    pages = list(con.execute("SELECT id, document_id, seq, review_state, ocr_text FROM page " + ("WHERE document_id=?" if doc_id else ""), ([doc_id] if doc_id else [])))
    revs = list(con.execute("SELECT page_id, MAX(version) AS v, MAX(similarity_score) AS sc FROM ocr_revision GROUP BY page_id"))
    sc_by_page = {r["page_id"]: (r["sc"] or 0.0) for r in revs}
    rows = []
    for p in pages:
        rows.append({"seq": p["seq"], "state": p["review_state"], "similarity": sc_by_page.get(p["id"], 0.0)})
    con.close()
    return jsonify({"pages": rows})


@app.post("/publish_to_geodocs")
def publish_to_geodocs():
    data = request.get_json(force=True) or {}
    doc_id = int(data.get("document_id"))
    quality = float(data.get("ocr_quality", 0.0))
    signed_by = data.get("signed_by","")
    signature = data.get("signature","")
    # Call backend
    cfg_path = Path(__file__).resolve().parents[1] / "geodocs_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    api = (cfg.get("api_base_url") or "").rstrip("/")
    token = cfg.get("jwt") or cfg.get("token") or ""
    try:
        r = requests.post(api + "/api/documentos/publish", headers={"Authorization": f"Bearer {token}"}, json={
            "document_id": doc_id, "workflow_state":"publicado", "ocr_quality": quality, "signed_by": signed_by, "signature": signature
        }, timeout=20, verify=cfg.get("verify_ssl", True))
        r.raise_for_status()
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 500
    # mark local
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("UPDATE document SET workflow_state='publicado' WHERE id=?", (doc_id,))
    cur.execute("INSERT INTO audit_log(action, user, role, details) VALUES (?,?,?,?)", ("publish_document", signed_by, None, json.dumps({"doc_id":doc_id,"ocr_quality":quality})))
    con.commit(); con.close()
    return jsonify({"ok": True})


@app.post("/run_quality_batch")
def run_quality_batch_endpoint():
    data = request.get_json(force=True) or {}
    doc_id = data.get("document_id")
    try:
        from modules.quality_engine import set_env, run_quality_batch
        set_env(DB, Path(__file__).resolve().parent.parent)
        res = run_quality_batch(doc_id=int(doc_id) if doc_id is not None else None)
        return jsonify({"ok": True, "result": res})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 500

@app.get("/scheduler_status")
def scheduler_status():
    p = Path(__file__).resolve().parents[1] / "quality_scheduler_status.json"
    if p.exists():
        import json as _j
        return jsonify(_j.loads(p.read_text(encoding="utf-8")))
    return jsonify({"last_run": None, "result": None})


@app.get("/calibration")
def get_calibration():
    # return calibration.json if exists + doc fields
    proj = Path(__file__).resolve().parents[1]
    cal = proj / "calibration.json"
    data = {}
    if cal.exists():
        import json as _j
        data = _j.loads(cal.read_text(encoding="utf-8"))
    # also attach document row if possible
    import sqlite3
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT id, dpi_x, dpi_y, calibrated_size, calibration_date FROM document ORDER BY id DESC LIMIT 1").fetchone()
    con.close()
    if r:
        data.setdefault("dpi_x", r["dpi_x"]); data.setdefault("dpi_y", r["dpi_y"])
        data.setdefault("size", r["calibrated_size"]); data.setdefault("date", r["calibration_date"])
    return jsonify(data)


@app.post("/enhance_project")
def enhance_project():
    data = request.get_json(force=True) or {}
    doc_id = data.get("document_id")
    try:
        from modules.quality_engine import set_env, run_quality_batch
        set_env(DB, Path(__file__).resolve().parent.parent)
        res = run_quality_batch(doc_id=int(doc_id) if doc_id else None)
        return jsonify({"ok": True, "result": res})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 500


@app.post("/tts")
def tts_endpoint():
    data = request.get_json(force=True) or {}
    page_id = data.get("page_id")
    corrected = bool(data.get("corrected"))
    voice = data.get("voice","es")
    # fetch text from DB
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT id, ocr_text, ocr_html FROM page WHERE id=?", (page_id,)).fetchone()
    con.close()
    if not r: return jsonify({"ok": False, "error":"page not found"}), 404
    text = (r["ocr_html"] or "") if corrected else (r["ocr_text"] or "")
    # strip HTML if needed
    import re
    text = re.sub("<[^<]+?>", " ", text) if corrected else text
    out = Path(__file__).resolve().parent / f"tts_page_{page_id}_{'corr' if corrected else 'raw'}.wav"
    try:
        from modules.tts import synth_to_file
        ok, path = synth_to_file(text, str(out), voice)
        return jsonify({"ok": True, "file": str(path), "corrected": corrected})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 500

@app.post("/spellcheck")
def spellcheck_endpoint():
    data = request.get_json(force=True) or {}
    page_id = data.get("page_id")
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT id, ocr_html FROM page WHERE id=?", (page_id,)).fetchone()
    con.close()
    if not r: return jsonify({"ok": False, "error":"page not found"}), 404
    import re
    text = re.sub("<[^<]+?>", " ", r["ocr_html"] or "")
    from modules.spellcheck import check_text
    from modules.glossary_manager import get_terms, apply_abbreviation_hints
    res = check_text(text, "es")
    terms = get_terms(DB, 'es')
    hints = apply_abbreviation_hints(text, terms)
    return jsonify({"ok": True, "tool": res["tool"], "issues": res["issues"], "abbrev_hints": hints})

@app.post("/xmp_sidecar")
def xmp_sidecar_endpoint():
    data = request.get_json(force=True) or {}
    page_id = data.get("page_id")
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT p.id, p.document_id, p.avg_confidence, p.visual_score, p.homography_matrix, p.processed_path, d.dpi_x, d.dpi_y, d.calibrated_size FROM page p JOIN document d ON p.document_id=d.id WHERE p.id=?", (page_id,)).fetchone()
    con.close()
    if not r: return jsonify({"ok": False, "error":"page not found"}), 404
    meta = {
        "document_id": r["document_id"],
        "page_id": r["id"],
        "dpi_x": r["dpi_x"], "dpi_y": r["dpi_y"],
        "calibrated_size": r["calibrated_size"],
        "homography_matrix": r["homography_matrix"] or "",
        "avg_confidence": r["avg_confidence"], "visual_score": r["visual_score"]
    }
    from modules.xmp_embed import write_xmp
    img = r["processed_path"]
    try:
        path = write_xmp(img, meta)
        return jsonify({"ok": True, "file": path})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 500


@app.get("/page_text")
def page_text():
    pid = int(request.args.get("page_id"))
    corrected = request.args.get("corrected","true").lower() in ("1","true","yes","y")
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT ocr_text, ocr_html FROM page WHERE id=?", (pid,)).fetchone()
    con.close()
    if not r: return jsonify({"ok": False, "error":"page not found"}), 404
    if corrected:
        return jsonify({"ok": True, "html": r["ocr_html"] or ""})
    else:
        return jsonify({"ok": True, "text": r["ocr_text"] or ""})

@app.post("/save_corrected")
def save_corrected():
    data = request.get_json(force=True) or {}
    pid = int(data.get("page_id"))
    html = data.get("html") or ""
    con = sqlite3.connect(DB)
    con.execute("UPDATE page SET ocr_html=? WHERE id=?", (html, pid))
    con.commit(); con.close()
    return jsonify({"ok": True})


@app.get("/tts_stream")
def tts_stream():
    # Params: page_id, corrected (0/1), voice=es
    try:
        page_id = int(request.args.get("page_id"))
    except Exception:
        return jsonify({"ok": False, "error":"page_id requerido"}), 400
    corrected = request.args.get("corrected","0") in ("1","true","True","yes","y")
    voice = request.args.get("voice","es")
    # fetch text
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT id, ocr_text, ocr_html FROM page WHERE id=?", (page_id,)).fetchone()
    con.close()
    if not r: return jsonify({"ok": False, "error":"page not found"}), 404
    text = (r["ocr_html"] or "") if corrected else (r["ocr_text"] or "")
    if corrected:
        import re
        text = re.sub("<[^<]+?>", " ", text)
    from modules.tts import synth_to_file
    from pathlib import Path as _P
    out = _P(__file__).resolve().parent / f"tts_stream_{page_id}_{'corr' if corrected else 'raw'}.wav"
    ok, path = synth_to_file(text, str(out), voice)
    # Stream file in chunks
    from flask import Response
    def generate(fp, chunk_size=4096):
        with open(fp, "rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data: break
                yield data
    mime = "audio/wav" if str(path).lower().endswith(".wav") else "audio/mpeg"
    return Response(generate(path), mimetype=mime)


@app.post("/spell_suggest")
def spell_suggest():
    data = request.get_json(force=True) or {}
    word = (data.get("word") or "").strip()
    if not word: return jsonify({"ok": False, "error":"word requerido"}), 400
    # Use pyspellchecker for suggestions if available
    try:
        from spellchecker import SpellChecker
        sc = SpellChecker(language='es')
        sugg = sc.candidates(word)
        return jsonify({"ok": True, "suggestions": list(sugg)[:10]})
    except Exception:
        return jsonify({"ok": True, "suggestions": []})


@app.get("/tts_voices")
def tts_voices():
    from modules.tts import list_voices
    return jsonify(list_voices())


@app.post("/audiobook")
def audiobook():
    data = request.get_json(force=True) or {}
    doc_id = int(data.get("document_id"))
    corrected = bool(data.get("corrected", True))
    voice_id = data.get("voice_id")
    rate = data.get("rate"); volume = data.get("volume"); lang = data.get("lang","es")
    seq_from = int(data.get("seq_from", 1)); seq_to = int(data.get("seq_to", 10**9))
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    rows = con.execute("SELECT seq, ocr_text, ocr_html FROM page WHERE document_id=? AND seq BETWEEN ? AND ? ORDER BY seq", (doc_id, seq_from, seq_to)).fetchall()
    con.close()
    import re
    texts = []
    for r in rows:
        t = (r["ocr_html"] or "") if corrected else (r["ocr_text"] or "")
        if corrected: t = re.sub("<[^<]+?>", " ", t)
        texts.append(t or "")
    out_dir = Path(__file__).resolve().parent / f"audiobook_doc_{doc_id}"
    from modules.tts import synth_audiobook
    res = synth_audiobook(texts, str(out_dir), base_name=f"doc_{doc_id}", voice_id=voice_id, rate=rate, volume=volume, voice_lang=lang)
    return jsonify({"ok": True, "result": res})


@app.get("/glossaries")
def glossaries_list():
    from modules.glossary_manager import list_glossaries
    return jsonify(glossaries=list_glossaries(DB))

@app.post("/glossaries")
def glossaries_create():
    data = request.get_json(force=True) or {}
    from modules.glossary_manager import create_glossary
    ok = create_glossary(DB, data.get("scope","project"), data.get("name","Nuevo glosario"), data.get("language","es"), data.get("terms",{}))
    return jsonify({"ok": ok})

@app.post("/glossaries/update")
def glossaries_update():
    data = request.get_json(force=True) or {}
    from modules.glossary_manager import update_glossary
    ok = update_glossary(DB, int(data.get("id")), data.get("terms"), data.get("name"))
    return jsonify({"ok": ok})

@app.post("/glossaries/delete")
def glossaries_delete():
    data = request.get_json(force=True) or {}
    from modules.glossary_manager import delete_glossary
    ok = delete_glossary(DB, int(data.get("id")))
    return jsonify({"ok": ok})


@app.post("/glossary_import")
def glossary_import():
    data = request.get_json(force=True) or {}
    fmt = data.get("format","csv")
    scope = data.get("scope","project")
    name = data.get("name","Glosario importado")
    field_map = data.get("field_map") or {}
    path = data.get("path")
    if not path: return jsonify({"ok":False,"error":"path requerido"}),400
    from modules.glossary_io import import_csv, import_json, import_xml, import_tei
    if fmt=='csv': terms = import_csv(path, field_map)
    elif fmt=='json': terms = import_json(path, field_map)
    elif fmt=='xml': terms = import_xml(path, field_map)
    elif fmt in ('tei','tei-xml'): terms = import_tei(path)
    else: return jsonify({"ok":False,"error":"formato no soportado"}),400
    from modules.glossary_manager import create_glossary
    ok = create_glossary(DB, scope, name, "es", terms)
    return jsonify({"ok": ok, "terms": len(terms)})


@app.post("/glossary_export")
def glossary_export():
    data = request.get_json(force=True) or {}
    gid = int(data.get("id"))
    fmt = data.get("format","csv")
    out = data.get("out")
    if not out: return jsonify({"ok":False,"error":"out requerido"}),400
    import json as _j, sqlite3
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT terms_json FROM glossary WHERE id=?", (gid,)).fetchone(); con.close()
    if not r: return jsonify({"ok":False,"error":"glosario no encontrado"}),404
    terms = _j.loads(r["terms_json"] or "{}")
    from modules.glossary_io import export_csv, export_json, export_tei
    if fmt=='csv': path = export_csv(terms, out)
    elif fmt=='json': path = export_json(terms, out)
    elif fmt in ('tei','xml'): path = export_tei(terms, out)
    else: return jsonify({"ok":False,"error":"formato no soportado"}),400
    return jsonify({"ok":True,"file": path})


CURRENT_ABBREV_STYLE = "Chicago"

@app.get("/abbrev_style")
def get_abbrev_style():
    return jsonify({"style": CURRENT_ABBREV_STYLE})

@app.post("/abbrev_style")
def set_abbrev_style():
    global CURRENT_ABBREV_STYLE
    data = request.get_json(force=True) or {}
    CURRENT_ABBREV_STYLE = data.get("style","Chicago")
    return jsonify({"ok": True, "style": CURRENT_ABBREV_STYLE})


@app.post("/glossary_diff")
def glossary_diff():
    data = request.get_json(force=True) or {}
    a = int(data.get("a")); b = int(data.get("b"))
    import json as _j, sqlite3
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    ra = con.execute("SELECT terms_json FROM glossary WHERE id=?", (a,)).fetchone()
    rb = con.execute("SELECT terms_json FROM glossary WHERE id=?", (b,)).fetchone()
    con.close()
    if not (ra and rb): return jsonify({"ok":False,"error":"glosario no encontrado"}),404
    A = _j.loads(ra["terms_json"] or "{}"); B = _j.loads(rb["terms_json"] or "{}")
    only_a = {k:A[k] for k in A.keys()-B.keys()}
    only_b = {k:B[k] for k in B.keys()-A.keys()}
    conflicts = {k:(A[k],B[k]) for k in A.keys()&B.keys() if A[k]!=B[k]}
    return jsonify({"ok":True,"only_a":only_a,"only_b":only_b,"conflicts":conflicts})

@app.post("/glossary_merge")
def glossary_merge():
    data = request.get_json(force=True) or {}
    base_id = int(data.get("base")); other_id = int(data.get("other"))
    strategy = data.get("strategy","prefer_base") # prefer_base | prefer_other
    import json as _j, sqlite3
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    rb = con.execute("SELECT terms_json FROM glossary WHERE id=?", (base_id,)).fetchone()
    ro = con.execute("SELECT terms_json FROM glossary WHERE id=?", (other_id,)).fetchone()
    if not (rb and ro): con.close(); return jsonify({"ok":False,"error":"glosario no encontrado"}),404
    B = _j.loads(rb["terms_json"] or "{}"); O = _j.loads(ro["terms_json"] or "{}")
    merged = dict(B)
    for k,v in O.items():
        if k not in merged or strategy=="prefer_other":
            merged[k]=v
    con.execute("UPDATE glossary SET terms_json=?, updated_at=datetime('now') WHERE id=?", (_j.dumps(merged, ensure_ascii=False), base_id))
    con.commit(); con.close()
    return jsonify({"ok":True,"merged_count":len(merged)})


@app.get("/style_templates")
def style_templates_list():
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    rows = con.execute("SELECT * FROM style_template ORDER BY updated_at DESC, created_at DESC").fetchall()
    con.close()
    return jsonify(templates=[dict(r) for r in rows])

@app.post("/style_templates")
def style_templates_create():
    data = request.get_json(force=True) or {}
    con = sqlite3.connect(DB)
    con.execute("INSERT INTO style_template(scope,name,language,style_name,rules_json,meta_json,updated_at) VALUES (?,?,?,?,?,?,datetime('now'))",
                (data.get("scope","project"), data.get("name","Plantilla"), data.get("language","es"), data.get("style_name","Chicago 17"),
                 json.dumps(data.get("rules") or {}, ensure_ascii=False), json.dumps(data.get("meta") or {}, ensure_ascii=False)))
    con.commit(); con.close()
    return jsonify({"ok": True})

@app.post("/style_templates/update")
def style_templates_update():
    data = request.get_json(force=True) or {}
    con = sqlite3.connect(DB)
    con.execute("UPDATE style_template SET name=?, rules_json=?, meta_json=?, updated_at=datetime('now') WHERE id=?",
                (data.get("name"), json.dumps(data.get("rules") or {}, ensure_ascii=False),
                 json.dumps(data.get("meta") or {}, ensure_ascii=False), int(data.get("id"))))
    con.commit(); con.close()
    return jsonify({"ok": True})

@app.post("/style_templates/delete")
def style_templates_delete():
    data = request.get_json(force=True) or {}
    con = sqlite3.connect(DB); con.execute("DELETE FROM style_template WHERE id=?", (int(data.get("id")),))
    con.commit(); con.close()
    return jsonify({"ok": True})


@app.post("/apply_style_doc")
def apply_style_doc():
    data = request.get_json(force=True) or {}
    doc_id = int(data.get("document_id"))
    # Regla: tomar del selector actual o de una plantilla ID
    rules = data.get("rules")
    tpl_id = data.get("template_id")
    if not rules and tpl_id:
        con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
        r = con.execute("SELECT rules_json FROM style_template WHERE id=?", (tpl_id,)).fetchone()
        con.close()
        if r: 
            import json as _j
            rules = _j.loads(r["rules_json"] or "{}")
    if not rules:
        from modules.abbr_styles import get_style_detail
        rules = get_style_detail("Chicago 17", "es")
    out_dir = Path(__file__).resolve().parent / f"style_changes_doc_{doc_id}"
    from modules.style_apply import apply_style_to_document
    res = apply_style_to_document(DB, doc_id, rules, str(out_dir), language="es")
    return jsonify({"ok": True, "result": res})


@app.get("/diff_page")
def diff_page():
    page_id = int(request.args.get("page_id"))
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT ocr_text, ocr_html, stylized_html FROM page WHERE id=?", (page_id,)).fetchone()
    con.close()
    if not r:
        return jsonify({"ok": False, "error": "page not found"}), 404
    from modules.diff_engine import diff_text
    def strip_html(h): 
        import re; return re.sub("<[^<]+?>", " ", h or "")
    diffs = {
        "orig_vs_corr": diff_text(r["ocr_text"] or "", strip_html(r["ocr_html"] or "")),
        "corr_vs_style": diff_text(strip_html(r["ocr_html"] or ""), strip_html(r.get("stylized_html") or (r["ocr_html"] or "")))
    }
    return jsonify({"ok": True, "diffs": diffs})


@app.post("/review_apply")
def review_apply():
    data = request.get_json(force=True) or {}
    page_id = int(data.get("page_id"))
    decision = data.get("decision")  # 'accept'|'reject'|'revert'
    # naive: if accept -> copy stylized_html to ocr_html; if reject -> keep; if revert -> set to ocr_text
    con = sqlite3.connect(DB); con.row_factory=sqlite3.Row
    r = con.execute("SELECT ocr_text, ocr_html, stylized_html FROM page WHERE id=?", (page_id,)).fetchone()
    if not r:
        con.close(); return jsonify({"ok": False, "error": "page not found"}), 404
    if decision == "accept":
        con.execute("UPDATE page SET ocr_html=? WHERE id=?", (r["stylized_html"] or r["ocr_html"], page_id))
    elif decision == "revert":
        # wrap original as simple <p>
        con.execute("UPDATE page SET ocr_html=? WHERE id=?", ("<p>"+(r["ocr_text"] or "")+"</p>", page_id))
    # else reject -> no change
    con.commit(); con.close()
    return jsonify({"ok": True})


@app.post("/context_rules")
def context_rules_set():
    data = request.get_json(force=True) or {}
    tpl_id = int(data.get("template_id"))
    rules = data.get("context_rules") or []
    con = sqlite3.connect(DB)
    import json as _j
    r = con.execute("SELECT rules_json FROM style_template WHERE id=?", (tpl_id,)).fetchone()
    if not r: con.close(); return jsonify({"ok":False,"error":"template not found"}),404
    base = _j.loads(r[0] or "{}")
    base["context_rules"] = rules
    con.execute("UPDATE style_template SET rules_json=?, updated_at=datetime('now') WHERE id=?", (_j.dumps(base, ensure_ascii=False), tpl_id))
    con.commit(); con.close()
    return jsonify({"ok": True})

@app.get("/context_rules")
def context_rules_get():
    tpl_id = int(request.args.get("template_id"))
    con = sqlite3.connect(DB)
    r = con.execute("SELECT rules_json FROM style_template WHERE id=?", (tpl_id,)).fetchone()
    con.close()
    if not r: return jsonify({"ok":False,"error":"template not found"}),404
    import json as _j
    base = _j.loads(r[0] or "{}")
    return jsonify({"ok": True, "context_rules": base.get("context_rules", [])})


@app.post("/export/iiif")
def export_iiif_endpoint():
    data = request.get_json(force=True) or {}
    doc = int(data.get("document_id")); out = data.get("out"); base_url = data.get("base_img_url","")
    from modules.exporters.iiif import export_iiif
    path = export_iiif(DB, doc, out, base_img_url=base_url)
    return jsonify({"ok": True, "file": path})

@app.post("/export/tei")
def export_tei_endpoint():
    data = request.get_json(force=True) or {}
    doc = int(data.get("document_id")); out = data.get("out"); inc = bool(data.get("include_zones", False))
    from modules.exporters.tei import export_tei
    path = export_tei(DB, doc, out, include_zones=inc)
    return jsonify({"ok": True, "file": path})

@app.post("/export/dc")
def export_dc_endpoint():
    data = request.get_json(force=True) or {}
    doc = int(data.get("document_id")); out = data.get("out")
    from modules.exporters.dc import export_dc
    path = export_dc(DB, doc, out)
    return jsonify({"ok": True, "file": path})

@app.post("/export/geojson")
def export_geojson_endpoint():
    data = request.get_json(force=True) or {}
    doc = int(data.get("document_id")); out = data.get("out")
    from modules.exporters.geojson import export_geojson
    path = export_geojson(DB, doc, out)
    return jsonify({"ok": True, "file": path})

@app.post("/export/bundle")
def export_bundle_endpoint():
    data = request.get_json(force=True) or {}
    doc = int(data.get("document_id")); out = data.get("out"); base_url = data.get("base_img_url","")
    from modules.exporters.bundle import export_bundle
    res = export_bundle(DB, doc, out, base_img_url=base_url)
    return jsonify({"ok": True, "result": res})


@app.post("/export/validate")
def export_validate():
    data = request.get_json(force=True) or {}
    paths = data.get("paths") or []
    import os
    res = {p: os.path.exists(p) for p in paths}
    return jsonify({"ok": True, "exists": res})


@app.post("/export/iiif_validate")
def export_iiif_validate():
    data = request.get_json(force=True) or {}
    path = data.get("path")
    from modules.exporters.iiif import validate_iiif
    res = validate_iiif(path)
    return jsonify(res)


REST_CFG_FILE = os.path.join(os.path.dirname(__file__), "..", "geodocs_rest.json")

@app.get("/rest_config")
def rest_config_get():
    try:
        import json as _j, os
        if os.path.exists(REST_CFG_FILE):
            return jsonify({"ok": True, "config": _j.loads(open(REST_CFG_FILE, "r", encoding="utf-8").read())})
        return jsonify({"ok": True, "config": {}})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 500

@app.post("/rest_config")
def rest_config_set():
    data = request.get_json(force=True) or {}
    try:
        import json as _j, os
        with open(REST_CFG_FILE, "w", encoding="utf-8") as f:
            f.write(_j.dumps(data, ensure_ascii=False, indent=2))
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 500


@app.post("/export/publish")
def export_publish():
    data = request.get_json(force=True) or {}
    doc = int(data.get("document_id")); out = data.get("out"); base_url = data.get("base_img_url","")
    from modules.exporters.bundle import export_bundle_zip
    bundle_path, res = export_bundle_zip(DB, doc, out, base_img_url=base_url)
    cfg = {}
    try:
        if os.path.exists(REST_CFG_FILE):
            import json as _j
            cfg = _j.loads(open(REST_CFG_FILE, "r", encoding="utf-8").read())
    except Exception:
        pass
    endpoint = data.get("endpoint") or (cfg.get("base_url", "").rstrip('/') + "/api/documentos")
    token = data.get("jwt") or cfg.get("jwt")
    ok = True; msg = "skipped"
    try:
        import requests
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        files = {"file": open(bundle_path, "rb")}
        meta = {"document_id": str(doc)}
        r = requests.post(endpoint, headers=headers, files=files, data=meta, timeout=60)
        ok = (200 <= r.status_code < 300)
        msg = f"status {r.status_code}"
    except Exception as ex:
        ok = False; msg = str(ex)
    return jsonify({"ok": ok, "bundle": bundle_path, "result": res, "msg": msg, "endpoint": endpoint})
