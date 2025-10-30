
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, platform, subprocess, sqlite3, csv, json, requests, traceback
from datetime import datetime
from pathlib import Path
import cv2
import numpy as np
from tkinter import Tk, Toplevel, Frame, Label, Button, Canvas, filedialog, StringVar, DoubleVar, IntVar, Checkbutton, Entry, ttk, Scale, Listbox, SINGLE, END, HORIZONTAL, LEFT, RIGHT, BOTH, X, Y, TOP, BOTTOM, messagebox, Menu
from PIL import Image, ImageTk
import book_scan_core as core

APP_NAME = "GeoDocs Scanner v12"
BASE_DIR = Path(__file__).resolve().parent
GLOBAL_DB = BASE_DIR / "geodocs_scanner.db"
CONFIG_PATH = BASE_DIR / "geodocs_config.json"
API_MAP_PATH = BASE_DIR / "geodocs_api_map.json"
IMG_EXTS = (".jpg",".jpeg",".png",".tif",".tiff",".bmp")

# ---------- Utilities for hashing and versioning ----------
def sha256_of_file(path: Path):
    h=hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def add_version_entry(document_id=None, page_id=None, user="local", action="update", details=""):
    with db_connect() as con:
        con.execute("INSERT INTO version_history (document_id,page_id,user,action,details,created_at) VALUES (?,?,?,?,?,datetime('now'))",
                    (document_id, page_id, user, action, details))
        con.commit()

# ---------- Citation helpers ----------
def citation_apa(autor, anio, titulo, archivo, fondo, signatura, lugar=None):
    p = []
    if autor: p.append(autor)
    if anio: p.append(f"({anio}).")
    if titulo: p.append(f"*{titulo}*.")
    cola = []
    if archivo: cola.append(archivo)
    if fondo: cola.append(f"Fondo {fondo}")
    if signatura: cola.append(f"Signatura {signatura}")
    if lugar: cola.append(lugar)
    if cola: p.append(", ".join(cola) + ".")
    return " ".join(p)

def citation_iso690(autor, anio, titulo, lugar, archivo, fondo, signatura):
    p = []
    if autor: p.append(autor.upper())
    if anio: p.append(f"({anio})")
    if titulo: p.append(titulo)
    cola = []
    if lugar: cola.append(lugar)
    if archivo: cola.append(archivo)
    if fondo: cola.append(f"Fondo {fondo}")
    if signatura: cola.append(f"Signatura {signatura}")
    if cola: p.append(". ".join(cola))
    return ". ".join([x for x in p if x])

# ---------- Report generator ----------

# ---------- Archival/Scholarly Exporters ----------
def export_ead3_xml(db_path: Path, doc_id: int, out_path: Path):
    import xml.etree.ElementTree as ET
    con = sqlite3.connect(db_path); cur = con.cursor()
    cur.execute("""SELECT d.id, d.title, d.autor, d.fecha_text, d.signatura, d.tema, d.tipo,
                          d.lugar, d.idioma, d.derechos, d.resumen, d.nivel_descripcion, d.productor, d.alcance_y_contenido,
                          a.nombre, f.nombre
                   FROM document d
                   LEFT JOIN archivo a ON a.id=d.archivo_id
                   LEFT JOIN fondo f ON f.id=d.fondo_id
                   WHERE d.id=?""", (doc_id,))
    row = cur.fetchone()
    if not row: con.close(); return False
    (did, title, autor, fecha, signa, tema, tipo, lugar, idioma, derechos, resumen, nivel, productor, alcance, arch, fond) = row
    root = ET.Element("ead")
    archdesc = ET.SubElement(root, "archdesc")
    did_el = ET.SubElement(archdesc, "did")
    if title: ET.SubElement(did_el, "unittitle").text = title
    if signa: ET.SubElement(did_el, "unitid").text = signa
    if autor: ET.SubElement(did_el, "origination").text = autor
    if fecha: ET.SubElement(did_el, "unitdate").text = fecha
    if nivel: ET.SubElement(did_el, "physdesc").text = nivel
    if arch: ET.SubElement(did_el, "repository").text = arch
    if fond: ET.SubElement(did_el, "collection").text = fond
    if lugar: ET.SubElement(did_el, "geogname").text = lugar
    if idioma: ET.SubElement(did_el, "langmaterial").text = idioma
    if derechos: ET.SubElement(did_el, "accessrestrict").text = derechos
    scope = ET.SubElement(archdesc, "scopecontent")
    if alcance or resumen or tema:
        scope.text = " | ".join([x for x in [alcance, resumen, tema] if x])
    # Pages as components
    dsc = ET.SubElement(archdesc, "dsc")
    for (seq, path) in sqlite3.connect(db_path).execute("SELECT seq, processed_path FROM page WHERE document_id=? ORDER BY seq", (doc_id,)):
        c = ET.SubElement(dsc, "c")
        ET.SubElement(c, "did")
        ET.SubElement(c, "unittitle").text = f"Página {seq:04d}"
        if path: ET.SubElement(c, "dao", {"href": path})
    tree = ET.ElementTree(root); tree.write(out_path, encoding="utf-8", xml_declaration=True)
    con.close(); return True

def export_dc_jsonld(db_path: Path, doc_id: int, out_path: Path):
    con = sqlite3.connect(db_path); cur = con.cursor()
    cur.execute("""SELECT d.title, d.autor, d.fecha_text, d.signatura, d.tema, d.tipo,
                          d.lugar, d.idioma, d.derechos, d.resumen, a.nombre, f.nombre
                   FROM document d LEFT JOIN archivo a ON a.id=d.archivo_id LEFT JOIN fondo f ON f.id=d.fondo_id
                   WHERE d.id=?""", (doc_id,))
    r = cur.fetchone(); con.close()
    if not r: return False
    (title, autor, fecha, signa, tema, tipo, lugar, idioma, derechos, resumen, arch, fond) = r
    obj = {
        "@context": "http://schema.org",
        "@type": "CreativeWork",
        "name": title, "creator": autor, "dateCreated": fecha, "description": resumen or tema,
        "inLanguage": idioma, "locationCreated": lugar, "copyrightNotice": derechos,
        "identifier": signa, "genre": tipo,
        "provider": {"@type":"Organization","name": arch},
        "isPartOf": {"@type":"Collection","name": fond}
    }
    out_path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return True

def export_tei_xml(db_path: Path, doc_id: int, out_path: Path):
    import xml.etree.ElementTree as ET
    con = sqlite3.connect(db_path); cur = con.cursor()
    cur.execute("""SELECT title, autor, fecha_text, lugar, idioma, resumen FROM document WHERE id=?""", (doc_id,))
    doc = cur.fetchone()
    if not doc: con.close(); return False
    title, autor, fecha, lugar, idioma, resumen = doc
    root = ET.Element("TEI", {"xmlns":"http://www.tei-c.org/ns/1.0"})
    teiHeader = ET.SubElement(root, "teiHeader")
    fileDesc = ET.SubElement(teiHeader, "fileDesc")
    titleStmt = ET.SubElement(fileDesc, "titleStmt"); ET.SubElement(titleStmt, "title").text = title or ""
    if autor: ET.SubElement(titleStmt, "author").text = autor
    pubStmt = ET.SubElement(fileDesc, "publicationStmt"); ET.SubElement(pubStmt, "publisher").text = "GeoDocs"
    sourceDesc = ET.SubElement(fileDesc, "sourceDesc"); ET.SubElement(sourceDesc, "p").text = resumen or ""
    text = ET.SubElement(root, "text"); body = ET.SubElement(text, "body")
    # Pages as divs with OCR (if any)
    for (seq, txt, pdf) in sqlite3.connect(db_path).execute("SELECT seq, ocr_txt_path, ocr_pdf_path FROM page WHERE document_id=? ORDER BY seq", (doc_id,)):
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
    con.close(); return True

def export_mets_alto(db_path: Path, doc_id: int, out_dir: Path):
    # Creates a simple METS-like XML and ALTO XML per page (simplified)
    import xml.etree.ElementTree as ET
    out_dir.mkdir(parents=True, exist_ok=True)
    mets = ET.Element("mets")
    fileSec = ET.SubElement(mets, "fileSec")
    filesEl = ET.SubElement(fileSec, "fileGrp", {"USE": "OCR"})
    con = sqlite3.connect(db_path); cur = con.cursor()
    cur.execute("SELECT seq, processed_path, ocr_txt_path FROM page WHERE document_id=? ORDER BY seq", (doc_id,))
    rows = cur.fetchall()
    for seq, img_path, ocr_path in rows:
        # ALTO file for this page
        alto = ET.Element("alto", {"xmlns":"http://www.loc.gov/standards/alto/ns-v4#"})
        layout = ET.SubElement(alto, "Layout"); page = ET.SubElement(layout, "Page", {"ID": f"p{seq}"})
        textblock = ET.SubElement(page, "PrintSpace")
        if ocr_path and Path(ocr_path).exists():
            try:
                text = Path(ocr_path).read_text(encoding="utf-8")
            except:
                text = ""
        else:
            text = ""
        # Minimal: one TextBlock with one TextLine
        tb = ET.SubElement(textblock, "TextBlock", {"ID": f"tb{seq}"})
        tl = ET.SubElement(tb, "TextLine", {"ID": f"tl{seq}"})
        ET.SubElement(tl, "String", {"CONTENT": text[:10000]})
        alto_path = out_dir / f"alto_{seq:04d}.xml"
        ET.ElementTree(alto).write(alto_path, encoding="utf-8", xml_declaration=True)
        # METS file entry
        ET.SubElement(filesEl, "file", {"ID": f"f{seq}", "SEQ": str(seq)}).text = str(alto_path)
    mets_path = out_dir / "mets.xml"
    ET.ElementTree(mets).write(mets_path, encoding="utf-8", xml_declaration=True)
    con.close()
    return True


