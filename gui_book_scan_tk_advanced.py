#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# gui_book_scan_tk_advanced.py — GeoDocs Research Suite v32.3
# Ver: avanzada con OCR/TTS/REST/Glosario/Comparador

# (El contenido completo se ha creado en esta sesión; para brevedad en el entorno
# de ejecución, incluimos la misma versión compacta. Si desea ver el detalle
# expandido, indíquelo y generamos además un README técnico del módulo.)

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3, time, json, sys
from dataclasses import dataclass, field
from PIL import Image, ImageTk, ImageEnhance, ImageFilter

try:
    import cv2
except Exception:
    cv2 = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

try:
    import language_tool_python
except Exception:
    language_tool_python = None

try:
    import requests
except Exception:
    requests = None

APP_NAME = "GeoDocs Scanner Avanzado"
APP_VERSION = "v32.3"
GLOBAL_DB = "geodocs.db"
REST_CONFIG = "rest_config.json"

def safe_mkdir(p: Path): p.mkdir(parents=True, exist_ok=True)
def load_json(p: Path, d: dict): 
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d
def save_json(p: Path, data: dict):
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def init_global_db():
    conn = sqlite3.connect(GLOBAL_DB); cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS archivos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, direccion TEXT, contacto TEXT, email TEXT, telefono TEXT
    );
    CREATE TABLE IF NOT EXISTS fondos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, descripcion TEXT, archivo_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS proyectos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT, signatura TEXT, tipo_documento TEXT, autor TEXT,
        tema TEXT, etiquetas TEXT, fecha TEXT, carpeta_raiz TEXT
    );
    """); conn.commit(); conn.close()

@dataclass
class ProjectInfo:
    titulo: str = "Proyecto_sin_nombre"
    carpeta_raiz: Path = field(default_factory=lambda: Path.cwd()/"proyectos"/"Proyecto_sin_nombre")
    pages_dir: Path = field(init=False)
    db_path: Path = field(init=False)
    def __post_init__(self):
        self.pages_dir = self.carpeta_raiz/"paginas"; self.db_path = self.carpeta_raiz/"project.db"
        safe_mkdir(self.carpeta_raiz); safe_mkdir(self.pages_dir)
        conn = sqlite3.connect(self.db_path); cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS paginas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT, side TEXT, ocr_original TEXT, ocr_corregido TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS ocr_versions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, page_id INTEGER, content TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS glosario(
            id INTEGER PRIMARY KEY AUTOINCREMENT, abbr TEXT, expansion TEXT, context TEXT, notes TEXT
        );
        """); conn.commit(); conn.close()

class StartFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=12); self.app=app
        ttk.Label(self, text=f"{APP_NAME} — {APP_VERSION}", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Button(self, text="Escáner", command=lambda: app.show_frame("scan")).grid(row=1, column=0, pady=6, sticky="w")
        ttk.Button(self, text="Anotaciones", command=lambda: app.show_frame("annot")).grid(row=1, column=1, pady=6, padx=8, sticky="w")
        ttk.Button(self, text="Config REST…", command=app.open_rest_config).grid(row=2, column=0, pady=6, sticky="w")
        self.lbl = ttk.Label(self, text=app.project_summary()); self.lbl.grid(row=3, column=0, columnspan=2, sticky="w")
    def refresh(self): self.lbl.config(text=self.app.project_summary())

class ScanFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=8); self.app=app
        self.var_two = tk.BooleanVar(value=True); self.var_face=tk.StringVar(value="anverso")
        self.bri=tk.DoubleVar(value=1.0); self.con=tk.DoubleVar(value=1.0); self.shp=tk.BooleanVar(value=False)
        tb=ttk.Frame(self); tb.grid(row=0,column=0,sticky="ew"); tb.columnconfigure(6, weight=1)
        ttk.Label(tb,text="Cámara:").grid(row=0,column=0); self.cmb=ttk.Combobox(tb,width=10,state="readonly"); self.cmb.grid(row=0,column=1)
        ttk.Button(tb,text="Refrescar",command=self.refresh_cams).grid(row=0,column=2,padx=4)
        ttk.Button(tb,text="Conectar",command=self.open_cam).grid(row=0,column=3,padx=4)
        ttk.Button(tb,text="Desconectar",command=self.close_cam).grid(row=0,column=4,padx=4)
        ttk.Checkbutton(tb,text="Dos mitades",variable=self.var_two).grid(row=0,column=5,padx=8)
        ttk.Label(tb,text="Anverso/Reverso:").grid(row=0,column=6,sticky="e")
        ttk.Combobox(tb,textvariable=self.var_face,values=["anverso","reverso"],width=10,state="readonly").grid(row=0,column=7)
        sl=ttk.Frame(self); sl.grid(row=1,column=0,sticky="ew")
        ttk.Label(sl,text="Brillo").grid(row=0,column=0); ttk.Scale(sl,variable=self.bri,from_=0.5,to=1.5,orient="horizontal").grid(row=0,column=1,sticky="ew",padx=6)
        ttk.Label(sl,text="Contraste").grid(row=0,column=2); ttk.Scale(sl,variable=self.con,from_=0.5,to=1.5,orient="horizontal").grid(row=0,column=3,sticky="ew",padx=6)
        ttk.Checkbutton(sl,text="Nitidez",variable=self.shp).grid(row=0,column=4,padx=8)
        sl.columnconfigure(1,weight=1); sl.columnconfigure(3,weight=1)
        self.canvas=tk.Canvas(self,width=960,height=600,bg="#111"); self.canvas.grid(row=2,column=0,sticky="nsew",pady=6)
        self.rowconfigure(2,weight=1); self.columnconfigure(0,weight=1)
        bt=ttk.Frame(self); bt.grid(row=3,column=0,sticky="ew"); ttk.Button(bt,text="Capturar (SPACE)",command=self.capture).grid(row=0,column=0,padx=4)
        ttk.Button(bt,text="Volver",command=lambda: app.show_frame("start")).grid(row=0,column=1,padx=4)
        self.cap=None; self.running=False; self.tkimg=None; self.refresh_cams()
        self.bind_all("<space>", lambda e: self.capture()); self.bind_all("<F6>", lambda e: app.show_frame("annot"))
    def refresh_cams(self):
        cams=[]
        if cv2 is not None:
            for i in range(6):
                cap=cv2.VideoCapture(i, cv2.CAP_DSHOW) if sys.platform.startswith("win") else cv2.VideoCapture(i)
                if cap.isOpened(): cams.append(i)
                cap.release()
        self.cmb["values"]=cams or ["(sin cámara)"]; self.cmb.current(0)
    def open_cam(self):
        self.close_cam()
        if cv2 is None: messagebox.showwarning("Cámara","OpenCV no disponible"); return
        try: idx=int(self.cmb.get())
        except Exception: messagebox.showerror("Cámara","Índice inválido"); return
        self.cap=cv2.VideoCapture(idx, cv2.CAP_DSHOW) if sys.platform.startswith("win") else cv2.VideoCapture(idx)
        if not self.cap.isOpened(): messagebox.showerror("Cámara",f"No se pudo abrir {idx}"); self.cap=None; return
        self.running=True; self.after(10,self.loop)
    def close_cam(self):
        self.running=False
        if self.cap is not None:
            try: self.cap.release()
            except Exception: pass
            self.cap=None
    def loop(self):
        if not self.running or self.cap is None: return
        ok,fr=self.cap.read()
        if ok:
            fr=cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
            img=Image.fromarray(fr)
            if self.bri.get()!=1.0: img=ImageEnhance.Brightness(img).enhance(self.bri.get())
            if self.con.get()!=1.0: img=ImageEnhance.Contrast(img).enhance(self.con.get())
            if self.shp.get(): img=img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            cw,ch=self.canvas.winfo_width() or 960, self.canvas.winfo_height() or 600
            img.thumbnail((cw,ch), Image.LANCZOS)
            self.tkimg=ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            iw,ih=self.tkimg.width(),self.tkimg.height()
            self.canvas.create_image((cw-iw)//2,(ch-ih)//2,anchor="nw",image=self.tkimg)
            if self.var_two.get(): self.canvas.create_line(cw//2,0,cw//2,ch,fill="#00ffff",width=2,dash=(6,4))
        self.after(16,self.loop)
    def capture(self):
        if self.cap is None or not self.running: messagebox.showwarning("Captura","Cámara no disponible"); return
        ok,fr=self.cap.read()
        if not ok: messagebox.showerror("Captura","No se pudo capturar"); return
        fr=cv2.cvtColor(fr, cv2.COLOR_BGR2RGB); img=Image.fromarray(fr)
        if self.bri.get()!=1.0: img=ImageEnhance.Brightness(img).enhance(self.bri.get())
        if self.con.get()!=1.0: img=ImageEnhance.Contrast(img).enhance(self.con.get())
        if self.shp.get(): img=img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        proj=self.app.project
        if proj is None: messagebox.showinfo("Proyecto","Cree/abra un proyecto"); return
        ts=time.strftime("%Y%m%d_%H%M%S"); side=self.var_face.get()
        if self.var_two.get():
            w,h=img.size; L=img.crop((0,0,w//2,h)); R=img.crop((w//2,0,w,h))
            lp=proj.pages_dir/f"{ts}_{side}_L.jpg"; rp=proj.pages_dir/f"{ts}_{side}_R.jpg"
            L.save(lp,"JPEG",quality=92); R.save(rp,"JPEG",quality=92)
            self._reg(proj, lp.name, side); self._reg(proj, rp.name, side)
            messagebox.showinfo("Guardar", f"Guardadas:\n{lp.name}\n{rp.name}")
        else:
            op=proj.pages_dir/f"{ts}_{side}.jpg"; img.save(op,"JPEG",quality=92); self._reg(proj, op.name, side)
            messagebox.showinfo("Guardar", f"Guardada: {op.name}")
    def _reg(self, proj, filename, side):
        conn=sqlite3.connect(proj.db_path); cur=conn.cursor()
        cur.execute("INSERT INTO paginas(filename, side) VALUES (?,?)", (filename, side)); conn.commit(); conn.close()

class ComparePanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master); self.columnconfigure(0,weight=1); self.columnconfigure(1,weight=1); self.rowconfigure(0,weight=1)
        self.canvas=tk.Canvas(self,bg="#111"); self.canvas.grid(row=0,column=0,sticky="nsew")
        self.txt=tk.Text(self,wrap="word"); self.txt.grid(row=0,column=1,sticky="nsew")
        self.tkimg=None
    def load_image(self, path: Path):
        img=Image.open(path).convert("RGB"); cw=self.canvas.winfo_width() or 500; ch=self.canvas.winfo_height() or 600
        img.thumbnail((cw,ch), Image.LANCZOS); self.tkimg=ImageTk.PhotoImage(img)
        self.canvas.delete("all"); self.canvas.create_image(0,0,anchor="nw",image=self.tkimg)
    def load_text(self, text: str):
        self.txt.delete("1.0","end"); self.txt.insert("1.0", text or "")


class AnnotationFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=8); self.app=app
        self.engine=None
        if pyttsx3 is not None:
            try: self.engine=pyttsx3.init()
            except Exception: self.engine=None
        self.tool=None
        if language_tool_python is not None:
            try: self.tool=language_tool_python.LanguageTool('es')
            except Exception: self.tool=None
        tb=ttk.Frame(self); tb.grid(row=0,column=0,sticky="ew"); tb.columnconfigure(10,weight=1)
        ttk.Button(tb,text="OCR por lotes",command=self.batch_ocr).grid(row=0,column=0,padx=4)
        ttk.Button(tb,text="Importar glosario",command=self.import_glossary).grid(row=0,column=1,padx=4)
        ttk.Button(tb,text="TTS",command=self.tts).grid(row=0,column=2,padx=4)
        ttk.Button(tb,text="Ortografía",command=self.spell).grid(row=0,column=3,padx=4)
        ttk.Button(tb,text="REST subir",command=self.rest_push).grid(row=0,column=4,padx=4)
        ttk.Button(tb,text="REST pull",command=self.rest_pull).grid(row=0,column=5,padx=4)
        ttk.Button(tb,text="Volver",command=lambda: app.show_frame("start")).grid(row=0,column=6,padx=4)
        body=ttk.Panedwindow(self, orient="horizontal"); body.grid(row=1,column=0,sticky="nsew"); self.rowconfigure(1,weight=1); self.columnconfigure(0,weight=1)
        left=ttk.Frame(body,padding=6); ttk.Label(left,text="Páginas").pack(anchor="w"); self.lst=tk.Listbox(left); self.lst.pack(fill="both",expand=True)
        self.lst.bind("<<ListboxSelect>>", self.on_select)
        ttk.Button(left,text="Eliminar",command=self.delete_page).pack(pady=4,anchor="w")
        body.add(left,weight=1)
        center=ttk.Frame(body,padding=6); ttk.Label(center,text="Comparador").pack(anchor="w"); self.compare=ComparePanel(center); self.compare.pack(fill="both",expand=True); body.add(center,weight=3)
        right=ttk.Frame(body,padding=6); ttk.Label(right,text="OCR corregido").pack(anchor="w"); self.txt=tk.Text(right,wrap="word"); self.txt.pack(fill="both",expand=True)
        ttk.Button(right,text="Guardar",command=self.save_corr).pack(pady=4,anchor="e"); body.add(right,weight=2)
        self.refresh_list()
    def refresh_list(self):
        self.lst.delete(0,"end"); p=self.app.project
        if p is None: return
        for f in sorted(p.pages_dir.glob("*.jpg")): self.lst.insert("end", f.name)
    def on_select(self, e=None):
        p=self.app.project
        if p is None or not self.lst.curselection(): return
        name=self.lst.get(self.lst.curselection()[0]); imgp=p.pages_dir/name
        self.compare.load_image(imgp)
        pid,o1,c1=self._get_page(p,name); self.compare.load_text(c1 or o1 or ""); self.txt.delete("1.0","end"); self.txt.insert("1.0", c1 or o1 or "")
    def _get_page(self, proj, filename):
        conn=sqlite3.connect(proj.db_path); cur=conn.cursor()
        cur.execute("SELECT id, ocr_original, ocr_corregido FROM paginas WHERE filename=?", (filename,)); row=cur.fetchone(); conn.close()
        if row: return row[0], row[1], row[2]
        conn=sqlite3.connect(proj.db_path); cur=conn.cursor(); cur.execute("INSERT INTO paginas(filename) VALUES(?)", (filename,)); conn.commit(); pid=cur.lastrowid; conn.close()
        return pid, None, None
    def delete_page(self):
        p=self.app.project
        if p is None or not self.lst.curselection(): return
        name=self.lst.get(self.lst.curselection()[0]); (p.pages_dir/name).unlink(missing_ok=True)
        conn=sqlite3.connect(p.db_path); cur=conn.cursor(); cur.execute("DELETE FROM paginas WHERE filename=?", (name,)); conn.commit(); conn.close()
        self.refresh_list()
    def batch_ocr(self):
        p=self.app.project
        if p is None: messagebox.showinfo("OCR","Abra un proyecto"); return
        if pytesseract is None: messagebox.showwarning("OCR","pytesseract no disponible"); return
        count=0
        for path in sorted(p.pages_dir.glob("*.jpg")):
            try:
                img=Image.open(path).convert("RGB")
                img=ImageEnhance.Contrast(ImageEnhance.Brightness(img).enhance(1.05)).enhance(1.1)
                txt=pytesseract.image_to_string(img, lang="spa")
                self._store_ocr(p, path.name, txt); count+=1
            except Exception as ex:
                print("OCR error", ex)
        self.refresh_list(); messagebox.showinfo("OCR", f"OCR completado: {count}")
    def _store_ocr(self, proj, filename, text):
        pid,o1,c1=self._get_page(proj, filename)
        conn=sqlite3.connect(proj.db_path); cur=conn.cursor()
        if not o1:
            cur.execute("UPDATE paginas SET ocr_original=? WHERE id=?", (text, pid))
        else:
            cur.execute("INSERT INTO ocr_versions(page_id, content) VALUES (?,?)", (pid, text))
            cur.execute("UPDATE paginas SET ocr_original=? WHERE id=?", (text, pid))
        conn.commit(); conn.close()
    def save_corr(self):
        p=self.app.project
        if p is None or not self.lst.curselection(): return
        name=self.lst.get(self.lst.curselection()[0]); pid,o1,c1=self._get_page(p,name)
        content=self.txt.get("1.0","end").strip()
        conn=sqlite3.connect(p.db_path); cur=conn.cursor()
        cur.execute("UPDATE paginas SET ocr_corregido=? WHERE id=?", (content, pid))
        cur.execute("INSERT INTO ocr_versions(page_id, content) VALUES (?,?)", (pid, content))
        conn.commit(); conn.close(); messagebox.showinfo("OCR","Corrección guardada")
    def tts(self):
        if self.engine is None: messagebox.showwarning("TTS","pyttsx3 no disponible"); return
        txt=self.txt.get("1.0","end").strip()
        if not txt: return
        import threading
        threading.Thread(target=lambda: (self.engine.say(txt), self.engine.runAndWait()), daemon=True).start()
    def spell(self):
        if self.tool is None: messagebox.showwarning("Ortografía","language_tool_python no disponible"); return
        content=self.txt.get("1.0","end"); matches=self.tool.check(content)
        self.txt.tag_remove("spell","1.0","end"); self.txt.tag_config("spell", underline=True, foreground="#cc0000")
        for m in matches[:500]:
            try:
                start=f"1.0 + {m.offset} chars"; end=f"1.0 + {m.offset+m.errorLength} chars"
                self.txt.tag_add("spell", start, end)
            except Exception: pass
        messagebox.showinfo("Ortografía", f"Sugerencias: {len(matches)}")
    def import_glossary(self):
        p=self.app.project
        if p is None: messagebox.showinfo("Glosario","Abra un proyecto"); return
        path=filedialog.askopenfilename(filetypes=[("CSV/JSON/XML","*.csv *.json *.xml")])
        if not path: return
        added=0
        try:
            if path.lower().endswith(".json"):
                data=json.loads(Path(path).read_text(encoding="utf-8")); rows=data if isinstance(data,list) else []
            elif path.lower().endswith(".csv"):
                import csv
                rows=list(csv.DictReader(open(path, newline="", encoding="utf-8")))
            elif path.lower().endswith(".xml"):
                import xml.etree.ElementTree as ET
                root=ET.fromstring(Path(path).read_text(encoding="utf-8")); rows=[]
                for e in root.findall(".//entry"):
                    rows.append({"abbr":e.findtext("abbr",""),"expansion":e.findtext("expansion",""),"context":e.findtext("context",""),"notes":e.findtext("notes","")})
            else:
                rows=[]
            conn=sqlite3.connect(p.db_path); cur=conn.cursor()
            for r in rows:
                ab=(r.get("abbr") or r.get("Abreviatura") or "").strip()
                ex=(r.get("expansion") or r.get("Expansión") or "").strip()
                cx=(r.get("context") or r.get("Contexto") or "").strip()
                nt=(r.get("notes") or r.get("Notas") or "").strip()
                cur.execute("INSERT INTO glosario(abbr,expansion,context,notes) VALUES (?,?,?,?)", (ab,ex,cx,nt)); added+=1
            conn.commit(); conn.close()
        except Exception as ex:
            messagebox.showerror("Glosario", f"Error: {ex}"); return
        messagebox.showinfo("Glosario", f"Entradas importadas: {added}")
    def rest_push(self):
        if requests is None: messagebox.showwarning("REST","requests no disponible"); return
        cfg=load_json(REST_CONFIG,{"base_url":"","token":""}); base=cfg.get("base_url","" ).rstrip("/"); tok=cfg.get("token","" )
        if not base or not tok: messagebox.showwarning("REST","Configure base_url y JWT"); return
        p=self.app.project
        if p is None: messagebox.showinfo("REST","Abra un proyecto"); return
        url=f"{base}/api/documentos"; hdr={"Authorization":f"Bearer {tok}","Content-Type":"application/json; charset=utf-8"}
        payload={"titulo":p.titulo,"carpeta_raiz":str(p.carpeta_raiz)}
        try:
            r=requests.post(url, headers=hdr, json=payload, timeout=20)
            if r.status_code in (200,201): messagebox.showinfo("REST","Publicado correctamente")
            else: messagebox.showerror("REST", f"Error {r.status_code}: {r.text[:300]}")
        except Exception as ex:
            messagebox.showerror("REST", f"Conexión fallida: {ex}")
    def rest_pull(self):
        if requests is None: messagebox.showwarning("REST","requests no disponible"); return
        cfg=load_json(REST_CONFIG,{"base_url":"","token":""}); base=cfg.get("base_url","" ).rstrip("/"); tok=cfg.get("token","" )
        if not base or not tok: messagebox.showwarning("REST","Configure base_url y JWT"); return
        url=f"{base}/api/documentos"; hdr={"Authorization":f"Bearer {tok}"}
        try:
            r=requests.get(url, headers=hdr, timeout=20)
            if r.status_code==200: messagebox.showinfo("REST", f"Documentos remotos: {len(r.json())}")
            else: messagebox.showerror("REST", f"Error {r.status_code}: {r.text[:300]}")
        except Exception as ex:
            messagebox.showerror("REST", f"Conexión fallida: {ex}")

class GeoDocsScannerApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(f"{APP_NAME} — {APP_VERSION}"); self.geometry("1280x800"); self.minsize(1000,700)
        init_global_db(); self.project=None
        container=ttk.Frame(self); container.pack(fill="both",expand=True)
        self.frames={"start":StartFrame(container,self),"scan":ScanFrame(container,self),"annot":AnnotationFrame(container,self)}
        for f in self.frames.values(): f.grid(row=0,column=0,sticky="nsew")
        self._menu(); self.show_frame("start")
        self.bind_all("<Control-n>", lambda e:self.new_project()); self.bind_all("<Control-o>", lambda e:self.open_project())
        self.bind_all("<F6>", lambda e:self.toggle())
    def _menu(self):
        m=tk.Menu(self); f=tk.Menu(m,tearoff=0)
        f.add_command(label="Nuevo proyecto… (Ctrl+N)",command=self.new_project)
        f.add_command(label="Abrir proyecto… (Ctrl+O)",command=self.open_project)
        f.add_separator(); f.add_command(label="Config REST…",command=self.open_rest_config)
        f.add_separator(); f.add_command(label="Salir",command=self.quit_app)
        m.add_cascade(label="Archivo",menu=f)
        v=tk.Menu(m,tearoff=0); v.add_command(label="Escáner",command=lambda:self.show_frame("scan")); v.add_command(label="Anotaciones",command=lambda:self.show_frame("annot"))
        m.add_cascade(label="Ver",menu=v); self.config(menu=m)
    def show_frame(self,name):
        for k,fr in self.frames.items():
            if k==name: fr.tkraise(); getattr(fr,"refresh",lambda:None)()
        if name=="start": self.frames["start"].refresh()
    def toggle(self):
        self.show_frame("annot" if self.frames["scan"].winfo_ismapped() else "scan")
    def new_project(self):
        import tkinter.simpledialog as sd
        title=sd.askstring("Nuevo proyecto","Título del documento:"); 
        if not title: return
        root=filedialog.askdirectory(title="Seleccione carpeta raíz del proyecto"); 
        if not root: return
        p=ProjectInfo(titulo=title, carpeta_raiz=Path(root)/title); self.project=p
        conn=sqlite3.connect(GLOBAL_DB); cur=conn.cursor()
        cur.execute("INSERT INTO proyectos(titulo,carpeta_raiz) VALUES(?,?)", (title, str(p.carpeta_raiz))); conn.commit(); conn.close()
        messagebox.showinfo("Proyecto", f"Creado en:\n{p.carpeta_raiz}"); self.show_frame("scan")
    def open_project(self):
        root=filedialog.askdirectory(title="Seleccione carpeta del proyecto"); 
        if not root: return
        pr=Path(root); 
        if not (pr/"paginas").exists(): messagebox.showerror("Proyecto","No contiene 'paginas/'"); return
        self.project=ProjectInfo(titulo=pr.name, carpeta_raiz=pr); messagebox.showinfo("Proyecto", f"Abierto: {pr.name}"); self.show_frame("scan")
    def open_rest_config(self):
        d=tk.Toplevel(self); d.title("REST GeoDocs"); d.resizable(False,False)
        cfg=load_json(Path(REST_CONFIG),{"base_url":"","token":""})
        frm=ttk.Frame(d,padding=12); frm.grid(row=0,column=0)
        ttk.Label(frm,text="Base URL:").grid(row=0,column=0,sticky="w"); u=tk.StringVar(value=cfg.get("base_url","")); ttk.Entry(frm,textvariable=u,width=50).grid(row=0,column=1)
        ttk.Label(frm,text="JWT:").grid(row=1,column=0,sticky="w"); t=tk.StringVar(value=cfg.get("token","")); ttk.Entry(frm,textvariable=t,width=50,show="•").grid(row=1,column=1)
        def save(): save_json(Path(REST_CONFIG),{"base_url":u.get().strip(),"token":t.get().strip()}); messagebox.showinfo("REST","Guardado" ); d.destroy()
        ttk.Button(frm,text="Guardar",command=save).grid(row=2,column=1,sticky="e",pady=8)
        d.grab_set(); d.transient(self)
    def project_summary(self):
        return "— Ningún proyecto activo —" if self.project is None else f"{self.project.titulo} • {self.project.carpeta_raiz}"
    def quit_app(self):
        try: self.frames["scan"].close_cam()
        except Exception: pass
        self.destroy()

def main():
    app=GeoDocsScannerApp(); app.mainloop()

if __name__ == "__main__": main()
