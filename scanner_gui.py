
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sqlite3, cv2, numpy as np, time, json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
GLOBAL_DB = BASE_DIR / "geodocs_scanner.db"

def ensure_dirs(proj):
    (proj/"raw").mkdir(parents=True, exist_ok=True)
    (proj/"images").mkdir(parents=True, exist_ok=True)

def db_connect():
    return sqlite3.connect(GLOBAL_DB)

def next_seq(doc_id):
    with db_connect() as con:
        row = con.execute("SELECT MAX(seq) FROM page WHERE document_id=?", (doc_id,)).fetchone()
        m = row[0] if row and row[0] is not None else -1
        return m + 1

def create_project(base_dir: Path, title="Proyecto sin título"):
    # Crea carpeta y registro mínimo de proyecto+documento si no existe
    proj_dir = base_dir
    ensure_dirs(proj_dir)
    with db_connect() as con:
        cur = con.cursor()
        # proyecto
        cur.execute("INSERT INTO project (name, base_dir, created_at) VALUES (?,?,datetime('now'))", (proj_dir.name, str(proj_dir)))
        pid = cur.lastrowid
        # documento
        cur.execute("INSERT INTO document (project_id, title, created_at) VALUES (?,?,datetime('now'))", (pid, title))
        did = cur.lastrowid
        con.commit()
    return did, proj_dir

def open_existing_project(base_dir: Path):
    # Encuentra el último documento asociado a esa carpeta
    with db_connect() as con:
        cur = con.cursor()
        row = cur.execute("SELECT id FROM project WHERE base_dir=?", (str(base_dir),)).fetchone()
        if not row:
            raise RuntimeError("No se encontró proyecto registrado para esa carpeta.")
        proj_id = row[0]
        drow = cur.execute("SELECT id FROM document WHERE project_id=? ORDER BY id DESC LIMIT 1", (proj_id,)).fetchone()
        if not drow:
            raise RuntimeError("Ese proyecto no tiene documento asociado.")
        did = drow[0]
    return did, base_dir

def preprocess(img):
    # Conversión rápida: gris, blur, edges, mejora
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(g, (5,5), 0)
    e = cv2.Canny(g, 50, 150)
    # pequeña dilatación para unir bordes
    e = cv2.dilate(e, np.ones((3,3), np.uint8), iterations=1)
    # apilado
    stacked = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
    stacked[e>0] = (0,255,0)
    return g, stacked