def export_project_report(db_path: Path, doc_id: int, out_pdf: Path, logo_path: Path=None):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    c = canvas.Canvas(str(out_pdf), pagesize=A4)
    W, H = A4
    y = H - 2*cm
    # Header with logo
    if logo_path and logo_path.exists():
        try:
            c.drawImage(str(logo_path), 2*cm, y-1.5*cm, width=2*cm, height=1.5*cm, preserveAspectRatio=True, mask='auto')
        except: pass
    c.setFont("Helvetica-Bold", 16); c.drawString(4.4*cm, y-0.5*cm, "GeoDocs — Informe de Proyecto")
    y -= 2.2*cm
    # Load document metadata
    con = sqlite3.connect(db_path); cur = con.cursor()
    cur.execute("""SELECT d.title, d.autor, d.fecha_text, d.tipo, d.signatura, d.tema, d.etiquetas, d.lugar, d.idioma, d.derechos,
                          a.nombre, f.nombre, p.base_dir, d.resumen
                   FROM document d
                   LEFT JOIN project p ON p.id=d.project_id
                   LEFT JOIN archivo a ON a.id=d.archivo_id
                   LEFT JOIN fondo f ON f.id=d.fondo_id
                   WHERE d.id=?""", (doc_id,))
    row = cur.fetchone()
    if not row:
        con.close(); return False
    (title, autor, fecha, tipo, signatura, tema, etiquetas, lugar, idioma, derechos, archivo_nombre, fondo_nombre, base_dir, resumen) = row
    # Summary block
    c.setFont("Helvetica-Bold", 12); c.drawString(2*cm, y, "Resumen")
    c.setFont("Helvetica", 10); y -= 0.6*cm
    text = c.beginText(2*cm, y)
    text.textLines(resumen or "-")
    c.drawText(text)
    y -= (min(6, (len((resumen or '').split())//20)+1))*0.5*cm
    y -= 0.4*cm
    # Metadata block
    c.setFont("Helvetica-Bold", 12); c.drawString(2*cm, y, "Metadatos")
    y -= 0.6*cm; c.setFont("Helvetica", 10)
    meta_lines = [
        ("Título", title), ("Autor", autor), ("Fecha", fecha), ("Tipo", tipo),
        ("Archivo", archivo_nombre), ("Fondo", fondo_nombre), ("Signatura", signatura),
        ("Tema", tema), ("Etiquetas", etiquetas), ("Lugar", lugar), ("Idioma", idioma), ("Derechos", derechos),
        ("Carpeta", base_dir)
    ]
    for k,v in meta_lines:
        c.drawString(2*cm, y, f"{k}: {v or '-'}"); y -= 0.45*cm
        if y < 4*cm: c.showPage(); y = H - 2*cm
    # Stats
    c.setFont("Helvetica-Bold", 12); c.drawString(2*cm, y, "Estadísticas")
    y -= 0.6*cm; c.setFont("Helvetica", 10)
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN ocr_txt_path IS NOT NULL THEN 1 ELSE 0 END) FROM page WHERE document_id=?", (doc_id,))
    n_pages, n_ocr = cur.fetchone()
    c.drawString(2*cm, y, f"Páginas: {n_pages or 0} | OCR: {n_ocr or 0}"); y -= 0.5*cm
    # Thumbnails (just list filenames)
    c.setFont("Helvetica-Bold", 12); c.drawString(2*cm, y, "Páginas")
    y -= 0.6*cm; c.setFont("Helvetica", 9)
    for (seq, processed_path, hashv) in cur.execute("SELECT seq, processed_path, hash_sha256 FROM page WHERE document_id=? ORDER BY seq", (doc_id,)):
        c.drawString(2*cm, y, f"{seq:04d} — {processed_path or '(sin archivo)'}  [{hashv or 'sin hash'}]"); y -= 0.38*cm
        if y < 2*cm: c.showPage(); y = H - 2*cm
    con.close()
    c.showPage(); c.save()
    return True


# ------- Environment profiles (dev/prod) -------
def load_profile_file(name: str):
    path = BASE_DIR / f"config.{name}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f: 
            return json.load(f)
    return None

def activate_profile(name: str):
    prof = load_profile_file(name)
    if not prof:
        raise RuntimeError(f"Perfil no encontrado: {name}")
    # Overwrite active config
    CONFIG_PATH.write_text(json.dumps(prof, indent=2), encoding="utf-8")
    return prof

def try_ping(api: GeoDocsAPI):
    # Try GET to /health if exists, else to pull_documents endpoint
    try:
        ep = api.map.get("endpoints",{}).get("pull_documents","/api/documentos")
        # if base has /health, prefer it
        url_health = api.base() + "/health"
        try:
            r = requests.get(url_health, headers=api.headers(), timeout=3, verify=api.verify())
            if r.status_code < 500:
                return True, "health"
        except Exception:
            pass
        r = requests.get(api.base()+ep, headers=api.headers(), timeout=3, verify=api.verify())
        return (r.status_code < 500), "endpoint"
    except Exception:
        return False, "error"

def detect_environment():
    # Preference: dev first (localhost), then prod
    dev = load_profile_file("dev")
    prod = load_profile_file("prod")
    # Try dev
    if dev:
        tmp = GeoDocsAPI()
        tmp.save_config(dev)
        ok, src = try_ping(tmp)
        if ok:
            return "development", dev
    # Try prod
    if prod:
        tmp = GeoDocsAPI()
        tmp.save_config(prod)
        ok, src = try_ping(tmp)
        if ok:
            return "production", prod
    return None, None


# ---------- Utilities ----------
def db_connect():
    return sqlite3.connect(GLOBAL_DB)

def ensure_schema():
    with db_connect() as con:
        cur=con.cursor()
        # Tables
        cur.execute("""CREATE TABLE IF NOT EXISTS archivo (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          nombre TEXT UNIQUE NOT NULL,
          sigla TEXT, ubicacion TEXT, direccion TEXT, contacto TEXT, telefono TEXT, email TEXT, web TEXT, descripcion TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS fondo (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          archivo_id INTEGER REFERENCES archivo(id),
          nombre TEXT NOT NULL,
          rango_fechas TEXT, volumen TEXT, nivel_descripcion TEXT, descripcion TEXT, notas TEXT,
          UNIQUE(archivo_id, nombre)
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS project (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT, base_dir TEXT, created_at TEXT, remote_id TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS document (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER REFERENCES project(id),
          title TEXT, signatura TEXT, archivo_id INTEGER, fondo_id INTEGER,
          tema TEXT, etiquetas TEXT, tipo TEXT, autor TEXT, fecha_text TEXT,
          lugar TEXT, idioma TEXT, derechos TEXT, referencia_bibliografica TEXT, resumen TEXT, notas_internas TEXT,
          remote_id TEXT, last_sync TEXT, created_at TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS page (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          document_id INTEGER REFERENCES document(id),
          seq INTEGER, src_path TEXT, processed_path TEXT, ocr_txt_path TEXT, ocr_pdf_path TEXT, created_at TEXT,
          remote_id TEXT, remote_url TEXT, ocr_url TEXT, downloaded INTEGER DEFAULT 0
        )""")
        con.commit()
        # Ensure columns (for upgrades)
        def ensure_column(table, col, decl):
            cur.execute(f"PRAGMA table_info({table})"); cols=[c[1] for c in cur.fetchall()]
            if col not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        ensure_column("project","remote_id","TEXT")
        for t,c in [("document","remote_id TEXT"),("document","last_sync TEXT"),
                    ("page","remote_id TEXT"),("page","remote_url TEXT"),("page","ocr_url TEXT"),("page","downloaded INTEGER DEFAULT 0")]:
            parts=c.split()
            ensure_column(t, parts[0], " ".join(parts[1:]))
        con.commit()

def list_cameras_with_names(max_devices=10):
    names={}; sys=platform.system().lower()
    if sys=="linux":
        for i in range(max_devices):
            dev=f"/sys/class/video4linux/video{i}/name"
            if os.path.exists(dev):
                try:
                    with open(dev,"r",encoding="utf-8",errors="ignore") as f: names[i]=f.read().strip()
                except: pass
    elif sys=="darwin":
        try:
            text=subprocess.check_output(["system_profiler","SPCameraDataType"], text=True, stderr=subprocess.DEVNULL, timeout=2); idx=0
            for line in text.splitlines():
                line=line.strip()
                if line and not line.startswith("System Information") and ": " not in line and not line.startswith("Models:"):
                    if idx<max_devices: names[idx]=line; idx+=1
        except: pass
    else:
        try:
            out=subprocess.check_output(["wmic","path","Win32_PnPEntity","where","PNPClass='Camera'","get","Name"], text=True, stderr=subprocess.DEVNULL, timeout=2); idx=0
            for line in out.splitlines():
                line=line.strip()
                if line and line.lower()!="name":
                    if idx<max_devices: names[idx]=line; idx+=1
        except:
            try:
                out=subprocess.check_output(["powershell","-NoProfile","-Command","Get-CimInstance Win32_PnPEntity -Filter \"PNPClass='Camera'\" | Select-Object -ExpandProperty Name"], text=True, stderr=subprocess.DEVNULL, timeout=2); idx=0
                for line in out.splitlines():
                    line=line.strip()
                    if line:
                        if idx<max_devices: names[idx]=line; idx+=1
            except: pass
    valid=[]
    for i in range(max_devices):
        cap=cv2.VideoCapture(i, cv2.CAP_DSHOW if sys=="windows" else 0)
        ok,_=cap.read()
        if ok: valid.append(i)
        cap.release()
    return [(i, names.get(i, f"Cámara {i}")) for i in valid] or [(0,"Cámara 0")]

# ---------- REST API + Mapping ----------
class GeoDocsAPI:
    def __init__(self):
        self.config = self.load_config()
        self.map = self.load_map()
    # Config
    def load_config(self):
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        d={"api_base_url":"", "api_key":"", "verify_tls":True, "timeout_sec":20}
        CONFIG_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")
        return d
    def save_config(self, cfg): self.config=cfg; CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    # Mapping
    def load_map(self):
        if API_MAP_PATH.exists():
            return json.loads(API_MAP_PATH.read_text(encoding="utf-8"))
        m={"endpoints":{},"field_map":{"document":{},"page":{}}}
        API_MAP_PATH.write_text(json.dumps(m, indent=2), encoding="utf-8")
        return m
    def save_map(self, m): self.map=m; API_MAP_PATH.write_text(json.dumps(m, indent=2), encoding="utf-8")

    # HTTP helpers
    def headers(self):
        h={"Content-Type":"application/json"}
        if (self.config.get("auth") or "").lower()=="jwt":
            tok=self.config.get("jwt_token") or ""
            if tok: h["Authorization"]=f"Bearer {tok}"
        else:
            key=self.config.get("api_key") or ""
            if key: h["Authorization"]=f"Bearer {key}"
        return h
    def base(self): return (self.config.get("api_base_url") or "").rstrip("/")
    def timeout(self): return int(self.config.get("timeout_sec", 20))
    def verify(self): return bool(self.config.get("verify_tls", True))
    def get(self, path, params=None):
        url=f"{self.base()}{path}"
        r=requests.get(url, headers=self.headers(), params=params or {}, timeout=self.timeout(), verify=self.verify())
        r.raise_for_status(); return r.json()
    def post(self, path, payload):
        url=f"{self.base()}{path}"
        r=requests.post(url, headers=self.headers(), json=payload, timeout=self.timeout(), verify=self.verify())
        r.raise_for_status(); return r.json()

    # Mapping helpers
    def map_local_to_remote_doc(self, doc:dict):
        fmap=self.map.get("field_map",{}).get("document",{})
        out={}
        for local, remote in fmap.items():
            out[remote]=doc.get(local)
        return out
    def map_local_to_remote_page(self, page:dict):
        fmap=self.map.get("field_map",{}).get("page",{})
        out={}
        for local, remote in fmap.items():
            out[remote]=page.get(local)
        return out
    def map_remote_to_local_doc(self, remote:dict):
        fmap=self.map.get("field_map",{}).get("document",{})
        inv={v:k for k,v in fmap.items()}
        out={}
        for rk, rv in remote.items():
            if rk in inv: out[inv[rk]]=rv
        return out
    def map_remote_to_local_page(self, remote:dict):
        fmap=self.map.get("field_map",{}).get("page",{})
        inv={v:k for k,v in fmap.items()}
        out={}
        for rk, rv in remote.items():
            if rk in inv: out[inv[rk]]=rv
        return out


def search_toponimos(self, q):
    ep = "/api/toponimos"
    return self.get(ep, params={"search": q})
def search_personas(self, q):
    ep = "/api/personas"
    return self.get(ep, params={"search": q})
def push_annotations(self, doc_id:int):
    # push all local annotations for document
    with db_connect() as con:
        con.row_factory=sqlite3.Row
        rows = list(con.execute("SELECT * FROM annotation WHERE document_id=?", (doc_id,)))
    ep = "/api/anotaciones"
    return self.post(ep, {"document_id": doc_id, "annotations": [dict(r) for r in rows]})

# ---------- Mapping CRUD / Validator ----------
class APIMapperDialog(Toplevel):
    def __init__(self, master, api:GeoDocsAPI):
        super().__init__(master); self.api=api
        self.title("Editar mapeo de endpoints y campos (GeoDocs API)")
        self.geometry("900x560")
        nb = ttk.Notebook(self); nb.pack(fill=BOTH, expand=True)

        # Tab: Endpoints
        self.tab_ep = Frame(nb); nb.add(self.tab_ep, text="Endpoints")
        self.tree_ep = ttk.Treeview(self.tab_ep, columns=("key","path"), show="headings")
        self.tree_ep.heading("key", text="Clave"); self.tree_ep.heading("path", text="Ruta/Endpoint")
        self.tree_ep.column("key", width=200); self.tree_ep.column("path", width=560)
        self.tree_ep.pack(fill=BOTH, expand=True, padx=6, pady=6)
        btns_ep = Frame(self.tab_ep); btns_ep.pack(fill=X)
        Button(btns_ep, text="Añadir", command=self.add_ep).pack(side=LEFT, padx=4)
        Button(btns_ep, text="Editar", command=self.edit_ep).pack(side=LEFT, padx=4)
        Button(btns_ep, text="Eliminar", command=self.del_ep).pack(side=LEFT, padx=4)
        Button(btns_ep, text="Guardar", command=self.save_all).pack(side=RIGHT, padx=4)
        Button(btns_ep, text="Probar conexión (pull_archives)", command=self.ping).pack(side=RIGHT, padx=4)

        # Tab: Field Map - Document
        self.tab_doc = Frame(nb); nb.add(self.tab_doc, text="Field Map — document")
        self.tree_doc = ttk.Treeview(self.tab_doc, columns=("local","remote"), show="headings")
        self.tree_doc.heading("local", text="Campo local (DB)"); self.tree_doc.heading("remote", text="Campo remoto (API)")
        self.tree_doc.column("local", width=260); self.tree_doc.column("remote", width=420)
        self.tree_doc.pack(fill=BOTH, expand=True, padx=6, pady=6)
        btns_doc = Frame(self.tab_doc); btns_doc.pack(fill=X)
        Button(btns_doc, text="Añadir", command=lambda: self.add_map(self.tree_doc, "document")).pack(side=LEFT, padx=4)
        Button(btns_doc, text="Editar", command=lambda: self.edit_map(self.tree_doc, "document")).pack(side=LEFT, padx=4)
        Button(btns_doc, text="Eliminar", command=lambda: self.del_map(self.tree_doc)).pack(side=LEFT, padx=4)
        Button(btns_doc, text="Guardar", command=self.save_all).pack(side=RIGHT, padx=4)

        # Tab: Field Map - Page
        self.tab_page = Frame(nb); nb.add(self.tab_page, text="Field Map — page")
        self.tree_page = ttk.Treeview(self.tab_page, columns=("local","remote"), show="headings")
        self.tree_page.heading("local", text="Campo local (DB)"); self.tree_page.heading("remote", text="Campo remoto (API)")
        self.tree_page.column("local", width=260); self.tree_page.column("remote", width=420)
        self.tree_page.pack(fill=BOTH, expand=True, padx=6, pady=6)
        btns_page = Frame(self.tab_page); btns_page.pack(fill=X)
        Button(btns_page, text="Añadir", command=lambda: self.add_map(self.tree_page, "page")).pack(side=LEFT, padx=4)
        Button(btns_page, text="Editar", command=lambda: self.edit_map(self.tree_page, "page")).pack(side=LEFT, padx=4)
        Button(btns_page, text="Eliminar", command=lambda: self.del_map(self.tree_page)).pack(side=LEFT, padx=4)
        Button(btns_page, text="Guardar", command=self.save_all).pack(side=RIGHT, padx=4)

        # Tab: Validator
        self.tab_val = Frame(nb); nb.add(self.tab_val, text="Validar esquema")
        Label(self.tab_val, text="Comprueba que todos los campos locales tienen mapeo remoto.").pack(side=TOP, pady=6)
        Button(self.tab_val, text="Validar correspondencia", command=self.validate_schema).pack(side=TOP, pady=4)
        self.tree_val = ttk.Treeview(self.tab_val, columns=("tabla","campo","estado"), show="headings")
        for c,w in [("tabla",120),("campo",220),("estado",420)]:
            self.tree_val.heading(c, text=c.upper()); self.tree_val.column(c, width=w, anchor="w")
        self.tree_val.pack(fill=BOTH, expand=True, padx=6, pady=6)

        self.load_to_ui()

    def load_to_ui(self):
        # endpoints
        for i in self.tree_ep.get_children(): self.tree_ep.delete(i)
        for k,v in self.api.map.get("endpoints",{}).items():
            self.tree_ep.insert("", END, values=(k,v))
        # maps
        for t, tree in [("document", self.tree_doc), ("page", self.tree_page)]:
            for i in tree.get_children(): tree.delete(i)
            for loc, rem in self.api.map.get("field_map",{}).get(t,{}).items():
                tree.insert("", END, values=(loc, rem))

    # endpoints CRUD
    def add_ep(self):
        self._edit_kv(self.tree_ep, title="Añadir endpoint", defaults=("", "/api/..."))
    def edit_ep(self):
        sel=self.tree_ep.selection(); if not sel: return
        vals=self.tree_ep.item(sel[0])["values"]; self._edit_kv(self.tree_ep, title="Editar endpoint", defaults=vals)
    def del_ep(self):
        sel=self.tree_ep.selection(); 
        if not sel: return
        self.tree_ep.delete(sel[0])
    # map CRUD
    def add_map(self, tree, section):
        self._edit_kv(tree, title=f"Añadir mapeo ({section})", defaults=("", ""))
    def edit_map(self, tree, section):
        sel=tree.selection(); if not sel: return
        vals=tree.item(sel[0])["values"]; self._edit_kv(tree, title=f"Editar mapeo ({section})", defaults=vals)
    def del_map(self, tree):
        sel=tree.selection(); 
        if not sel: return
        tree.delete(sel[0])

    def _edit_kv(self, tree, title, defaults):
        win=Toplevel(self); win.title(title)
        Label(win, text="Clave / Local:").grid(row=0,column=0,sticky="e",padx=6,pady=6)
        Label(win, text="Valor / Remoto:").grid(row=1,column=0,sticky="e",padx=6,pady=6)
        e_k=Entry(win, width=40); e_v=Entry(win, width=60)
        e_k.grid(row=0,column=1,padx=6,pady=6); e_v.grid(row=1,column=1,padx=6,pady=6)
        e_k.insert(0, defaults[0]); e_v.insert(0, defaults[1])
        def save():
            # replace if exists selected, else insert new
            sel=tree.selection()
            if sel:
                tree.item(sel[0], values=(e_k.get().strip(), e_v.get().strip()))
            else:
                tree.insert("", END, values=(e_k.get().strip(), e_v.get().strip()))
            win.destroy()
        Button(win, text="Guardar", command=save).grid(row=2,column=1,sticky="e",padx=6,pady=6)

    def save_all(self):
        # gather to map
        m={"endpoints":{}, "field_map":{"document":{}, "page":{}}}
        for iid in self.tree_ep.get_children():
            k,v=self.tree_ep.item(iid)["values"]
            if k: m["endpoints"][str(k)]=str(v)
        for t, tree in [("document", self.tree_doc), ("page", self.tree_page)]:
            for iid in tree.get_children():
                loc, rem = tree.item(iid)["values"]
                if loc: m["field_map"][t][str(loc)]=str(rem)
        self.api.save_map(m)
        messagebox.showinfo("Mapeo", "Guardado correctamente.")

    def ping(self):
        try:
            ep=self.api.map.get("endpoints",{}).get("pull_archives")
            if not ep: raise RuntimeError("Endpoint pull_archives no definido")
            data = self.api.get(ep)
            messagebox.showinfo("Ping OK", f"Respuesta:\n{str(data)[:800]}...")
        except Exception as ex:
            messagebox.showerror("Error de conexión", f"{ex}")

    def validate_schema(self):
        # compare DB fields vs field_map
        with db_connect() as con:
            cur=con.cursor()
            def cols(table):
                cur.execute(f"PRAGMA table_info({table})"); return [r[1] for r in cur.fetchall()]
            doc_cols=cols("document"); page_cols=cols("page")
        mapped_doc=set(self.api.map.get("field_map",{}).get("document",{}).keys())
        mapped_page=set(self.api.map.get("field_map",{}).get("page",{}).keys())
        for i in self.tree_val.get_children(): self.tree_val.delete(i)
        # document
        for c in doc_cols:
            state = "✅ Mapeado" if c in mapped_doc else "⚠️ Sin mapeo"
            self.tree_val.insert("", END, values=("document", c, state))
        # page
        for c in page_cols:
            state = "✅ Mapeado" if c in mapped_page else "⚠️ Sin mapeo"
            self.tree_val.insert("", END, values=("page", c, state))
        messagebox.showinfo("Validación", "Validación completada. Revisa la tabla de resultados.")

# ---------- Pull documents (metadata only) & download images ----------
class DocumentPullDialog(Toplevel):
    def __init__(self, master, api:GeoDocsAPI):
        super().__init__(master); self.api=api; self.title("Descargar documentos (solo metadatos)")
        self.geometry("1000x600")
        # Filters
        filt=Frame(self); filt.pack(fill=X, pady=4)
        Label(filt, text="Buscar título:").pack(side=LEFT, padx=4)
        self.e_title=Entry(filt, width=28); self.e_title.pack(side=LEFT, padx=4)
        Button(filt, text="Buscar", command=self.search).pack(side=LEFT, padx=6)
        Button(filt, text="Importar seleccionado (metadatos)", command=self.import_selected).pack(side=LEFT, padx=10)
        Button(filt, text="Descargar imágenes…", command=self.download_images_for_selected).pack(side=LEFT, padx=10)

        # Results
        self.tree = ttk.Treeview(self, columns=("remote_id","archivo","fondo","titulo","autor","fecha","estado"), show="headings")
        for c,w in [("remote_id",120),("archivo",200),("fondo",200),("titulo",260),("autor",160),("fecha",110),("estado",120)]:
            self.tree.heading(c, text=c.upper()); self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill=BOTH, expand=True, padx=6, pady=6)

        self.remote_docs = []  # store raw for import

        self.search()

    def search(self):
        try:
            ep=self.api.map.get("endpoints",{}).get("pull_documents")
            if not ep: raise RuntimeError("Endpoint pull_documents no definido. Edítalo en el mapeador.")
            params={}
            title = self.e_title.get().strip()
            if title: params["q"]=title
            data=self.api.get(ep, params=params)
            self.remote_docs = data.get("documents", data if isinstance(data, list) else [])
            for i in self.tree.get_children(): self.tree.delete(i)
            for item in self.remote_docs:
                # Try to resolve human labels
                rid = item.get("id") or item.get("id_remoto") or item.get("remote_id") or ""
                archivo = item.get("archivo") or item.get("archivo_nombre") or ""
                fondo = item.get("fondo") or item.get("fondo_nombre") or ""
                titulo = item.get("title") or item.get("titulo") or ""
                autor = item.get("autor") or ""
                fecha = item.get("fecha") or item.get("fecha_text") or ""
                estado = "No importado"
                self.tree.insert("", END, values=(rid, archivo, fondo, titulo, autor, fecha, estado))
        except Exception as ex:
            messagebox.showerror("Pull", f"Error obteniendo lista: {ex}")

    def import_selected(self):
        sel=self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        item = self.remote_docs[idx]
        # Map remote -> local
        loc = self.api.map_remote_to_local_doc(item)
        # Ask for local project dir
        proj_dir = filedialog.askdirectory(title="Selecciona carpeta donde crear el proyecto local")
        if not proj_dir: return
        base_dir = Path(proj_dir) / (self._slug(loc.get("title") or "documento"))
        for sub in ["raw","processed","ocr","pdf"]:
            (base_dir / sub).mkdir(parents=True, exist_ok=True)
        # Insert into DB
        with db_connect() as con:
            cur=con.cursor()
            cur.execute("INSERT INTO project (name, base_dir, created_at, remote_id) VALUES (?,?,?,?)",
                        (loc.get("title"), str(base_dir), datetime.now().isoformat(), item.get("id") or item.get("id_remoto") or item.get("remote_id")))
            pid = cur.lastrowid
            cur.execute("""INSERT INTO document (project_id, title, signatura, archivo_id, fondo_id, tema, etiquetas, tipo, autor, fecha_text,
                           lugar, idioma, derechos, referencia_bibliografica, resumen, notas_internas, remote_id, last_sync, created_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (pid, loc.get("title"), loc.get("signatura"), loc.get("archivo_id"), loc.get("fondo_id"),
                         loc.get("tema"), loc.get("etiquetas"), loc.get("tipo"), loc.get("autor"), loc.get("fecha_text"),
                         loc.get("lugar"), loc.get("idioma"), loc.get("derechos"), loc.get("referencia_bibliografica"), loc.get("resumen"),
                         loc.get("notas_internas"), item.get("id") or item.get("id_remoto") or item.get("remote_id"),
                         datetime.now().isoformat(), datetime.now().isoformat()))
            did = cur.lastrowid
            # Pages metadata only (if provided)
            pages = item.get("pages") or item.get("paginas") or []
            for k, rp in enumerate(pages):
                lp = self.api.map_remote_to_local_page(rp)
                cur.execute("""INSERT INTO page (document_id, seq, src_path, processed_path, ocr_txt_path, ocr_pdf_path, created_at,
                              remote_id, remote_url, ocr_url, downloaded) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                            (did, lp.get("seq", k), None, None, None, None, datetime.now().isoformat(),
                             lp.get("remote_id") or rp.get("id") or None, lp.get("remote_url") or rp.get("url_imagen") or None,
                             lp.get("ocr_url") or rp.get("url_ocr") or None, 0))
            con.commit()
        messagebox.showinfo("Importación", f"Proyecto creado en {base_dir} (metadatos importados).")
        self.search()

    def download_images_for_selected(self):
        sel=self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        item = self.remote_docs[idx]
        # Find local document by remote_id
        rid = item.get("id") or item.get("id_remoto") or item.get("remote_id")
        if not rid:
            messagebox.showwarning("Descarga", "No se encontró remote_id en el documento."); return
        with db_connect() as con:
            cur=con.cursor()
            cur.execute("""SELECT d.id, p.base_dir FROM document d
                           LEFT JOIN project p ON p.id=d.project_id WHERE d.remote_id=?""", (str(rid),))
            row = cur.fetchone()
            if not row:
                messagebox.showwarning("Descarga", "Primero importa el documento (metadatos)."); return
            doc_id, base_dir = row
            base_dir = Path(base_dir)
            processed = base_dir / "processed"; processed.mkdir(exist_ok=True, parents=True)
            ocrdir = base_dir / "ocr"; ocrdir.mkdir(exist_ok=True, parents=True)

            headers=self.api.headers()
            count=0
            for (pid, seq, remote_url, ocr_url) in con.execute("SELECT id, seq, remote_url, ocr_url FROM page WHERE document_id=? AND downloaded=0 ORDER BY seq", (doc_id,)):
                if remote_url:
                    try:
                        r=requests.get(remote_url, headers=headers, timeout=self.api.timeout(), verify=self.api.verify())
                        r.raise_for_status()
                        fname=f"page_{seq:04d}.jpg"
                        out_path = processed / fname
                        out_path.write_bytes(r.content)
                        # Update
                        con.execute("UPDATE page SET processed_path=?, downloaded=1 WHERE id=?", (str(out_path), pid))
                        count += 1
                    except Exception as ex:
                        print("Error descargando imagen:", ex)
                if ocr_url:
                    try:
                        r=requests.get(ocr_url, headers=headers, timeout=self.api.timeout(), verify=self.api.verify())
                        r.raise_for_status()
                        ext=".pdf" if "pdf" in r.headers.get("content-type","").lower() else ".txt"
                        fname=f"page_{seq:04d}{ext}"
                        out_path = ocrdir / fname
                        out_path.write_bytes(r.content)
                        con.execute("UPDATE page SET ocr_pdf_path=? WHERE id=?", (str(out_path), pid))
                    except Exception as ex:
                        print("Error descargando OCR:", ex)
            con.commit()
        messagebox.showinfo("Descarga", f"Imágenes descargadas: {count}")

    def _slug(self, t):
        import re; s=re.sub(r'[^a-z0-9]+','-', (t or '').strip().lower()); s=re.sub(r'-+','-',s).strip('-'); return s or "documento"

# ---------- Simple Fullscreen preview ----------
class FullscreenPreview:
    def __init__(self, master, original_bgr, processed_bgr, title_text="Previsualización"):
        self.top=Toplevel(master); self.top.title(title_text); self.top.attributes("-fullscreen", True); self.top.configure(bg="black")
        self.canvas=Canvas(self.top,bg="black",highlightthickness=0); self.canvas.pack(fill=BOTH, expand=True)
        self.orig=cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB); self.proc=cv2.cvtColor(processed_bgr, cv2.COLOR_BGR2RGB)
        self.scale=1.0; self.offx=0; self.offy=0
        self.top.bind("<Escape>", lambda e: self.top.destroy()); self.top.bind("<Button-3>", lambda e: self.top.destroy())
        self.top.bind("<MouseWheel>", self.on_zoom); self.canvas.bind("<ButtonPress-1>", self.start_pan); self.canvas.bind("<B1-Motion>", self.do_pan)
        self.redraw()
    def start_pan(self, e): self._start=(e.x,e.y)
    def do_pan(self, e): dx=e.x-self._start[0]; dy=e.y-self._start[1]; self.offx+=dx; self.offy+=dy; self._start=(e.x,e.y); self.redraw()
    def on_zoom(self, e): self.scale=max(0.1, min(6.0, self.scale*(1.1 if e.delta>0 else 0.9))); self.redraw()
    def redraw(self):
        cw=self.canvas.winfo_width() or 800; ch=self.canvas.winfo_height() or 600; self.canvas.delete("all")
        h,w,_=self.orig.shape; fit=min(cw/(w*2), ch/h); s=fit*self.scale; nw=max(1,int(w*s)); nh=max(1,int(h*s))
        o=Image.fromarray(self.orig).resize((nw,nh)); p=Image.fromarray(self.proc).resize((nw,nh))
        self.tko=ImageTk.PhotoImage(o); self.tkp=ImageTk.PhotoImage(p); gap=4; total=nw*2+gap; sx=(cw-total)//2+int(self.offx); sy=(ch-nh)//2+int(self.offy)
        self.canvas.create_image(sx+nw//2, sy+nh//2, image=self.tko); self.canvas.create_image(sx+nw+gap+nw//2, sy+nh//2, image=self.tkp)

# ---------- Main App ----------
class App:
    def __init__(self, root):
        ensure_schema(); self.api=GeoDocsAPI()
        self.root=root; root.title(APP_NAME); root.geometry("1500x940")
        self.output_dir=Path.cwd()/ "output_tk"; self.output_dir.mkdir(exist_ok=True)
        self.cap=None; self.frame_bgr=None; self.last_color=None
        self.photo_preview=None; self.photo_result=None; self.manual_points=[]; self.scale_preview=1.0
        self.saved_images=[]; self.project_root=None; self.project_id=None; self.doc_id=None

        # Metadata
        self.title_var=StringVar(value="Documento GeoDocs"); self.author_var=StringVar(value="Autor")
        self.sig_var=StringVar(value="Signatura"); self.tema_var=StringVar(value=""); self.etiquetas_var=StringVar(value="")
        self.tipo_var=StringVar(value="libro"); self.fecha_var=StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.lugar_var=StringVar(value=""); self.idioma_var=StringVar(value="spa"); self.derechos_var=StringVar(value="Uso interno")
        self.refbib_var=StringVar(value=""); self.resumen_var=StringVar(value=""); self.notas_var=StringVar(value="")
        self.dewarp_mode=StringVar(value="mesh"); self.dewarp_strength=DoubleVar(value=0.22)
        self.contrast_mode=StringVar(value="clahe"); self.final_scale=DoubleVar(value=1.0)
        self.ocr_enabled=IntVar(value=0); self.ocr_lang=StringVar(value="spa+eng")
        self.mesh_cols=IntVar(value=10); self.mesh_rows=IntVar(value=12); self.asymmetric_mesh=IntVar(value=1); self.capture_mode=StringVar(value="double")
        self.cam_list=list_cameras_with_names(); self.exposure_var=DoubleVar(value=-6.0); self.wb_var=IntVar(value=4500)

        # Menus
        menubar=Menu(root)
        m_api=Menu(menubar, tearoff=0)
        m_api.add_command(label="Ajustes API…", command=self.open_api_config)
        m_api.add_command(label="Editar mapeo de endpoints…", command=lambda: APIMapperDialog(root, self.api))
        m_api.add_command(label="Validar mapeo/DB…", command=self.open_validator)
        m_api.add_separator()
        m_api.add_command(label="Descargar documentos (pull)…", command=lambda: DocumentPullDialog(root, self.api))
        m_api.add_command(label="Descargar imágenes…", command=self.download_images_menu)
        m_api.add_separator()
        m_api.add_command(label="Subir Documento + Páginas (push)…", command=self.api_push_document)
        menubar.add_cascade(label="GeoDocs API", menu=m_api)
        
        m_exp=Menu(menubar, tearoff=0)
        m_exp.add_command(label="Exportar EAD3 (XML)…", command=self.export_ead)
        m_exp.add_command(label="Exportar Dublin Core (JSON-LD)…", command=self.export_dc)
        m_exp.add_command(label="Exportar TEI-XML (OCR)…", command=self.export_tei)
        m_exp.add_command(label="Exportar METS/ALTO…", command=self.export_mets_alto)
        m_exp.add_command(label="Exportar GeoJSON…", command=self.export_geojson)
        m_exp.add_command(label="Exportar IIIF Presentation 3.0…", command=self.export_iiif_manifest)
        m_exp.add_command(label="Exportar Linked Places (GeoJSON-LD)…", command=self.export_linked_places)
        m_exp.add_command(label="Exportar IIIF (Image API)…", command=self.export_iiif_manifest_imageapi)
        m_exp.add_command(label="Exportar IIIF Annotations (regiones)…", command=self.export_iiif_region_annotations)
        menubar.add_cascade(label="Exportar", menu=m_exp)
        m_sync=Menu(menubar, tearoff=0)
        m_sync.add_command(label="Subir OCR (documento)…", command=self.upload_ocr_document)
        m_sync.add_command(label="Subir OCR (página actual)…", command=self.upload_ocr_page)
        menubar.add_cascade(label="Sincronizar", menu=m_sync)
        m_quality=Menu(menubar, tearoff=0)
        m_quality.add_command(label="Forzar análisis de calidad (proyecto)", command=self.force_quality_batch)
        m_quality.add_command(label="Activar/Desactivar scheduler", command=self.toggle_scheduler)
        m_quality.add_command(label="Mejorar imagen (actual)...", command=self.apply_enhancer_current)
        m_quality.add_command(label="Mejorar imágenes (proyecto)...", command=self.apply_enhancer_project)
        m_quality.add_command(label="Validar calidad geométrica (proyecto)", command=self.validate_geom)
        m_quality.add_command(label="Exportar informe de calibración (PDF/HTML)", command=self.export_quality_report)
        menubar.add_cascade(label="Calidad", menu=m_quality)
        m_cal=Menu(menubar, tearoff=0)
        m_cal.add_command(label="Calibrar (A3)", command=lambda: self.run_calibration_size("A3"))
        m_cal.add_command(label="Calibrar (A4)", command=lambda: self.run_calibration_size("A4"))
        m_cal.add_command(label="Calibrar (A5)", command=lambda: self.run_calibration_size("A5"))
        m_cal.add_command(label="Calibrar (A6)", command=lambda: self.run_calibration_size("A6"))
        menubar.add_cascade(label="Calibración", menu=m_cal)
        m_cam=Menu(menubar, tearoff=0)
        m_cam.add_command(label="Activar Auto-Exposición", command=self.enable_auto_exposure)
        m_cam.add_command(label="Desactivar Auto-Exposición", command=self.disable_auto_exposure)
        m_cam.add_command(label="Ajustar exposición (auto)", command=self.auto_adjust_exposure)
        menubar.add_cascade(label="Cámara", menu=m_cam)
        m_a11y=Menu(menubar, tearoff=0)
        m_a11y.add_command(label="Zoom UI +10%", command=lambda: self.ui_zoom(1.1))
        m_a11y.add_command(label="Zoom UI -10%", command=lambda: self.ui_zoom(0.9))
        m_a11y.add_command(label="Alto contraste (toggle)", command=self.toggle_high_contrast)
        menubar.add_cascade(label="Accesibilidad", menu=m_a11y)
        m_tools=Menu(menubar, tearoff=0)
        m_tools.add_command(label="TTS (OCR original)", command=lambda: self.tts_run(False))
        m_tools.add_command(label="TTS (OCR corregido)", command=lambda: self.tts_run(True))
        m_tools.add_command(label="Revisión ortográfica (página)", command=self.spellcheck_page)
        m_tools.add_command(label="Generar TTS (página actual)", command=self.tts_generate_current)
        m_tools.add_command(label="Reproducir audio TTS...", command=self.tts_play_file)
        m_tools.add_command(label="Exportar Audiolibro (rango)", command=self.export_audiobook)
        menubar.add_cascade(label="Herramientas", menu=m_tools)
        m_style=Menu(menubar, tearoff=0)
        m_style.add_command(label="Aplicar estilo (documento)", command=self.apply_style_doc)
        m_style.add_command(label="Diff glosarios (A vs B)", command=self.diff_gloss)
        m_style.add_command(label="Merge glosarios (preferir A)", command=self.merge_gloss)
        menubar.add_cascade(label="Estilos/Glosarios", menu=m_style)
        m_help=Menu(menubar, tearoff=0)
        m_help.add_command(label="Ver tabla de abreviaturas (CSV/MD)", command=self.show_abbrev_info)
        menubar.add_cascade(label="Ayuda", menu=m_help)
        m_search=Menu(menubar, tearoff=0)
        m_search.add_command(label="Búsqueda avanzada…", command=self.open_advanced_search)
        menubar.add_cascade(label="Buscar", menu=m_search)
        m_ana=Menu(menubar, tearoff=0)
        m_ana.add_command(label="Prosopografía…", command=self.open_prosopography)
        m_ana.add_command(label="Grafo (exportar)…", command=self.export_graph_cooccurrence)
        m_ana.add_command(label="Grafo (visualizar)…", command=self.visualize_graph_cooccurrence)
        menubar.add_cascade(label="Analítica", menu=m_ana)

m_env=Menu(menubar, tearoff=0)
m_env.add_command(label="Cambiar entorno…", command=self.change_environment_dialog)
m_env.add_command(label="Autodetectar entorno", command=self.auto_detect_environment)
menubar.add_cascade(label="Entorno", menu=m_env)
        root.config(menu=menubar)

        # Top controls
        top=Frame(root); top.pack(side=TOP, fill=X)
        Label(top,text="Cámara:").pack(side=LEFT,padx=5)
        self.combo_cam=ttk.Combobox(top,state="readonly",width=34,values=[f"{i}: {n}" for i,n in self.cam_list]); self.combo_cam.current(0); self.combo_cam.pack(side=LEFT,padx=5)
        Label(top,text="Modo:").pack(side=LEFT,padx=10)
        self.combo_mode=ttk.Combobox(top,state="readonly",width=10,values=["single","double"]); self.combo_mode.set(self.capture_mode.get()); self.combo_mode.pack(side=LEFT)
        self.combo_mode.bind("<<ComboboxSelected>>", lambda e: self.capture_mode.set(self.combo_mode.get()))
        Button(top,text="Iniciar",command=self.start_camera).pack(side=LEFT,padx=8)
        Button(top,text="Detener",command=self.stop_camera).pack(side=LEFT,padx=8)
        Button(top,text="Capturar + Procesar",command=self.capture_and_process).pack(side=LEFT,padx=10)
        Button(top,text="Nuevo proyecto...",command=self.create_project_dialog).pack(side=LEFT,padx=10)
        Button(top,text="Procesar carpeta (lote)...",command=self.batch_process_dialog).pack(side=LEFT,padx=6)

        # Camera controls
        camctrl=Frame(root); camctrl.pack(side=TOP, fill=X, pady=4)
        Label(camctrl,text="Exposición:").pack(side=LEFT,padx=5)
        Scale(camctrl,from_=-13,to=0,resolution=0.5,orient=HORIZONTAL,variable=self.exposure_var,command=self.apply_camera_props,length=200).pack(side=LEFT)
        Label(camctrl,text="Balance blancos K:").pack(side=LEFT,padx=5)
        Scale(camctrl,from_=2800,to=7500,resolution=100,orient=HORIZONTAL,variable=self.wb_var,command=self.apply_camera_props,length=250).pack(side=LEFT)

        # Middle panels
        mid=Frame(root); mid.pack(side=TOP, fill=BOTH, expand=True)
        left=Frame(mid); left.pack(side=LEFT, fill=BOTH, expand=True)
        right=Frame(mid); right.pack(side=RIGHT, fill=Y)
        self.canvas_preview=Canvas(left,bg="#111",width=700,height=400); self.canvas_result=Canvas(left,bg="#111",width=700,height=400)
        self.canvas_preview.pack(side=TOP,fill=BOTH,expand=True,padx=5,pady=5); self.canvas_result.pack(side=TOP,fill=BOTH,expand=True,padx=5,pady=5)
        self.canvas_preview.bind("<Configure>", lambda e: self.redraw_preview()); self.canvas_result.bind("<Configure>", lambda e: self.redraw_result())
        Label(right,text="Páginas escaneadas").pack(side=TOP,pady=4)
        self.listbox=Listbox(right,selectmode=SINGLE,width=52,height=26); self.listbox.pack(side=TOP,padx=6,pady=4)
        btns=Frame(right); btns.pack(side=TOP,pady=4)
        Button(btns,text="↑",width=4,command=self.move_up).pack(side=LEFT,padx=2)
        Button(btns,text="↓",width=4,command=self.move_down).pack(side=LEFT,padx=2)
        Button(btns,text="Eliminar",command=self.delete_selected).pack(side=LEFT,padx=6)
        Button(btns,text="Previsualizar",command=self.preview_selected).pack(side=LEFT,padx=6)

        # Processing params
        proc=Frame(root); proc.pack(side=TOP, fill=X, pady=6)
        Label(proc,text="Descurvado:").pack(side=LEFT,padx=5)
        self.combo_dewarp=ttk.Combobox(proc,state="readonly",width=14,values=["none","cylindrical","mesh"]); self.combo_dewarp.set(self.dewarp_mode.get()); self.combo_dewarp.pack(side=LEFT,padx=5)
        self.combo_dewarp.bind("<<ComboboxSelected>>", lambda e: self.dewarp_mode.set(self.combo_dewarp.get()))
        Checkbutton(proc,text="Malla asimétrica (pliegue)",variable=self.asymmetric_mesh).pack(side=LEFT,padx=6)
        Label(proc,text="Fuerza (cilíndrico):").pack(side=LEFT,padx=5)
        Scale(proc,from_=0.10,to=0.50,resolution=0.01,orient=HORIZONTAL,variable=self.dewarp_strength,length=160).pack(side=LEFT)
        Label(proc,text="Contraste:").pack(side=LEFT,padx=5)
        self.combo_contrast=ttk.Combobox(proc,state="readonly",width=10,values=["clahe","adaptive"]); self.combo_contrast.set(self.contrast_mode.get()); self.combo_contrast.pack(side=LEFT,padx=5)
        self.combo_contrast.bind("<<ComboboxSelected>>", lambda e: self.contrast_mode.set(self.combo_contrast.get()))
        Label(proc,text="Escala:").pack(side=LEFT,padx=5)
        Scale(proc,from_=0.2,to=2.0,resolution=0.1,orient=HORIZONTAL,variable=self.final_scale,length=160).pack(side=LEFT)
        Checkbutton(proc,text="OCR",variable=self.ocr_enabled).pack(side=LEFT,padx=10)
        Label(proc,text="OCR lang:").pack(side=LEFT,padx=5); Entry(proc,textvariable=self.ocr_lang,width=10).pack(side=LEFT,padx=2)
        Label(proc,text="Malla cols/rows:").pack(side=LEFT,padx=5); ttk.Spinbox(proc,from_=4,to=18,textvariable=self.mesh_cols,width=4).pack(side=LEFT); ttk.Spinbox(proc,from_=6,to=24,textvariable=self.mesh_rows,width=4).pack(side=LEFT)

        # Metadata panel
        meta=Frame(root); meta.pack(side=TOP, fill=X, pady=4)
        Label(meta,text="Título:").pack(side=LEFT,padx=5); Entry(meta,textvariable=self.title_var,width=26).pack(side=LEFT,padx=5)
        Label(meta,text="Autor:").pack(side=LEFT,padx=5); Entry(meta,textvariable=self.author_var,width=18).pack(side=LEFT,padx=5)
        Label(meta,text="Signatura:").pack(side=LEFT,padx=5); Entry(meta,textvariable=self.sig_var,width=18).pack(side=LEFT,padx=5)

        meta2=Frame(root); meta2.pack(side=TOP, fill=X, pady=2)
        Label(meta2,text="Tema:").pack(side=LEFT,padx=5); Entry(meta2,textvariable=self.tema_var,width=20).pack(side=LEFT,padx=5)
        Label(meta2,text="Etiquetas:").pack(side=LEFT,padx=5); Entry(meta2,textvariable=self.etiquetas_var,width=18).pack(side=LEFT,padx=5)
        Label(meta2,text="Tipo:").pack(side=LEFT,padx=5); self.combo_tipo=ttk.Combobox(meta2,state="readonly",width=12,values=["libro","revista","legajo","fichas","expediente","otros"]); self.combo_tipo.set(self.tipo_var.get()); self.combo_tipo.pack(side=LEFT,padx=2)
        self.combo_tipo.bind("<<ComboboxSelected>>", lambda e: self.tipo_var.set(self.combo_tipo.get()))
        Label(meta2,text="Fecha:").pack(side=LEFT,padx=5); Entry(meta2,textvariable=self.fecha_var,width=12).pack(side=LEFT,padx=5)
        Label(meta2,text="Lugar:").pack(side=LEFT,padx=5); Entry(meta2,textvariable=self.lugar_var,width=14).pack(side=LEFT,padx=5)
        Label(meta2,text="Idioma:").pack(side=LEFT,padx=5); Entry(meta2,textvariable=self.idioma_var,width=8).pack(side=LEFT,padx=5)
        Label(meta2,text="Derechos:").pack(side=LEFT,padx=5); Entry(meta2,textvariable=self.derechos_var,width=14).pack(side=LEFT,padx=5)

        meta3=Frame(root); meta3.pack(side=TOP, fill=X, pady=2)
        Label(meta3,text="Ref. bibliográfica:").pack(side=LEFT,padx=5); Entry(meta3,textvariable=self.refbib_var,width=44).pack(side=LEFT,padx=5)
        Label(meta3,text="Resumen:").pack(side=LEFT,padx=5); Entry(meta3,textvariable=self.resumen_var,width=48).pack(side=LEFT,padx=5)

        out=Frame(root); out.pack(side=TOP, fill=X, pady=6)
        self.out_dir_var=StringVar(value=str(self.output_dir))
        Label(out,text="Salida:").pack(side=LEFT,padx=5); Entry(out,textvariable=self.out_dir_var,width=60).pack(side=LEFT,padx=5)
        Button(out,text="Cambiar carpeta...",command=self.choose_output_dir).pack(side=LEFT,padx=5)
        Button(out,text="Exportar PDF/A",command=self.export_pdf).pack(side=LEFT,padx=10)
        Button(out,text="Procesar imagen desde disco...",command=self.load_and_process_image).pack(side=LEFT,padx=10)

        self.status_var=StringVar(value="Listo — Sin proyecto"); Label(root,textvariable=self.status_var).pack(side=BOTTOM, fill=X)

        # Shortcuts
        root.bind_all("<Control-space>", lambda e: self.capture_and_process())
        root.bind_all("<Control-Delete>", lambda e: self.delete_selected())
        root.bind_all("<Control-Up>", lambda e: self.move_up())
        root.bind_all("<Control-Down>", lambda e: self.move_down())
        root.bind_all("<Control-p>", lambda e: self.preview_selected())
        root.bind_all("<Control-e>", lambda e: self.export_pdf())
        root.bind_all("<Control-q>", lambda e: self.root.destroy())

        self.root.after(30, self.update_preview_loop)

# ISAD(G) panel
isad=Frame(root); isad.pack(side=TOP, fill=X, pady=6)
Label(isad,text="ISAD(G) — Nivel:").pack(side=LEFT,padx=5)
self.isad_nivel=ttk.Combobox(isad,state="readonly",width=16,values=["Fondo","Subfondo","Serie","Subserie","Unidad documental"])
self.isad_nivel.set("Unidad documental"); self.isad_nivel.pack(side=LEFT,padx=4)
Label(isad,text="Productor:").pack(side=LEFT,padx=5); 
self.isad_productor=StringVar(value=""); Entry(isad,textvariable=self.isad_productor,width=24).pack(side=LEFT,padx=4)
Label(isad,text="Alcance y contenido:").pack(side=LEFT,padx=5); 
self.isad_alcance=StringVar(value=""); Entry(isad,textvariable=self.isad_alcance,width=40).pack(side=LEFT,padx=4)
Button(isad,text="Guardar ISAD(G)",command=self.save_isad).pack(side=LEFT,padx=10)

# Tools bar for citations & report
tools=Frame(root); tools.pack(side=TOP, fill=X, pady=6)
Button(tools,text="Cita APA",command=self.show_citation_apa).pack(side=LEFT,padx=4)
Button(tools,text="Cita ISO 690",command=self.show_citation_iso).pack(side=LEFT,padx=4)
Button(tools,text="Informe del proyecto (PDF)",command=self.export_project_pdf).pack(side=LEFT,padx=12)


    # -------- API helpers --------
    def open_api_config(self):
        dlg=Toplevel(self.root); dlg.title("Ajustes API (GeoDocs)"); dlg.geometry("520x240")
        cfg=self.api.config
        Label(dlg, text="Base URL:").grid(row=0,column=0,sticky="e",padx=6,pady=4)
        Label(dlg, text="API Key:").grid(row=1,column=0,sticky="e",padx=6,pady=4)
        Label(dlg, text="Timeout (s):").grid(row=2,column=0,sticky="e",padx=6,pady=4)
        Label(dlg, text="Verificar TLS:").grid(row=3,column=0,sticky="e",padx=6,pady=4)
        e_url=Entry(dlg,width=50); e_url.insert(0, cfg.get("api_base_url",""))
        e_key=Entry(dlg,width=50); e_key.insert(0, cfg.get("api_key",""))
        e_to=Entry(dlg,width=10); e_to.insert(0, str(cfg.get("timeout_sec",20)))
        v_tls=IntVar(value=1 if cfg.get("verify_tls",True) else 0); chk=Checkbutton(dlg,variable=v_tls)
        e_url.grid(row=0,column=1); e_key.grid(row=1,column=1); e_to.grid(row=2,column=1); chk.grid(row=3,column=1,sticky="w")
        Button(dlg,text="Guardar",command=lambda:self._save_api_config(dlg,e_url,e_key,e_to,v_tls)).grid(row=4,column=1,sticky="e",padx=6,pady=6)
    def _save_api_config(self, dlg, e_url, e_key, e_to, v_tls):
        try:
            cfg={"api_base_url":e_url.get().strip(), "api_key":e_key.get().strip(), "verify_tls":bool(v_tls.get()), "timeout_sec":int(e_to.get().strip() or "20")}
            self.api.save_config(cfg); dlg.destroy(); self.status("Config API guardada.")
        except Exception as ex:
            messagebox.showerror("Config", f"Error guardando: {ex}")
    def open_validator(self):
        APIMapperDialog(self.root, self.api).validate_schema()

    def download_images_menu(self):
        # List local documents with remote_id and pages not downloaded
        dlg=Toplevel(self.root); dlg.title("Descargar imágenes — documentos importados"); dlg.geometry("900x520")
        tree=ttk.Treeview(dlg, columns=("doc_id","titulo","pendientes","base_dir"), show="headings")
        for c,w in [("doc_id",80),("titulo",320),("pendientes",120),("base_dir",320)]:
            tree.heading(c, text=c.upper()); tree.column(c, width=w, anchor="w")
        tree.pack(fill=BOTH, expand=True, padx=6, pady=6)
        with db_connect() as con:
            rows=list(con.execute("""SELECT d.id, d.title, p.base_dir, SUM(CASE WHEN pg.downloaded=0 AND (pg.remote_url IS NOT NULL) THEN 1 ELSE 0 END) as pending
                                     FROM document d 
                                     LEFT JOIN project p ON p.id=d.project_id
                                     LEFT JOIN page pg ON pg.document_id=d.id
                                     WHERE d.remote_id IS NOT NULL
                                     GROUP BY d.id, d.title, p.base_dir
                                     ORDER BY pending DESC, d.id DESC"""))
        for r in rows:
            tree.insert("", END, values=(r[0], r[1], int(r[3] or 0), r[2]))
        def do_download():
            sel=tree.selection(); 
            if not sel: return
            doc_id=tree.item(sel[0])["values"][0]
            # emulate same behavior as in DocumentPullDialog.download_images_for_selected
            with db_connect() as con:
                cur=con.cursor(); cur.execute("SELECT p.base_dir FROM project p INNER JOIN document d ON d.project_id=p.id WHERE d.id=?", (doc_id,)); row=cur.fetchone()
                if not row: return
                base_dir=Path(row[0]); processed=base_dir/"processed"; processed.mkdir(parents=True, exist_ok=True); ocrdir=base_dir/"ocr"; ocrdir.mkdir(parents=True, exist_ok=True)
                headers=self.api.headers()
                count=0
                for (pid, seq, remote_url, ocr_url) in con.execute("SELECT id, seq, remote_url, ocr_url FROM page WHERE document_id=? AND downloaded=0 ORDER BY seq", (doc_id,)):
                    if remote_url:
                        try:
                            r=requests.get(remote_url, headers=headers, timeout=self.api.timeout(), verify=self.api.verify()); r.raise_for_status()
                            fname=f"page_{seq:04d}.jpg"; out=processed/fname; out.write_bytes(r.content)
                            con.execute("UPDATE page SET processed_path=?, downloaded=1 WHERE id=?", (str(out), pid)); count+=1
                        except Exception as ex:
                            print("Descarga img error:", ex)
                    if ocr_url:
                        try:
                            r=requests.get(ocr_url, headers=headers, timeout=self.api.timeout(), verify=self.api.verify()); r.raise_for_status()
                            ext=".pdf" if "pdf" in r.headers.get("content-type","").lower() else ".txt"
                            out=ocrdir/f"page_{seq:04d}{ext}"; out.write_bytes(r.content)
                            con.execute("UPDATE page SET ocr_pdf_path=? WHERE id=?", (str(out), pid))
                        except Exception as ex:
                            print("Descarga OCR error:", ex)
                con.commit()
            messagebox.showinfo("Descarga", f"Imágenes descargadas: {count}")
            dlg.destroy()
        Button(dlg, text="Descargar imágenes del seleccionado", command=do_download).pack(side=BOTTOM, pady=8)

    # -------- Push document --------
    def api_push_document(self):
        if not self.doc_id:
            messagebox.showwarning("API", "Crea un proyecto primero."); return
        try:
            with db_connect() as con:
                cur=con.cursor()
                cur.execute("""SELECT d.id, d.project_id, d.title, d.signatura, d.archivo_id, d.fondo_id, d.tema, d.etiquetas, d.tipo,
                                      d.autor, d.fecha_text, d.lugar, d.idioma, d.derechos, d.referencia_bibliografica, d.resumen, d.notas_internas,
                                      p.name, p.base_dir, d.remote_id
                               FROM document d LEFT JOIN project p ON p.id=d.project_id WHERE d.id=?""",(self.doc_id,))
                row=cur.fetchone()
                if not row: messagebox.showerror("API","Documento no encontrado."); return
                cols=["id","project_id","title","signatura","archivo_id","fondo_id","tema","etiquetas","tipo","autor","fecha_text","lugar","idioma","derechos","referencia_bibliografica","resumen","notas_internas","project_name","project_base","remote_id"]
                doc=dict(zip(cols,row))
                pages=[{"seq":r[0],"src_path":r[1],"processed_path":r[2],"ocr_txt_path":r[3],"ocr_pdf_path":r[4],"created_at":r[5],"remote_id":r[6]}
                       for r in con.execute("SELECT seq,src_path,processed_path,ocr_txt_path,ocr_pdf_path,created_at,remote_id FROM page WHERE document_id=? ORDER BY seq",(self.doc_id,))]
            # Map fields to remote schema
            doc_remote=self.api.map_local_to_remote_doc(doc)
            pages_remote=[self.api.map_local_to_remote_page(p) for p in pages]
            payload={"document": doc_remote, "pages": pages_remote}
            ep=self.api.map.get("endpoints",{}).get("push_document","/api/sync/document")
            resp=self.api.post(ep, payload)
            with db_connect() as con:
                con.execute("UPDATE document SET last_sync=? WHERE id=?", (datetime.now().isoformat(), self.doc_id)); con.commit()
            messagebox.showinfo("API", f"Documento subido.\nRespuesta:\n{str(resp)[:800]}")
        except Exception as ex:
            traceback.print_exc()
            messagebox.showerror("API", f"Error: {ex}")

    # -------- Camera & processing --------
    def start_camera(self):
        sel=self.combo_cam.get(); idx=int(sel.split(":")[0])
        self.cap=cv2.VideoCapture(idx, cv2.CAP_DSHOW if platform.system().lower()=="windows" else 0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,3840); self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,2160)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS,0); self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE,0.25)
        self.status("Cámara iniciada")
    def stop_camera(self):
        if self.cap: self.cap.release(); self.cap=None; self.status("Cámara detenida")
    def apply_camera_props(self, *_):
        if not self.cap: return
        try: self.cap.set(cv2.CAP_PROP_EXPOSURE,float(self.exposure_var.get()))
        except: pass
        try: self.cap.set(cv2.CAP_PROP_WHITE_BALANCE_BLUE_U,float(int(self.wb_var.get())))
        except: pass
    def update_preview_loop(self):
        if self.cap and self.cap.isOpened():
            ok,frame=self.cap.read()
            if ok: self.frame_bgr=frame; self.draw_preview(frame)
        self.root.after(30, self.update_preview_loop)

