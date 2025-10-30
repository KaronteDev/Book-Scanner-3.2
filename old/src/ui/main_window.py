#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import cv2
import numpy as np
from pathlib import Path
import platform
import book_scan_core as core

from core.constants import (
    APP_NAME, BASE_DIR, GLOBAL_DB, 
    CONFIG_PATH, API_MAP_PATH, IMG_EXTS
)
from core.utils import sha256_of_file, list_cameras_with_names
from database.db import Database 
from api.geodocs import GeoDocsAPI

class MainWindow:
    def __init__(self, root: tk.Tk, db: Database, api: GeoDocsAPI):
        self.root = root
        self.db = db
        self.api = api
        
        # Estado de la aplicación
        self.cap = None  # Captura de cámara
        self.frame_bgr = None  # Frame actual
        self.photo_result = None  # Resultado procesado
        self.photo_preview = None  # Vista previa
        self.saved_images = []  # Imágenes guardadas
        self.project_root = None  # Carpeta del proyecto
        self.doc_id = None  # ID del documento actual
        
        # Configurar ventana principal
        self.root.title(APP_NAME)
        
        # Inicializar variables y UI
        self.setup_vars()
        self.setup_ui()
        
        # Configurar atajos de teclado
        self.setup_shortcuts()
        
        # Iniciar bucle de vista previa
        self.root.after(30, self.update_preview_loop)
    
    def setup_vars(self):
        """Inicializar variables de la interfaz."""
        # Document metadata
        self.title_var = tk.StringVar(value="Documento")
        self.author_var = tk.StringVar(value="")
        self.sig_var = tk.StringVar(value="")
        self.tema_var = tk.StringVar(value="")
        self.etiquetas_var = tk.StringVar(value="")
        self.tipo_var = tk.StringVar(value="")
        self.fecha_var = tk.StringVar(value="")
        self.lugar_var = tk.StringVar(value="")
        self.idioma_var = tk.StringVar(value="")
        self.derechos_var = tk.StringVar(value="")
        self.resumen_var = tk.StringVar(value="")
        self.refbib_var = tk.StringVar(value="")
        self.notas_var = tk.StringVar(value="")
        
        # Processing settings
        self.dewarp_mode = tk.StringVar(value="none")
        self.dewarp_strength = tk.DoubleVar(value=0.2)
        self.contrast_mode = tk.StringVar(value="clahe")
        self.final_scale = tk.DoubleVar(value=1.0)
        self.ocr_enabled = tk.IntVar(value=0)
        self.ocr_lang = tk.StringVar(value="spa+eng")
        self.mesh_cols = tk.IntVar(value=8)
        self.mesh_rows = tk.IntVar(value=12)
        self.asymmetric_mesh = tk.IntVar(value=0)
        self.capture_mode = tk.StringVar(value="single")
        
        # Camera settings
        self.exposure_var = tk.DoubleVar(value=-5.0)
        self.wb_var = tk.DoubleVar(value=5000)
        
        # Output settings
        self.out_dir_var = tk.StringVar(value=str(BASE_DIR))
        self.status_var = tk.StringVar(value="Listo - Sin proyecto")
    
    def setup_ui(self):
        """Configurar interfaz de usuario."""
        # Top controls
        top = tk.Frame(self.root)
        top.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(top, text="Cámara:").pack(side=tk.LEFT, padx=5)
        self.cam_list = list_cameras_with_names()
        self.combo_cam = ttk.Combobox(top, state="readonly", width=34,
                                     values=[f"{i}: {n}" for i,n in self.cam_list])
        self.combo_cam.current(0)
        self.combo_cam.pack(side=tk.LEFT, padx=5)
        
        tk.Label(top, text="Modo:").pack(side=tk.LEFT, padx=10)
        self.combo_mode = ttk.Combobox(top, state="readonly", width=10,
                                      values=["single", "double"])
        self.combo_mode.set(self.capture_mode.get())
        self.combo_mode.pack(side=tk.LEFT)
        
        tk.Button(top, text="Iniciar", command=self.start_camera).pack(side=tk.LEFT, padx=8)
        tk.Button(top, text="Detener", command=self.stop_camera).pack(side=tk.LEFT, padx=8)
        tk.Button(top, text="Capturar + Procesar",
                 command=self.capture_and_process).pack(side=tk.LEFT, padx=10)
        
        # Camera controls
        cam_ctrl = tk.Frame(self.root)
        cam_ctrl.pack(side=tk.TOP, fill=tk.X, pady=4)
        
        tk.Label(cam_ctrl, text="Exposición:").pack(side=tk.LEFT, padx=5)
        tk.Scale(cam_ctrl, from_=-13, to=0, resolution=0.5,
                orient=tk.HORIZONTAL, variable=self.exposure_var,
                command=self.apply_camera_props, length=200).pack(side=tk.LEFT)
        
        tk.Label(cam_ctrl, text="Balance blancos K:").pack(side=tk.LEFT, padx=5)
        tk.Scale(cam_ctrl, from_=2800, to=7500, resolution=100,
                orient=tk.HORIZONTAL, variable=self.wb_var,
                command=self.apply_camera_props, length=250).pack(side=tk.LEFT)
        
        # Main content area
        mid = tk.Frame(self.root)
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        left = tk.Frame(mid)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas_preview = tk.Canvas(left, bg="#111", width=700, height=400)
        self.canvas_preview.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas_result = tk.Canvas(left, bg="#111", width=700, height=400)
        self.canvas_result.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Page list
        right = tk.Frame(mid)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Label(right, text="Páginas escaneadas").pack(side=tk.TOP, pady=4)
        self.listbox = tk.Listbox(right, selectmode=tk.SINGLE, width=52, height=26)
        self.listbox.pack(side=tk.TOP, padx=6, pady=4)
        
        btns = tk.Frame(right)
        btns.pack(side=tk.TOP, pady=4)
        tk.Button(btns, text="↑", width=4, command=self.move_up).pack(side=tk.LEFT, padx=2)
        tk.Button(btns, text="↓", width=4, command=self.move_down).pack(side=tk.LEFT, padx=2)
        tk.Button(btns, text="Eliminar",
                 command=self.delete_selected).pack(side=tk.LEFT, padx=6)
        tk.Button(btns, text="Previsualizar",
                 command=self.preview_selected).pack(side=tk.LEFT, padx=6)
        
        # Processing controls
        proc = tk.Frame(self.root)
        proc.pack(side=tk.TOP, fill=tk.X, pady=6)
        
        tk.Label(proc, text="Descurvado:").pack(side=tk.LEFT, padx=5)
        self.combo_dewarp = ttk.Combobox(proc, state="readonly", width=14,
                                        values=["none", "cylindrical", "mesh"])
        self.combo_dewarp.set(self.dewarp_mode.get())
        self.combo_dewarp.pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(proc, text="Malla asimétrica (pliegue)",
                       variable=self.asymmetric_mesh).pack(side=tk.LEFT, padx=6)
        
        tk.Label(proc, text="Fuerza (cilíndrico):").pack(side=tk.LEFT, padx=5)
        tk.Scale(proc, from_=0.10, to=0.50, resolution=0.01,
                orient=tk.HORIZONTAL, variable=self.dewarp_strength,
                length=160).pack(side=tk.LEFT)
        
        tk.Label(proc, text="Contraste:").pack(side=tk.LEFT, padx=5)
        self.combo_contrast = ttk.Combobox(proc, state="readonly", width=10,
                                         values=["clahe", "adaptive"])
        self.combo_contrast.set(self.contrast_mode.get())
        self.combo_contrast.pack(side=tk.LEFT, padx=5)
        
        # Output panel
        out = tk.Frame(self.root)
        out.pack(side=tk.TOP, fill=tk.X, pady=6)
        
        tk.Label(out, text="Salida:").pack(side=tk.LEFT, padx=5)
        tk.Entry(out, textvariable=self.out_dir_var,
                width=60).pack(side=tk.LEFT, padx=5)
        tk.Button(out, text="Cambiar carpeta...",
                 command=self.choose_output_dir).pack(side=tk.LEFT, padx=5)
        tk.Button(out, text="Exportar PDF/A",
                 command=self.export_pdf).pack(side=tk.LEFT, padx=10)
        
        # Status bar
        tk.Label(self.root, textvariable=self.status_var).pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_shortcuts(self):
        """Configurar atajos de teclado."""
        self.root.bind_all("<Control-space>", lambda e: self.capture_and_process())
        self.root.bind_all("<Control-Delete>", lambda e: self.delete_selected())
        self.root.bind_all("<Control-Up>", lambda e: self.move_up())
        self.root.bind_all("<Control-Down>", lambda e: self.move_down())
        self.root.bind_all("<Control-p>", lambda e: self.preview_selected())
        self.root.bind_all("<Control-e>", lambda e: self.export_pdf())
        self.root.bind_all("<Control-q>", lambda e: self.root.destroy())
    
    def start_camera(self):
        """Inicializar y activar la cámara."""
        if not hasattr(self, 'cam_list'):
            self.cam_list = list_cameras_with_names()
        sel = self.combo_cam.get()
        idx = int(sel.split(":")[0])
        
        self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW if platform.system().lower()=="windows" else 0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        
        self.status("Cámara iniciada")
        
        # Aplicar configuración inicial
        self.apply_camera_props()
    
    def stop_camera(self):
        """Detener y liberar la cámara."""
        if self.cap:
            self.cap.release()
            self.cap = None
            self.status("Cámara detenida")
    
    def update_preview_loop(self):
        """Actualizar vista previa de la cámara."""
        if self.cap and self.cap.isOpened():
            ok, frame = self.cap.read()
            if ok:
                self.frame_bgr = frame
                self.draw_preview(frame)
        self.root.after(30, self.update_preview_loop)
    
    def draw_preview(self, bgr):
        """Dibujar frame en el canvas de vista previa."""
        h, w = bgr.shape[:2]
        cw = self.canvas_preview.winfo_width() or 640
        ch = self.canvas_preview.winfo_height() or 360
        scale = min(cw/w, ch/h)
        
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        im = Image.fromarray(rgb).resize((int(w*scale), int(h*scale)))
        self.photo_preview = ImageTk.PhotoImage(im)
        
        self.canvas_preview.delete("all")
        self.canvas_preview.create_image(cw//2, ch//2, image=self.photo_preview)
    
    def capture_and_process(self):
        """Capturar imagen y procesar."""
        if self.frame_bgr is None:
            self.status("No hay frame de cámara")
            return
            
        bgr = self.frame_bgr.copy()
        res = core.process_one_image(
            bgr,
            do_dewarp=None if self.dewarp_mode.get()=="none" else self.dewarp_mode.get(),
            dewarp_strength=float(self.dewarp_strength.get()),
            contrast_mode=self.contrast_mode.get(),
            final_scale=float(self.final_scale.get()),
            manual_quad=None,
            mesh=(self.dewarp_mode.get()=="mesh"),
            mesh_cols=int(self.mesh_cols.get()),
            mesh_rows=int(self.mesh_rows.get()),
            asymmetric=bool(self.asymmetric_mesh.get()),
            split_spread=(self.capture_mode.get()=="double"),
            ocr_lang=(self.ocr_lang.get() if self.ocr_enabled.get() else None)
        )
        
        out_dir = Path(self.out_dir_var.get())
        out_dir.mkdir(parents=True, exist_ok=True)
        
        pages = res if isinstance(res, list) else [res]
        for i, page in enumerate(pages, start=1):
            # Preparar visualización
            base = page["dewarped"]
            mono = page["post_gray"]
            stacked = np.hstack([base, cv2.cvtColor(mono, cv2.COLOR_GRAY2BGR)])
            
            # Mostrar resultado
            im = Image.fromarray(cv2.cvtColor(stacked, cv2.COLOR_BGR2RGB))
            cw, ch = self.canvas_result.winfo_width() or 640, self.canvas_result.winfo_height() or 360
            scale = min(cw/im.width, ch/im.height)
            im = im.resize((int(im.width*scale), int(im.height*scale)))
            self.photo_result = ImageTk.PhotoImage(im)
            self.canvas_result.delete("all")
            self.canvas_result.create_image(cw//2, ch//2, image=self.photo_result)
            
            # Guardar imagen
            fname = f"{self._slug(self.title_var.get())}_{len(self.saved_images)+1:04d}.jpg"
            out = out_dir / fname
            core.imwrite_auto(str(out), stacked, quality=95)
            self.saved_images.append(str(out))
            self.listbox.insert(tk.END, fname)
            
            # Calcular hash y guardar en DB
            hash_v = sha256_of_file(out)
            if self.doc_id:
                self.db.add_page(
                    self.doc_id,
                    len(self.saved_images)-1,
                    processed_path=str(out),
                    hash_sha256=hash_v
                )
                self.db.add_version_entry(
                    document_id=self.doc_id,
                    action="add_page",
                    details=f"{fname} hash={hash_v}"
                )
    
    def create_project_dialog(self):
        """Diálogo para crear nuevo proyecto."""
        proj_dir = filedialog.askdirectory(title="Selecciona carpeta del proyecto")
        if not proj_dir:
            return
            
        self.project_root = Path(proj_dir)
        for sub in ["raw", "processed", "ocr", "pdf"]:
            (self.project_root / sub).mkdir(parents=True, exist_ok=True)
        
        self.out_dir_var.set(str(self.project_root / "processed"))
        
        # Crear proyecto en DB
        project_id = self.db.create_project(
            self.title_var.get(),
            str(self.project_root)
        )
        
        # Crear documento
        self.doc_id = self.db.create_document(
            project_id,
            title=self.title_var.get(),
            signatura=self.sig_var.get(),
            tema=self.tema_var.get(),
            etiquetas=self.etiquetas_var.get(),
            tipo=self.tipo_var.get(),
            autor=self.author_var.get(),
            fecha_text=self.fecha_var.get(),
            lugar=self.lugar_var.get(),
            idioma=self.idioma_var.get(),
            derechos=self.derechos_var.get(),
            referencia_bibliografica=self.refbib_var.get(),
            resumen=self.resumen_var.get(),
            notas_internas=self.notas_var.get()
        )
        
        self.status(f"Proyecto creado — project_id={project_id}, doc_id={self.doc_id}")
    
    def batch_process_dialog(self):
        """Procesar un lote de imágenes."""
        folder = filedialog.askdirectory(title="Seleccionar carpeta con imágenes")
        if not folder:
            return
            
        folder = Path(folder)
        files = sorted([p for p in folder.iterdir() if p.suffix.lower() in IMG_EXTS])
        
        if not files:
            messagebox.showwarning("Lote", "Sin imágenes.")
            return
            
        if not self.project_root:
            if not messagebox.askyesno("Proyecto",
                "No hay proyecto activo. ¿Crear proyecto rápido en esta carpeta?"):
                return
            
            self.project_root = folder / "_proyecto"
            for sub in ["raw", "processed", "ocr", "pdf"]:
                (self.project_root / sub).mkdir(parents=True, exist_ok=True)
            
            self.out_dir_var.set(str(self.project_root / "processed"))
            
            # Crear proyecto y documento
            project_id = self.db.create_project(
                self.title_var.get(),
                str(self.project_root)
            )
            
            self.doc_id = self.db.create_document(
                project_id,
                title=self.title_var.get(),
                signatura=self.sig_var.get(),
                tema=self.tema_var.get(),
                etiquetas=self.etiquetas_var.get(),
                tipo=self.tipo_var.get(),
                autor=self.author_var.get(),
                fecha_text=self.fecha_var.get(),
                lugar=self.lugar_var.get(),
                idioma=self.idioma_var.get(),
                derechos=self.derechos_var.get(),
                referencia_bibliografica=self.refbib_var.get(),
                resumen=self.resumen_var.get(),
                notas_internas=self.notas_var.get()
            )
        
        processed_dir = Path(self.out_dir_var.get())
        raw_dir = self.project_root / "raw" if self.project_root else folder
        
        count = 0
        for p in files:
            bgr = core.imread_auto(str(p))
            if bgr is None:
                continue
                
            try:
                import shutil as _sh
                dest = raw_dir / p.name
                if str(dest).lower() != str(p).lower():
                    _sh.copy2(p, dest)
            except:
                pass
                
            # Procesar imagen
            res = core.process_one_image(
                bgr,
                do_dewarp=None if self.dewarp_mode.get()=="none" else self.dewarp_mode.get(),
                dewarp_strength=float(self.dewarp_strength.get()),
                contrast_mode=self.contrast_mode.get(),
                final_scale=float(self.final_scale.get()),
                manual_quad=None,
                mesh=(self.dewarp_mode.get()=="mesh"),
                mesh_cols=int(self.mesh_cols.get()),
                mesh_rows=int(self.mesh_rows.get()),
                asymmetric=bool(self.asymmetric_mesh.get()),
                split_spread=(self.capture_mode.get()=="double"),
                ocr_lang=(self.ocr_lang.get() if self.ocr_enabled.get() else None)
            )
            
            pages = res if isinstance(res, list) else [res]
            for page in pages:
                base = page["dewarped"]
                mono = page["post_gray"]
                stacked = np.hstack([base, cv2.cvtColor(mono, cv2.COLOR_GRAY2BGR)])
                
                fname = f"{self._slug(self.title_var.get())}_{count+1:04d}.jpg"
                out = processed_dir / fname
                
                core.imwrite_auto(str(out), stacked, quality=95)
                self.saved_images.append(str(out))
                self.listbox.insert(tk.END, fname)
                
                hash_v = sha256_of_file(out)
                self.db.add_page(
                    self.doc_id,
                    len(self.saved_images)-1,
                    src_path=str(raw_dir / p.name),
                    processed_path=str(out),
                    hash_sha256=hash_v
                )
                
                self.db.add_version_entry(
                    document_id=self.doc_id,
                    action="add_page",
                    details=f"{fname} hash={hash_v}"
                )
                
                count += 1
        
        self.status(f"Lote completado: {count} páginas")
    
    def _slug(self, t):
        """Convertir texto a slug para nombres de archivo."""
        import re
        s = re.sub(r'[^a-z0-9]+', '-', (t or '').strip().lower())
        s = re.sub(r'-+', '-', s).strip('-')
        return s or "documento"
        
    def move_up(self):
        """Mover la página seleccionada hacia arriba en la lista."""
        sel = self.listbox.curselection()
        if not sel:
            return
        i = sel[0]
        if i == 0:
            return
        self._swap(i, i-1)
        self._update_order_db()
    
    def move_down(self):
        """Mover la página seleccionada hacia abajo en la lista."""
        sel = self.listbox.curselection()
        if not sel:
            return
        i = sel[0]
        if i >= self.listbox.size()-1:
            return
        self._swap(i, i+1)
        self._update_order_db()
    
    def _swap(self, i, j):
        """Intercambiar dos elementos en la lista."""
        a = self.listbox.get(i)
        b = self.listbox.get(j)
        self.listbox.delete(j)
        self.listbox.insert(j, a)
        self.listbox.delete(i)
        self.listbox.insert(i, b)
        self.saved_images[i], self.saved_images[j] = self.saved_images[j], self.saved_images[i]
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(j)
    
    def _update_order_db(self):
        """Actualizar el orden de las páginas en la base de datos."""
        if not self.doc_id:
            return
        con = self.db.connect()
        try:
            for i, p in enumerate(self.saved_images):
                con.execute("UPDATE page SET seq=? WHERE processed_path=?", (i, p))
            con.commit()
        finally:
            con.close()
    
    def delete_selected(self):
        """Eliminar la página seleccionada."""
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        path = self.saved_images[idx]
        try:
            os.remove(path)
        except:
            pass
        del self.saved_images[idx]
        self.listbox.delete(idx)
        if self.doc_id:
            con = self.db.connect()
            try:
                con.execute("DELETE FROM page WHERE processed_path=?", (path,))
                con.commit()
            finally:
                con.close()
        self._update_order_db()
        self.status(f"Eliminada: {Path(path).name}")
    
    def preview_selected(self):
        """Previsualizar la página seleccionada."""
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < 0 or idx >= len(self.saved_images):
            return
        path = self.saved_images[idx]
        try:
            bgr = cv2.imread(path)
            if bgr is not None:
                h, w = bgr.shape[:2]
                cw = self.canvas_result.winfo_width() or 640
                ch = self.canvas_result.winfo_height() or 360
                scale = min(cw/w, ch/h)
                im = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                im = im.resize((int(w*scale), int(h*scale)))
                self.photo_result = ImageTk.PhotoImage(im)
                self.canvas_result.delete("all")
                self.canvas_result.create_image(cw//2, ch//2, image=self.photo_result)
        except Exception as ex:
            self.status(f"Error previsualizando: {ex}")
    
    def apply_camera_props(self, *args):
        """Aplicar configuración de la cámara."""
        if not self.cap:
            return
        try:
            self.cap.set(cv2.CAP_PROP_EXPOSURE, float(self.exposure_var.get()))
        except:
            pass
        try:
            self.cap.set(cv2.CAP_PROP_WHITE_BALANCE_BLUE_U, float(int(self.wb_var.get())))
        except:
            pass
    
    def choose_output_dir(self):
        """Diálogo para elegir carpeta de salida."""
        d = filedialog.askdirectory(title="Elegir carpeta de salida", 
                                   initialdir=self.out_dir_var.get())
        if d:
            self.out_dir_var.set(d)
            
    def status(self, msg):
        """Actualizar mensaje de estado."""
        self.status_var.set(msg)
        
    def export_pdf(self):
        """Exportar PDF/A con las páginas escaneadas."""
        if not self.saved_images:
            self.status("No hay páginas")
            return
            
        out_pdf = ((self.project_root / "pdf" / f"{self._slug(self.title_var.get())}.pdf") 
                   if self.project_root else (Path(self.out_dir_var.get()) / "libro_tk.pdf"))
                   
        meta = {
            "title": self.title_var.get(),
            "author": self.author_var.get(),
            "subject": self.sig_var.get(),
            "keywords": f"{self.tema_var.get()},{self.etiquetas_var.get()}",
            "creator": APP_NAME
        }
        
        try:
            core.assemble_pdf_from_images(self.saved_images, str(out_pdf),
                                        dpi=300, meta=meta, pdfa=True)
            self.status(f"PDF exportado: {out_pdf}")
        except Exception as ex:
            self.status(f"Error exportando PDF: {ex}")