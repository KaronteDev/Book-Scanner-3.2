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
CALIBRATION_CONFIG = "camera_calibration.json"

# Paper format presets (in mm)
PAPER_FORMATS = {
    "A3": (297, 420),
    "A4": (210, 297),
    "A5": (148, 210),
    "A6": (105, 148),
    "Custom": None
}

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

def detect_cameras(max_index: int = 8) -> List[tuple]:
    """Detect available cameras and return list of (index, name) tuples."""
    if cv2 is None:
        return []
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if sys.platform.startswith("win") else cv2.VideoCapture(i)
        ok = cap.isOpened()
        if ok:
            # Try to get camera name
            name = f"Cámara {i}"
            try:
                # On Windows with DSHOW, try to get more info
                if sys.platform.startswith("win"):
                    # Try to read a frame to ensure camera is working
                    ret, _ = cap.read()
                    if ret:
                        # Get frame dimensions as additional info
                        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        name = f"Cámara {i} ({w}x{h})"
                else:
                    # Try to get backend name on other platforms
                    backend = cap.getBackendName() if hasattr(cap, 'getBackendName') else ""
                    if backend:
                        name = f"Cámara {i} ({backend})"
            except:
                pass
            found.append((i, name))
        cap.release()
    return found

# ========== IMAGE PROCESSING FUNCTIONS ==========

def detect_finger_regions(img_array):
    """Detect and return mask of potential finger/hand regions using skin tone detection."""
    if cv2 is None:
        return None
    try:
        import numpy as np
        # Convert to YCrCb for better skin detection
        ycrcb = cv2.cvtColor(img_array, cv2.COLOR_RGB2YCrCb)
        
        # Skin color range in YCrCb (more robust than HSV)
        lower_skin = np.array([0, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 173, 127], dtype=np.uint8)
        mask = cv2.inRange(ycrcb, lower_skin, upper_skin)
        
        # Also try HSV for complementary detection
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        lower_hsv = np.array([0, 15, 0], dtype=np.uint8)
        upper_hsv = np.array([17, 170, 255], dtype=np.uint8)
        mask_hsv = cv2.inRange(hsv, lower_hsv, upper_hsv)
        
        # Combine both masks
        mask = cv2.bitwise_or(mask, mask_hsv)
        
        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Find contours and filter by area (keep only significant regions)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Create new mask with only large enough contours (likely fingers/hands)
        filtered_mask = np.zeros_like(mask)
        min_area = img_array.shape[0] * img_array.shape[1] * 0.001  # 0.1% of image
        max_area = img_array.shape[0] * img_array.shape[1] * 0.15   # 15% of image
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                cv2.drawContours(filtered_mask, [contour], -1, 255, -1)
        
        # Dilate to expand the mask slightly to cover edges
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        filtered_mask = cv2.dilate(filtered_mask, kernel_dilate, iterations=1)
        
        return filtered_mask
    except Exception as e:
        return None

def remove_fingers_inpaint(img_array, mask):
    """Remove detected finger regions using inpainting."""
    if cv2 is None or mask is None:
        return img_array
    try:
        # Inpaint the regions
        result = cv2.inpaint(img_array, mask, 3, cv2.INPAINT_TELEA)
        return result
    except:
        return img_array

def auto_adjust_brightness_contrast(img_array):
    """Automatically adjust brightness and contrast using histogram equalization."""
    if cv2 is None:
        return img_array
    try:
        import numpy as np
        # Convert to LAB color space
        lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        # Merge back
        lab = cv2.merge([l, a, b])
        result = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        return result
    except:
        return img_array

def dewarp_page(img_array, contour):
    """Apply dewarping to correct page curvature."""
    if cv2 is None or contour is None:
        return img_array
    try:
        import numpy as np
        # This is a simplified dewarping - for production, consider using more advanced methods
        # Get bounding rect to estimate page boundaries
        x, y, w, h = cv2.boundingRect(contour)
        # Create a simple mesh grid for dewarping
        rows, cols = img_array.shape[:2]
        # For now, just use perspective transform (basic dewarping)
        # Advanced dewarping would require detecting text lines and page curve
        return img_array
    except:
        return img_array

def detect_two_pages(img_array):
    """Detect if image contains one or two pages opened."""
    if cv2 is None:
        return False
    try:
        import numpy as np
        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        # Find vertical edges in the middle section
        h, w = gray.shape
        middle_section = gray[:, w//3:2*w//3]
        edges = cv2.Canny(middle_section, 50, 150)
        # Look for a strong vertical line in the middle
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=h//3, maxLineGap=20)
        if lines is not None and len(lines) > 0:
            # Check if there's a vertical line near center
            for line in lines:
                x1, y1, x2, y2 = line[0]
                # Check if line is mostly vertical
                if abs(x2 - x1) < 20 and abs(y2 - y1) > h//4:
                    return True
        return False
    except:
        return False

def detect_two_pages_line(img_array):
    """Detect a (possibly tilted) center fold line indicating two pages.
    Returns ((x1,y1),(x2,y2)) in source image coordinates if found, else None.
    Two-stage approach: Hough for clear lines; fallback to Scharr X column projection
    constrained to bright page regions.
    """
    if cv2 is None:
        return None
    try:
        import numpy as np, math
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape
        cx = w/2.0
        # ROI around center (30%-70% width) to avoid borders/clamps
        rx0 = int(w * 0.30); rx1 = int(w * 0.70)
        roi = gray[:, rx0:rx1]
        # Equalize to improve low-contrast gutters
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            roi_eq = clahe.apply(roi)
        except Exception:
            roi_eq = roi
        # First attempt: Hough on Canny
        edges = cv2.Canny(cv2.GaussianBlur(roi_eq, (5,5), 0), 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=85, minLineLength=max(30, h//4), maxLineGap=22)
        best = None; best_score = -1.0
        if lines is not None and len(lines) > 0:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                X1, X2, Y1, Y2 = x1 + rx0, x2 + rx0, y1, y2
                dx, dy = (X2 - X1), (Y2 - Y1)
                length = math.hypot(dx, dy)
                if length < h * 0.3:
                    continue
                angle = abs(math.atan2(dy, dx))
                angle_score = math.exp(-((abs(math.pi/2 - angle))/0.35)**2)
                xm = (X1 + X2) / 2.0
                center_prox = math.exp(-((abs(xm - cx))/(w*0.18))**2)
                length_score = min(1.0, length / (h*0.8))
                score = angle_score*0.6 + center_prox*0.25 + length_score*0.15
                if score > best_score:
                    best_score = score; best = ((int(X1), int(Y1)), (int(X2), int(Y2)))
        # Fallback if Hough weak or none: Scharr X column projection inside bright mask
        if best is None or best_score < 0.6:
            # Bright mask to suppress table/background
            _, mask = cv2.threshold(roi_eq, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3,3)))
            mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (9,3)), iterations=1)
            # Scharr X emphasizes vertical transitions
            scharr = cv2.Scharr(roi_eq, cv2.CV_32F, 1, 0)
            scharr = cv2.convertScaleAbs(scharr)
            scharr = cv2.bitwise_and(scharr, scharr, mask=mask)
            # Column projection with Gaussian center weighting
            col_sum = scharr.sum(axis=0).astype(np.float32)
            if col_sum.size > 0:
                cols = np.arange(col_sum.size, dtype=np.float32)
                # Map cols to full-image x to weight proximity to center
                full_x = cols + rx0
                center_weight = np.exp(-((np.abs(full_x - cx))/(w*0.18))**2)
                score_vec = col_sum * center_weight
                j = int(np.argmax(score_vec))
                peak = score_vec[j]; med = float(np.median(score_vec)); std = float(np.std(score_vec) + 1e-6)
                if peak > med + 1.5*std and (rx0 + j) > int(w*0.25) and (rx0 + j) < int(w*0.75):
                    x_split = int(rx0 + j)
                    best = ((x_split, 0), (x_split, h))
        return best
    except Exception:
        return None