# ISAD(G) panel
isad=Frame(root); isad.pack(side=TOP, fill=X, pady=6)
Label(isad,text="ISAD(G) — Nivel:").pack(side=LEFT,padx=5)
self.isad_nivel=ttk.Combobox(isad,state="readonly",width=16,values=["Fondo","Subfondo","Serie","Subserie","Unidad documental"])
self.isad_nivel.set("Unidad documental"); self.isad_nivel.pack(side=LEFT,padx=4)
Label(isad,text="Productor:").pack(side=LEFT,padx=5); 
self.isad_productor=StringVar(value=""); Entry(isad,textvariable=self.isad_productor,width=24).pack(side=LEFT,padx=4)
Label(isad,text="Alcance y contenido:").pack(side=LEFT,padx=5); 
self.isad_alcance=StringVar(value=""); Entry(isad,textvariable=self.isad_alcance,width=40).pack(side=LEFT,padx=4)
Button(isad,text="Guardar ISAD(G)",command=self.save_isad).pack(side=LEFT,padx=10)

# Tools bar for citations & report
tools=Frame(root); tools.pack(side=TOP, fill=X, pady=6)
Button(tools,text="Cita APA",command=self.show_citation_apa).pack(side=LEFT,padx=4)
Button(tools,text="Cita ISO 690",command=self.show_citation_iso).pack(side=LEFT,padx=4)
Button(tools,text="Informe del proyecto (PDF)",command=self.export_project_pdf).pack(side=LEFT,padx=12)


    def draw_preview(self,bgr):
        h,w=bgr.shape[:2]; cw=self.canvas_preview.winfo_width() or 640; ch=self.canvas_preview.winfo_height() or 360
        scale=min(cw/w, ch/h); self.scale_preview=scale
        rgb=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB); im=Image.fromarray(rgb).resize((int(w*scale), int(h*scale)))
        self.photo_preview=ImageTk.PhotoImage(im); self.canvas_preview.delete("all")
        self.canvas_preview.create_image(cw//2, ch//2, image=self.photo_preview)
    def redraw_preview(self):
        if self.frame_bgr is not None: self.draw_preview(self.frame_bgr)
    def redraw_result(self):
        if self.photo_result is not None:
            self.canvas_result.delete("all"); self.canvas_result.create_image(self.canvas_result.winfo_width()//2, self.canvas_result.winfo_height()//2, image=self.photo_result)

    def capture_and_process(self):
        if self.frame_bgr is None: self.status("No hay frame de cámara"); return
        bgr=self.frame_bgr.copy()
        res=core.process_one_image(bgr, do_dewarp=None if self.dewarp_mode.get()=="none" else self.dewarp_mode.get(),
                                   dewarp_strength=float(self.dewarp_strength.get()), contrast_mode=self.contrast_mode.get(), final_scale=float(self.final_scale.get()),
                                   manual_quad=None, mesh=(self.dewarp_mode.get()=="mesh"), mesh_cols=int(self.mesh_cols.get()), mesh_rows=int(self.mesh_rows.get()),
                                   asymmetric=bool(self.asymmetric_mesh.get()), split_spread=(self.capture_mode.get()=="double"),
                                   ocr_lang=(self.ocr_lang.get() if self.ocr_enabled.get() else None))
        out_dir=Path(self.out_dir_var.get()); out_dir.mkdir(parents=True, exist_ok=True)
        pages=res if isinstance(res,list) else [res]
        for i,page in enumerate(pages, start=1):
            base=page["dewarped"]; mono=page["post_gray"]; stacked=np.hstack([base, cv2.cvtColor(mono, cv2.COLOR_GRAY2BGR)])
            im=Image.fromarray(cv2.cvtColor(stacked, cv2.COLOR_BGR2RGB)); cw,ch=self.canvas_result.winfo_width() or 640, self.canvas_result.winfo_height() or 360
            scale=min(cw/im.width, ch/im.height); im=im.resize((int(im.width*scale), int(im.height*scale)))
            self.photo_result=ImageTk.PhotoImage(im); self.redraw_result()
            fname=f"{self._slug(self.title_var.get())}_{len(self.saved_images)+1:04d}.jpg"; out=out_dir/fname
            core.imwrite_auto(str(out), stacked, quality=95); self.saved_images.append(str(out)); self.listbox.insert(END, fname)
            # compute hash & version entry
            hashv = sha256_of_file(out)
            if self.doc_id:
                with db_connect() as con:
                    con.execute("""INSERT INTO page (document_id,seq,src_path,processed_path,created_at,downloaded,hash_sha256) VALUES (?,?,?,?,?,1,?)""",
                                (self.doc_id,len(self.saved_images)-1,None,str(out),datetime.now().isoformat(),hashv)); con.commit()
            add_version_entry(document_id=self.doc_id, action="add_page", details=f"{fname} hash={hashv}")

    # -------- Project & batch --------
    def create_project_dialog(self):
        proj_dir=filedialog.askdirectory(title="Selecciona carpeta del proyecto"); 
        if not proj_dir: return
        self.project_root=Path(proj_dir)
        for sub in ["raw","processed","ocr","pdf"]: (self.project_root/sub).mkdir(parents=True, exist_ok=True)
        self.out_dir_var.set(str(self.project_root/"processed"))
        with db_connect() as con:
            cur=con.cursor(); cur.execute("INSERT INTO project (name,base_dir,created_at) VALUES (?,?,?)",(self.title_var.get(), str(self.project_root), datetime.now().isoformat())); self.project_id=cur.lastrowid
            cur.execute("""INSERT INTO document (project_id,title,signatura,archivo_id,fondo_id,tema,etiquetas,tipo,autor,fecha_text,lugar,idioma,derechos,referencia_bibliografica,resumen,notas_internas,created_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (self.project_id,self.title_var.get(),self.sig_var.get(),None,None,self.tema_var.get(),self.etiquetas_var.get(),self.tipo_var.get(),self.author_var.get(),self.fecha_var.get(),self.lugar_var.get(),self.idioma_var.get(),self.derechos_var.get(),self.refbib_var.get(),self.resumen_var.get(),self.notas_var.get(),datetime.now().isoformat()))
            self.doc_id=cur.lastrowid; con.commit()
        self.status(f"Proyecto creado — project_id={self.project_id}, doc_id={self.doc_id}")

    def batch_process_dialog(self):
        folder=filedialog.askdirectory(title="Seleccionar carpeta con imágenes"); 
        if not folder: return
        folder=Path(folder); files=sorted([p for p in folder.iterdir() if p.suffix.lower() in IMG_EXTS])
        if not files: messagebox.showwarning("Lote","Sin imágenes."); return
        if not self.project_root:
            if not messagebox.askyesno("Proyecto","No hay proyecto activo. ¿Crear proyecto rápido en esta carpeta?"): return
            self.project_root=folder/"_proyecto"; 
            for sub in ["raw","processed","ocr","pdf"]: (self.project_root/sub).mkdir(parents=True, exist_ok=True)
            self.out_dir_var.set(str(self.project_root/"processed"))
            with db_connect() as con:
                cur=con.cursor(); cur.execute("INSERT INTO project (name,base_dir,created_at) VALUES (?,?,?)",(self.title_var.get(), str(self.project_root), datetime.now().isoformat())); self.project_id=cur.lastrowid
                cur.execute("""INSERT INTO document (project_id,title,signatura,archivo_id,fondo_id,tema,etiquetas,tipo,autor,fecha_text,lugar,idioma,derechos,referencia_bibliografica,resumen,notas_internas,created_at)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (self.project_id,self.title_var.get(),self.sig_var.get(),None,None,self.tema_var.get(),self.etiquetas_var.get(),self.tipo_var.get(),self.author_var.get(),self.fecha_var.get(),self.lugar_var.get(),self.idioma_var.get(),self.derechos_var.get(),self.refbib_var.get(),self.resumen_var.get(),self.notas_var.get(),datetime.now().isoformat()))
                self.doc_id=cur.lastrowid; con.commit()
        processed_dir=Path(self.out_dir_var.get()); raw_dir=self.project_root/"raw" if self.project_root else folder
        count=0
        for p in files:
            bgr=core.imread_auto(str(p)) if hasattr(core,"imread_auto") else cv2.imread(str(p))
            if bgr is None: continue
            try:
                import shutil as _sh
                dest=raw_dir/p.name
                if str(dest).lower()!=str(p).lower(): _sh.copy2(p,dest)
            except: pass
            res=core.process_one_image(bgr, do_dewarp=None if self.dewarp_mode.get()=="none" else self.dewarp_mode.get(),
                                       dewarp_strength=float(self.dewarp_strength.get()), contrast_mode=self.contrast_mode.get(), final_scale=float(self.final_scale.get()),
                                       manual_quad=None, mesh=(self.dewarp_mode.get()=="mesh"), mesh_cols=int(self.mesh_cols.get()), mesh_rows=int(self.mesh_rows.get()),
                                       asymmetric=bool(self.asymmetric_mesh.get()), split_spread=(self.capture_mode.get()=="double"),
                                       ocr_lang=(self.ocr_lang.get() if self.ocr_enabled.get() else None))
            pages=res if isinstance(res,list) else [res]
            for page in pages:
                base=page["dewarped"]; mono=page["post_gray"]; stacked=np.hstack([base, cv2.cvtColor(mono, cv2.COLOR_GRAY2BGR)])
                fname=f"{self._slug(self.title_var.get())}_{count+1:04d}.jpg"; out=processed_dir/fname
                core.imwrite_auto(str(out), stacked, quality=95); self.saved_images.append(str(out)); self.listbox.insert(END, fname)
                hashv = sha256_of_file(out)
                with db_connect() as con:
                    con.execute("""INSERT INTO page (document_id,seq,src_path,processed_path,created_at,downloaded,hash_sha256) VALUES (?,?,?,?,?,1,?)""",
                                (self.doc_id,len(self.saved_images)-1,str(raw_dir/p.name),str(out),datetime.now().isoformat(),hashv)); con.commit()
                add_version_entry(document_id=self.doc_id, action="add_page", details=f"{fname} hash={hashv}")
                count+=1
        self.status(f"Lote completado: {count} páginas")

    # -------- Export --------
    def export_pdf(self):
        if not self.saved_images: self.status("No hay páginas"); return
        out_pdf=(self.project_root/"pdf"/f"{self._slug(self.title_var.get())}.pdf") if self.project_root else (Path(self.out_dir_var.get())/"libro_tk.pdf")
        meta={"title":self.title_var.get(),"author":self.author_var.get(),"subject":self.sig_var.get(),"keywords":f"{self.tema_var.get()},{self.etiquetas_var.get()}","creator":APP_NAME}
        core.assemble_pdf_from_images(self.saved_images, str(out_pdf), dpi=300, meta=meta, pdfa=True); self.status(f"PDF exportado: {out_pdf}")

    # -------- Helpers --------
    def choose_output_dir(self):
        d=filedialog.askdirectory(title="Elegir carpeta de salida", initialdir=str(self.output_dir)); 
        if d: self.out_dir_var.set(d)
    def status(self,msg): 
        self.status_var.set(msg)
    def preview_selected(self):
        if self.frame_bgr is None and not self.saved_images: return
        orig=self.frame_bgr if self.frame_bgr is not None else core.imread_auto(self.saved_images[0])
        proc=orig if self.frame_bgr is None else self.frame_bgr
        FullscreenPreview(self.root, orig, proc, title_text="Comparador (Original/Procesada)")
    def move_up(self):
        sel=self.listbox.curselection(); 
        if not sel: return
        i=sel[0]; 
        if i==0: return
        self._swap(i, i-1); self._update_order_db()
    def move_down(self):
        sel=self.listbox.curselection(); 
        if not sel: return
        i=sel[0]; 
        if i>=self.listbox.size()-1: return
        self._swap(i, i+1); self._update_order_db()
    def _swap(self,i,j):
        a=self.listbox.get(i); b=self.listbox.get(j)
        self.listbox.delete(j); self.listbox.insert(j, a)
        self.listbox.delete(i); self.listbox.insert(i, b)
        self.saved_images[i], self.saved_images[j]=self.saved_images[j], self.saved_images[i]
        self.listbox.selection_clear(0, END); self.listbox.selection_set(j)
    def _update_order_db(self):
        if not self.doc_id: return
        with db_connect() as con:
            for i,p in enumerate(self.saved_images): con.execute("UPDATE page SET seq=? WHERE processed_path=?", (i,p))
            con.commit()
    def delete_selected(self):
        sel=self.listbox.curselection(); 
        if not sel: return
        idx=sel[0]; path=self.saved_images[idx]
        try: os.remove(path)
        except: pass
        del self.saved_images[idx]; self.listbox.delete(idx)
        if self.doc_id:
            with db_connect() as con: con.execute("DELETE FROM page WHERE processed_path=?", (path,)); con.commit()
        self._update_order_db(); self.status(f"Eliminada: {Path(path).name}")
    def _slug(self, t):
        import re; s=re.sub(r'[^a-z0-9]+','-', (t or '').strip().lower()); s=re.sub(r'-+','-',s).strip('-'); return s or "documento"


# ------- Environment switching -------
def change_environment_dialog(self):
    win=Toplevel(self.root); win.title("Cambiar entorno"); win.geometry("520x260")
    v=StringVar(value="development" if (self.api.config.get("environment")=="development") else "production")
    Label(win, text="Selecciona entorno activo:").pack(side=TOP,pady=8)
    frm=Frame(win); frm.pack(side=TOP,pady=6)
    rb1=ttk.Radiobutton(frm, text="Desarrollo (dev)", variable=v, value="development"); rb1.pack(anchor="w")
    rb2=ttk.Radiobutton(frm, text="Producción (prod)", variable=v, value="production"); rb2.pack(anchor="w")
    Label(win, text=f"Actual: {self.api.config.get('environment','(no definido)')} / {self.api.config.get('api_base_url','')}").pack(side=TOP,pady=6)
    def apply_env():
        name="dev" if v.get()=="development" else "prod"
        try:
            prof=activate_profile(name)
            self.api.save_config(prof)  # reload into API
            messagebox.showinfo("Entorno", f"Activo: {prof.get('environment')} ({prof.get('api_base_url')})")
            win.destroy()
        except Exception as ex:
            messagebox.showerror("Entorno", f"Error activando entorno: {ex}")
    Button(win, text="Activar entorno seleccionado", command=apply_env).pack(side=TOP, pady=10)

def auto_detect_environment(self):
    env, prof = detect_environment()
    if env and prof:
        self.api.save_config(prof)
        # Persist to active file
        CONFIG_PATH.write_text(json.dumps(prof, indent=2), encoding="utf-8")
        messagebox.showinfo("Autodetección", f"Entorno detectado: {env} → {prof.get('api_base_url')}")
    else:
        messagebox.showwarning("Autodetección", "No se pudo detectar automáticamente. Revisa que el backend esté accesible.")



# ------- ISAD(G) save -------
def save_isad(self):
    if not self.doc_id:
        messagebox.showwarning("ISAD(G)","Crea un proyecto primero."); return
    nivel=self.isad_nivel.get(); productor=self.isad_productor.get(); alcance=self.isad_alcance.get()
    with db_connect() as con:
        # Ensure columns exist
        cur=con.cursor(); cur.execute("PRAGMA table_info(document)"); cols=[r[1] for r in cur.fetchall()]
        if "nivel_descripcion" not in cols:
            cur.execute("ALTER TABLE document ADD COLUMN nivel_descripcion TEXT")
        if "productor" not in cols:
            cur.execute("ALTER TABLE document ADD COLUMN productor TEXT")
        if "alcance_y_contenido" not in cols:
            cur.execute("ALTER TABLE document ADD COLUMN alcance_y_contenido TEXT")
        cur.execute("UPDATE document SET nivel_descripcion=?, productor=?, alcance_y_contenido=? WHERE id=?",
                    (nivel, productor, alcance, self.doc_id))
        con.commit()
    add_version_entry(document_id=self.doc_id, action="update_metadata", details="ISAD(G) actualizado")
    self.status("ISAD(G) guardado.")

# ------- Citations -------
def show_citation_apa(self):
    with db_connect() as con:
        cur=con.cursor(); cur.execute("""SELECT d.autor, d.fecha_text, d.title, a.nombre, f.nombre, d.signatura, d.lugar
                                         FROM document d LEFT JOIN archivo a ON a.id=d.archivo_id LEFT JOIN fondo f ON f.id=d.fondo_id WHERE d.id=?""", (self.doc_id,))
        r=cur.fetchone()
    if not r: messagebox.showwarning("Cita","Completa los metadatos y crea un proyecto."); return
    autor, fecha, titulo, arch, fondo, signa, lugar = r
    cita=citation_apa(autor, fecha, titulo, arch, fondo, signa, lugar)
    messagebox.showinfo("Cita APA", cita)

def show_citation_iso(self):
    with db_connect() as con:
        cur=con.cursor(); cur.execute("""SELECT d.autor, d.fecha_text, d.title, d.lugar, a.nombre, f.nombre, d.signatura
                                         FROM document d LEFT JOIN archivo a ON a.id=d.archivo_id LEFT JOIN fondo f ON f.id=d.fondo_id WHERE d.id=?""", (self.doc_id,))
        r=cur.fetchone()
    if not r: messagebox.showwarning("Cita","Completa los metadatos y crea un proyecto."); return
    autor, fecha, titulo, lugar, arch, fondo, signa = r
    cita=citation_iso690(autor or "", fecha or "", titulo or "", lugar or "", arch or "", fondo or "", signa or "")
    messagebox.showinfo("Cita ISO 690", cita)

# ------- Project report -------
def export_project_pdf(self):
    if not self.doc_id:
        messagebox.showwarning("Informe","Crea un proyecto primero."); return
    out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF","*.pdf")], initialfile="informe_proyecto.pdf")
    if not out: return
    ok = export_project_report(GLOBAL_DB, self.doc_id, Path(out), logo_path=BASE_DIR / "logo_geodocs.png")
    if ok: self.status(f"Informe exportado: {out}")
    else: messagebox.showerror("Informe","No fue posible generar el informe.")




# ------- Annotations -------
def add_annotation(self):
    if not self.doc_id:
        messagebox.showwarning("Anotaciones","Crea un proyecto primero."); return
    # Determine selected page index if any
    sel=self.listbox.curselection()
    page_idx = sel[0] if sel else None
    page_id = None
    if page_idx is not None:
        with db_connect() as con:
            cur=con.cursor(); cur.execute("SELECT id FROM page WHERE document_id=? AND seq=?", (self.doc_id, page_idx))
            r=cur.fetchone(); 
            if r: page_id = r[0]
    with db_connect() as con:
        con.execute("""INSERT INTO annotation (document_id, page_id, user, type, tags, body, target_region, created_at)
                       VALUES (?,?,?,?,?,?,?,datetime('now'))""",
                    (self.doc_id, page_id, self.anno_user.get(), self.anno_tipo.get(), self.anno_tags.get(), self.anno_body.get(), self.anno_region.get()))
        con.commit()
    add_version_entry(document_id=self.doc_id, page_id=page_id, action="add_annotation", details=self.anno_body.get())
    self.status("Anotación añadida.")

# ------- Exporters menu -------
def export_ead(self):
    if not self.doc_id: messagebox.showwarning("EAD3","Crea/abre un proyecto."); return
    path = filedialog.asksaveasfilename(defaultextension=".xml", filetypes=[("XML","*.xml")], initialfile="ead3.xml")
    if not path: return
    ok = export_ead3_xml(GLOBAL_DB, self.doc_id, Path(path))
    self.status("EAD3 exportado." if ok else "Error al exportar EAD3")

def export_dc(self):
    if not self.doc_id: messagebox.showwarning("Dublin Core","Crea/abre un proyecto."); return
    path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")], initialfile="dublin_core.json")
    if not path: return
    ok = export_dc_jsonld(GLOBAL_DB, self.doc_id, Path(path))
    self.status("JSON-LD exportado." if ok else "Error al exportar JSON-LD")

def export_tei(self):
    if not self.doc_id: messagebox.showwarning("TEI-XML","Crea/abre un proyecto."); return
    path = filedialog.asksaveasfilename(defaultextension=".xml", filetypes=[("XML","*.xml")], initialfile="tei.xml")
    if not path: return
    ok = export_tei_xml(GLOBAL_DB, self.doc_id, Path(path))
    self.status("TEI-XML exportado." if ok else "Error al exportar TEI-XML")

def export_mets_alto(self):
    if not self.doc_id: messagebox.showwarning("METS/ALTO","Crea/abre un proyecto."); return
    directory = filedialog.askdirectory(title="Selecciona carpeta destino para METS/ALTO")
    if not directory: return
    ok = export_mets_alto(GLOBAL_DB, self.doc_id, Path(directory))
    self.status("METS/ALTO exportado." if ok else "Error al exportar METS/ALTO")



# ------- GeoDocs entity search -------
def search_toponimo(self):
    q=self.ent_topo_q.get().strip()
    if not q: return
    try:
        data=self.api.search_toponimos(q)
        items=data.get("results", data) if isinstance(data, dict) else data
        # Expect list of {id, nombre, lat, lon}
        vals=[f"{it.get('id')} · {it.get('nombre','')} ({it.get('lat','?')},{it.get('lon','?')})" for it in items]
        self.ent_topo_sel["values"]=vals
        if vals: self.ent_topo_sel.current(0)
    except Exception as ex:
        messagebox.showerror("Topónimos", str(ex))

def search_persona(self):
    q=self.ent_pers_q.get().strip()
    if not q: return
    try:
        data=self.api.search_personas(q)
        items=data.get("results", data) if isinstance(data, dict) else data
        vals=[f"{it.get('id')} · {it.get('nombre','')}" for it in items]
        self.ent_pers_sel["values"]=vals
        if vals: self.ent_pers_sel.current(0)
    except Exception as ex:
        messagebox.showerror("Personas", str(ex))

def save_geo_to_annotation(self):
    if not self.doc_id:
        messagebox.showwarning("Geo","Crea un proyecto primero."); return
    sel=self.listbox.curselection()
    page_idx = int(sel[0]) if sel else None
    page_id = None
    if page_idx is not None:
        with db_connect() as con:
            cur=con.cursor(); cur.execute("SELECT id FROM page WHERE document_id=? AND seq=?", (self.doc_id, page_idx))
            r=cur.fetchone()
            if r: page_id = r[0]
    # Parse selected entities
    topo_sel = self.ent_topo_sel.get().strip()
    pers_sel = self.ent_pers_sel.get().strip()
    topo_id = topo_sel.split("·")[0].strip() if topo_sel else None
    pers_id = pers_sel.split("·")[0].strip() if pers_sel else None
    # Coordinates
    lat = self.lat_var.get().strip()
    lon = self.lon_var.get().strip()
    try:
        lat_v = float(lat) if lat else None
        lon_v = float(lon) if lon else None
    except:
        messagebox.showwarning("Geo","Lat/Lon no válidos."); return
    # Create minimal annotation if none typed
    body = self.anno_body.get() or f"Geo: {lat},{lon}"
    with db_connect() as con:
        con.execute("""INSERT INTO annotation (document_id, page_id, user, type, tags, body, target_region, latitude, longitude, toponimo_id, persona_id, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                    (self.doc_id, page_id, self.anno_user.get(), self.anno_tipo.get(), self.anno_tags.get(), body, self.anno_region.get(), lat_v, lon_v, topo_id, pers_id))
        con.commit()
    add_version_entry(document_id=self.doc_id, page_id=page_id, action="add_annotation_geo", details=body)
    self.status("Geolocalización guardada en anotación.")

def open_web_map(self):
    # Launch Flask server and open browser
    import threading, webbrowser, subprocess, sys
    server_py = BASE_DIR / "web_viewer" / "server.py"
    def run_server():
        subprocess.run([sys.executable, str(server_py)], cwd=str(BASE_DIR))
    threading.Thread(target=run_server, daemon=True).start()
    import time; time.sleep(0.8)
    # Get doc title
    with db_connect() as con:
        cur=con.cursor(); cur.execute("SELECT title FROM document WHERE id=?", (self.doc_id,)); r=cur.fetchone()
        title=r[0] if r else ""
    webbrowser.open(f"http://127.0.0.1:5000/?document_id={self.doc_id}&title={title}")

def push_annotations(self):
    try:
        resp=self.api.push_annotations(self.doc_id)
        messagebox.showinfo("GeoDocs","Anotaciones sincronizadas.")
    except Exception as ex:
        messagebox.showerror("GeoDocs", f"Error: {ex}")

# ------- Thumbnails overlay (regions) -------
def refresh_thumbnails(self):
    # Draw simple overlay preview for selected page using target_region if present (x,y,w,h in 0..1 normalized)
    sel=self.listbox.curselection()
    if not sel: 
        self.status("Selecciona una página."); 
        return
    idx=sel[0]
    with db_connect() as con:
        cur=con.cursor(); cur.execute("SELECT processed_path FROM page WHERE document_id=? AND seq=?", (self.doc_id, idx))
        r=cur.fetchone()
        if not r or not r[0] or not Path(r[0]).exists():
            self.status("Sin imagen procesada."); return
        img_path = r[0]
        # Fetch first annotation w/ region for this page
        cur.execute("SELECT target_region FROM annotation WHERE document_id=? AND page_id=(SELECT id FROM page WHERE document_id=? AND seq=?) AND target_region IS NOT NULL AND target_region!='' ORDER BY id DESC LIMIT 1", (self.doc_id, self.doc_id, idx))
        ar = cur.fetchone()
    import cv2, numpy as np
    bgr = cv2.imread(img_path)
    if bgr is None:
        self.status("No se pudo cargar la imagen."); return
    if ar and ar[0]:
        try:
            x,y,w,h = [float(v) for v in ar[0].split(",")]
            H,W=bgr.shape[:2]
            cv2.rectangle(bgr, (int(x*W),int(y*H)), (int((x+w)*W),int((y+h)*H)), (0,0,255), 4)
        except:
            pass
    # Show on result canvas
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    from PIL import Image, ImageTk
    im = Image.fromarray(rgb)
    cw,ch=self.canvas_result.winfo_width() or 640, self.canvas_result.winfo_height() or 360
    scale=min(cw/im.width, ch/im.height)
    im=im.resize((int(im.width*scale), int(im.height*scale)))
    self.photo_result=ImageTk.PhotoImage(im); self.redraw_result()



def on_toponimo_selected(self, event=None):
    import re
    txt = self.ent_topo_sel.get().strip()
    m = re.search(r"\(([+-]?\d+\.?\d*),\s*([+-]?\d+\.?\d*)\)", txt)
    if m:
        lat, lon = m.group(1), m.group(2)
        if self.lat_var.get() and self.lon_var.get():
            if not messagebox.askyesno("Coordenadas", "Reemplazar las existentes por las del topónimo?"):
                return
        self.lat_var.set(lat); self.lon_var.set(lon)
        add_version_entry(document_id=self.doc_id, action="update_coords_from_toponimo", details=f"{txt} → {lat},{lon}")
        self.status(f"Coordenadas autocompletadas: {lat}, {lon}")

def pull_annotations(self):
    try:
        c = self.api.config
        base = (c.get("api_base_url") or "").rstrip("/")
        import requests
        r = requests.get(base + "/api/anotaciones", headers=self.api.headers(), params={"document_id": self.doc_id},
                         timeout=self.api.timeout(), verify=self.api.verify())
        r.raise_for_status()
        data = r.json()
        anns = data.get("annotations", data if isinstance(data, list) else [])
        with db_connect() as con:
            cur = con.cursor()
            for a in anns:
                cur.execute("""SELECT id FROM annotation WHERE document_id=? AND IFNULL(page_id,'')=IFNULL(?, '') AND IFNULL(body,'')=IFNULL(?, '') AND IFNULL(type,'')=IFNULL(?, '')""", (self.doc_id, a.get("page_id"), a.get("body"), a.get("type")))
                row = cur.fetchone()
                if row:
                    cur.execute("""UPDATE annotation SET latitude=?, longitude=?, toponimo_id=?, persona_id=?, tags=?, target_region=?, updated_at=datetime('now') WHERE id=?""", (a.get("latitude"), a.get("longitude"), a.get("toponimo_id"), a.get("persona_id"), a.get("tags"), a.get("target_region"), row[0]))
                else:
                    cur.execute("""INSERT INTO annotation (document_id,page_id,user,type,tags,body,target_region,latitude,longitude,toponimo_id,persona_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""", (self.doc_id, a.get("page_id"), a.get("user","remote"), a.get("type"), a.get("tags"), a.get("body"), a.get("target_region"), a.get("latitude"), a.get("longitude"), a.get("toponimo_id"), a.get("persona_id")))
            con.commit()
        add_version_entry(document_id=self.doc_id, action="pull_annotations", details=f"{len(anns)} anotaciones")
        messagebox.showinfo("GeoDocs", f"Anotaciones descargadas: {len(anns)}")
    except Exception as ex:
        messagebox.showerror("GeoDocs", f"Error en pull: {ex}")

def open_picker(self):
    import threading, subprocess, sys, time, webbrowser
    server_py = BASE_DIR / "web_viewer" / "server.py"
    def run_server():
        subprocess.run([sys.executable, str(server_py)], cwd=str(BASE_DIR))
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(0.8)
    webbrowser.open("http://127.0.0.1:5000/pick")

def read_picker_coords(self):
    fp = BASE_DIR / "web_viewer" / "last_coords.json"
    if not fp.exists():
        messagebox.showwarning("Mini-mapa", "Aún no hay coordenadas guardadas (haz clic en el mapa)."); return
    try:
        d = json.loads(fp.read_text(encoding="utf-8"))
        self.lat_var.set(str(d.get("lat"))); self.lon_var.set(str(d.get("lon")))
        self.status(f"Coords del mini-mapa: {d.get('lat')}, {d.get('lon')}")
    except Exception as ex:
        messagebox.showerror("Mini-mapa", f"No se pudieron leer coords: {ex}")

def apply_annotation_filter(self):
    self.status(f"Filtro activo: {self.filter_tipo.get()}")

def export_geojson(self):
    if not self.doc_id:
        messagebox.showwarning("GeoJSON","Crea/abre un proyecto."); return
    path = filedialog.asksaveasfilename(defaultextension=".geojson", filetypes=[("GeoJSON","*.geojson")], initialfile="anotaciones.geojson")
    if not path: return
    feats = []
    with db_connect() as con:
        con.row_factory = sqlite3.Row
        for r in con.execute("SELECT * FROM annotation WHERE document_id=?", (self.doc_id,)):
            lat = r["latitude"]; lon = r["longitude"]
            if lat is not None and lon is not None:
                feats.append({
                    "type":"Feature",
                    "geometry":{"type":"Point","coordinates":[lon, lat]},
                    "properties":{"id": r["id"], "type": r["type"], "tags": r["tags"], "body": r["body"], "page_id": r["page_id"], "toponimo_id": r["toponimo_id"], "persona_id": r["persona_id"]}
                })
    fc = {"type":"FeatureCollection","features":feats}
    Path(path).write_text(json.dumps(fc, ensure_ascii=False, indent=2), encoding="utf-8")
    self.status(f"GeoJSON exportado: {path}")



def open_advanced_search(self):
    win=Toplevel(self.root); win.title("Búsqueda avanzada"); win.geometry("520x380")
    q_text=StringVar(value=""); q_tags=StringVar(value=""); q_tipo=StringVar(value="(cualquiera)"); q_from=StringVar(value=""); q_to=StringVar(value="")
    q_topo=StringVar(value=""); q_pers=StringVar(value="")
    Label(win,text="Texto contiene:").pack(anchor="w", padx=8, pady=4); Entry(win,textvariable=q_text,width=60).pack(padx=8)
    Label(win,text="Etiquetas contiene:").pack(anchor="w", padx=8, pady=4); Entry(win,textvariable=q_tags,width=60).pack(padx=8)
    frm=Frame(win); frm.pack(fill="x", padx=8, pady=6)
    Label(frm,text="Tipo:").pack(side="left"); cb=ttk.Combobox(frm,state="readonly",values=["(cualquiera)","nota","cita","referencia","comentario"], width=18, textvariable=q_tipo); cb.current(0); cb.pack(side="left", padx=6)
    Label(frm,text="Desde (YYYY-MM-DD):").pack(side="left", padx=6); Entry(frm,textvariable=q_from,width=12).pack(side="left")
    Label(frm,text="Hasta (YYYY-MM-DD):").pack(side="left", padx=6); Entry(frm,textvariable=q_to,width=12).pack(side="left")
    frm2=Frame(win); frm2.pack(fill="x", padx=8, pady=6)
    Label(frm2,text="Topónimo ID:").pack(side="left"); Entry(frm2,textvariable=q_topo,width=10).pack(side="left", padx=6)
    Label(frm2,text="Persona ID:").pack(side="left"); Entry(frm2,textvariable=q_pers,width=10).pack(side="left", padx=6)
    out=Frame(win); out.pack(fill="both", expand=True, padx=8, pady=8)
    txt=Text(out, height=10); txt.pack(fill="both", expand=True)

    def run_query():
        sql = "SELECT id, page_id, type, tags, body, latitude, longitude, created_at FROM annotation WHERE document_id=?"
        args = [self.doc_id]
        if q_text.get().strip():
            sql += " AND body LIKE ?"; args.append(f"%{q_text.get().strip()}%")
        if q_tags.get().strip():
            sql += " AND IFNULL(tags,'') LIKE ?"; args.append(f"%{q_tags.get().strip()}%")
        if q_tipo.get() != "(cualquiera)":
            sql += " AND type=?"; args.append(q_tipo.get())
        if q_from.get().strip():
            sql += " AND IFNULL(created_at,'') >= ?"; args.append(q_from.get().strip())
        if q_to.get().strip():
            sql += " AND IFNULL(created_at,'') <= ?"; args.append(q_to.get().strip())
        if q_topo.get().strip():
            sql += " AND IFNULL(toponimo_id,'') = ?"; args.append(q_topo.get().strip())
        if q_pers.get().strip():
            sql += " AND IFNULL(persona_id,'') = ?"; args.append(q_pers.get().strip())
        with db_connect() as con:
            con.row_factory=sqlite3.Row
            rows = list(con.execute(sql, args))
        txt.delete("1.0","end")
        for r in rows:
            txt.insert("end", f"#{r['id']} p:{r['page_id']} [{r['type']}] {r['body']}\n  tags={r['tags']} | lat={r['latitude']} lon={r['longitude']} | {r['created_at']}\n\n")

    Button(win, text="Buscar", command=run_query).pack(pady=6)




def publish_iiif_manifest(self):
    if not self.doc_id:
        messagebox.showwarning("Publicar IIIF","Crea/abre un proyecto."); return
    # Choose source: either a file or generate fresh Presentation v3 manifest
    if messagebox.askyesno("Publicar IIIF","¿Generar manifest v3 al vuelo y subirlo?\n(Si eliges No, podrás elegir un archivo JSON existente)"):
        # reuse existing export_iiif_manifest (Presentation v3 simple)
        import io
        with db_connect() as con:
            con.row_factory=sqlite3.Row
            d = con.execute("""SELECT d.id, d.title, d.autor, d.resumen, d.fecha_text, a.nombre AS archivo, f.nombre AS fondo
                               FROM document d LEFT JOIN archivo a ON a.id=d.archivo_id LEFT JOIN fondo f ON f.id=d.fondo_id WHERE d.id=?""",(self.doc_id,)).fetchone()
            pages = list(con.execute("SELECT id, seq, processed_path, remote_url FROM page WHERE document_id=? ORDER BY seq",(self.doc_id,)))
        canvases = []
        for r in pages:
            seq = r["seq"]
            img = r["remote_url"] or r["processed_path"]
            if not img: continue
            canvases.append({
                "id": f"urn:geodocs:canvas:{self.doc_id}:{seq}",
                "type": "Canvas",
                "height": 1000, "width": 700,
                "label": {"es": [f"Página {seq:04d}"]},
                "items": [{
                    "id": f"urn:geodocs:ap:{self.doc_id}:{seq}",
                    "type": "AnnotationPage",
                    "items": [{
                        "id": f"urn:geodocs:anno:{self.doc_id}:{seq}",
                        "type": "Annotation",
                        "motivation": "painting",
                        "target": f"urn:geodocs:canvas:{self.doc_id}:{seq}",
                        "body": {"id": img, "type": "Image", "format": "image/jpeg"}
                    }]
                }]
            })
        manifest = {
            "@context": "http://iiif.io/api/presentation/3/context.json",
            "id": f"urn:geodocs:manifest:{self.doc_id}",
            "type": "Manifest",
            "label": {"es": [d["title"] or f"Documento {self.doc_id}"]},
            "summary": {"es": [d["resumen"] or ""]},
            "items": canvases
        }
        payload = manifest
    else:
        fp = filedialog.askopenfilename(filetypes=[("JSON","*.json")], title="Selecciona manifest IIIF")
        if not fp: return
        try:
            payload = json.loads(Path(fp).read_text(encoding="utf-8"))
        except Exception as ex:
            messagebox.showerror("Publicar IIIF", f"No se pudo leer el JSON: {ex}"); return
    # POST to /api/iiif/manifest
    base = (self.api.config.get("api_base_url") or "").rstrip("/")
    url = base + "/api/iiif/manifest"
    import requests
    try:
        r = requests.post(url, headers=self.api.headers(), json=payload, timeout=self.api.timeout(), verify=self.api.verify())
        r.raise_for_status()
        messagebox.showinfo("GeoDocs", "Manifest IIIF publicado correctamente.")
    except Exception as ex:
        messagebox.showerror("GeoDocs", f"Error al publicar manifest: {ex}")

    def open_prosopography(self):
    # Compute frequencies and simple co-occurrence by page
    import matplotlib.pyplot as plt
    with db_connect() as con:
        con.row_factory=sqlite3.Row
        persons = list(con.execute("SELECT persona_id, COUNT(*) c FROM annotation WHERE document_id=? AND persona_id IS NOT NULL GROUP BY persona_id ORDER BY c DESC", (self.doc_id,)))
        places = list(con.execute("SELECT toponimo_id, COUNT(*) c FROM annotation WHERE document_id=? AND toponimo_id IS NOT NULL GROUP BY toponimo_id ORDER BY c DESC", (self.doc_id,)))
        # co-occurrence (per page)
        pairs = {}
        rows = list(con.execute("""SELECT page_id, GROUP_CONCAT(DISTINCT IFNULL(persona_id,'')) AS P, GROUP_CONCAT(DISTINCT IFNULL(toponimo_id,'')) AS T 
                                   FROM annotation WHERE document_id=? GROUP BY page_id""", (self.doc_id,)))
    # Bar chart persons
    if persons:
        ids=[str(r["persona_id"]) for r in persons][:15]
        cnt=[int(r["c"]) for r in persons][:15]
        plt.figure(); plt.bar(range(len(cnt)), cnt); plt.xticks(range(len(ids)), ids, rotation=45, ha="right")
        plt.title("Frecuencia de personas (top 15)"); plt.tight_layout(); plt.show()
    # Bar chart places
    if places:
        ids=[str(r["toponimo_id"]) for r in places][:15]
        cnt=[int(r["c"]) for r in places][:15]
        plt.figure(); plt.bar(range(len(cnt)), cnt); plt.xticks(range(len(ids)), ids, rotation=45, ha="right")
        plt.title("Frecuencia de topónimos (top 15)"); plt.tight_layout(); plt.show()



def export_graph_cooccurrence(self):
    if not self.doc_id:
        messagebox.showwarning("Grafo","Crea/abre un proyecto."); return
    import networkx as nx
    G = nx.Graph()
    with db_connect() as con:
        con.row_factory=sqlite3.Row
        # Build sets of persons and places per page
        pages = list(con.execute("SELECT id FROM page WHERE document_id=?", (self.doc_id,)))
        for p in pages:
            pid = p["id"]
            per = [str(r[0]) for r in con.execute("SELECT DISTINCT persona_id FROM annotation WHERE page_id=? AND persona_id IS NOT NULL", (pid,))]
            top = [str(r[0]) for r in con.execute("SELECT DISTINCT toponimo_id FROM annotation WHERE page_id=? AND toponimo_id IS NOT NULL", (pid,))]
            # add nodes
            for a in per: G.add_node(f"person:{a}", kind="person")
            for b in top: G.add_node(f"place:{b}", kind="place")
            # co-appear person-person
            for i in range(len(per)):
                for j in range(i+1, len(per)):
                    u=f"person:{per[i]}"; v=f"person:{per[j]}"
                    G.add_edge(u,v,weight=G.get_edge_data(u,v,{}).get("weight",0)+1)
            # co-appear place-place
            for i in range(len(top)):
                for j in range(i+1, len(top)):
                    u=f"place:{top[i]}"; v=f"place:{top[j]}"
                    G.add_edge(u,v,weight=G.get_edge_data(u,v,{}).get("weight",0)+1)
            # person-place edges
            for a in per:
                for b in top:
                    u=f"person:{a}"; v=f"place:{b}"
                    G.add_edge(u,v,weight=G.get_edge_data(u,v,{}).get("weight",0)+1)
    # Ask format
    fmt = tk.simpledialog.askstring("Exportar grafo", "Formato (gexf/graphml):", initialvalue="gexf")
    if not fmt: return
    path = filedialog.asksaveasfilename(defaultextension=f".{fmt}", filetypes=[("GEXF","*.gexf"),("GraphML","*.graphml")], initialfile=f"cooc.{fmt}")
    if not path: return
    if fmt.lower()=="gexf":
        nx.write_gexf(G, path)
    else:
        nx.write_graphml(G, path)
    self.status(f"Grafo exportado: {path}")

def visualize_graph_cooccurrence(self):
    # Basic in-app visualization using networkx + matplotlib
    import networkx as nx, matplotlib.pyplot as plt
    G = nx.Graph()
    with db_connect() as con:
        con.row_factory=sqlite3.Row
        rows = list(con.execute("SELECT page_id, persona_id, toponimo_id FROM annotation WHERE document_id=?", (self.doc_id,)))
    per=set(); top=set(); pages={}
    for r in rows:
        if r["persona_id"]: per.add(f"person:{r['persona_id']}")
        if r["toponimo_id"]: top.add(f"place:{r['toponimo_id']}")
    for u in per: G.add_node(u, kind="person")
    for v in top: G.add_node(v, kind="place")
    # simple edges: person-place co-occurrence
    from collections import Counter, defaultdict
    per_by_page=defaultdict(set); top_by_page=defaultdict(set)
    for r in rows:
        pid=r["page_id"]
        if r["persona_id"]: per_by_page[pid].add(f"person:{r['persona_id']}")
        if r["toponimo_id"]: top_by_page[pid].add(f"place:{r['toponimo_id']}")
    weight=Counter()
    for pid in per_by_page:
        for u in per_by_page[pid]:
            for v in top_by_page.get(pid, []):
                weight[(u,v)] += 1
    for (u,v),w in weight.items():
        G.add_edge(u,v,weight=w)
    pos = nx.spring_layout(G, seed=42)
    plt.figure()
    nx.draw(G, pos, with_labels=False, node_size=120)
    # Label a subset to avoid clutter:
    lbls = {n:n for i,n in enumerate(G.nodes()) if i<30}
    nx.draw_networkx_labels(G, pos, labels=lbls, font_size=6)
    plt.title("Grafo de coapariciones (muestra)")
    plt.show()



# ------- IIIF Validator (quick structural checks) -------
def validate_iiif_json(self):
    fp = filedialog.askopenfilename(filetypes=[("JSON","*.json")], title="Selecciona JSON IIIF (Manifest o Annotation*)")
    if not fp: return
    try:
        obj = json.loads(Path(fp).read_text(encoding="utf-8"))
    except Exception as ex:
        messagebox.showerror("IIIF - Validador", f"No se pudo leer JSON: {ex}"); return
    errors = []
    ctx = obj.get("@context") or obj.get("['@context']")
    if not ctx:
        errors.append("Falta @context")
    typ = obj.get("type")
    if not typ:
        errors.append("Falta type")
    else:
        if typ == "Manifest":
            if "items" not in obj or not isinstance(obj["items"], list) or not obj["items"]:
                errors.append("Manifest: falta 'items' (Canvases)")
        elif typ in ("AnnotationPage","AnnotationCollection"):
            items = obj.get("items")
            if not isinstance(items, list) or not items:
                errors.append(f"{typ}: falta 'items'")
            else:
                for i,ann in enumerate(items if typ=="AnnotationPage" else []):
                    if ann.get("type") != "Annotation":
                        errors.append(f"items[{i}] no es Annotation")
                    if "target" not in ann:
                        errors.append(f"Annotation items[{i}] sin 'target'")
        # not exhaustive, just sanity
    if errors:
        messagebox.showwarning("IIIF - Validador", "Problemas detectados:\n- " + "\n- ".join(errors))
    else:
        messagebox.showinfo("IIIF - Validador", "Estructura básica OK.")



def push_iiif_annotationpages(self):
    if not self.doc_id:
        messagebox.showwarning("IIIF AnnoPages","Crea/abre un proyecto."); return
    # Build in-memory AnnotationCollection (reuse exporter logic inline)
    import cv2
    out = {"@context": "http://iiif.io/api/presentation/3/context.json", "type":"AnnotationCollection", "id": f"urn:geodocs:ac:{self.doc_id}", "items":[]}
    with db_connect() as con:
        con.row_factory=sqlite3.Row
        rows = list(con.execute("""SELECT a.id AS aid, a.page_id, a.body, a.type, a.tags, a.target_region, p.seq, p.processed_path 
                                   FROM annotation a LEFT JOIN page p ON p.id=a.page_id 
                                   WHERE a.document_id=? AND IFNULL(a.target_region,'')!='' ORDER BY p.seq, a.id""",(self.doc_id,)))
    from collections import defaultdict
    by_seq = defaultdict(list)
    for r in rows: by_seq[r["seq"]].append(r)
    for seq, anns in sorted(by_seq.items()):
        W=700; H=1000
        img_path = next((r["processed_path"] for r in anns if r["processed_path"]), None)
        if img_path and Path(img_path).exists():
            try:
                im = cv2.imread(img_path); 
                if im is not None: H, W = im.shape[:2]
            except: pass
        ap = {"id": f"urn:geodocs:ap:px:{self.doc_id}:{seq}", "type":"AnnotationPage", "items":[]}
        for r in anns:
            try:
                x,y,w,h = [float(v) for v in (r["target_region"] or "").split(",")]
                target = f"urn:geodocs:canvas:{self.doc_id}:{seq}#xywh=pixel:{int(x*W)},{int(y*H)},{max(1,int(w*W))},{max(1,int(h*H))}"
            except: 
                continue
            ap["items"].append({
                "id": f"urn:geodocs:wa:px:{r['aid']}",
                "type":"Annotation",
                "motivation":["highlighting","commenting"],
                "body":[{"type":"TextualBody","value": r["body"] or "", "format":"text/plain","purpose":"commenting"}],
                "target": target
            })
        out["items"].append(ap)
    # POST to /api/iiif/annotations
    base = (self.api.config.get("api_base_url") or "").rstrip("/")
    url = base + "/api/iiif/annotations"
    import requests
    try:
        r = requests.post(url, headers=self.api.headers(), json=out, timeout=self.api.timeout(), verify=self.api.verify())
        r.raise_for_status()
        messagebox.showinfo("GeoDocs", "AnnotationPages (pixel) subidas correctamente.")
    except Exception as ex:
        messagebox.showerror("GeoDocs", f"Error al subir AnnotationPages: {ex}")

def push_linked_places(self):
    if not self.doc_id:
        messagebox.showwarning("Linked Places","Crea/abre un proyecto."); return
    # Build minimal Linked Places GeoJSON-LD in-memory (reuse exporter)
    ctx = [
        "http://geojson.org/geojson-ld/geojson-context.jsonld",
        {"lp":"http://linkedpasts.org/vocab#","dcterms":"http://purl.org/dc/terms/","name":"http://schema.org/name"}
    ]
    feats=[]
    with db_connect() as con:
        con.row_factory=sqlite3.Row
        for r in con.execute("""SELECT a.id, a.latitude, a.longitude, a.body, a.tags, a.toponimo_id, a.persona_id 
                                FROM annotation a WHERE a.document_id=? AND a.latitude IS NOT NULL AND a.longitude IS NOT NULL""",(self.doc_id,)):
            feats.append({
                "type":"Feature",
                "geometry":{"type":"Point","coordinates":[r["longitude"], r["latitude"]]},
                "properties":{"name": r["body"], "lp:relationType":"mentions", "toponimo_id": r["toponimo_id"], "persona_id": r["persona_id"], "tags": r["tags"]}
            })
    obj={"type":"FeatureCollection","features":feats,"@context":ctx}
    base = (self.api.config.get("api_base_url") or "").rstrip("/")
    url = base + "/api/linked-places"
    import requests
    try:
        r = requests.post(url, headers=self.api.headers(), json=obj, timeout=self.api.timeout(), verify=self.api.verify())
        r.raise_for_status()
        messagebox.showinfo("GeoDocs", "Linked Places subido correctamente.")
    except Exception as ex:
        messagebox.showerror("GeoDocs", f"Error al subir Linked Places: {ex}")



# -------- OCR handlers --------
def load_ocr_text(self):
    sel = self.listbox.curselection()
    if not sel: 
        self.status("Selecciona una página."); return
    seq = int(sel[0])
    with db_connect() as con:
        con.row_factory = sqlite3.Row
        r = con.execute("SELECT ocr_text FROM page WHERE document_id=? AND seq=?", (self.doc_id, seq)).fetchone()
    self.ocr_text.delete("1.0","end")
    if r and r["ocr_text"]:
        self.ocr_text.insert("1.0", r["ocr_text"])

def save_ocr_text(self):
    sel = self.listbox.curselection()
    if not sel: 
        self.status("Selecciona una página."); return
    seq = int(sel[0])
    txt = self.ocr_text.get("1.0","end").strip()
    with db_connect() as con:
        con.execute("UPDATE page SET ocr_text=?, face=?, status='done' WHERE document_id=? AND seq=?", (txt, self.face_var.get(), self.doc_id, seq))
        con.commit()
    self.status("Texto OCR guardado.")

def do_ocr_current_page(self):
    # Try running pytesseract if available
    try:
        import pytesseract
        from PIL import Image
    except Exception as ex:
        messagebox.showwarning("OCR","pytesseract no disponible en este entorno."); return
    sel = self.listbox.curselection()
    if not sel: 
        self.status("Selecciona una página."); return
    seq = int(sel[0])
    with db_connect() as con:
        r = con.execute("SELECT processed_path FROM page WHERE document_id=? AND seq=?", (self.doc_id, seq)).fetchone()
    if not r or not r[0] or not Path(r[0]).exists():
        messagebox.showwarning("OCR","No hay imagen para esta página."); return
    img = r[0]
    # Basic config
    conf = {"default_lang":"spa+eng","psm":3,"oem":3}
    cfg_path = BASE_DIR/"ocr_config.json"
    if cfg_path.exists():
        try:
            conf = json.loads(cfg_path.read_text(encoding="utf-8"))
        except: pass
    cfg = f'--psm {int(conf.get("psm",3))} --oem {int(conf.get("oem",3))}'
    lang = conf.get("default_lang","spa+eng")
    try:
        text = pytesseract.image_to_string(Image.open(img), lang=lang, config=cfg)
    except Exception as ex:
        messagebox.showerror("OCR", str(ex)); return
    self.ocr_text.delete("1.0","end")
    self.ocr_text.insert("1.0", text)
    with db_connect() as con:
        con.execute("UPDATE page SET ocr_text=?, status='done' WHERE document_id=? AND seq=?", (text, self.doc_id, seq))
        con.commit()
    self.status("OCR actualizado.")

# -------- OCR upload (REST) --------
def upload_ocr_page(self):
    sel = self.listbox.curselection()
    if not sel: 
        self.status("Selecciona una página."); return
    seq = int(sel[0])
    with db_connect() as con:
        con.row_factory=sqlite3.Row
        r = con.execute("SELECT p.id, p.seq, p.processed_path, p.ocr_text FROM page p WHERE p.document_id=? AND p.seq=?", (self.doc_id, seq)).fetchone()
    if not r: 
        messagebox.showwarning("OCR","No se encontró la página."); return
    base = (self.api.config.get("api_base_url") or "").rstrip("/")
    url = base + "/api/pages/upload"
    import requests
    files = {}
    data = {"document_id": self.doc_id, "page_number": r["seq"]}
    if r["processed_path"] and Path(r["processed_path"]).exists():
        files["file"] = open(r["processed_path"], "rb")
    if r["ocr_text"]:
        files["ocr"] = ("page_{:04d}.txt".format(r["seq"]), r["ocr_text"], "text/plain")
    try:
        resp = requests.post(url, headers=self.api.headers(), files=files, data=data, timeout=self.api.timeout(), verify=self.api.verify())
        resp.raise_for_status()
        messagebox.showinfo("GeoDocs","OCR de la página subido.")
    except Exception as ex:
        messagebox.showerror("GeoDocs", f"Error al subir OCR: {ex}")
    finally:
        for k,v in list(files.items()):
            if hasattr(v, "close"):
                v.close()

def upload_ocr_document(self):
    # Create a temp ZIP with images + ocr
    import tempfile, zipfile
    tmpdir = tempfile.mkdtemp()
    ocr_dir = Path(tmpdir)/"ocr"; img_dir = Path(tmpdir)/"images"
    ocr_dir.mkdir(parents=True, exist_ok=True); img_dir.mkdir(parents=True, exist_ok=True)
    with db_connect() as con:
        con.row_factory=sqlite3.Row
        rows = list(con.execute("SELECT seq, processed_path, ocr_text FROM page WHERE document_id=? ORDER BY seq", (self.doc_id,)))
    for r in rows:
        if r["processed_path"] and Path(r["processed_path"]).exists():
            shutil.copy2(r["processed_path"], img_dir/("page_{:04d}.png".format(r["seq"])))
        if r["ocr_text"]:
            (ocr_dir/("page_{:04d}.txt".format(r["seq"]))).write_text(r["ocr_text"], encoding="utf-8")
    manifest = {"document_id": self.doc_id, "count": len(rows)}
    (Path(tmpdir)/"metadata.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    zip_path = Path(tmpdir)/f"document_{self.doc_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in img_dir.rglob("*"):
            z.write(p, arcname=p.relative_to(Path(tmpdir)))
        for p in ocr_dir.rglob("*"):
            z.write(p, arcname=p.relative_to(Path(tmpdir)))
        z.write(Path(tmpdir)/"metadata.json", arcname="metadata.json")
    base = (self.api.config.get("api_base_url") or "").rstrip("/")
    url = base + "/api/documentos/upload"
    import requests
    try:
        with open(zip_path, "rb") as f:
            resp = requests.post(url, headers=self.api.headers(), files={"file":("document.zip", f, "application/zip")}, timeout=self.api.timeout(), verify=self.api.verify())
            resp.raise_for_status()
        messagebox.showinfo("GeoDocs", "ZIP con imágenes+OCR subido.")
    except Exception as ex:
        messagebox.showerror("GeoDocs", f"Error al subir ZIP: {ex}")



def force_quality_batch(self):
    try:
        from modules.quality_engine import set_env, run_quality_batch
        set_env(GLOBAL_DB, BASE_DIR)
        res = run_quality_batch(doc_id=self.doc_id if hasattr(self, 'doc_id') else None)
        messagebox.showinfo("Calidad", f"Analizadas {res['processed']} páginas en {res['seconds']}s.")
    except Exception as ex:
        messagebox.showerror("Calidad", str(ex))

def toggle_scheduler(self):
    try:
        from modules.scheduler import SCHEDULER
        if SCHEDULER._th and SCHEDULER._th.is_alive():
            SCHEDULER.stop()
            messagebox.showinfo("Scheduler", "Scheduler detenido.")
        else:
            SCHEDULER.start()
            messagebox.showinfo("Scheduler", "Scheduler iniciado.")
    except Exception as ex:
        messagebox.showerror("Scheduler", str(ex))



def run_calibration_size(self, size_name):
    from tkinter import filedialog, messagebox
    try:
        path = filedialog.askopenfilename(title=f"Imagen para calibración {size_name}", filetypes=[("Images","*.jpg *.jpeg *.png *.tif *.tiff")])
        if not path: return
        from modules.calibration import run_calibration
        calib = run_calibration(path, size_name, BASE_DIR, GLOBAL_DB, getattr(self, 'doc_id', 1))
        messagebox.showinfo("Calibración", f"DPI estimados: {calib['dpi_x']} x {calib['dpi_y']} — Guardado en calibration.json")
    except Exception as ex:
        messagebox.showerror("Calibración", str(ex))



    def enable_auto_exposure(self):
        from tkinter import messagebox
        try:
            from modules.camera_control import AutoExposureController
            self._aec = AutoExposureController(getattr(self, "camera_index", 0))
            ok, msg = self._aec.start()
            messagebox.showinfo("Cámara", msg)
        except Exception as ex:
            messagebox.showerror("Cámara", str(ex))
    def disable_auto_exposure(self):
        from tkinter import messagebox
        try:
            if hasattr(self, "_aec") and self._aec: self._aec.stop()
            messagebox.showinfo("Cámara", "Auto-exposición detenida.")
        except Exception as ex:
            messagebox.showerror("Cámara", str(ex))
    def apply_enhancer_current(self):
        from tkinter import messagebox, filedialog
        try:
            from modules.image_enhancer import enhance_image
            path = filedialog.askopenfilename(title="Imagen a mejorar", filetypes=[("Images","*.jpg *.jpeg *.png *.tif *.tiff")])
            if not path: return
            out = path.rsplit('.',1)[0] + "_enhanced.jpg"
            enh_path, meta = enhance_image(path, out, None, None, {})
            messagebox.showinfo("Mejora", f"Guardado en: {enh_path}\n{meta['method'] if meta else ''}")
        except Exception as ex:
            messagebox.showerror("Mejora", str(ex))
    
def auto_adjust_exposure(self):
    from tkinter import messagebox, simpledialog
    try:
        tgt = simpledialog.askfloat("Cámara", "Brillo objetivo [0..1] (por defecto 0.5):", minvalue=0.1, maxvalue=0.9)
        if tgt is None: tgt = 0.5
        from modules.camera_control import AutoExposureController
        if not hasattr(self, "_aec") or self._aec is None:
            self._aec = AutoExposureController(getattr(self, "camera_index", 0))
            self._aec.start()
        ok, msg = self._aec.auto_adjust_loop(target_mean=float(tgt))
        messagebox.showinfo("Cámara", msg if ok else "No soportado por el backend")
    except Exception as ex:
        messagebox.showerror("Cámara", str(ex))

def apply_enhancer_project(self):
        from tkinter import messagebox
        try:
            from modules.quality_engine import set_env, run_quality_batch
            set_env(GLOBAL_DB, BASE_DIR)
            res = run_quality_batch(doc_id=getattr(self, 'doc_id', None))
            messagebox.showinfo("Mejora por lotes", f"Procesadas {res['processed']} páginas.")
        except Exception as ex:
            messagebox.showerror("Mejora por lotes", str(ex))



    def validate_geom(self):
        from tkinter import messagebox, filedialog
        try:
            from modules.batch_validator import validate_project
            out = filedialog.asksaveasfilename(title="Guardar CSV de validación", defaultextension=".csv", initialfile="geom_validation.csv")
            if not out: return
            res = validate_project(GLOBAL_DB, out)
            messagebox.showinfo("Validación", f"Filas: {len(res)}\nCSV: {out}")
        except Exception as ex:
            messagebox.showerror("Validación", str(ex))

    def export_quality_report(self):
        from tkinter import messagebox, filedialog
        try:
            from modules.batch_validator import build_report_pdf
            csv_path = filedialog.askopenfilename(title="Seleccionar CSV de validación", filetypes=[("CSV","*.csv")])
            if not csv_path: return
            out_pdf = filedialog.asksaveasfilename(title="Guardar informe (PDF)", defaultextension=".pdf", initialfile="informe_calidad.pdf")
            if not out_pdf: return
            ok, path = build_report_pdf(BASE_DIR, csv_path, out_pdf)
            if ok: messagebox.showinfo("Informe", f"PDF generado: {path}")
            else: messagebox.showwarning("Informe", f"No se pudo generar PDF. Informe alternativo: {path}")
        except Exception as ex:
            messagebox.showerror("Informe", str(ex))



    def ui_zoom(self, factor):
        try:
            import tkinter as tk
            s = tk.Tk().tk.call('tk', 'scaling')
        except Exception:
            s = 1.0
        new = max(0.6, min(2.0, s*factor))
        try:
            import tkinter as tk
            tk._default_root.tk.call('tk', 'scaling', new)
        except Exception:
            pass
    def toggle_high_contrast(self):
        try:
            import tkinter as tk
            style_bg = "#111111" if getattr(self, "_hc", False) is False else "#f0f0f0"
            fg = "#ffffff" if style_bg=="#111111" else "#000000"
            tk._default_root.configure(bg=style_bg)
            self._hc = not getattr(self, "_hc", False)
        except Exception:
            pass



    def tts_run(self, corrected: bool):
        from tkinter import simpledialog, messagebox
        try:
            pid = simpledialog.askinteger("TTS", "ID de página:")
            if not pid: return
            import sqlite3, re, os
            con = sqlite3.connect(GLOBAL_DB); con.row_factory=sqlite3.Row
            r = con.execute("SELECT ocr_text, ocr_html FROM page WHERE id=?", (pid,)).fetchone(); con.close()
            if not r: messagebox.showerror("TTS","Página no encontrada"); return
            text = (r["ocr_html"] or "") if corrected else (r["ocr_text"] or "")
            if corrected: text = re.sub("<[^<]+?>", " ", text)
            out = os.path.join(BASE_DIR, f"tts_page_{pid}_{'corr' if corrected else 'raw'}.wav")
            from modules.tts import synth_to_file
            ok, path = synth_to_file(text, out, "es")
            if ok: messagebox.showinfo("TTS", f"Audio: {path}")
            else: messagebox.showwarning("TTS", f"No se pudo sintetizar; se guardó TXT: {path}")
        except Exception as ex:
            messagebox.showerror("TTS", str(ex))

    def spellcheck_page(self):
        from tkinter import simpledialog, messagebox
        try:
            pid = simpledialog.askinteger("Revisión", "ID de página:")
            if not pid: return
            import sqlite3, re, json
            con = sqlite3.connect(GLOBAL_DB); con.row_factory=sqlite3.Row
            r = con.execute("SELECT ocr_html FROM page WHERE id=?", (pid,)).fetchone(); con.close()
            text = re.sub("<[^<]+?>", " ", (r["ocr_html"] or ""))
            from modules.spellcheck import check_text
            res = check_text(text, "es")
            messagebox.showinfo("Revisión", f"Herramienta: {res['tool']}\nHallazgos: {len(res['issues'])}")
        except Exception as ex:
            messagebox.showerror("Revisión", str(ex))



    def tts_generate_current(self):
        from tkinter import simpledialog, messagebox
        try:
            pid = simpledialog.askinteger("TTS", "ID de página:")
            if not pid: return
            import sqlite3, re, os
            con = sqlite3.connect(GLOBAL_DB); con.row_factory=sqlite3.Row
            r = con.execute("SELECT ocr_text, ocr_html FROM page WHERE id=?", (pid,)).fetchone(); con.close()
            if not r: messagebox.showerror("TTS","Página no encontrada"); return
            choice = messagebox.askyesno("TTS", "¿Usar OCR CORREGIDO? (Sí) / Original (No)")
            text = (r["ocr_html"] or "") if choice else (r["ocr_text"] or "")
            if choice:
                text = re.sub("<[^<]+?>", " ", text)
            out = os.path.join(BASE_DIR, f"tts_page_{pid}_{'corr' if choice else 'raw'}")
            from modules.tts import synth_to_file
            ok, path = synth_to_file(text, out + ".wav", "es")
            messagebox.showinfo("TTS", f"Generado: {path}")
        except Exception as ex:
            messagebox.showerror("TTS", str(ex))

    def tts_play_file(self):
        from tkinter import filedialog, messagebox
        try:
            path = filedialog.askopenfilename(title="Seleccionar audio TTS", filetypes=[("Audio","*.wav *.mp3")])
            if not path: return
            from modules.tts import play_audio
            ok, backend = play_audio(path)
            if ok: messagebox.showinfo("TTS", f"Reproduciendo ({backend})")
            else: messagebox.showwarning("TTS", "No se pudo reproducir el audio (instale simpleaudio o playsound).")
        except Exception as ex:
            messagebox.showerror("TTS", str(ex))



    def export_audiobook(self):
        from tkinter import simpledialog, messagebox, filedialog
        import re, os, sqlite3
        try:
            doc = simpledialog.askinteger("Audiolibro", "ID de documento:")
            if not doc: return
            seq_from = simpledialog.askinteger("Rango", "Desde seq:", initialvalue=1) or 1
            seq_to = simpledialog.askinteger("Rango", "Hasta seq:", initialvalue=9999) or 9999
            use_corr = messagebox.askyesno("Audiolibro", "¿Usar OCR CORREGIDO? (Sí) / Original (No)")
            voice = simpledialog.askstring("Voz", "ID de voz (opcional):")
            rate = simpledialog.askinteger("Velocidad", "Rate pyttsx3 (opcional):")
            volume = simpledialog.askfloat("Volumen", "0.0..1.0 (opcional):")
            con = sqlite3.connect(GLOBAL_DB); con.row_factory=sqlite3.Row
            rows = con.execute("SELECT seq, ocr_text, ocr_html FROM page WHERE document_id=? AND seq BETWEEN ? AND ? ORDER BY seq", (doc, seq_from, seq_to)).fetchall(); con.close()
            texts = []
            for r in rows:
                t = (r["ocr_html"] or "") if use_corr else (r["ocr_text"] or "")
                if use_corr: t = re.sub("<[^<]+?>", " ", t)
                texts.append(t or "")
            outDir = filedialog.askdirectory(title="Carpeta de salida")
            if not outDir: return
            from modules.tts import synth_audiobook
            res = synth_audiobook(texts, outDir, base_name=f"doc_{doc}", voice_id=voice or None, rate=rate, volume=volume, voice_lang="es")
            messagebox.showinfo("Audiolibro", f"Generado en: {outDir}\nPistas: {len(res['tracks'])}\nPlaylist: {res['playlist']}\nMerge: {res.get('merged')}")
        except Exception as ex:
            messagebox.showerror("Audiolibro", str(ex))



    def show_abbrev_info(self):
        from tkinter import messagebox
        import os
        csv_p = os.path.join(BASE_DIR, "docs", "abreviaturas_academicas_es.csv")
        md_p = os.path.join(BASE_DIR, "docs", "abreviaturas_academicas_es.md")
        messagebox.showinfo("Abreviaturas", f"CSV: {csv_p}\nMD: {md_p}")



    def apply_style_doc(self):
        from tkinter import simpledialog, messagebox, filedialog
        try:
            doc = simpledialog.askinteger("Estilo", "ID de documento:")
            if not doc: return
            rules = simpledialog.askstring("Reglas JSON (opcional)", "{"expand_first_occurrence": true}")
            try:
                obj = json.loads(rules) if rules else None
            except Exception:
                obj = {"expand_first_occurrence": True}
            from modules.style_apply import apply_style_to_document
            out_dir = filedialog.askdirectory(title="Carpeta de salida para changelog")
            if not out_dir: return
            res = apply_style_to_document(GLOBAL_DB, doc, obj or {"expand_first_occurrence": True}, out_dir, language="es")
            messagebox.showinfo("Estilo", f"Cambios: {res['count']}\nCSV: {res['changes_csv']}")
        except Exception as ex:
            messagebox.showerror("Estilo", str(ex))

    def diff_gloss(self):
        from tkinter import simpledialog, messagebox
        import sqlite3, json
        try:
            a = simpledialog.askinteger("Diff glosarios", "ID A:")
            b = simpledialog.askinteger("Diff glosarios", "ID B:")
            if not a or not b: return
            con = sqlite3.connect(GLOBAL_DB); con.row_factory=sqlite3.Row
            ra = con.execute("SELECT terms_json FROM glossary WHERE id=?", (a,)).fetchone()
            rb = con.execute("SELECT terms_json FROM glossary WHERE id=?", (b,)).fetchone(); con.close()
            if not (ra and rb): messagebox.showerror("Diff","Glosarios no encontrados"); return
            A = json.loads(ra["terms_json"] or "{}"); B = json.loads(rb["terms_json"] or "{}")
            only_a = {k:A[k] for k in set(A)-set(B)}
            only_b = {k:B[k] for k in set(B)-set(A)}
            conflicts = {k:(A[k],B[k]) for k in set(A)&set(B) if A[k]!=B[k]}
            messagebox.showinfo("Diff", f"Solo A: {len(only_a)} | Solo B: {len(only_b)} | Conflictos: {len(conflicts)}")
        except Exception as ex:
            messagebox.showerror("Diff", str(ex))

    def merge_gloss(self):
        from tkinter import simpledialog, messagebox
        import sqlite3, json
        try:
            a = simpledialog.askinteger("Merge glosarios", "Base (A):")
            b = simpledialog.askinteger("Merge glosarios", "Otro (B):")
            if not a or not b: return
            con = sqlite3.connect(GLOBAL_DB); con.row_factory=sqlite3.Row
            ra = con.execute("SELECT terms_json FROM glossary WHERE id=?", (a,)).fetchone()
            rb = con.execute("SELECT terms_json FROM glossary WHERE id=?", (b,)).fetchone()
            if not (ra and rb): con.close(); messagebox.showerror("Merge","Glosarios no encontrados"); return
            A = json.loads(ra["terms_json"] or "{}"); B = json.loads(rb["terms_json"] or "{}")
            merged = dict(A); merged.update({k:v for k,v in B.items() if k not in merged})
            con.execute("UPDATE glossary SET terms_json=?, updated_at=datetime('now') WHERE id=?", (json.dumps(merged, ensure_ascii=False), a)); con.commit(); con.close()
            messagebox.showinfo("Merge", "Fusión completada en A")
        except Exception as ex:
            messagebox.showerror("Merge", str(ex))


def main():
    ensure_schema()
    root=Tk(); App(root); root.mainloop()

if __name__=="__main__":
    main()