class ScannerApp:
    def __init__(self, root):
        self.root = root
        root.title("GeoDocs — Escáner (módulo de captura)")
        menubar = tk.Menu(root)
        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="Importar páginas…", command=self.import_pages)
        m_file.add_command(label="Procesar (cola OCR) – ejecutar una pasada", command=self.run_queue_once)
        menubar.add_cascade(label="Archivo", menu=m_file)
        root.config(menu=menubar)
        self.cap = None
        self.running = False
        self.project_dir = None
        self.doc_id = None
        # UI
        top = ttk.Frame(root, padding=8); top.pack(fill="x")
        ttk.Button(top, text="📁 Abrir proyecto…", command=self.open_project).pack(side="left", padx=4)
        ttk.Button(top, text="🗂 Crear proyecto…", command=self.create_project_dialog).pack(side="left", padx=4)
        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(top, text="▶️ Iniciar cámara", command=self.start_cam).pack(side="left", padx=4)
        ttk.Button(top, text="⏸️ Detener cámara", command=self.stop_cam).pack(side="left", padx=4)
        ttk.Button(top, text="📸 Capturar", command=self.capture).pack(side="left", padx=4)
        ttk.Button(top, text="➡️ Ir a Anotar", command=self.open_annotator).pack(side="right", padx=4)
        # Status
        self.lbl = ttk.Label(root, text="Proyecto: (ninguno) — Cámara: detenida"); self.lbl.pack(anchor="w", padx=10, pady=6)
        # Canvases
        self.cv_live = tk.Canvas(root, width=640, height=360, bg="#222"); self.cv_live.pack(padx=8, pady=8)
        self.cv_prev = tk.Canvas(root, width=640, height=200, bg="#111"); self.cv_prev.pack(padx=8, pady=8)
        self.photo_live = None; self.photo_prev = None
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.stop_cam()
        self.root.destroy()

    def open_project(self):
        p = filedialog.askdirectory(title="Selecciona la carpeta raíz del proyecto")
        if not p: return
        did, proj = open_existing_project(Path(p))
        self.doc_id, self.project_dir = did, proj
        self.lbl.config(text=f"Proyecto: {proj.name} — Documento #{did}")

    def create_project_dialog(self):
        p = filedialog.askdirectory(title="Elige carpeta donde crear el proyecto")
        if not p: return
        title = "Nuevo proyecto"
        did, proj = create_project(Path(p), title=title)
        self.doc_id, self.project_dir = did, proj
        self.lbl.config(text=f"Proyecto creado: {proj.name} — Documento #{did}")

    def start_cam(self):
        if self.running: return
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Cámara", "No se pudo abrir la cámara"); return
        self.running = True
        self.update_loop()

    def stop_cam(self):
        self.running = False
        if self.cap:
            self.cap.release(); self.cap = None
        self.lbl.config(text=f"Proyecto: {self.project_dir.name if self.project_dir else '(ninguno)'} — Cámara: detenida")

    def update_loop(self):
        if not self.running: return
        ok, frame = self.cap.read()
        if ok:
            g, stacked = preprocess(frame)
            self.show_image(self.cv_live, frame)
            self.show_image(self.cv_prev, stacked)
            self.lbl.config(text=f"Proyecto: {self.project_dir.name if self.project_dir else '(ninguno)'} — Cámara: activa")
        self.root.after(30, self.update_loop)

    def show_image(self, canvas, bgr):
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        import PIL.Image, PIL.ImageTk
        im = PIL.Image.fromarray(rgb)
        cw, ch = int(canvas["width"]), int(canvas["height"])
        scale = min(cw/im.width, ch/im.height)
        im = im.resize((max(1,int(im.width*scale)), max(1,int(im.height*scale))))
        ph = PIL.ImageTk.PhotoImage(im)
        canvas.delete("all")
        canvas.create_image(cw//2, ch//2, image=ph, anchor="center")
        # keep reference
        if canvas is self.cv_live: self.photo_live = ph
        else: self.photo_prev = ph

    def capture(self):
        if not self.doc_id or not self.project_dir:
            messagebox.showwarning("Proyecto", "Crea o abre un proyecto antes de capturar."); return
        if not self.cap or not self.running:
            messagebox.showwarning("Cámara", "Inicia la cámara para capturar."); return
        ok, frame = self.cap.read()
        if not ok:
            messagebox.showerror("Cámara", "No se pudo leer frame."); return
        # Procesamiento simple (aquí podrías llamar a funciones de corrección avanzadas)
        g, stacked = preprocess(frame)
        seq = next_seq(self.doc_id)
        img_dir = self.project_dir/"images"; img_dir.mkdir(parents=True, exist_ok=True)
        out_path = img_dir/f"page_{seq:04d}.png"
        cv2.imwrite(str(out_path), frame)
        # Inserta fila en DB
        with db_connect() as con:
            con.execute("""INSERT INTO page (document_id, seq, src_path, processed_path, created_at, downloaded) VALUES (?,?,?,?,datetime('now'),1)""",
                        (self.doc_id, seq, None, str(out_path)))
            con.commit()
        messagebox.showinfo("Captura", f"Guardada página #{seq:04d}: {out_path}")

    def open_annotator(self):
        import subprocess, sys
        subprocess.Popen([sys.executable, str(BASE_DIR/"annotator_gui.py")])


def import_pages(self):
    # Simple importer: pick a folder of images (PNG/JPG/TIF). For PDF/TIFF multipágina requiere extras opcionales.
    folder = filedialog.askdirectory(title="Selecciona carpeta con imágenes")
    if not folder: return
    if not self.doc_id or not self.project_dir:
        messagebox.showwarning("Proyecto", "Crea o abre un proyecto antes de importar."); return
    import imghdr
    img_dir = Path(folder)
    count = 0
    for p in sorted(img_dir.iterdir()):
        if p.is_file() and imghdr.what(p) in ("png","jpeg","tiff","bmp"):
            seq = next_seq(self.doc_id)
            dest = (self.project_dir/"images"/f"page_{seq:04d}.png")
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                from PIL import Image
                Image.open(p).save(dest)
            except Exception:
                shutil.copy2(p, dest)
            with db_connect() as con:
                con.execute("INSERT INTO page (document_id, seq, processed_path, status, created_at, downloaded) VALUES (?,?,?,?,datetime('now'),1)", (self.doc_id, seq, str(dest), 'pending'))
                con.commit()
            count += 1
    messagebox.showinfo("Importación", f"Importadas {count} imágenes.")

def run_queue_once(self):
    import subprocess, sys
    proc = Path(__file__).resolve().parent / "processor_queue.py"
    subprocess.Popen([sys.executable, str(proc)])
    messagebox.showinfo("Cola", "Cola lanzada (una pasada). Revisa estados en Anotador.")


def main():
    root = tk.Tk()
    app = ScannerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