def get_calibration_for_camera(camera_idx, project_name=None):
    """Load calibration settings for specific camera and project."""
    try:
        cfg_path = Path.cwd() / CALIBRATION_CONFIG
        if cfg_path.exists():
            data = load_json(cfg_path, {})
            key = f"cam_{camera_idx}"
            if project_name:
                key = f"{key}_{project_name}"
            return data.get(key, {})
        return {}
    except:
        return {}

def save_calibration_for_camera(camera_idx, settings, project_name=None):
    """Save calibration settings for specific camera and project."""
    try:
        cfg_path = Path.cwd() / CALIBRATION_CONFIG
        data = load_json(cfg_path, {})
        key = f"cam_{camera_idx}"
        if project_name:
            key = f"{key}_{project_name}"
        data[key] = settings
        save_json(cfg_path, data)
    except:
        pass

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

class CalibrationDialog(tk.Toplevel):
    def __init__(self, master, scan_frame):
        super().__init__(master)
        self.title("Calibración de cámara")
        self.geometry("1200x700")
        self.scan_frame = scan_frame
        
        # Main container
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Left panel: Camera preview
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ttk.Label(left_frame, text="Vista previa - Ajuste el área de captura", 
                 font=("Segoe UI", 10, "bold")).pack(pady=(0,5))
        
        self.canvas = tk.Canvas(left_frame, width=800, height=600, bg="#111")
        self.canvas.pack()
        
        # Instructions
        inst_text = "Arrastra las esquinas del rectángulo para ajustar el área de captura según el formato seleccionado"
        ttk.Label(left_frame, text=inst_text, wraplength=780).pack(pady=5)
        
        # Right panel: Controls
        right_frame = ttk.Frame(main_frame, width=350)
        right_frame.pack(side="right", fill="y")
        right_frame.pack_propagate(False)
        
        ttk.Label(right_frame, text="Configuración de captura", 
                 font=("Segoe UI", 10, "bold")).pack(pady=(0,12), anchor="w")
        
        # Paper format with DPI info
        format_frame = ttk.LabelFrame(right_frame, text="Formato de papel", padding=10)
        format_frame.pack(fill="x", pady=(0,10))
        
        self.var_format = scan_frame.var_paper_format
        for fmt, size in PAPER_FORMATS.items():
            if size:
                text = f"{fmt} ({size[0]}x{size[1]} mm)"
            else:
                text = fmt
            ttk.Radiobutton(format_frame, text=text, value=fmt, 
                           variable=self.var_format,
                           command=self.on_format_changed).pack(anchor="w", pady=2)
        
        # DPI settings
        dpi_frame = ttk.LabelFrame(right_frame, text="Resolución", padding=10)
        dpi_frame.pack(fill="x", pady=(0,10))
        
        ttk.Label(dpi_frame, text="DPI objetivo:").pack(anchor="w")
        self.var_target_dpi = tk.StringVar(value="300")
        dpi_combo = ttk.Combobox(dpi_frame, textvariable=self.var_target_dpi, 
                                 values=["150", "200", "300", "400", "600"], 
                                 width=10, state="readonly")
        dpi_combo.pack(anchor="w", pady=(2,5))
        dpi_combo.bind('<<ComboboxSelected>>', lambda e: self.update_dpi_info())
        
        self.lbl_dpi_info = ttk.Label(dpi_frame, text="", foreground="#0066cc")
        self.lbl_dpi_info.pack(anchor="w")
        
        # Processing options
        proc_frame = ttk.LabelFrame(right_frame, text="Procesamiento automático", padding=10)
        proc_frame.pack(fill="x", pady=(0,10))
        
        ttk.Checkbutton(proc_frame, text="Eliminar dedos", 
                       variable=scan_frame.var_auto_fingers).pack(anchor="w", pady=2)
        
        ttk.Checkbutton(proc_frame, text="Auto brillo/contraste", 
                       variable=scan_frame.var_auto_brightness).pack(anchor="w", pady=2)
        
        ttk.Checkbutton(proc_frame, text="Auto recorte", 
                       variable=scan_frame.var_auto_crop).pack(anchor="w", pady=2)
        
        ttk.Checkbutton(proc_frame, text="Corregir curvatura", 
                       variable=scan_frame.var_dewarp).pack(anchor="w", pady=2)
        
        # Buttons
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(side="bottom", fill="x", pady=(10,0))
        
        ttk.Button(btn_frame, text="Guardar y cerrar", 
                  command=self.save_and_close).pack(side="top", fill="x", pady=2)
        ttk.Button(btn_frame, text="Restablecer", 
                  command=self.reset_area).pack(side="top", fill="x", pady=2)
        ttk.Button(btn_frame, text="Cancelar", 
                  command=self.destroy).pack(side="top", fill="x", pady=2)
        
        # Calibration area (corners in percentage of image)
        self.calib_area = {
            'tl': [0.1, 0.1],  # top-left
            'tr': [0.9, 0.1],  # top-right
            'br': [0.9, 0.9],  # bottom-right
            'bl': [0.1, 0.9]   # bottom-left
        }
        
        # Load saved calibration if exists
        if scan_frame.current_camera_idx is not None:
            proj_name = scan_frame.app.project.titulo if scan_frame.app.project else None
            saved = get_calibration_for_camera(scan_frame.current_camera_idx, proj_name)
            if 'calib_area' in saved:
                self.calib_area = saved['calib_area']
            if 'target_dpi' in saved:
                self.var_target_dpi.set(str(saved['target_dpi']))
        
        # Preview state
        self._preview_running = True
        self._preview_img = None
        self._dragging = None
        self._canvas_items = []
        
        # Bind mouse events for dragging corners
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Start preview thread
        threading.Thread(target=self._preview_loop, daemon=True).start()
        
        self.grab_set()
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Initial format update
        self.on_format_changed()
    
    def _preview_loop(self):
        """Capture and display camera preview with calibration overlay."""
        while self._preview_running:
            if self.scan_frame.cap is None or not self.scan_frame.cap.isOpened():
                time.sleep(0.1)
                continue
            
            ret, frame = self.scan_frame.cap.read()
            if not ret:
                time.sleep(0.02)
                continue
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._preview_img = Image.fromarray(frame_rgb)
            
            # Schedule UI update on main thread
            self.after(0, self._draw_preview)
            time.sleep(0.03)  # ~30 FPS
    
    def _draw_preview(self):
        """Draw preview with calibration rectangle overlay."""
        if self._preview_img is None:
            return
        
        # Resize to fit canvas
        img = self._preview_img.copy()
        img.thumbnail((800, 600), Image.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(img)
        
        # Update canvas
        self.canvas.delete("all")
        cw, ch = 800, 600
        iw, ih = photo.width(), photo.height()
        x = (cw - iw) // 2
        y = (ch - ih) // 2
        
        self.canvas.create_image(x, y, anchor="nw", image=photo)
        self.canvas._photo = photo  # Keep reference
        
        # Draw calibration area
        corners_px = {
            'tl': (x + int(self.calib_area['tl'][0] * iw), y + int(self.calib_area['tl'][1] * ih)),
            'tr': (x + int(self.calib_area['tr'][0] * iw), y + int(self.calib_area['tr'][1] * ih)),
            'br': (x + int(self.calib_area['br'][0] * iw), y + int(self.calib_area['br'][1] * ih)),
            'bl': (x + int(self.calib_area['bl'][0] * iw), y + int(self.calib_area['bl'][1] * ih))
        }
        
        # Draw rectangle
        points = [corners_px['tl'], corners_px['tr'], corners_px['br'], corners_px['bl']]
        flat = [coord for pt in points for coord in pt]
        self.canvas.create_polygon(*flat, outline="#00ff00", width=3, fill="", dash=(10, 5))
        
        # Draw corner handles
        for corner_name, (cx, cy) in corners_px.items():
            r = 8
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, 
                                   fill="#00ff00", outline="#ffffff", width=2,
                                   tags=corner_name)
    
    def on_mouse_down(self, event):
        """Start dragging a corner if clicked."""
        # Check if clicked near a corner
        for corner_name in ['tl', 'tr', 'br', 'bl']:
            items = self.canvas.find_withtag(corner_name)
            if items:
                coords = self.canvas.coords(items[0])
                cx, cy = (coords[0] + coords[2]) / 2, (coords[1] + coords[3]) / 2
                dist = ((event.x - cx)**2 + (event.y - cy)**2)**0.5
                if dist < 15:
                    self._dragging = corner_name
                    break
    
    def on_mouse_drag(self, event):
        """Update corner position while dragging."""
        if self._dragging and self._preview_img:
            img = self._preview_img.copy()
            img.thumbnail((800, 600), Image.LANCZOS)
            iw, ih = img.width, img.height
            cw, ch = 800, 600
            x_offset = (cw - iw) // 2
            y_offset = (ch - ih) // 2
            
            # Convert canvas coordinates to relative position
            rel_x = max(0, min(1, (event.x - x_offset) / iw))
            rel_y = max(0, min(1, (event.y - y_offset) / ih))
            
            self.calib_area[self._dragging] = [rel_x, rel_y]
            self.update_dpi_info()
    
    def on_mouse_up(self, event):
        """Stop dragging."""
        self._dragging = None
    
    def on_format_changed(self):
        """Adjust calibration area based on selected format."""
        fmt = self.var_format.get()
        if fmt in PAPER_FORMATS and PAPER_FORMATS[fmt] is not None:
            w_mm, h_mm = PAPER_FORMATS[fmt]
            # Calculate aspect ratio
            aspect = w_mm / h_mm
            
            # Adjust rectangle to match aspect ratio (centered)
            center_x, center_y = 0.5, 0.5
            width = 0.7
            height = width / aspect
            
            if height > 0.8:
                height = 0.8
                width = height * aspect
            
            self.calib_area = {
                'tl': [center_x - width/2, center_y - height/2],
                'tr': [center_x + width/2, center_y - height/2],
                'br': [center_x + width/2, center_y + height/2],
                'bl': [center_x - width/2, center_y + height/2]
            }
        self.update_dpi_info()
    
    def update_dpi_info(self):
        """Calculate and display actual DPI based on calibration area."""
        try:
            if self._preview_img is None:
                return
            
            img_w, img_h = self._preview_img.size
            
            # Calculate pixel dimensions of calibration area
            tl = self.calib_area['tl']
            br = self.calib_area['br']
            px_w = abs(br[0] - tl[0]) * img_w
            px_h = abs(br[1] - tl[1]) * img_h
            
            # Get paper dimensions
            fmt = self.var_format.get()
            if fmt in PAPER_FORMATS and PAPER_FORMATS[fmt]:
                mm_w, mm_h = PAPER_FORMATS[fmt]
                # Convert mm to inches
                inch_w = mm_w / 25.4
                inch_h = mm_h / 25.4
                
                # Calculate actual DPI
                dpi_w = px_w / inch_w
                dpi_h = px_h / inch_h
                dpi_avg = (dpi_w + dpi_h) / 2
                
                self.lbl_dpi_info.config(text=f"DPI actual: {dpi_avg:.0f}\n({px_w:.0f}x{px_h:.0f} px)")
            else:
                self.lbl_dpi_info.config(text=f"Área: {px_w:.0f}x{px_h:.0f} px")
        except:
            pass
    
    def reset_area(self):
        """Reset calibration area to default."""
        self.calib_area = {
            'tl': [0.1, 0.1],
            'tr': [0.9, 0.1],
            'br': [0.9, 0.9],
            'bl': [0.1, 0.9]
        }
        self.on_format_changed()
    
    def save_and_close(self):
        """Save calibration and close dialog."""
        settings = {
            'paper_format': self.var_format.get(),
            'auto_fingers': self.scan_frame.var_auto_fingers.get(),
            'auto_brightness': self.scan_frame.var_auto_brightness.get(),
            'auto_crop': self.scan_frame.var_auto_crop.get(),
            'dewarp': self.scan_frame.var_dewarp.get(),
            'target_dpi': int(self.var_target_dpi.get()),
            'calib_area': self.calib_area
        }
        
        if self.scan_frame.current_camera_idx is not None:
            proj_name = self.scan_frame.app.project.titulo if self.scan_frame.app.project else None
            save_calibration_for_camera(self.scan_frame.current_camera_idx, settings, proj_name)
            
            # Update calibration status label in main window
            fmt = settings['paper_format']
            dpi = settings['target_dpi']
            self.scan_frame.lbl_calib_status.config(text=f"Calibración: {fmt} @ {dpi} DPI")
            
            self.scan_frame.show_toast(f"✓ Calibración guardada")
        
        self.on_closing()
    
    def on_closing(self):
        """Stop preview and close."""
        self._preview_running = False
        self.destroy()

class StartFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=16)
        self.app = app
        ttk.Label(self, text=f"{APP_NAME} — {APP_VERSION}", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, pady=12)
        ttk.Label(self, text="Seleccione un módulo:").grid(row=1, column=0, pady=(0,12))
        buttons = ttk.Frame(self); buttons.grid(row=2, column=0, pady=12)
        ttk.Button(buttons, text="📷 Módulo Escáner", command=app.open_scanner_window, width=22).grid(row=0, column=0, padx=10)
        ttk.Button(buttons, text="📝 Módulo Anotador", command=app.open_annotation_window, width=22).grid(row=0, column=1, padx=10)
        ttk.Label(self, text="Proyecto activo:", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, pady=(20,4), sticky="w")
        self.lbl_proj = ttk.Label(self, text=self.app.project_summary()); self.lbl_proj.grid(row=4, column=0, sticky="w")
        ttk.Button(self, text="Configurar REST…", command=self.app.open_rest_config).grid(row=5, column=0, pady=10, sticky="w")
    def refresh(self):
        self.lbl_proj.config(text=self.app.project_summary())

class ScannerWindow(tk.Toplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.title(f"{APP_NAME} — Módulo Escáner")
        self.geometry("1400x800")
        self.app = app
        
        # Main frame
        main_frame = ttk.Frame(self, padding=8)
        main_frame.pack(fill="both", expand=True)
        
        # Main container with left gallery and right scanner
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # LEFT PANEL: Gallery
        gallery_frame = ttk.Frame(main_frame, width=200)
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
        scanner_frame = ttk.Frame(main_frame)
        scanner_frame.grid(row=0, column=1, sticky="nsew")
        scanner_frame.rowconfigure(2, weight=1)
        scanner_frame.columnconfigure(0, weight=1)
        
        toolbar = ttk.Frame(scanner_frame); toolbar.grid(row=0, column=0, sticky="ew"); toolbar.columnconfigure(6, weight=1)
        ttk.Label(toolbar, text="Cámara:").grid(row=0, column=0, padx=(0,4))
        self.cmb_cam = ttk.Combobox(toolbar, width=25, state="readonly"); self.cmb_cam.grid(row=0, column=1)
        ttk.Button(toolbar, text="Refrescar", command=self.refresh_cameras).grid(row=0, column=2, padx=6)
        ttk.Button(toolbar, text="Conectar", command=self.open_camera).grid(row=0, column=3, padx=6)
        ttk.Button(toolbar, text="Desconectar", command=self.close_camera).grid(row=0, column=4, padx=6)
        self.var_two_halves = tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text="Dos mitades fijas", variable=self.var_two_halves).grid(row=0, column=5, padx=12)
        ttk.Label(toolbar, text="Lado:").grid(row=0, column=6, padx=(12,4), sticky="e")
        self.var_face = tk.StringVar(value="ambas")
        ttk.Combobox(toolbar, textvariable=self.var_face, values=["ambas","anverso","reverso"], width=10, state="readonly").grid(row=0, column=7)
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
        
        # Second toolbar row: Calibration button only
        toolbar2 = ttk.Frame(scanner_frame)
        toolbar2.grid(row=1, column=0, sticky="ew", pady=(4,0))
        toolbar2.columnconfigure(1, weight=1)
        
        ttk.Button(toolbar2, text="⚙ Calibrar cámara y procesamiento", 
                  command=self.open_calibration_dialog, width=35).grid(row=0, column=0, padx=6)
        
        # Status label for calibration
        self.lbl_calib_status = ttk.Label(toolbar2, text="", foreground="#666666")
        self.lbl_calib_status.grid(row=0, column=1, sticky="w", padx=12)
        
        # Initialize processing variables (will be set from calibration)
        self.var_auto_fingers = tk.BooleanVar(value=False)
        self.var_auto_brightness = tk.BooleanVar(value=False)
        self.var_auto_crop = tk.BooleanVar(value=False)
        self.var_dewarp = tk.BooleanVar(value=False)
        self.var_paper_format = tk.StringVar(value="A4")
        
        sliders = ttk.Frame(scanner_frame); sliders.grid(row=2, column=0, sticky="ew", pady=(6,4))
        ttk.Label(sliders, text="Brillo").grid(row=0, column=0, padx=(0,4))
        self.s_brightness = tk.DoubleVar(value=1.0)
        ttk.Scale(sliders, variable=self.s_brightness, from_=0.5, to=1.5, orient="horizontal").grid(row=0, column=1, sticky="ew");
        ttk.Label(sliders, text="Contraste").grid(row=0, column=2, padx=(12,4))
        self.s_contrast = tk.DoubleVar(value=1.0)
        ttk.Scale(sliders, variable=self.s_contrast, from_=0.5, to=1.5, orient="horizontal").grid(row=0, column=3, sticky="ew")
        sliders.columnconfigure(1, weight=1); sliders.columnconfigure(3, weight=1)
        self.canvas = tk.Canvas(scanner_frame, width=960, height=600, bg="#111"); self.canvas.grid(row=3, column=0, pady=6, sticky="nsew")
        # persistent image item to avoid flicker
        self._tkimg = None
        self._image_item = self.canvas.create_image(0, 0, anchor="nw", image=None)
        scanner_frame.rowconfigure(3, weight=1); scanner_frame.columnconfigure(0, weight=1)
        bottom = ttk.Frame(scanner_frame); bottom.grid(row=4, column=0, sticky="ew", pady=(6,2))
        ttk.Button(bottom, text="Capturar (SPACE)", command=self.capture).grid(row=0, column=0, padx=6)
        ttk.Button(bottom, text="Guardar imagen", command=self.capture).grid(row=0, column=1, padx=6)
        ttk.Button(bottom, text="Cerrar", command=self.on_window_close).grid(row=0, column=2, padx=6)
        ttk.Button(bottom, text="Recortar página", command=self.auto_crop_page).grid(row=0, column=3, padx=6)
        self.cap = None; self._preview_running = False; self._tkimg = None
        self._last_detected = None
        self._last_middle_line = None
        self._frame_counter = 0
        self.gallery_images = []  # Store image paths for gallery
        self.gallery_thumbnails = []  # Store PhotoImage references
        self.gallery_frames = []  # Store frame widgets
        self.selected_gallery_idx = None
        self.drag_data = {"item": None, "y": 0}
        self.camera_map = {}  # Map camera names to indices
        self.current_camera_idx = None  # Track current camera for calibration
        self.calibration_settings = {}  # Store current calibration
        self.refresh_cameras(); self.bind_all_shortcuts()
        self.refresh_gallery()
        # Show "CAMERA OFF" initially
        self._show_camera_off_screen()
        # Auto-connect to first camera if available
        self.after(500, self._auto_connect_camera)
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)
    
    def on_window_close(self):
        """Clean up camera before closing window."""
        self.close_camera()
        self.destroy()
    
    def _auto_connect_camera(self):
        """Automatically connect to the first available camera."""
        if cv2 is not None and self.cap is None and len(self.camera_map) > 0:
            self.open_camera()
    
    def refresh_cameras(self):
        cams = detect_cameras()
        self.camera_map = {}
        if not cams:
            self.cmb_cam["values"] = ["(sin cámara)"]
            self.cmb_cam.current(0)
        else:
            # cams is list of (index, name) tuples
            names = [name for idx, name in cams]
            self.camera_map = {name: idx for idx, name in cams}
            self.cmb_cam["values"] = names
            self.cmb_cam.current(0)
    
    def open_camera(self):
        self.close_camera()
        if cv2 is None:
            self.show_toast("⚠ OpenCV no instalado. Vista previa deshabilitada."); return
        sel = self.cmb_cam.get()
        # Get camera index from name
        if sel in self.camera_map:
            idx = self.camera_map[sel]
        else:
            # Fallback: try to parse as integer
            try:
                idx = int(sel)
            except Exception:
                messagebox.showerror("Cámara", "Seleccione una cámara válida.", parent=self); return
        self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if sys.platform.startswith("win") else cv2.VideoCapture(idx)
        if not self.cap.isOpened():
            messagebox.showerror("Cámara", f"No se pudo abrir la cámara {idx}.", parent=self); self.cap.release(); self.cap=None; return
        
        # Store current camera index and load calibration
        self.current_camera_idx = idx
        proj_name = self.app.project.titulo if self.app.project else None
        self.calibration_settings = get_calibration_for_camera(idx, proj_name)
        
        # Apply saved settings if available
        if self.calibration_settings:
            if 'paper_format' in self.calibration_settings:
                self.var_paper_format.set(self.calibration_settings['paper_format'])
            if 'auto_fingers' in self.calibration_settings:
                self.var_auto_fingers.set(self.calibration_settings['auto_fingers'])
            if 'auto_brightness' in self.calibration_settings:
                self.var_auto_brightness.set(self.calibration_settings['auto_brightness'])
            if 'auto_crop' in self.calibration_settings:
                self.var_auto_crop.set(self.calibration_settings['auto_crop'])
            if 'dewarp' in self.calibration_settings:
                self.var_dewarp.set(self.calibration_settings['dewarp'])
            
            # Update calibration status label
            fmt = self.calibration_settings.get('paper_format', 'N/A')
            dpi = self.calibration_settings.get('target_dpi', 'N/A')
            self.lbl_calib_status.config(text=f"Calibración: {fmt} @ {dpi} DPI")
        else:
            self.lbl_calib_status.config(text="Sin calibración")
        
        self._preview_running = True; threading.Thread(target=self._loop_preview, daemon=True).start()
    
    def close_camera(self):
        self._preview_running = False
        # Give the thread time to stop
        time.sleep(0.1)
        if self.cap is not None:
            try: self.cap.release()
            except Exception: pass
            self.cap = None
        # Clear preview and show "CAMERA OFF" message after ensuring thread has stopped
        self.after(150, self._show_camera_off_screen)
    
    def _show_camera_off_screen(self):
        """Display a black screen with 'CAMERA OFF' text."""
        cw = self.canvas.winfo_width() or 960
        ch = self.canvas.winfo_height() or 600
        # Create a black image
        black_img = Image.new("RGB", (cw, ch), color="#111111")
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(black_img)
        # Draw text
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()
        text = "CAMERA OFF"
        # Get text bbox for centering
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (cw - text_w) // 2
        y = (ch - text_h) // 2
        draw.text((x, y), text, fill="#666666", font=font)
        # Update canvas
        self._tkimg = ImageTk.PhotoImage(black_img)
        self.canvas.itemconfig(self._image_item, image=self._tkimg)
        self.canvas.delete("overlay")
    
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
            midline = None
            try:
                if cv2 is not None and self.var_detect_page.get():
                    self._frame_counter += 1
                    if self._frame_counter % self._detect_interval == 0:
                        detected = self._detect_page_contour_from_frame(frame)
                        self._last_detected = detected
                        # also compute middle line at the same cadence
                        midline = detect_two_pages_line(frame)
                        self._last_middle_line = midline
                    else:
                        detected = self._last_detected
                        midline = getattr(self, "_last_middle_line", None)
                else:
                    # detection disabled -> clear cached detection
                    self._last_detected = None
                    self._last_middle_line = None
                    detected = None
                    midline = None
            except Exception:
                detected = None; midline = None
            # Safely query canvas size; it may be destroyed during shutdown
            try:
                cw = self.canvas.winfo_width(); ch = self.canvas.winfo_height()
            except Exception:
                break
            img = self._fit_to_canvas(img, (cw, ch))
            # Pass original frame size and detected points so they can be scaled to the displayed image
            orig_size = (frame.shape[1], frame.shape[0])
            # Schedule UI update on main thread to avoid Tkinter threading issues
            try:
                self.after(0, lambda im=img, os=orig_size, det=detected, ml=midline: self._draw_preview(im, orig_size=os, orig_points=det, midline=ml))
            except Exception:
                # fallback to direct call if scheduling fails
                self._draw_preview(img, orig_size=orig_size, orig_points=detected, midline=midline)
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
    def _draw_preview(self, img: Image.Image, orig_size: Optional[Tuple[int,int]] = None, orig_points: Optional[List[Tuple[int,int]]] = None, midline: Optional[Tuple[Tuple[int,int],Tuple[int,int]]] = None):
        """Draw current preview image onto canvas and optionally draw a polygon overlay.

        orig_size: (width, height) of the source frame (before scaling).
        orig_points: list of (x,y) points in the source frame coordinates.
        """
        # Don't update if camera is not running
        if not self._preview_running or self.cap is None:
            return
        
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
        # Draw detected middle line and shaded regions if any
        if orig_size and midline:
            try:
                (x1,y1),(x2,y2) = midline
                ow, oh = orig_size; sx = iw / float(ow); sy = ih / float(oh)
                X1 = x + int(x1 * sx); Y1 = y + int(y1 * sy)
                X2 = x + int(x2 * sx); Y2 = y + int(y2 * sy)
                # Draw line
                self.canvas.create_line(X1, Y1, X2, Y2, fill="#ffcc00", width=3, dash=(8,6), tag="overlay")
                # Compute intersections with top/bottom of displayed image
                top_y = y; bot_y = y + ih
                def clamp(v, lo, hi):
                    return lo if v < lo else hi if v > hi else v
                if abs(Y2 - Y1) > 1:
                    xtop = X1 + (X2 - X1) * ( (top_y - Y1) / float(Y2 - Y1) )
                    xbot = X1 + (X2 - X1) * ( (bot_y - Y1) / float(Y2 - Y1) )
                else:
                    # nearly horizontal; fall back to mid x
                    xtop = x + iw//2; xbot = x + iw//2
                xtop = int(clamp(xtop, x, x+iw)); xbot = int(clamp(xbot, x, x+iw))
                # Left shaded polygon
                left_poly = [x, top_y, xtop, top_y, xbot, bot_y, x, bot_y]
                # Right shaded polygon
                right_poly = [xtop, top_y, x+iw, top_y, x+iw, bot_y, xbot, bot_y]
                # Draw with stipple to simulate transparency
                self.canvas.create_polygon(*left_poly, fill="#000000", outline="", stipple="gray25", tag="overlay")
                self.canvas.create_polygon(*right_poly, fill="#000000", outline="", stipple="gray25", tag="overlay")
            except Exception:
                pass
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
            messagebox.showerror("Captura", "No se pudo capturar imagen.", parent=self); return
        
        # Convert to RGB for processing
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Apply calibrated area crop if available
        if self.calibration_settings and 'calib_area' in self.calibration_settings:
            try:
                import numpy as np
                h, w = frame_rgb.shape[:2]
                area = self.calibration_settings['calib_area']
                
                # Get coordinates
                x1 = int(area['tl'][0] * w)
                y1 = int(area['tl'][1] * h)
                x2 = int(area['br'][0] * w)
                y2 = int(area['br'][1] * h)
                
                # Crop to calibrated area
                frame_rgb = frame_rgb[y1:y2, x1:x2]
            except Exception:
                pass  # If crop fails, use full frame
        
        # Apply auto-processing if enabled (on the current working RGB frame)
        processed_frame = frame_rgb.copy()
        
        # 1. Remove fingers if enabled
        if self.var_auto_fingers.get():
            finger_mask = detect_finger_regions(processed_frame)
            if finger_mask is not None:
                processed_frame = remove_fingers_inpaint(processed_frame, finger_mask)
        
        # 2. Auto brightness/contrast if enabled
        if self.var_auto_brightness.get():
            processed_frame = auto_adjust_brightness_contrast(processed_frame)
        
        # 3. Auto crop if enabled: re-detect page on the CURRENT frame (avoid using preview cache)
        if self.var_auto_crop.get():
            try:
                pts = self._detect_page_contour_from_frame(processed_frame)
                if pts and len(pts) >= 4:
                    ordered = self._order_points(pts)
                    if len(ordered) == 4:
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
                        if maxWidth > 0 and maxHeight > 0:
                            import numpy as np
                            src_pts = np.array(ordered, dtype="float32")
                            dst_pts = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
                            M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                            processed_frame = cv2.warpPerspective(processed_frame, M, (maxWidth, maxHeight))
            except Exception:
                # If auto-crop fails, continue with uncropped processed_frame
                pass
        
        # 4. Convert to PIL and apply manual brightness/contrast adjustments AFTER crop
        img = Image.fromarray(processed_frame)
        img = ImageEnhance.Brightness(img).enhance(self.s_brightness.get())
        img = ImageEnhance.Contrast(img).enhance(self.s_contrast.get())
        
        proj = self.app.project
        if proj is None:
            self.show_toast("⚠ Cree o abra un proyecto para guardar"); return
        
        # Get next page number based on last image in gallery
        next_num = self._get_next_page_number()
        
        # Decide if we should split into two pages and compute the split line on the FINAL image
        midline_captured = None
        try:
            import numpy as np
            arr_final = np.array(img.convert("RGB"))
            midline_captured = detect_two_pages_line(arr_final)
            if midline_captured:
                # update cache for overlay continuity
                self._last_middle_line = midline_captured
        except Exception:
            midline_captured = None

        should_split = self.var_two_halves.get() or (midline_captured is not None)

        if should_split:
            w, h = img.size
            # use detected split x if available, else center
            x_split = w//2
            try:
                if midline_captured:
                    (x1,y1),(x2,y2) = midline_captured
                    x_split = max(1, min(w-1, int((x1 + x2)//2)))
            except Exception:
                x_split = w//2
            # Split into halves
            left = img.crop((0, 0, x_split, h)); right = img.crop((x_split, 0, w, h))
            
            # If auto-crop is enabled, try to detect and warp each half individually
            if self.var_auto_crop.get():
                try:
                    import numpy as np
                    # Left half
                    left_arr = np.array(left.convert("RGB"))
                    pts_left = self._detect_page_contour_from_frame(left_arr)
                    if pts_left and len(pts_left) >= 4:
                        ordered = self._order_points(pts_left)
                        if len(ordered) == 4:
                            def dist(a, b):
                                import math
                                return math.hypot(a[0]-b[0], a[1]-b[1])
                            widthA = dist(ordered[2], ordered[3])
                            widthB = dist(ordered[1], ordered[0])
                            maxWidth = max(int(widthA), int(widthB))
                            heightA = dist(ordered[1], ordered[2])
                            heightB = dist(ordered[0], ordered[3])
                            maxHeight = max(int(heightA), int(heightB))
                            if maxWidth > 0 and maxHeight > 0:
                                src = np.array(ordered, dtype="float32")
                                dst = np.array([[0,0],[maxWidth-1,0],[maxWidth-1,maxHeight-1],[0,maxHeight-1]], dtype="float32")
                                M = cv2.getPerspectiveTransform(src, dst)
                                left_warp = cv2.warpPerspective(left_arr, M, (maxWidth, maxHeight))
                                left = Image.fromarray(left_warp)
                    # Right half
                    right_arr = np.array(right.convert("RGB"))
                    pts_right = self._detect_page_contour_from_frame(right_arr)
                    if pts_right and len(pts_right) >= 4:
                        ordered = self._order_points(pts_right)
                        if len(ordered) == 4:
                            def dist(a, b):
                                import math
                                return math.hypot(a[0]-b[0], a[1]-b[1])
                            widthA = dist(ordered[2], ordered[3])
                            widthB = dist(ordered[1], ordered[0])
                            maxWidth = max(int(widthA), int(widthB))
                            heightA = dist(ordered[1], ordered[2])
                            heightB = dist(ordered[0], ordered[3])
                            maxHeight = max(int(heightA), int(heightB))
                            if maxWidth > 0 and maxHeight > 0:
                                src = np.array(ordered, dtype="float32")
                                dst = np.array([[0,0],[maxWidth-1,0],[maxWidth-1,maxHeight-1],[0,maxHeight-1]], dtype="float32")
                                M = cv2.getPerspectiveTransform(src, dst)
                                right_warp = cv2.warpPerspective(right_arr, M, (maxWidth, maxHeight))
                                right = Image.fromarray(right_warp)
                except Exception:
                    # If any of the per-half crops fail, keep the simple halves
                    pass

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
        # Scroll to the last captured image (wait for gallery to fully load)
        self.after(300, self._scroll_to_last_image)
    
    def _scroll_to_last_image(self):
        """Scroll the gallery to show the last image."""
        if len(self.gallery_images) == 0:
            return
        
        # Select the last image
        last_idx = len(self.gallery_images) - 1
        self.select_gallery_item(last_idx)
        
        # Force update of canvas layout
        self.gallery_canvas.update_idletasks()
        
        # Scroll to bottom
        if last_idx < len(self.gallery_frames):
            # Update scroll region
            self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all"))
            
            # Get scroll region dimensions
            scroll_region = self.gallery_canvas.cget("scrollregion")
            if scroll_region:
                try:
                    coords = [float(x) for x in scroll_region.split()]
                    total_height = coords[3] - coords[1]
                    canvas_height = self.gallery_canvas.winfo_height()
                    
                    if total_height > canvas_height:
                        # Scroll to show the last item at the bottom
                        frame = self.gallery_frames[last_idx]
                        frame_y = frame.winfo_y()
                        frame_h = frame.winfo_height()
                        
                        # Calculate scroll position to show item at bottom
                        target_y = frame_y + frame_h - canvas_height + 10
                        scroll_fraction = target_y / total_height
                        scroll_fraction = max(0.0, min(1.0, scroll_fraction))
                        
                        self.gallery_canvas.yview_moveto(scroll_fraction)
                    else:
                        # All items fit, scroll to top
                        self.gallery_canvas.yview_moveto(0)
                except:
                    # Fallback: just scroll to bottom
                    self.gallery_canvas.yview_moveto(1.0)
    
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
    
    def open_calibration_dialog(self):
        """Open calibration dialog for current camera."""
        if self.current_camera_idx is None:
            self.show_toast("⚠ Conecte una cámara primero")
            return
        CalibrationDialog(self, self)
    
    def save_current_calibration(self):
        """Save current processing settings as calibration for this camera."""
        if self.current_camera_idx is None:
            self.show_toast("⚠ Conecte una cámara primero")
            return
        
        settings = {
            'paper_format': self.var_paper_format.get(),
            'auto_fingers': self.var_auto_fingers.get(),
            'auto_brightness': self.var_auto_brightness.get(),
            'auto_crop': self.var_auto_crop.get(),
            'dewarp': self.var_dewarp.get(),
            'brightness': self.s_brightness.get(),
            'contrast': self.s_contrast.get()
        }
        
        proj_name = self.app.project.titulo if self.app.project else None
        save_calibration_for_camera(self.current_camera_idx, settings, proj_name)
        
        # Update calibration status label
        fmt = self.var_paper_format.get()
        dpi = settings.get('target_dpi', 'N/A')
        self.lbl_calib_status.config(text=f"Calibración: {fmt} @ {dpi} DPI")
        
        self.show_toast(f"✓ Calibración guardada para cámara {self.current_camera_idx}")
    
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
        if messagebox.askyesno("Borrar", f"¿Borrar {img_path.name}?", parent=self):
            try:
                img_path.unlink()
                self.show_toast(f"Borrada: {img_path.name}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo borrar: {e}", parent=self)
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
            messagebox.showerror("Preview", f"Error al abrir imagen: {e}", parent=self)
    def bind_all_shortcuts(self):
        self.bind_all("<space>", lambda e: self.capture())
        self.bind_all("<Control-s>", lambda e: self.capture())
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
            messagebox.showerror("Recortar", "No se pudo leer frame de la cámara.", parent=self)
            return
        # Work on RGB and honor calibration area like capture()
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        try:
            if self.calibration_settings and 'calib_area' in self.calibration_settings:
                h, w = frame_rgb.shape[:2]
                area = self.calibration_settings['calib_area']
                x1 = int(area['tl'][0] * w); y1 = int(area['tl'][1] * h)
                x2 = int(area['br'][0] * w); y2 = int(area['br'][1] * h)
                frame_rgb = frame_rgb[y1:y2, x1:x2]
        except Exception:
            pass

        # If a midline exists, pick the half according to Anverso/Reverso and crop there
        import numpy as np
        midline = None
        try:
            midline = detect_two_pages_line(frame_rgb)
        except Exception:
            midline = None

        roi_rgb = frame_rgb
        if midline is not None:
            h, w = frame_rgb.shape[:2]
            (mx1, my1), (mx2, my2) = midline
            x_split = max(1, min(w-1, int((mx1 + mx2)//2)))
            side_choice = self.var_face.get()
            # Very small margin only for left side to avoid gutter; no margin on right
            margin_left = max(2, int(w * 0.002))
            margin_right = 0  # No margin on right to preserve full page
            
            # Handle "ambas" mode - capture both sides
            if side_choice == "ambas":
                # Process left side (reverso)
                left_roi = frame_rgb[:, 0:min(x_split + 1, w)]
                if left_roi.shape[1] > margin_left:
                    left_roi = left_roi[:, :-margin_left]
                
                pts_left = None
                try:
                    pts_left = self._detect_page_contour_from_frame(left_roi)
                except Exception:
                    pts_left = None
                if not pts_left:
                    # Fallback for left
                    try:
                        gray = cv2.cvtColor(left_roi, cv2.COLOR_RGB2GRAY)
                        try:
                            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                            gray = clahe.apply(gray)
                        except Exception:
                            pass
                        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9,9)))
                        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5,5)))
                        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        if not contours:
                            edges = cv2.Canny(gray, 50, 150)
                            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        if contours:
                            contours = sorted(contours, key=cv2.contourArea, reverse=True)
                            rect = cv2.minAreaRect(contours[0])
                            box = cv2.boxPoints(rect)
                            pts_left = [(int(x), int(y)) for x, y in box]
                    except Exception:
                        pass
                
                if pts_left:
                    ordered_left = self._order_points(pts_left)
                    if len(ordered_left) == 4:
                        (tl, tr, br, bl) = ordered_left
                        def dist(a, b):
                            import math
                            return math.hypot(a[0]-b[0], a[1]-b[1])
                        widthA = dist(br, bl); widthB = dist(tr, tl); maxWidth = max(int(widthA), int(widthB))
                        heightA = dist(tr, br); heightB = dist(tl, bl); maxHeight = max(int(heightA), int(heightB))
                        if maxWidth > 0 and maxHeight > 0:
                            try:
                                src_pts = np.array(ordered_left, dtype="float32")
                                dst_pts = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
                                M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                                warped = cv2.warpPerspective(left_roi, M, (maxWidth, maxHeight))
                                pil = Image.fromarray(warped)
                                pil = ImageEnhance.Brightness(pil).enhance(self.s_brightness.get())
                                pil = ImageEnhance.Contrast(pil).enhance(self.s_contrast.get())
                                proj = self.app.project
                                if proj:
                                    next_num = self._get_next_page_number()
                                    left_path = proj.pages_dir / f"page_{next_num:04d}_reverso.jpg"
                                    pil.save(left_path, "JPEG", quality=92)
                                    self.show_toast(f"Guardado reverso: {left_path.name}")
                            except Exception:
                                pass
                
                # Process right side (anverso)
                right_roi = frame_rgb[:, max(x_split - 1, 0):w]
                # No margin trimming on right side to preserve full page edge
                
                pts_right = None
                try:
                    pts_right = self._detect_page_contour_from_frame(right_roi)
                except Exception:
                    pts_right = None
                if not pts_right:
                    # Fallback for right
                    try:
                        gray = cv2.cvtColor(right_roi, cv2.COLOR_RGB2GRAY)
                        try:
                            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                            gray = clahe.apply(gray)
                        except Exception:
                            pass
                        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9,9)))
                        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5,5)))
                        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        if not contours:
                            edges = cv2.Canny(gray, 50, 150)
                            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        if contours:
                            contours = sorted(contours, key=cv2.contourArea, reverse=True)
                            rect = cv2.minAreaRect(contours[0])
                            box = cv2.boxPoints(rect)
                            pts_right = [(int(x), int(y)) for x, y in box]
                    except Exception:
                        pass
                
                if pts_right:
                    ordered_right = self._order_points(pts_right)
                    if len(ordered_right) == 4:
                        (tl, tr, br, bl) = ordered_right
                        def dist(a, b):
                            import math
                            return math.hypot(a[0]-b[0], a[1]-b[1])
                        widthA = dist(br, bl); widthB = dist(tr, tl); maxWidth = max(int(widthA), int(widthB))
                        heightA = dist(tr, br); heightB = dist(tl, bl); maxHeight = max(int(heightA), int(heightB))
                        if maxWidth > 0 and maxHeight > 0:
                            try:
                                src_pts = np.array(ordered_right, dtype="float32")
                                dst_pts = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
                                M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                                warped = cv2.warpPerspective(right_roi, M, (maxWidth, maxHeight))
                                pil = Image.fromarray(warped)
                                pil = ImageEnhance.Brightness(pil).enhance(self.s_brightness.get())
                                pil = ImageEnhance.Contrast(pil).enhance(self.s_contrast.get())
                                proj = self.app.project
                                if proj:
                                    next_num = self._get_next_page_number()
                                    right_path = proj.pages_dir / f"page_{next_num:04d}_anverso.jpg"
                                    pil.save(right_path, "JPEG", quality=92)
                                    self.show_toast(f"Guardado anverso: {right_path.name}")
                            except Exception:
                                pass
                
                self.refresh_gallery()
                return
            
            # Single side mode
            take_right = (side_choice == "anverso")
            if take_right:
                roi_rgb = frame_rgb[:, max(x_split - 1, 0):w]
                # No margin on right side
            else:
                roi_rgb = frame_rgb[:, 0:min(x_split + 1, w)]
                if roi_rgb.shape[1] > margin_left:
                    roi_rgb = roi_rgb[:, :-margin_left]

        # Detect page contour inside the chosen ROI and warp
        pts = None
        try:
            pts = self._detect_page_contour_from_frame(roi_rgb)
        except Exception:
            pts = None
        if not pts:
            try:
                gray = cv2.cvtColor(roi_rgb, cv2.COLOR_RGB2GRAY)
                try:
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                    gray = clahe.apply(gray)
                except Exception:
                    pass
                _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9,9)))
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5,5)))
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not contours:
                    edges = cv2.Canny(gray, 50, 150)
                    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    contours = sorted(contours, key=cv2.contourArea, reverse=True)
                    c = contours[0]
                    rect = cv2.minAreaRect(c)
                    box = cv2.boxPoints(rect)
                    pts = [(int(x), int(y)) for x, y in box]
                else:
                    pts = None
            except Exception:
                pts = None
        if not pts:
            self.show_toast("⚠ No se detectó una página en el área seleccionada")
            return
        ordered = self._order_points(pts)
        if len(ordered) != 4:
            messagebox.showerror("Recortar", "No se pudo ordenar los puntos de la página detectada.", parent=self)
            return
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
            messagebox.showerror("Recortar", "Dimensiones inválidas para recorte.", parent=self)
            return
        try:
            src_pts = np.array(ordered, dtype="float32")
            dst_pts = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
            M = cv2.getPerspectiveTransform(src_pts, dst_pts)
            warped = cv2.warpPerspective(roi_rgb, M, (maxWidth, maxHeight))
            pil = Image.fromarray(warped)
            # Apply brightness/contrast adjustments
            pil = ImageEnhance.Brightness(pil).enhance(self.s_brightness.get())
            pil = ImageEnhance.Contrast(pil).enhance(self.s_contrast.get())
            proj = self.app.project
            if proj is None:
                self.show_toast("⚠ Cree o abra un proyecto para guardar")
                return
            next_num = self._get_next_page_number()
            out_path = proj.pages_dir / f"page_{next_num:04d}.jpg"
            pil.save(out_path, "JPEG", quality=92)
            self.show_toast(f"Recorte guardado: {out_path.name}")
            self.refresh_gallery()
        except Exception as e:
            messagebox.showerror("Recortar", f"Error realizando recorte: {e}", parent=self)

