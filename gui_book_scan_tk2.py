#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui_book_scan_tk.py — GeoDocs Research Suite · Scanner GUI (estable v32.3)
Limpio, sin duplicados de imports/definiciones, con estructura modular y atajos de teclado.
"""
import os
import sys
import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple, List

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import cv2  # Opcional
except Exception:
    cv2 = None

try:
    import psutil  # Opcional para verificación de instancia única
except Exception:
    psutil = None

from PIL import Image, ImageTk, ImageEnhance

APP_NAME = "GeoDocs Scanner"
APP_VERSION = "v32.3 estable"
GLOBAL_DB = "geodocs.db"
REST_CONFIG = "rest_config.json"

def safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def load_json(path: Path, default: dict) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default

def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def init_global_db(base: Path) -> None:
    db_path = base / GLOBAL_DB
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS archivos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        direccion TEXT,
        contacto TEXT,
        email TEXT,
        telefono TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fondos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        archivo_id INTEGER,
        FOREIGN KEY (archivo_id) REFERENCES archivos(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS proyectos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        signatura TEXT,
        tipo_documento TEXT,
        autor TEXT,
        tema TEXT,
        etiquetas TEXT,
        fecha TEXT,
        carpeta_raiz TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def detect_cameras(max_index: int = 8) -> List[int]:
    if cv2 is None:
        return []
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if sys.platform.startswith("win") else cv2.VideoCapture(i)
        ok = cap.isOpened()
        if ok:
            found.append(i)
        cap.release()
    return found

@dataclass
class ProjectInfo:
    titulo: str = "Proyecto_sin_nombre"
    carpeta_raiz: Path = field(default_factory=lambda: Path.cwd() / "proyectos" / "Proyecto_sin_nombre")
    signatura: str = ""
    tipo_documento: str = "libro"
    autor: str = ""
    tema: str = ""
    etiquetas: str = ""
    fecha: str = ""
    pages_dir: Path = field(init=False)
    def __post_init__(self):
        self.pages_dir = self.carpeta_raiz / "paginas"
        safe_mkdir(self.carpeta_raiz)
        safe_mkdir(self.pages_dir)

class RestConfigDialog(tk.Toplevel):
    def __init__(self, master, config_path: Path):
        super().__init__(master)
        self.title("Configuración REST GeoDocs")
        self.resizable(False, False)
        self.config_path = config_path
        cfg = load_json(config_path, {"base_url": "", "token": ""})
        frm = ttk.Frame(self, padding=12); frm.grid(row=0, column=0, sticky="nsew")
        ttk.Label(frm, text="Base URL:").grid(row=0, column=0, sticky="w", pady=4)
        self.var_url = tk.StringVar(value=cfg.get("base_url", ""))
        ttk.Entry(frm, textvariable=self.var_url, width=48).grid(row=0, column=1, sticky="w")
        ttk.Label(frm, text="JWT (token):").grid(row=1, column=0, sticky="w", pady=4)
        self.var_jwt = tk.StringVar(value=cfg.get("token", ""))
        ttk.Entry(frm, textvariable=self.var_jwt, width=48, show="•").grid(row=1, column=1, sticky="w")
        btns = ttk.Frame(frm); btns.grid(row=2, column=0, columnspan=2, pady=8, sticky="e")
        ttk.Button(btns, text="Guardar", command=self.save).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Cancelar", command=self.destroy).grid(row=0, column=1)
        self.grab_set(); self.transient(master)
    def save(self):
        data = {"base_url": self.var_url.get().strip(), "token": self.var_jwt.get().strip()}
        save_json(self.config_path, data)
        messagebox.showinfo("REST", "Configuración guardada.")
        self.destroy()

class StartFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=16)
        self.app = app
        ttk.Label(self, text=f"{APP_NAME} — {APP_VERSION}", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, pady=12)
        ttk.Label(self, text="Seleccione un módulo:").grid(row=1, column=0, pady=(0,12))
        buttons = ttk.Frame(self); buttons.grid(row=2, column=0, pady=12)
        ttk.Button(buttons, text="Escáner", command=lambda: app.show_frame("scan")).grid(row=0, column=0, padx=10)
        ttk.Button(buttons, text="Anotaciones", command=lambda: app.show_frame("annot")).grid(row=0, column=1, padx=10)
        ttk.Label(self, text="Proyecto activo:", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, pady=(20,4), sticky="w")
        self.lbl_proj = ttk.Label(self, text=self.app.project_summary()); self.lbl_proj.grid(row=4, column=0, sticky="w")
        ttk.Button(self, text="Configurar REST…", command=self.app.open_rest_config).grid(row=5, column=0, pady=10, sticky="w")
    def refresh(self):
        self.lbl_proj.config(text=self.app.project_summary())

class ScanFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=8)
        self.app = app
        
        # Main container with left gallery and right scanner
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        
        # LEFT PANEL: Gallery
        gallery_frame = ttk.Frame(self, width=200)
        gallery_frame.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        gallery_frame.rowconfigure(1, weight=1)
        
        ttk.Label(gallery_frame, text="Galería", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, pady=(0,4), sticky="w")
        
        # Canvas for thumbnails with scrollbar
        self.gallery_canvas = tk.Canvas(gallery_frame, width=200, bg="#2b2b2b", highlightthickness=0)
        self.gallery_canvas.grid(row=1, column=0, sticky="nsew")
        
        gallery_scroll = ttk.Scrollbar(gallery_frame, orient="vertical", command=self.gallery_canvas.yview)
        gallery_scroll.grid(row=1, column=1, sticky="ns")
        self.gallery_canvas.config(yscrollcommand=gallery_scroll.set)
        
        # Frame inside canvas to hold thumbnails
        self.gallery_inner = tk.Frame(self.gallery_canvas, bg="#2b2b2b")
        self.gallery_canvas_window = self.gallery_canvas.create_window((0, 0), window=self.gallery_inner, anchor="nw")
        
        self.gallery_inner.bind("<Configure>", lambda e: self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all")))
        self.gallery_canvas.bind("<Double-Button-1>", lambda e: self.preview_image())
        # DELETE removed from canvas - only works via button
        
        # Reorder buttons
        btn_frame = ttk.Frame(gallery_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=4)
        ttk.Button(btn_frame, text="↑", width=3, command=self.move_up).grid(row=0, column=0, padx=2)
        ttk.Button(btn_frame, text="↓", width=3, command=self.move_down).grid(row=0, column=1, padx=2)
        ttk.Button(btn_frame, text="🗑", width=3, command=self.delete_image).grid(row=0, column=2, padx=2)
        
        # RIGHT PANEL: Scanner controls
        scanner_frame = ttk.Frame(self)
        scanner_frame.grid(row=0, column=1, sticky="nsew")
        scanner_frame.rowconfigure(2, weight=1)
        scanner_frame.columnconfigure(0, weight=1)
        
        toolbar = ttk.Frame(scanner_frame); toolbar.grid(row=0, column=0, sticky="ew"); toolbar.columnconfigure(6, weight=1)
        ttk.Label(toolbar, text="Cámara:").grid(row=0, column=0, padx=(0,4))
        self.cmb_cam = ttk.Combobox(toolbar, width=10, state="readonly"); self.cmb_cam.grid(row=0, column=1)
        ttk.Button(toolbar, text="Refrescar", command=self.refresh_cameras).grid(row=0, column=2, padx=6)
        ttk.Button(toolbar, text="Conectar", command=self.open_camera).grid(row=0, column=3, padx=6)
        ttk.Button(toolbar, text="Desconectar", command=self.close_camera).grid(row=0, column=4, padx=6)
        self.var_two_halves = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Dos mitades fijas", variable=self.var_two_halves).grid(row=0, column=5, padx=12)
        ttk.Label(toolbar, text="Anverso/Reverso:").grid(row=0, column=6, padx=(12,4), sticky="e")
        self.var_face = tk.StringVar(value="anverso")
        ttk.Combobox(toolbar, textvariable=self.var_face, values=["anverso","reverso"], width=10, state="readonly").grid(row=0, column=7)
        # Page detection toggle
        self.var_detect_page = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Detectar página", variable=self.var_detect_page).grid(row=0, column=8, padx=(12,0))
        # Detection interval control and status (load saved preference if present)
        cfg = load_json(Path.cwd() / REST_CONFIG, {})
        try:
            saved_interval = int(cfg.get("detect_interval", 5))
        except Exception:
            saved_interval = 5
        self._detect_interval = saved_interval
        self.var_detect_interval = tk.StringVar(value=str(self._detect_interval))
        ttk.Label(toolbar, text="Cada:").grid(row=0, column=9, padx=(8,2))
        self.cmb_detect_interval = ttk.Combobox(toolbar, textvariable=self.var_detect_interval, values=["1","2","3","4","5","10"], width=4, state="readonly")
        self.cmb_detect_interval.grid(row=0, column=10)
        self.cmb_detect_interval.bind('<<ComboboxSelected>>', lambda e: self._on_detect_interval_changed())
        self.lbl_detect_status = ttk.Label(toolbar, text=f"Detección: 1/{self._detect_interval}")
        self.lbl_detect_status.grid(row=0, column=11, padx=(8,0))
        sliders = ttk.Frame(scanner_frame); sliders.grid(row=1, column=0, sticky="ew", pady=(6,4))
        ttk.Label(sliders, text="Brillo").grid(row=0, column=0, padx=(0,4))
        self.s_brightness = tk.DoubleVar(value=1.0)
        ttk.Scale(sliders, variable=self.s_brightness, from_=0.5, to=1.5, orient="horizontal").grid(row=0, column=1, sticky="ew");
        ttk.Label(sliders, text="Contraste").grid(row=0, column=2, padx=(12,4))
        self.s_contrast = tk.DoubleVar(value=1.0)
        ttk.Scale(sliders, variable=self.s_contrast, from_=0.5, to=1.5, orient="horizontal").grid(row=0, column=3, sticky="ew")
        sliders.columnconfigure(1, weight=1); sliders.columnconfigure(3, weight=1)
        self.canvas = tk.Canvas(scanner_frame, width=960, height=600, bg="#111"); self.canvas.grid(row=2, column=0, pady=6, sticky="nsew")
        # persistent image item to avoid flicker
        self._tkimg = None
        self._image_item = self.canvas.create_image(0, 0, anchor="nw", image=None)
        scanner_frame.rowconfigure(2, weight=1); scanner_frame.columnconfigure(0, weight=1)
        bottom = ttk.Frame(scanner_frame); bottom.grid(row=3, column=0, sticky="ew", pady=(6,2))
        ttk.Button(bottom, text="Capturar (SPACE)", command=self.capture).grid(row=0, column=0, padx=6)
        ttk.Button(bottom, text="Guardar imagen", command=self.capture).grid(row=0, column=1, padx=6)
        ttk.Button(bottom, text="Volver", command=lambda: self.app.show_frame("start")).grid(row=0, column=2, padx=6)
        ttk.Button(bottom, text="Recortar página", command=self.auto_crop_page).grid(row=0, column=3, padx=6)
        self.cap = None; self._preview_running = False; self._tkimg = None
        self._last_detected = None
        self._frame_counter = 0
        self.gallery_images = []  # Store image paths for gallery
        self.gallery_thumbnails = []  # Store PhotoImage references
        self.gallery_frames = []  # Store frame widgets
        self.selected_gallery_idx = None
        self.drag_data = {"item": None, "y": 0}
        self.refresh_cameras(); self.bind_all_shortcuts()
        self.refresh_gallery()
    
    def on_show(self):
        """Called when frame is shown - refresh gallery to load images."""
        self.refresh_gallery()
    
    def refresh_cameras(self):
        cams = detect_cameras()
        if not cams:
            self.cmb_cam["values"] = ["(sin cámara)"]; self.cmb_cam.current(0)
        else:
            self.cmb_cam["values"] = cams; self.cmb_cam.current(0)
    def open_camera(self):
        self.close_camera()
        if cv2 is None:
            self.show_toast("⚠ OpenCV no instalado. Vista previa deshabilitada."); return
        sel = self.cmb_cam.get()
        try:
            idx = int(sel)
        except Exception:
            messagebox.showerror("Cámara", "Seleccione un índice de cámara válido."); return
        self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if sys.platform.startswith("win") else cv2.VideoCapture(idx)
        if not self.cap.isOpened():
            messagebox.showerror("Cámara", f"No se pudo abrir la cámara {idx}."); self.cap.release(); self.cap=None; return
        self._preview_running = True; threading.Thread(target=self._loop_preview, daemon=True).start()
    def close_camera(self):
        self._preview_running = False
        if self.cap is not None:
            try: self.cap.release()
            except Exception: pass
            self.cap = None
    def _loop_preview(self):
        while self._preview_running and self.cap is not None:
            ret, frame = self.cap.read()
            if not ret: time.sleep(0.02); continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            if abs(self.s_brightness.get()-1.0) > 1e-3: img = ImageEnhance.Brightness(img).enhance(self.s_brightness.get())
            if abs(self.s_contrast.get()-1.0) > 1e-3: img = ImageEnhance.Contrast(img).enhance(self.s_contrast.get())
            # Run page detection on the raw OpenCV frame when enabled (throttle 1/5 frames)
            detected = None
            try:
                if cv2 is not None and self.var_detect_page.get():
                    self._frame_counter += 1
                    if self._frame_counter % self._detect_interval == 0:
                        detected = self._detect_page_contour_from_frame(frame)
                        self._last_detected = detected
                    else:
                        detected = self._last_detected
                else:
                    # detection disabled -> clear cached detection
                    self._last_detected = None
                    detected = None
            except Exception:
                detected = None
            img = self._fit_to_canvas(img, (self.canvas.winfo_width(), self.canvas.winfo_height()))
            # Pass original frame size and detected points so they can be scaled to the displayed image
            orig_size = (frame.shape[1], frame.shape[0])
            # Schedule UI update on main thread to avoid Tkinter threading issues
            try:
                self.after(0, lambda im=img, os=orig_size, det=detected: self._draw_preview(im, orig_size=os, orig_points=det))
            except Exception:
                # fallback to direct call if scheduling fails
                self._draw_preview(img, orig_size=orig_size, orig_points=detected)
            time.sleep(0.02)
    def _detect_page_contour_from_frame(self, frame_rgb) -> Optional[List[Tuple[int,int]]]:
        """Detect a quad-like page contour in the RGB frame and return 4 points (x,y) or None.
        This is a lightweight heuristic: blur -> Canny -> findContours -> approxPolyDP
        """
        if cv2 is None:
            return None
        try:
            gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edged = cv2.Canny(blur, 50, 150)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return None
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:8]
            h, w = gray.shape
            min_area = (w * h) * 0.03
            for c in contours:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) == 4 and cv2.contourArea(approx) > min_area:
                    pts = [tuple(pt[0]) for pt in approx]
                    return pts
        except Exception:
            return None
        return None
    def _fit_to_canvas(self, img: Image.Image, size: Tuple[int,int]) -> Image.Image:
        cw, ch = size; cw = cw if cw>1 else 960; ch = ch if ch>1 else 600
        img.thumbnail((cw, ch), Image.LANCZOS); return img
    def _draw_preview(self, img: Image.Image, orig_size: Optional[Tuple[int,int]] = None, orig_points: Optional[List[Tuple[int,int]]] = None):
        """Draw current preview image onto canvas and optionally draw a polygon overlay.

        orig_size: (width, height) of the source frame (before scaling).
        orig_points: list of (x,y) points in the source frame coordinates.
        """
        # update persistent image item instead of clearing canvas to prevent flicker
        self._tkimg = ImageTk.PhotoImage(img)
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height(); iw, ih = self._tkimg.width(), self._tkimg.height()
        x = (cw - iw)//2; y = (ch - ih)//2
        # move and update image
        self.canvas.coords(self._image_item, x, y)
        self.canvas.itemconfig(self._image_item, image=self._tkimg)
        # remove old overlays only
        self.canvas.delete("overlay")
        # Draw the fixed vertical separator if requested
        if self.var_two_halves.get():
            self.canvas.create_line(cw//2, 0, cw//2, ch, fill="#00ffff", width=2, dash=(6,4), tag="overlay")
        # Draw detected page polygon if any
        if orig_size and orig_points:
            try:
                ow, oh = orig_size; sx = iw / float(ow); sy = ih / float(oh)
                scaled = []
                for px, py in orig_points:
                    sxp = int(x + px * sx); syp = int(y + py * sy)
                    scaled.append((sxp, syp))
                # draw polygon
                if len(scaled) >= 2:
                    flat = [coord for pt in scaled for coord in pt]
                    self.canvas.create_polygon(*flat, outline="#00ff88", width=3, fill="", dash=(4,2), tag="overlay")
                    # draw small handles
                    for sxp, syp in scaled:
                        r = 4
                        self.canvas.create_oval(sxp-r, syp-r, sxp+r, syp+r, fill="#00ff88", outline="#002200", tag="overlay")
            except Exception:
                pass
    def capture(self):
        if self.cap is None or cv2 is None:
            self.show_toast("⚠ Cámara no disponible"); return
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Captura", "No se pudo capturar imagen."); return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); img = Image.fromarray(frame)
        img = ImageEnhance.Brightness(img).enhance(self.s_brightness.get())
        img = ImageEnhance.Contrast(img).enhance(self.s_contrast.get())
        proj = self.app.project
        if proj is None:
            self.show_toast("⚠ Cree o abra un proyecto para guardar"); return
        
        # Get next page number based on last image in gallery
        next_num = self._get_next_page_number()
        
        if self.var_two_halves.get():
            w, h = img.size
            left = img.crop((0, 0, w//2, h)); right = img.crop((w//2, 0, w, h))
            # Izquierda = reverso, Derecha = anverso
            left_path = proj.pages_dir / f"page_{next_num:04d}.jpg"
            right_path = proj.pages_dir / f"page_{next_num+1:04d}.jpg"
            left.save(left_path, "JPEG", quality=92)
            right.save(right_path, "JPEG", quality=92)
            self.show_toast(f"Guardadas: {left_path.name}, {right_path.name}")
        else:
            out_path = proj.pages_dir / f"page_{next_num:04d}.jpg"
            img.save(out_path, "JPEG", quality=92)
            self.show_toast(f"Guardada: {out_path.name}")
        self.refresh_gallery()
    
    def _get_next_page_number(self):
        """Get the next page number based on existing images."""
        proj = self.app.project
        if proj is None or not proj.pages_dir.exists():
            return 1
        
        # Find all page_NNNN.jpg files
        import re
        max_num = 0
        for img_file in proj.pages_dir.glob("page_*.jpg"):
            match = re.match(r'page_(\d+)\.jpg', img_file.name)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
        
        return max_num + 1
    
    def refresh_gallery(self):
        """Load and display all images from project pages directory with thumbnails."""
        # Clear existing thumbnails
        for frame in self.gallery_frames:
            frame.destroy()
        self.gallery_frames = []
        self.gallery_thumbnails = []
        self.gallery_images = []
        self.selected_gallery_idx = None
        
        proj = self.app.project
        if proj is None or not proj.pages_dir.exists():
            return
        
        # Find all image files - use set to avoid duplicates
        img_set = set()
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
            for img in proj.pages_dir.glob(ext):
                img_set.add(img)
        self.gallery_images = list(img_set)
        
        # Sort by name
        self.gallery_images.sort(key=lambda p: p.name)
        
        # Create thumbnail for each image
        for idx, img_path in enumerate(self.gallery_images):
            try:
                # Load and create thumbnail
                img = Image.open(img_path)
                img.thumbnail((180, 120), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.gallery_thumbnails.append(photo)
                
                # Create frame for this thumbnail
                item_frame = tk.Frame(self.gallery_inner, bg="#3a3a3a", relief="raised", bd=2)
                item_frame.pack(fill="x", padx=5, pady=5)
                self.gallery_frames.append(item_frame)
                
                # Thumbnail image
                img_label = tk.Label(item_frame, image=photo, bg="#3a3a3a")
                img_label.pack(pady=5)
                
                # Filename label
                name_label = tk.Label(item_frame, text=img_path.name, bg="#3a3a3a", fg="white", 
                                     font=("Segoe UI", 8), wraplength=180)
                name_label.pack(pady=(0,5))
                
                # Bind click events
                for widget in [item_frame, img_label, name_label]:
                    widget.bind("<Button-1>", lambda e, i=idx: self.select_gallery_item(i))
                    widget.bind("<Double-Button-1>", lambda e, i=idx: self.preview_image())
                    # Drag and drop bindings
                    widget.bind("<ButtonPress-1>", lambda e, i=idx: self.on_drag_start(e, i))
                    widget.bind("<B1-Motion>", self.on_drag_motion)
                    widget.bind("<ButtonRelease-1>", self.on_drag_release)
                
            except Exception as e:
                print(f"Error loading thumbnail for {img_path.name}: {e}")
        
        self.gallery_canvas.update_idletasks()
        self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all"))
    
    def select_gallery_item(self, idx):
        """Highlight selected gallery item."""
        # Unhighlight previous selection
        if self.selected_gallery_idx is not None and self.selected_gallery_idx < len(self.gallery_frames):
            self.gallery_frames[self.selected_gallery_idx].config(bg="#3a3a3a", relief="raised")
            for child in self.gallery_frames[self.selected_gallery_idx].winfo_children():
                child.config(bg="#3a3a3a")
        
        # Highlight new selection
        self.selected_gallery_idx = idx
        if idx < len(self.gallery_frames):
            self.gallery_frames[idx].config(bg="#4a4a4a", relief="sunken")
            for child in self.gallery_frames[idx].winfo_children():
                child.config(bg="#4a4a4a")
    
    def move_up(self):
        """Move selected image up in the list and rename files to maintain order."""
        if self.selected_gallery_idx is None or self.selected_gallery_idx == 0:
            return
        idx = self.selected_gallery_idx
        # Swap in list
        self.gallery_images[idx], self.gallery_images[idx-1] = self.gallery_images[idx-1], self.gallery_images[idx]
        self._rename_sequence()
        self.refresh_gallery()
        self.select_gallery_item(idx-1)
    
    def move_down(self):
        """Move selected image down in the list and rename files to maintain order."""
        if self.selected_gallery_idx is None or self.selected_gallery_idx >= len(self.gallery_images) - 1:
            return
        idx = self.selected_gallery_idx
        # Swap in list
        self.gallery_images[idx], self.gallery_images[idx+1] = self.gallery_images[idx+1], self.gallery_images[idx]
        self._rename_sequence()
        self.refresh_gallery()
        self.select_gallery_item(idx+1)
    
    def _rename_sequence(self):
        """Rename all files in gallery_images to maintain sequential order."""
        proj = self.app.project
        if proj is None:
            return
        import tempfile
        # Rename to temp names first to avoid conflicts
        temp_paths = []
        for i, img_path in enumerate(self.gallery_images):
            suffix = img_path.suffix
            temp_name = f"_tmp_{i:04d}{suffix}"
            temp_path = proj.pages_dir / temp_name
            try:
                img_path.rename(temp_path)
                temp_paths.append(temp_path)
            except Exception:
                temp_paths.append(img_path)
        # Now rename to final sequence
        for i, temp_path in enumerate(temp_paths):
            suffix = temp_path.suffix
            final_name = f"page_{i+1:04d}{suffix}"
            final_path = proj.pages_dir / final_name
            try:
                temp_path.rename(final_path)
                self.gallery_images[i] = final_path
            except Exception:
                self.gallery_images[i] = temp_path
    
    def delete_image(self):
        """Delete selected image from disk and refresh gallery."""
        if self.selected_gallery_idx is None:
            return
        idx = self.selected_gallery_idx
        img_path = self.gallery_images[idx]
        if messagebox.askyesno("Borrar", f"¿Borrar {img_path.name}?"):
            try:
                img_path.unlink()
                self.show_toast(f"Borrada: {img_path.name}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo borrar: {e}")
            self.refresh_gallery()
    
    def on_drag_start(self, event, idx):
        """Start dragging an item."""
        self.drag_data["item"] = idx
        self.drag_data["y"] = event.y_root
        self.select_gallery_item(idx)
        if idx < len(self.gallery_frames):
            self.gallery_frames[idx].config(relief="groove")
    
    def on_drag_motion(self, event):
        """Handle drag motion."""
        if self.drag_data["item"] is None:
            return
        # Visual feedback during drag
        delta_y = event.y_root - self.drag_data["y"]
        if abs(delta_y) > 10:  # Threshold to start visual drag
            idx = self.drag_data["item"]
            if idx < len(self.gallery_frames):
                self.gallery_frames[idx].config(bg="#5a5a5a")
    
    def on_drag_release(self, event):
        """Handle drag release and reorder if needed."""
        if self.drag_data["item"] is None:
            return
        
        drag_idx = self.drag_data["item"]
        
        # Determine drop position based on y coordinate
        # Find which item the cursor is over
        drop_idx = None
        for i, frame in enumerate(self.gallery_frames):
            try:
                frame_y = frame.winfo_rooty()
                frame_h = frame.winfo_height()
                if frame_y <= event.y_root <= frame_y + frame_h:
                    drop_idx = i
                    break
            except Exception:
                pass
        
        # Reset visual state
        if drag_idx < len(self.gallery_frames):
            self.gallery_frames[drag_idx].config(relief="raised")
        
        # Perform reorder if valid drop
        if drop_idx is not None and drop_idx != drag_idx:
            # Remove from old position and insert at new position
            item = self.gallery_images.pop(drag_idx)
            self.gallery_images.insert(drop_idx, item)
            self._rename_sequence()
            self.refresh_gallery()
            self.select_gallery_item(drop_idx)
        
        # Clear drag data
        self.drag_data = {"item": None, "y": 0}
    
    def preview_image(self):
        """Open a window showing the selected image at full size."""
        if self.selected_gallery_idx is None:
            return
        idx = self.selected_gallery_idx
        img_path = self.gallery_images[idx]
        try:
            preview_win = tk.Toplevel(self)
            preview_win.title(img_path.name)
            preview_win.geometry("800x600")
            img = Image.open(img_path)
            img.thumbnail((780, 580), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(preview_win, image=photo)
            lbl.image = photo  # keep reference
            lbl.pack(expand=True)
        except Exception as e:
            messagebox.showerror("Preview", f"Error al abrir imagen: {e}")
    def bind_all_shortcuts(self):
        self.bind_all("<space>", lambda e: self.capture())
        self.bind_all("<Control-s>", lambda e: self.capture())
        self.bind_all("<F6>", lambda e: self.app.toggle_frames())
        self.bind_all("<Escape>", lambda e: self.app.quit_app())
        self.bind_all("b", lambda e: self.var_two_halves.set(not self.var_two_halves.get()))
        self.bind_all("<Control-Shift-C>", lambda e: self.auto_crop_page())

    def _on_detect_interval_changed(self):
        try:
            val = int(self.var_detect_interval.get())
        except Exception:
            val = 5
        if val < 1:
            val = 1
        self._detect_interval = val
        try:
            self.lbl_detect_status.config(text=f"Detección: 1/{self._detect_interval}")
        except Exception:
            pass
        # persist to REST_CONFIG
        try:
            cfg = load_json(Path.cwd() / REST_CONFIG, {})
            cfg["detect_interval"] = self._detect_interval
            save_json(Path.cwd() / REST_CONFIG, cfg)
        except Exception:
            # don't block UI on save errors
            pass
    def on_show(self): pass
    def on_hide(self): self.close_camera()

    def show_toast(self, message: str, duration: int = 2000):
        """Show a temporary toast notification overlay on the canvas."""
        try:
            # Create a semi-transparent label overlay
            toast = tk.Label(self, text=message, bg="#333333", fg="#ffffff", 
                           font=("Segoe UI", 10), padx=16, pady=8, relief="flat")
            toast.place(relx=0.5, rely=0.05, anchor="n")
            # Auto-destroy after duration
            self.after(duration, toast.destroy)
        except Exception:
            pass

    def _order_points(self, pts: List[Tuple[int,int]]) -> List[Tuple[float,float]]:
        """Return points ordered as (tl, tr, br, bl) in a robust way.

        Algorithm:
        - compute centroid (cx, cy)
        - compute angle = atan2(y - cy, x - cx) for each point
        - sort points by angle (ascending). For a rectangle this yields TL, TR, BR, BL
        - rotate the list so the point with smallest (x+y) (top-left) is first
        """
        if not pts or len(pts) < 4:
            return pts
        import math
        pts_f = [(float(x), float(y)) for (x, y) in pts]
        cx = sum(p[0] for p in pts_f) / len(pts_f)
        cy = sum(p[1] for p in pts_f) / len(pts_f)
        with_angles = []
        for (x, y) in pts_f:
            ang = math.atan2(y - cy, x - cx)
            with_angles.append(((x, y), ang))
        with_angles.sort(key=lambda t: t[1])
        ordered = [p for (p, a) in with_angles]
        # rotate so that the point with minimal x+y (top-left) is first
        sums = [p[0] + p[1] for p in ordered]
        min_idx = sums.index(min(sums))
        ordered = ordered[min_idx:] + ordered[:min_idx]
        return ordered

    def auto_crop_page(self):
        """Capture a frame, detect a page contour and save a perspective-corrected crop to project folder."""
        if cv2 is None:
            self.show_toast("⚠ OpenCV no disponible. Instale opencv-python.")
            return
        if self.cap is None:
            self.show_toast("⚠ Cámara no conectada")
            return
        ret, frame_bgr = self.cap.read()
        if not ret or frame_bgr is None:
            messagebox.showerror("Recortar", "No se pudo leer frame de la cámara.")
            return
        # Use RGB copy for detection helper which expects RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pts = None
        try:
            pts = self._detect_page_contour_from_frame(frame_rgb)
        except Exception:
            pts = None
        if not pts:
            self.show_toast("⚠ No se detectó una página")
            return
        ordered = self._order_points(pts)
        if len(ordered) != 4:
            messagebox.showerror("Recortar", "No se pudo ordenar los puntos de la página detectada.")
            return
        # Compute destination size
        (tl, tr, br, bl) = ordered
        def dist(a, b):
            import math
            return math.hypot(a[0]-b[0], a[1]-b[1])
        widthA = dist(br, bl)
        widthB = dist(tr, tl)
        maxWidth = max(int(widthA), int(widthB))
        heightA = dist(tr, br)
        heightB = dist(tl, bl)
        maxHeight = max(int(heightA), int(heightB))
        if maxWidth <= 0 or maxHeight <= 0:
            messagebox.showerror("Recortar", "Dimensiones inválidas para recorte.")
            return
        try:
            import numpy as np
            src_pts = np.array(ordered, dtype="float32")
            dst_pts = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
            M = cv2.getPerspectiveTransform(src_pts, dst_pts)
            warped = cv2.warpPerspective(frame_bgr, M, (maxWidth, maxHeight))
            warped_rgb = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(warped_rgb)
            # Apply brightness/contrast adjustments
            pil = ImageEnhance.Brightness(pil).enhance(self.s_brightness.get())
            pil = ImageEnhance.Contrast(pil).enhance(self.s_contrast.get())
            proj = self.app.project
            if proj is None:
                self.show_toast("⚠ Cree o abra un proyecto para guardar")
                return
            
            # Get next page number based on last image in gallery
            next_num = self._get_next_page_number()
            out_path = proj.pages_dir / f"page_{next_num:04d}.jpg"
            pil.save(out_path, "JPEG", quality=92)
            self.show_toast(f"Recorte guardado: {out_path.name}")
            self.refresh_gallery()
        except Exception as e:
            messagebox.showerror("Recortar", f"Error realizando recorte: {e}")

class AnnotationFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=16)
        self.app = app
        ttk.Label(self, text="Módulo de Anotaciones (placeholder estable)", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(self, text="Aquí irá el visor, editor WYSIWYG, geolocalización y enlaces a Topónimos/Personas.").grid(row=1, column=0, sticky="w")
        ttk.Button(self, text="Volver", command=lambda: self.app.show_frame("start")).grid(row=2, column=0, pady=8, sticky="w")
    def on_show(self): pass
    def on_hide(self): pass

class GeoDocsScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — {APP_VERSION}"); self.geometry("1100x780"); self.minsize(900, 640)
        self.project: Optional[ProjectInfo] = None
        init_global_db(Path.cwd())
        
        # Check for single instance
        self.lock_file = Path.cwd() / ".geodocs_scanner.lock"
        if not self._acquire_lock():
            messagebox.showerror("Instancia activa", "Ya hay una instancia de GeoDocs Scanner ejecutándose.")
            self.destroy()
            return
        
        self._build_menu()
        container = ttk.Frame(self); container.pack(fill="both", expand=True)
        self.frames = {"start": StartFrame(container, self), "scan": ScanFrame(container, self), "annot": AnnotationFrame(container, self)}
        for f in self.frames.values(): f.grid(row=0, column=0, sticky="nsew")
        
        # Load last project if exists
        self._load_last_project()
        
        self.show_frame("start")
        self.bind_all("<Control-n>", lambda e: self.new_project())
        self.bind_all("<Control-o>", lambda e: self.open_project())
        self.bind_all("<F6>", lambda e: self.toggle_frames())
        
        # Release lock on close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    def _build_menu(self):
        menubar = tk.Menu(self)
        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="Nuevo proyecto… (Ctrl+N)", command=self.new_project)
        m_file.add_command(label="Abrir proyecto… (Ctrl+O)", command=self.open_project)
        m_file.add_separator(); m_file.add_command(label="Config REST…", command=self.open_rest_config)
        m_file.add_separator(); m_file.add_command(label="Salir", command=self.quit_app)
        menubar.add_cascade(label="Archivo", menu=m_file)
        m_view = tk.Menu(menubar, tearoff=0)
        m_view.add_command(label="Escáner", command=lambda: self.show_frame("scan"))
        m_view.add_command(label="Anotaciones", command=lambda: self.show_frame("annot"))
        menubar.add_cascade(label="Ver", menu=m_view)
        self.config(menu=menubar)
    def show_frame(self, name: str):
        for key, frame in self.frames.items():
            if key == name:
                frame.tkraise(); getattr(frame, "on_show", lambda: None)()
            else:
                getattr(frame, "on_hide", lambda: None)()
        if name == "start": self.frames["start"].refresh()
    def toggle_frames(self):
        current = self.frames["scan"].winfo_ismapped(); self.show_frame("annot" if current else "scan")
    def new_project(self):
        import tkinter.simpledialog as simpledialog
        title = simpledialog.askstring("Nuevo proyecto", "Título del documento:")
        if not title: return
        root_dir = filedialog.askdirectory(title="Seleccione carpeta raíz para el proyecto")
        if not root_dir: return
        proj_path = Path(root_dir) / title
        pinfo = ProjectInfo(titulo=title, carpeta_raiz=proj_path); self.project = pinfo
        self._save_project_to_global_db(pinfo)
        self._save_last_project(proj_path)
        self.frames["scan"].show_toast(f"✓ Proyecto creado: {pinfo.titulo}")
        self.show_frame("scan")
    def open_project(self):
        root_dir = filedialog.askdirectory(title="Seleccione carpeta del proyecto")
        if not root_dir: return
        proj_path = Path(root_dir); pages = proj_path / "paginas"
        if not pages.exists():
            messagebox.showerror("Proyecto", "Carpeta inválida: no contiene 'paginas/'."); return
        title = proj_path.name; self.project = ProjectInfo(titulo=title, carpeta_raiz=proj_path)
        self._save_last_project(proj_path)
        self.frames["scan"].show_toast(f"✓ Proyecto abierto: {title}")
        self.show_frame("scan")
    def _save_project_to_global_db(self, proj: ProjectInfo):
        dbp = Path.cwd() / GLOBAL_DB; conn = sqlite3.connect(dbp); cur = conn.cursor()
        cur.execute("""INSERT INTO proyectos (titulo, signatura, tipo_documento, autor, tema, etiquetas, fecha, carpeta_raiz)
                       VALUES (?,?,?,?,?,?,?,?)""", (proj.titulo, proj.signatura, proj.tipo_documento, proj.autor, proj.tema, proj.etiquetas, proj.fecha, str(proj.carpeta_raiz)))
        conn.commit(); conn.close()
    def open_rest_config(self):
        RestConfigDialog(self, Path.cwd() / REST_CONFIG)
    def project_summary(self) -> str:
        if self.project is None: return "— Ningún proyecto activo —"
        return f"{self.project.titulo}  •  {self.project.carpeta_raiz}"
    def quit_app(self):
        try: self.frames["scan"].close_camera()
        except Exception: pass
        self.destroy()
    
    def _acquire_lock(self) -> bool:
        """Try to acquire lock file for single instance."""
        try:
            if self.lock_file.exists():
                # Check if process is still running
                try:
                    pid_str = self.lock_file.read_text().strip()
                    pid = int(pid_str)
                    # Try to check if process exists (platform-specific)
                    if psutil is not None:
                        if psutil.pid_exists(pid):
                            return False
                except Exception:
                    # If we can't verify, remove stale lock
                    self.lock_file.unlink()
            
            # Create lock file with our PID
            self.lock_file.write_text(str(os.getpid()))
            return True
        except Exception:
            # If psutil not available, try simple file lock
            try:
                if self.lock_file.exists():
                    return False
                self.lock_file.write_text(str(os.getpid()))
                return True
            except Exception:
                return True  # If can't create lock, allow anyway
    
    def _release_lock(self):
        """Release lock file."""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception:
            pass
    
    def _on_closing(self):
        """Handle window close event."""
        self._release_lock()
        self.quit_app()
    
    def _save_last_project(self, proj_path: Path):
        """Save last opened project to config."""
        try:
            cfg = load_json(Path.cwd() / REST_CONFIG, {})
            cfg["last_project"] = str(proj_path)
            save_json(Path.cwd() / REST_CONFIG, cfg)
        except Exception:
            pass
    
    def _load_last_project(self):
        """Load last opened project from config."""
        try:
            cfg = load_json(Path.cwd() / REST_CONFIG, {})
            last_proj = cfg.get("last_project")
            if last_proj:
                proj_path = Path(last_proj)
                if proj_path.exists() and (proj_path / "paginas").exists():
                    title = proj_path.name
                    self.project = ProjectInfo(titulo=title, carpeta_raiz=proj_path)
                    # Refresh gallery after loading project
                    self.after(100, lambda: self.frames["scan"].refresh_gallery())
        except Exception:
            pass

def main():
    app = GeoDocsScannerApp(); app.mainloop()

if __name__ == "__main__":
    main()
