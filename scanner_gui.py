
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sqlite3, cv2, numpy as np, time, json
from pathlib import Path
from services.capture_service import CaptureService
from services.export_service import ExportService
from models.book import Book, Annotation
import tkinter as tk
import webbrowser
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

        m_view = tk.Menu(menubar, tearoff=0)
        m_view.add_command(label="Visualización 3D del Libro", command=self.open_book_3d)
        menubar.add_cascade(label="Vista", menu=m_view)

        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="Ayuda / Documentación", command=self.open_help)
        menubar.add_cascade(label="Ayuda", menu=m_help)
        # Menú de exportación
        m_export = tk.Menu(menubar, tearoff=0)
        m_export.add_command(label="Exportar PDF…", command=self.export_pdf_action)
        m_export.add_command(label="Exportar IIIF Manifest…", command=self.export_iiif_action)
        m_export.add_command(label="Exportar TEI XML…", command=self.export_tei_action)
        m_export.add_command(label="Exportar Dublin Core…", command=self.export_dc_action)
        m_export.add_command(label="Exportar GeoJSON Anotaciones…", command=self.export_geojson_action)
        m_export.add_separator()
        m_export.add_command(label="Exportar Paquete Completo…", command=self.export_bundle_action)
        m_export.add_command(label="Exportar Selección Multiple…", command=self.open_export_dialog)
        menubar.add_cascade(label="Exportar", menu=m_export)
        root.config(menu=menubar)
        self.cap = None
        self.running = False
        self.project_dir = None
        self.doc_id = None
        self.export_service = ExportService()
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
        if self.capture_service.running:
            return
        if not self.capture_service.start():
            messagebox.showerror("Cámara", "No se pudo abrir la cámara"); return
        self.update_loop()
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
        self.capture_service.stop()
        self.lbl.config(text=f"Proyecto: {self.project_dir.name if self.project_dir else '(ninguno)'} — Cámara: detenida")
    def stop_cam(self):
        self.running = False
        if not self.capture_service.running:
            return
        frame = self.capture_service.read_frame()
        if frame is not None:
            _g, stacked = self.capture_service.preprocess(frame)
            self.show_image(self.cv_live, frame)
            self.show_image(self.cv_prev, stacked)
            self.lbl.config(text=f"Proyecto: {self.project_dir.name if self.project_dir else '(ninguno)'} — Cámara: activa")
        self.root.after(30, self.update_loop)
            g, stacked = preprocess(frame)
            self.show_image(self.cv_live, frame)
            self.show_image(self.cv_prev, stacked)
            self.lbl.config(text=f"Proyecto: {self.project_dir.name if self.project_dir else '(ninguno)'} — Cámara: activa")
        if not self.capture_service.running:
            messagebox.showwarning("Cámara", "Inicia la cámara para capturar."); return
        frame = self.capture_service.read_frame()
        if frame is None:
            messagebox.showerror("Cámara", "No se pudo leer frame."); return
        seq = next_seq(self.doc_id)
        img_dir = self.project_dir/"images"; img_dir.mkdir(parents=True, exist_ok=True)
        out_path = img_dir/f"page_{seq:04d}.png"
        if not self.capture_service.capture_and_save(frame, out_path):
            messagebox.showerror("Captura", "Error al guardar la imagen."); return
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
    def open_tutorial_wizard(self):
        try:
            from views.tutorial_wizard import open_tutorial
            open_tutorial(self.root)
        except Exception as e:
            messagebox.showerror("Tutorial", f"No se pudo abrir el tutorial: {e}")
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

    def open_book_3d(self):
        """Abre el visor 3D (Three.js) en navegador o integración incrustada si cefpython está disponible."""
        try:
            from views.book_3d_view import Book3DView
        except Exception:
            messagebox.showerror("3D", "No se pudo importar Book3DView.")
            return
        view = Book3DView()
        html = view.get_html_file()
        if not os.path.exists(html):
            messagebox.showwarning("3D", f"Archivo HTML no encontrado: {html}")
            return
        # Intento de incrustar con cefpython si existe
        try:
            import cefpython3 as cef
            win = tk.Toplevel(self.root)
            win.title("Libro 3D")
            frm = ttk.Frame(win); frm.pack(fill="both", expand=True)
            # Nota: Implementación completa de CEF requiere loop especial. Aquí fallback a navegador.
            raise RuntimeError("CEF embedding simplificada no implementada aún")
        except Exception:
            webbrowser.open_new_tab(f"file://{html}")
            messagebox.showinfo("3D", "Visor 3D abierto en el navegador.")

    def open_help(self):
        try:
            from views.help_window import open_help_window
        except Exception as e:
            messagebox.showerror("Ayuda", f"No se pudo cargar la ventana de ayuda: {e}")
            return
        open_help_window(self.root)

    # ==== Exportación ====
    def build_book(self) -> Book:
        if not self.project_dir:
            raise RuntimeError("No hay proyecto activo")
        images_dir = self.project_dir/"images"
        pages = []
        if images_dir.exists():
            for p in sorted(images_dir.glob("page_*.png")):
                pages.append(str(p))
        # Cargar anotaciones dinámicamente con metadatos extra
        annotations = []
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='annotation'")
                if cur.fetchone():
                    # Detectar columnas para meta (excluyendo las estándar conocidas)
                    cols = [c[1] for c in cur.execute("PRAGMA table_info(annotation)").fetchall()]
                    standard = {"id","document_id","page_seq","x","y","w","h","text"}
                    extra_cols = [c for c in cols if c not in standard]
                    select_cols = ["id","page_seq","x","y","w","h","text"] + extra_cols
                    sql = f"SELECT {', '.join(select_cols)} FROM annotation WHERE document_id=?"
                    for row in cur.execute(sql, (self.doc_id,)):
                        base_len = 7  # id,page_seq,x,y,w,h,text
                        aid, page_seq, x, y, w, h, txt = row[:base_len]
                        meta_values = row[base_len:]
                        meta = {}
                        for col_name, val in zip(extra_cols, meta_values):
                            if val is not None:
                                meta[col_name] = val
                        annotations.append(Annotation(id=str(aid), page=page_seq, bbox=(x, y, w, h), text=txt or "", meta=meta))
        except Exception as e:
            # Silenciar errores de anotaciones para no bloquear exportación
            print("[WARN] Error cargando anotaciones:", e)
        title = f"Documento {self.doc_id}" if self.doc_id else "Sin título"
        return Book(title=title, pages=pages, annotations=annotations)

    def ask_destination(self, filename: str, is_folder: bool = False) -> str:
        if is_folder:
            folder = filedialog.askdirectory(title="Selecciona carpeta destino")
            return folder if folder else ""
        base = filedialog.askdirectory(title="Selecciona carpeta destino")
        if not base:
            return ""
        return str(Path(base)/filename)

    def _ensure_project_and_pages(self) -> bool:
        if not self.doc_id or not self.project_dir:
            messagebox.showwarning("Proyecto", "Crea o abre un proyecto antes de exportar.")
            return False
        images_dir = self.project_dir/"images"
        if not images_dir.exists() or not any(images_dir.glob("page_*.png")):
            messagebox.showwarning("Páginas", "No hay páginas capturadas para exportar.")
            return False
        return True

    def export_pdf_action(self):
        if not self._ensure_project_and_pages():
            return
        dest = self.ask_destination("book.pdf")
        if not dest: return
        book = self.build_book()
        self._run_with_progress(lambda: self.export_service.export_pdf(book, dest), "Exportando PDF…", fmt="pdf")

    def export_iiif_action(self):
        if not self._ensure_project_and_pages():
            return
        dest = self.ask_destination("manifest.json")
        if not dest: return
        book = self.build_book()
        self._run_with_progress(lambda: self.export_service.export_iiif(book, dest), "Exportando IIIF…", fmt="iiif")

    def export_tei_action(self):
        if not self._ensure_project_and_pages():
            return
        dest = self.ask_destination("book.xml")
        if not dest: return
        book = self.build_book()
        self._run_with_progress(lambda: self.export_service.export_tei(book, dest), "Exportando TEI…", fmt="tei")

    def export_dc_action(self):
        if not self._ensure_project_and_pages():
            return
        dest = self.ask_destination("dublin_core.json")
        if not dest: return
        book = self.build_book()
        self._run_with_progress(lambda: self.export_service.export_dublin_core(book, dest), "Exportando Dublin Core…", fmt="dc")

    def export_geojson_action(self):
        if not self._ensure_project_and_pages():
            return
        dest = self.ask_destination("annotations.geojson")
        if not dest: return
        book = self.build_book()
        self._run_with_progress(lambda: self.export_service.export_geojson(book, dest), "Exportando GeoJSON…", fmt="geojson")

    def export_bundle_action(self):
        if not self._ensure_project_and_pages():
            return
        folder = self.ask_destination("bundle", is_folder=True)
        if not folder: return
        book = self.build_book()
        self._run_with_progress(lambda: self.export_service.export_bundle(book, folder), "Exportando paquete…", fmt="bundle")

    def open_export_dialog(self):
        if not self._ensure_project_and_pages():
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Exportar selección de formatos")
        frm = ttk.Frame(dlg, padding=10); frm.pack(fill="both", expand=True)
        vars = {}
        formats = [
            ("PDF", "pdf"),
            ("IIIF Manifest", "iiif"),
            ("TEI XML", "tei"),
            ("Dublin Core JSON-LD", "dc"),
            ("GeoJSON Anotaciones", "geojson"),
        ]
        for label, key in formats:
            v = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(frm, text=label, variable=v)
            cb.pack(anchor="w")
            vars[key] = v
        out_dir_var = tk.StringVar()
        def choose_dir():
            d = filedialog.askdirectory(title="Carpeta destino")
            if d: out_dir_var.set(d)
        ttk.Button(frm, text="Elegir carpeta destino…", command=choose_dir).pack(pady=6)
        ttk.Entry(frm, textvariable=out_dir_var, width=50).pack(fill="x")
        status = ttk.Label(frm, text="")
        status.pack(pady=4, anchor="w")
        progress = ttk.Progressbar(frm, mode="determinate", maximum=5, value=0)
        progress.pack(fill="x", pady=4)
        def run_export():
            folder = out_dir_var.get().strip()
            if not folder:
                messagebox.showwarning("Destino", "Selecciona carpeta destino."); return
            book = self.build_book()
            generated = []
            formats_order = ['pdf','iiif','tei','dc','geojson']
            total_selected = sum(1 for k in formats_order if vars[k].get())
            progress.config(maximum=max(1,total_selected), value=0)
            for k in formats_order:
                if not vars[k].get():
                    continue
                try:
                    if k == 'pdf':
                        generated.append(self.export_service.export_pdf(book, str(Path(folder)/'book.pdf')))
                    elif k == 'iiif':
                        generated.append(self.export_service.export_iiif(book, str(Path(folder)/'manifest.json')))
                    elif k == 'tei':
                        generated.append(self.export_service.export_tei(book, str(Path(folder)/'book.xml')))
                    elif k == 'dc':
                        generated.append(self.export_service.export_dublin_core(book, str(Path(folder)/'dublin_core.json')))
                    elif k == 'geojson':
                        generated.append(self.export_service.export_geojson(book, str(Path(folder)/'annotations.geojson')))
                    progress.step(1)
                    dlg.update_idletasks()
                except Exception as e:
                    messagebox.showerror("Exportación", f"Error en {k}: {e}"); return
            status.config(text=f"Generados {len(generated)} archivos.")
            # Mostrar resumen validaciones
            rep = self.export_service.validation_report
            lines = [f"{k}: size={v.get('size')} sha256={v.get('sha256')} ok={v.get('exists')}" for k,v in rep.items() if not k.startswith('__')]
            messagebox.showinfo("Exportación", "Exportación completada.\n" + "\n".join(lines))
        ttk.Button(frm, text="Exportar", command=run_export).pack(pady=10)
        ttk.Button(frm, text="Cerrar", command=dlg.destroy).pack()

    # === Utilidad de progreso para exportaciones individuales ===
    def _run_with_progress(self, func, msg: str, fmt: str):
        win = tk.Toplevel(self.root)
        win.title(msg)
        ttk.Label(win, text=msg).pack(padx=10, pady=6)
        bar = ttk.Progressbar(win, mode="indeterminate")
        bar.pack(fill="x", padx=10, pady=6)
        bar.start(10)
        status = ttk.Label(win, text="")
        status.pack(padx=10, pady=4, anchor="w")
        def do_export():
            try:
                out = func()
                rep = self.export_service.validation_report.get(fmt, {})
                status.config(text=f"Hecho: {out}")
                messagebox.showinfo("Exportación", f"{fmt} listo\nsize={rep.get('size')} sha256={rep.get('sha256')}")
            except Exception as e:
                status.config(text=f"Error: {e}")
                messagebox.showerror("Exportación", f"Fallo {fmt}: {e}")
            finally:
                bar.stop(); win.after(600, win.destroy)
        self.root.after(100, do_export)


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