class AnnotationWindow(tk.Toplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.title(f"{APP_NAME} — Módulo Anotador")
        self.geometry("1100x780")
        self.app = app
        
        # Main frame
        main_frame = ttk.Frame(self, padding=16)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="Módulo de Anotaciones (placeholder estable)", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(main_frame, text="Aquí irá el visor, editor WYSIWYG, geolocalización y enlaces a Topónimos/Personas.").grid(row=1, column=0, sticky="w")

class GeoDocsScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — {APP_VERSION}"); self.geometry("800x600"); self.minsize(700, 500)
        self.project: Optional[ProjectInfo] = None
        init_global_db(Path.cwd())
        
        # Check for single instance
        self.lock_file = Path.cwd() / ".geodocs_scanner.lock"
        if not self._acquire_lock():
            messagebox.showerror("Instancia activa", "Ya hay una instancia de GeoDocs Scanner ejecutándose.")
            self.destroy()
            return
        
        # Track child windows
        self.scanner_window = None
        self.annotation_window = None
        
        self._build_menu()
        container = ttk.Frame(self); container.pack(fill="both", expand=True)
        self.start_frame = StartFrame(container, self)
        self.start_frame.pack(fill="both", expand=True)
        
        # Load last project if exists
        self._load_last_project()
        
        self.bind_all("<Control-n>", lambda e: self.new_project())
        self.bind_all("<Control-o>", lambda e: self.open_project())
        self.bind_all("<F6>", lambda e: self.open_scanner_window())
        self.bind_all("<F7>", lambda e: self.open_annotation_window())
        
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
        m_view.add_command(label="📷 Abrir Escáner (F6)", command=self.open_scanner_window)
        m_view.add_command(label="📝 Abrir Anotador (F7)", command=self.open_annotation_window)
        menubar.add_cascade(label="Herramientas", menu=m_view)
        self.config(menu=menubar)
    
    def open_scanner_window(self):
        """Open or focus the scanner window."""
        if self.scanner_window is None or not self.scanner_window.winfo_exists():
            self.scanner_window = ScannerWindow(self, self)
            # Refresh gallery after window is created if project is loaded
            if self.project:
                self.scanner_window.after(100, self.scanner_window.refresh_gallery)
        else:
            self.scanner_window.lift()
            self.scanner_window.focus_force()
    
    def open_annotation_window(self):
        """Open or focus the annotation window."""
        if self.annotation_window is None or not self.annotation_window.winfo_exists():
            self.annotation_window = AnnotationWindow(self, self)
        else:
            self.annotation_window.lift()
            self.annotation_window.focus_force()
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
        self.start_frame.refresh()
        messagebox.showinfo("Proyecto", f"✓ Proyecto creado: {pinfo.titulo}")
        self.open_scanner_window()
    
    def open_project(self):
        root_dir = filedialog.askdirectory(title="Seleccione carpeta del proyecto")
        if not root_dir: return
        proj_path = Path(root_dir); pages = proj_path / "paginas"
        if not pages.exists():
            messagebox.showerror("Proyecto", "Carpeta inválida: no contiene 'paginas/'."); return
        title = proj_path.name; self.project = ProjectInfo(titulo=title, carpeta_raiz=proj_path)
        self._save_last_project(proj_path)
        self.start_frame.refresh()
        messagebox.showinfo("Proyecto", f"✓ Proyecto abierto: {title}")
        self.open_scanner_window()
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
                    self.start_frame.refresh()
        except Exception:
            pass

def main():
    app = GeoDocsScannerApp(); app.mainloop()

if __name__ == "__main__":
    main()
