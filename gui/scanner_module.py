#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scanner_module.py — Core camera scanning functionality
Extracted from gui_book_scan_tk2.py and refactored for modular integration
"""
import os
# Suppress OpenCV logging before import - set to SILENT level
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.dialogs import Messagebox
    USE_BOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    Messagebox = None
    USE_BOOTSTRAP = False
try:
    import pywinstyles
except ImportError:
    pywinstyles = None
from pathlib import Path
import sys
import threading
import time
from typing import Optional, List, Tuple
from utils.window_utils import center_to_parent
import json

# Ensure project root on sys.path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.theme_titlebar import apply_titlebar_theme
from utils import app_config
from utils import db_manager as db
try:
    from gui.metadata_manager import open_metadata_manager
except Exception:
    open_metadata_manager = None

try:
    import cv2
    import numpy as np
    # Additional runtime suppression (though env vars should handle most)
    try:
        cv2.setLogLevel(0)  # 0 = SILENT
    except Exception:
        pass
except ImportError:
    cv2 = None
    np = None

try:
    from PIL import Image, ImageTk, ImageEnhance, ImageDraw
except ImportError:
    Image = None
    ImageTk = None
    ImageDraw = None


class CameraScanner:
    """Core scanner functionality with camera preview and capture"""
    
    def __init__(self, parent, output_dir: Path):
        self.parent = parent
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # UI preferences file (store under output directory)
        self._prefs_path = self.output_dir / "_ui_prefs.json"
        
        self.cap = None
        self._preview_running = False
        self._tkimg = None
        self.current_camera_idx = None
        self.camera_map = {}
        self.camera_resolutions = {}
        self._frame_counter = 0
        self._detection_frame_counter = 0  # For detection throttling
        
        # Frame buffer for thread-safe display
        self._current_frame = None
        self._frame_lock = threading.Lock()
        
        # Calibration and detection
        self.calibration_area = None  # {tl: (x, y), br: (x, y)} normalized coords
        self.detect_page = tk.BooleanVar(value=True)
        self.book_mode = tk.BooleanVar(value=False)
        self.detected_contour = None
        self._stable_contour = None  # Smoothed contour for display
        self._contour_history = []  # For smoothing
        self._book_split_line = None  # Vertical line for book mode
        # Gallery thumbnail padding color (visual frame)
        self.thumb_pad_color = '#ffffff'
        
        self.setup_ui()
        # Restore persisted UI state (window geometry and paned sash)
        self._restore_ui_prefs()
        self.refresh_cameras()
        
    def setup_ui(self):
        """Create the scanner UI"""
        # Main container
        main_frame = ttk.Frame(self.parent, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(toolbar, text="Cámara:").pack(side=tk.LEFT, padx=5)

        self.cmb_cam = ttk.Combobox(toolbar, width=35, state="readonly")
        self.cmb_cam.pack(side=tk.LEFT, padx=5)

        ttk.Button(toolbar, text="Refrescar", command=self.refresh_cameras).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Conectar", command=self.open_camera).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Desconectar", command=self.close_camera).pack(side=tk.LEFT, padx=5)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Checkbutton(toolbar, text="Detectar página", variable=self.detect_page).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(toolbar, text="Modo libro", variable=self.book_mode).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="⚙️ Calibrar área", command=self.open_calibration).pack(side=tk.LEFT, padx=5)

        # Detection status indicator
        self.detection_status_label = ttk.Label(toolbar, text="", foreground="gray")
        self.detection_status_label.pack(side=tk.LEFT, padx=10)

        # Paned window (left: preview, right: gallery)
        self.paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(self.paned)
        right_panel = ttk.Frame(self.paned, width=280)
        self.paned.add(left_panel, weight=3)
        self.paned.add(right_panel, weight=1)

        # Preview canvas in left panel
        canvas_frame = ttk.Frame(left_panel)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.canvas = tk.Canvas(canvas_frame, width=960, height=720, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self._image_item = self.canvas.create_image(0, 0, anchor="nw", image=None)

        # Image adjustments (left panel)
        controls_frame = ttk.Frame(left_panel)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(controls_frame, text="Brillo:").pack(side=tk.LEFT, padx=5)
        self.s_brightness = tk.DoubleVar(value=1.0)
        ttk.Scale(controls_frame, variable=self.s_brightness, from_=0.5, to=1.5, orient="horizontal", length=150).pack(side=tk.LEFT, padx=5)
        ttk.Label(controls_frame, text="Contraste:").pack(side=tk.LEFT, padx=(20, 5))
        self.s_contrast = tk.DoubleVar(value=1.0)
        ttk.Scale(controls_frame, variable=self.s_contrast, from_=0.5, to=1.5, orient="horizontal", length=150).pack(side=tk.LEFT, padx=5)

        # Thumbnail visual padding control (repurposed from page margin)
        ttk.Label(controls_frame, text="Padding miniatura %:").pack(side=tk.LEFT, padx=(20, 5))
        self.page_margin = tk.DoubleVar(value=0.0)  # percent (0-10) used as gallery thumb padding
        ttk.Scale(
            controls_frame,
            variable=self.page_margin,
            from_=0.0,
            to=10.0,
            orient="horizontal",
            length=120,
            command=lambda v: self._on_thumb_padding_change(),
        ).pack(side=tk.LEFT, padx=5)
        # Color chooser for padding
        ttk.Button(controls_frame, text="Color…", command=self._on_choose_thumb_color).pack(side=tk.LEFT, padx=(8, 4))
        self._thumb_color_swatch = tk.Label(controls_frame, width=2, bg=self.thumb_pad_color, relief='groove', bd=1)
        self._thumb_color_swatch.pack(side=tk.LEFT, padx=(2, 0))

        # Resize controls
        ttk.Label(controls_frame, text="Redimensionar:").pack(side=tk.LEFT, padx=(20, 5))
        self.resize_enabled = tk.BooleanVar(value=False)
        self.chk_resize = ttk.Checkbutton(controls_frame, variable=self.resize_enabled, command=self._toggle_resize_controls)
        self.chk_resize.pack(side=tk.LEFT, padx=(0, 8))
        self.lbl_width = ttk.Label(controls_frame, text="Ancho(px):")
        self.lbl_width.pack(side=tk.LEFT, padx=(8, 4))
        self.target_width = tk.IntVar(value=0)
        self.spin_width = tk.Spinbox(controls_frame, from_=0, to=10000, width=6, textvariable=self.target_width, state='disabled')
        self.spin_width.pack(side=tk.LEFT)
        self.lbl_height = ttk.Label(controls_frame, text="Alto(px):")
        self.lbl_height.pack(side=tk.LEFT, padx=(8, 4))
        self.target_height = tk.IntVar(value=0)
        self.spin_height = tk.Spinbox(controls_frame, from_=0, to=10000, width=6, textvariable=self.target_height, state='disabled')
        self.spin_height.pack(side=tk.LEFT)

        # Bottom buttons (left panel)
        buttons_frame = ttk.Frame(left_panel)
        buttons_frame.pack(fill=tk.X)
        ttk.Button(buttons_frame, text="📸 Capturar (Espacio)", command=self.capture_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="📂 Abrir carpeta", command=self.open_output_folder).pack(side=tk.LEFT, padx=5)
        ttk.Separator(buttons_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(buttons_frame, text="📁 Seleccionar Proyecto…", command=self._select_project).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="➕ Crear Proyecto", command=self._create_project).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="⚙️ Tablas…", command=lambda: (open_metadata_manager(self.parent, focus_tab='archivos') if open_metadata_manager else None)).pack(side=tk.LEFT, padx=5)

        # --- Gallery (right panel) ---
        # High-contrast scrollbar style (best effort; some themes may ignore)
        try:
            self._style = ttk.Style(self.parent)
            self._style.configure('Gallery.Vertical.TScrollbar', background='#bfbfbf')
            # On some themes troughcolor is honored:
            self._style.configure('Gallery.Vertical.TScrollbar', troughcolor='#1e1e1e')
            # Improve active state contrast
            self._style.map('Gallery.Vertical.TScrollbar', background=[('active', '#d9d9d9'), ('!active', '#bfbfbf')])
        except Exception:
            pass
        self.gallery_container = ttk.Frame(right_panel)
        # Increase right-side distance from panel border
        self.gallery_container.pack(fill=tk.BOTH, expand=True, padx=(6, 18), pady=6)

        # Scrollable canvas for thumbnails
        self.gallery_canvas = tk.Canvas(self.gallery_container, bg="#0f0f0f", highlightthickness=0)
        self.gallery_scroll = ttk.Scrollbar(self.gallery_container, orient=tk.VERTICAL, command=self.gallery_canvas.yview, style='Gallery.Vertical.TScrollbar')
        self.gallery_view = ttk.Frame(self.gallery_canvas)
        self.gallery_view.bind("<Configure>", lambda e: self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all")))
        # Keep a reference to the created window so we can resize it with the canvas
        self._gallery_window_id = self.gallery_canvas.create_window((0, 0), window=self.gallery_view, anchor="nw")
        self.gallery_canvas.configure(yscrollcommand=self.gallery_scroll.set)
        # Pack scrollbar first to ensure it always reserves space on the right
        # (prevents visual overlap during rapid resizes)
        # Make scrollbar a bit wider for visibility and add a small left padding
        try:
            self._gallery_scrollbar_width = 20
            self.gallery_scroll.config(width=self._gallery_scrollbar_width)
        except Exception:
            self._gallery_scrollbar_width = 12
        self.gallery_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))
        self.gallery_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Mouse wheel scrolling
        self.gallery_canvas.bind('<MouseWheel>', self._on_gallery_mousewheel)
        self.gallery_canvas.bind('<Button-4>', lambda e: self._gallery_scroll(-1))  # Linux scroll up
        self.gallery_canvas.bind('<Button-5>', lambda e: self._gallery_scroll(1))   # Linux scroll down
        # Rebuild thumbnails on width changes to adapt to gallery width
        self.gallery_canvas.bind('<Configure>', lambda e: self._on_gallery_resize())

        # State for gallery
        self._gallery_order = []
        self._thumb_cache = {}
        self._selected_index = None
        self._dragging_index = None

        # Load existing images and build gallery
        self._load_gallery_manifest()
        self._build_gallery()

        # Keyboard bindings
        self.parent.bind('<space>', lambda e: self.capture_image())
        self.parent.bind('<Escape>', lambda e: self.close_camera())
        # Bind Delete only when gallery has focus to avoid global side-effects
        self.gallery_container.bind('<Delete>', self._on_delete_key)
        # Optional keyboard reordering: Ctrl+Up / Ctrl+Down
        self.gallery_container.bind('<Control-Up>', lambda e: self._move_selected(-1))
        self.gallery_container.bind('<Control-Down>', lambda e: self._move_selected(1))

        # Show initial state on preview
        self._show_camera_off_screen()
        # Ensure resize controls reflect current toggle
        self._toggle_resize_controls()
        # Current project
        self.current_project = None

    def _restore_ui_prefs(self):
        """Restore window geometry, paned sash and UI options if saved previously"""
        try:
            if self._prefs_path.exists():
                data = json.loads(self._prefs_path.read_text(encoding="utf-8"))
                geom = data.get("geometry")
                sash = data.get("sash")
                pm = data.get("page_margin")
                thumb_color = data.get("thumb_padding_color")
                resize = data.get("resize") or {}
                if isinstance(geom, str):
                    # Apply window geometry to parent toplevel
                    self.parent.geometry(geom)
                if sash is not None:
                    # Defer sash restore until layout is ready
                    self.parent.after(100, lambda: self._set_sash_safe(sash))
                # Restore page margin
                try:
                    if pm is not None:
                        self.page_margin.set(float(pm))
                except Exception:
                    pass
                # Restore thumbnail padding color
                try:
                    if isinstance(thumb_color, str) and thumb_color.startswith('#'):
                        self.thumb_pad_color = thumb_color
                        try:
                            self._thumb_color_swatch.config(bg=self.thumb_pad_color)
                        except Exception:
                            pass
                except Exception:
                    pass

                # Restore resize settings
                try:
                    en = resize.get("enabled")
                    if en is not None:
                        self.resize_enabled.set(bool(en))
                    tw = resize.get("width")
                    if tw is not None:
                        self.target_width.set(int(tw))
                    th = resize.get("height")
                    if th is not None:
                        self.target_height.set(int(th))
                    # Reflect toggle state in controls
                    self._toggle_resize_controls()
                except Exception:
                    pass
        except Exception:
            # Ignore restore errors silently
            pass

    def _set_sash_safe(self, pos):
        try:
            if hasattr(self, "paned") and self.paned.winfo_ismapped():
                total = max(self.paned.winfo_width(), 1)
                # Clamp sash position reasonably
                clamped = max(200, min(int(pos), total - 150))
                try:
                    self.paned.sashpos(0, clamped)
                except Exception:
                    pass
        except Exception:
            pass

    # --- Gallery helpers ---
    def _gallery_files_in_dir(self) -> List[str]:
        exts = {'.jpg', '.jpeg', '.png', '.bmp'}
        files = []
        try:
            for p in sorted(self.output_dir.iterdir()):
                if p.suffix.lower() in exts and p.is_file():
                    files.append(p.name)
        except Exception:
            pass
        return files

    def _manifest_path(self) -> Path:
        return self.output_dir / "_gallery.json"

    def _load_gallery_manifest(self):
        mp = self._manifest_path()
        if mp.exists():
            try:
                data = json.load(mp.open('r', encoding='utf-8'))
                if isinstance(data, list):
                    self._gallery_order = [fn for fn in data if (self.output_dir / fn).exists()]
                else:
                    self._gallery_order = []
            except Exception:
                self._gallery_order = []
        else:
            # Initialize from directory
            self._gallery_order = self._gallery_files_in_dir()
            self._save_gallery_manifest()

    def _save_gallery_manifest(self):
        try:
            json.dump(self._gallery_order, self._manifest_path().open('w', encoding='utf-8'), ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _thumb_for(self, filename: str, max_width: int):
        key = (filename, max_width)
        if key in self._thumb_cache:
            return self._thumb_cache[key]
        try:
            full = self.output_dir / filename
            img = Image.open(full)
            # Target width equals available gallery width minus padding
            w, h = img.size
            tw = max(50, int(max_width))
            scale = min(1.0, tw / max(1, w))
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            if new_w != w or new_h != h:
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            tkimg = ImageTk.PhotoImage(img)
            self._thumb_cache[key] = tkimg
            return tkimg
        except Exception:
            return None

    def _build_gallery(self):
        # Clear
        for w in list(self.gallery_view.children.values()):
            w.destroy()
        # Compute target width for thumbnails
        t_width = self._thumb_target_width()
        
        # Helper para agregar bindings de scroll a widgets
        def bind_mousewheel(widget):
            widget.bind('<MouseWheel>', self._on_gallery_mousewheel)
            widget.bind('<Button-4>', lambda e: self._gallery_scroll(-1))
            widget.bind('<Button-5>', lambda e: self._gallery_scroll(1))
        
        for idx, fn in enumerate(self._gallery_order):
            # Highlight selection background in green
            bg = "#1e1e1e" if idx != self._selected_index else "#2d5f2d"

            item = tk.Frame(self.gallery_view, bg=bg)
            item.pack(fill=tk.X, pady=6, padx=8)
            item.bind('<Button-1>', lambda e, i=idx: self._on_thumb_click(i, e))
            item.bind('<Double-Button-1>', lambda e, i=idx: self._open_preview(i))
            bind_mousewheel(item)

            inner = tk.Frame(item, bg=bg)
            inner.pack(fill=tk.X, expand=True)
            bind_mousewheel(inner)

            thumb = self._thumb_for(fn, t_width)
            if thumb:
                pad_px = self._thumb_padding_px(t_width)
                if pad_px > 0:
                    pad_frame = tk.Frame(inner, bg=self.thumb_pad_color)
                    pad_frame.pack(padx=6, pady=(6, 2), anchor='center')
                    bind_mousewheel(pad_frame)
                    lbl_img = tk.Label(pad_frame, image=thumb, bg=self.thumb_pad_color)
                    lbl_img.image = thumb
                    lbl_img.pack(padx=pad_px, pady=pad_px)
                    # Bind events on both frame and label
                    for wdg in (pad_frame, lbl_img):
                        wdg.bind('<Button-1>', lambda e, i=idx: self._on_thumb_click(i, e))
                        wdg.bind('<Double-Button-1>', lambda e, i=idx: self._open_preview(i))
                        bind_mousewheel(wdg)
                else:
                    lbl_img = tk.Label(inner, image=thumb, bg=bg)
                    lbl_img.image = thumb
                    lbl_img.pack(padx=6, pady=(6, 2), anchor='center')
                    lbl_img.bind('<Button-1>', lambda e, i=idx: self._on_thumb_click(i, e))
                    lbl_img.bind('<Double-Button-1>', lambda e, i=idx: self._open_preview(i))
                    bind_mousewheel(lbl_img)

            lbl_text = tk.Label(item, text=fn, bg=bg, fg='#ddd', wraplength=t_width, justify='center')
            lbl_text.pack(fill=tk.X, padx=6, pady=(0, 6))
            lbl_text.bind('<Button-1>', lambda e, i=idx: self._on_thumb_click(i, e))
            lbl_text.bind('<Double-Button-1>', lambda e, i=idx: self._open_preview(i))
            bind_mousewheel(lbl_text)

    def _thumb_padding_px(self, t_width: int) -> int:
        """Compute pixel padding for thumbnail based on percentage control and target width."""
        try:
            pct = float(self.page_margin.get())
        except Exception:
            pct = 0.0
        pct = max(0.0, min(20.0, pct))  # clamp 0-20%
        return int(t_width * (pct / 100.0))

    def _on_thumb_padding_change(self):
        """Rebuild gallery when padding slider changes (throttled)."""
        try:
            if hasattr(self, '_thumb_padding_after') and self._thumb_padding_after:
                self.parent.after_cancel(self._thumb_padding_after)
        except Exception:
            pass
        self._thumb_padding_after = self.parent.after(80, self._build_gallery)

    def _on_choose_thumb_color(self):
        try:
            color = colorchooser.askcolor(parent=self.parent, color=self.thumb_pad_color, title="Color de padding de miniatura")
            # askcolor returns (rgb_tuple, hex) or (None, None)
            if color and color[1]:
                self.thumb_pad_color = color[1]
                try:
                    self._thumb_color_swatch.config(bg=self.thumb_pad_color)
                except Exception:
                    pass
                self._build_gallery()
            # Ensure scanner window stays on top/focused (prevent main app popping to front)
            try:
                self.parent.lift()
                self.parent.focus_force()
            except Exception:
                pass
        except Exception:
            pass

    def _thumb_target_width(self) -> int:
        try:
            # Canvas width minus padding and scrollbar (~8px left/right + 12px)
            cw = self.gallery_canvas.winfo_width()
            if cw <= 0:
                return 180
            # Account for outer padding (item padx=8) and some margin
            sbw = getattr(self, '_gallery_scrollbar_width', 12)
            return max(100, cw - 8 - sbw - 12)
        except Exception:
            return 180

    def _on_gallery_resize(self):
        """Rebuild gallery thumbnails when the canvas size changes."""
        try:
            # Ensure the embedded frame tracks the canvas width
            try:
                if hasattr(self, '_gallery_window_id') and self._gallery_window_id:
                    self.gallery_canvas.itemconfig(self._gallery_window_id, width=self.gallery_canvas.winfo_width())
            except Exception:
                pass
            # Throttle rapid resizes and rebuild thumbs after layout settles
            if hasattr(self, '_gallery_resize_after') and self._gallery_resize_after:
                self.parent.after_cancel(self._gallery_resize_after)
        except Exception:
            pass
        self._gallery_resize_after = self.parent.after(120, self._build_gallery)

    def _on_gallery_mousewheel(self, event):
        """Scroll gallery canvas with mouse wheel (Windows/macOS)."""
        try:
            delta = event.delta
            if delta == 0:
                return 'break'
            step = -1 if delta > 0 else 1
            self.gallery_canvas.yview_scroll(step, 'units')
        except Exception:
            pass
        return 'break'

    def _gallery_scroll(self, direction: int):
        """Scroll helper for Linux button-4/5 events."""
        try:
            self.gallery_canvas.yview_scroll(direction, 'units')
        except Exception:
            pass
        return 'break'

    def _scroll_selected_into_view(self):
        """Ensure the selected gallery item is visible by adjusting the canvas yview."""
        try:
            if self._selected_index is None:
                return
            children = list(self.gallery_view.children.values())
            if not (0 <= self._selected_index < len(children)):
                return
            target = children[self._selected_index]
            # Compute target y within the scroll region
            self.gallery_view.update_idletasks()
            bbox = self.gallery_canvas.bbox('all')
            if not bbox:
                return
            _, y1, _, y2 = bbox
            total_h = max(1, y2 - y1)
            item_y = target.winfo_y()
            # Scroll so that item's top is near the top (with margin)
            frac = max(0.0, min(1.0, (item_y - 10) / total_h))
            self.gallery_canvas.yview_moveto(frac)
        except Exception:
            pass

    def _open_preview(self, index: int):
        """Open a preview window for the selected image, with simple Left/Right navigation."""
        try:
            if not (0 <= index < len(self._gallery_order)):
                return
            self._selected_index = index
            self._build_gallery()

            top = tk.Toplevel(self.parent)
            try:
                center_to_parent(top, self.parent)
            except Exception:
                pass
            top.title(f"Previsualización - {self._gallery_order[index]}")
            top.geometry("1000x800")

            # Toolbar (zoom controls)
            toolbar = ttk.Frame(top)
            toolbar.pack(fill=tk.X)
            # Container: canvas with scrollbars
            cont = ttk.Frame(top)
            cont.pack(fill=tk.BOTH, expand=True)
            vbar = ttk.Scrollbar(cont, orient=tk.VERTICAL)
            hbar = ttk.Scrollbar(cont, orient=tk.HORIZONTAL)
            canvas = tk.Canvas(cont, bg="#000000", highlightthickness=0,
                               yscrollcommand=vbar.set, xscrollcommand=hbar.set)
            vbar.config(command=canvas.yview)
            hbar.config(command=canvas.xview)
            vbar.pack(side=tk.RIGHT, fill=tk.Y)
            hbar.pack(side=tk.BOTTOM, fill=tk.X)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # State for preview
            state = {
                'pil': None,   # current PIL image (possibly downscaled base)
                'scale': 1.0,  # current zoom scale
                'fit': False   # fit-to-window mode flag
            }

            def clamp(val, a, b):
                return max(a, min(b, val))

            def render():
                if state['pil'] is None:
                    return
                try:
                    w, h = state['pil'].size
                    # If fit mode is on, compute scale from current canvas size
                    if state['fit']:
                        cw = max(1, canvas.winfo_width())
                        ch = max(1, canvas.winfo_height())
                        state['scale'] = clamp(min(cw / w, ch / h), 0.05, 5.0)
                    s = state['scale']
                    new_w = max(1, int(w * s))
                    new_h = max(1, int(h * s))
                    disp = state['pil'] if (new_w == w and new_h == h) else state['pil'].resize((new_w, new_h), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(disp)
                    canvas.delete("all")
                    
                    # Center the image in the canvas
                    cw = max(1, canvas.winfo_width())
                    ch = max(1, canvas.winfo_height())
                    x = max(new_w, cw) // 2
                    y = max(new_h, ch) // 2
                    canvas.create_image(x, y, anchor="center", image=photo)
                    canvas.image = photo
                    
                    # Scroll region: max of canvas size or image size to allow centering
                    scroll_w = max(cw, new_w)
                    scroll_h = max(ch, new_h)
                    canvas.config(scrollregion=(0, 0, scroll_w, scroll_h))
                    
                    # Center the viewport on the image
                    if new_w < cw:
                        canvas.xview_moveto(0)
                    else:
                        canvas.xview_moveto((new_w - cw) / (2 * scroll_w))
                    if new_h < ch:
                        canvas.yview_moveto(0)
                    else:
                        canvas.yview_moveto((new_h - ch) / (2 * scroll_h))
                except Exception as e:
                    print(f"Preview render error: {e}")

            def set_scale(new_scale: float):
                state['fit'] = False
                state['scale'] = clamp(new_scale, 0.05, 5.0)
                render()

            def fit_to_window():
                state['fit'] = True
                render()

            def on_canvas_resize(event):
                if state['fit']:
                    render()

            canvas.bind('<Configure>', on_canvas_resize)

            def zoom_in():
                set_scale(state['scale'] * 1.25)

            def zoom_out():
                set_scale(state['scale'] / 1.25)

            def reset_100():
                set_scale(1.0)

            # Toolbar buttons
            ttk.Button(toolbar, text="-", width=3, command=zoom_out).pack(side=tk.LEFT, padx=(6, 2), pady=6)
            ttk.Button(toolbar, text="+", width=3, command=zoom_in).pack(side=tk.LEFT, padx=2, pady=6)
            ttk.Button(toolbar, text="Ajustar", command=fit_to_window).pack(side=tk.LEFT, padx=(8, 2), pady=6)
            ttk.Button(toolbar, text="100%", command=reset_100).pack(side=tk.LEFT, padx=2, pady=6)

            def load_and_show(idx: int):
                # Clamp index
                idx_clamped = max(0, min(idx, len(self._gallery_order) - 1))
                fn = self._gallery_order[idx_clamped]
                top.title(f"Previsualización - {fn}")
                try:
                    pil = Image.open(self.output_dir / fn)
                    # Downscale large images to avoid Tk memory issues (cap max dimension ~2000px)
                    max_dim = 2000
                    w0, h0 = pil.size
                    base_scale = min(1.0, max_dim / max(w0, h0))
                    if base_scale < 1.0:
                        pil = pil.resize((int(w0 * base_scale), int(h0 * base_scale)), Image.Resampling.LANCZOS)
                except Exception as e:
                    if Messagebox:
                        Messagebox.show_error(title="Vista previa", message=f"No se pudo cargar la imagen: {e}", parent=self.root)
                    else:
                        messagebox.showerror("Vista previa", f"No se pudo cargar la imagen: {e}", parent=self.root)
                    return

                state['pil'] = pil
                # Auto-fit to window when loading a new image
                state['fit'] = True
                render()
                # Update selected/highlight in gallery
                self._selected_index = idx_clamped
                self._build_gallery()
                self.parent.after(50, self._scroll_selected_into_view)

            def go_prev(event=None):
                load_and_show(self._selected_index - 1)
                return 'break'

            def go_next(event=None):
                load_and_show(self._selected_index + 1)
                return 'break'

            # Navigation row
            nav = ttk.Frame(top)
            nav.pack(fill=tk.X)
            ttk.Button(nav, text="◀ Anterior", command=lambda: go_prev()).pack(side=tk.LEFT, padx=8, pady=6)
            ttk.Button(nav, text="Siguiente ▶", command=lambda: go_next()).pack(side=tk.LEFT, padx=8, pady=6)

            top.bind('<Left>', go_prev)
            top.bind('<Right>', go_next)
            top.focus_force()

            # Initial load
            load_and_show(index)
        except Exception:
            pass

    def _on_thumb_click(self, index: int, event):
        """Simple click handler - only selects, no dragging"""
        if self._selected_index == index:
            return  # Already selected, do nothing
        
        old_index = self._selected_index
        self._selected_index = index
        
        # Update only the affected frames' backgrounds without rebuilding
        try:
            frames = [w for w in self.gallery_view.children.values() if isinstance(w, tk.Frame)]
            if old_index is not None and old_index < len(frames):
                self._update_frame_bg(frames[old_index], "#1e1e1e")
            if index < len(frames):
                self._update_frame_bg(frames[index], "#2d5f2d")
            self.gallery_container.focus_set()
        except Exception:
            # Fallback to full rebuild if optimization fails
            self._build_gallery()
    
    def _update_frame_bg(self, frame, color):
        """Recursively update background color of frame and its children"""
        try:
            if hasattr(frame, 'config'):
                frame.config(bg=color)
            for child in frame.winfo_children():
                if isinstance(child, (tk.Frame, tk.Label)):
                    self._update_frame_bg(child, color)
        except Exception:
            pass

    def _move_selected(self, delta: int):
        """Move selected gallery item up/down by delta (±1) using keyboard."""
        if self._selected_index is None:
            return 'break'
        i = self._selected_index
        j = i + delta
        if j < 0 or j >= len(self._gallery_order):
            return 'break'
        # Swap items
        self._gallery_order[i], self._gallery_order[j] = self._gallery_order[j], self._gallery_order[i]
        self._selected_index = j
        self._save_gallery_manifest()
        self._build_gallery()
        # Scroll into view
        self.parent.after(50, self._scroll_selected_into_view)
        try:
            self.gallery_container.focus_set()
        except Exception:
            pass
        return 'break'
    
    def _on_delete_key(self, event):
        """Delete key pressed in gallery - confirm and delete selected item."""
        if self._selected_index is None:
            return 'break'
        fn = self._gallery_order[self._selected_index]
        if (Messagebox.yesno(title="Borrar miniatura", message=f"¿Desea borrar la miniatura '{fn}'?", parent=self.root) if Messagebox else messagebox.askyesno("Borrar miniatura", f"¿Desea borrar la miniatura '{fn}'?", parent=self.root)):
            try:
                (self.output_dir / fn).unlink(missing_ok=True)
                self._thumb_cache.pop(fn, None)
                self._gallery_order.pop(self._selected_index)
                if self._selected_index >= len(self._gallery_order):
                    self._selected_index = len(self._gallery_order) - 1 if self._gallery_order else None
                self._save_gallery_manifest()
                self._build_gallery()
            except Exception as e:
                if Messagebox:
                    Messagebox.show_error(title="Borrado", message=f"No se pudo borrar: {e}", parent=self.root)
                else:
                    messagebox.showerror("Borrado", f"No se pudo borrar: {e}", parent=self.root)
        try:
            self.gallery_container.focus_set()
        except Exception:
            pass
        return 'break'

    def _move_selected(self, delta: int):
        """Move selected gallery item up/down by delta (±1) using keyboard."""
        if self._selected_index is None:
            return 'break'
        i = self._selected_index
        j = i + delta
        if j < 0 or j >= len(self._gallery_order):
            return 'break'
        # Swap items
        self._gallery_order[i], self._gallery_order[j] = self._gallery_order[j], self._gallery_order[i]
        self._selected_index = j
        self._save_gallery_manifest()
        self._build_gallery()
        # Scroll into view
        self.parent.after(50, self._scroll_selected_into_view)
        try:
            self.gallery_container.focus_set()
        except Exception:
            pass
        return 'break'

    def _on_delete_key(self, event):
        """Delete key pressed in gallery - confirm and delete selected item."""
        if self._selected_index is None:
            return 'break'
        fn = self._gallery_order[self._selected_index]
        if (Messagebox.yesno(title="Borrar miniatura", message=f"¿Desea borrar la miniatura '{fn}'?", parent=self.root) if Messagebox else messagebox.askyesno("Borrar miniatura", f"¿Desea borrar la miniatura '{fn}'?", parent=self.root)):
            try:
                (self.output_dir / fn).unlink(missing_ok=True)
                self._thumb_cache.pop(fn, None)
                self._gallery_order.pop(self._selected_index)
                if self._selected_index >= len(self._gallery_order):
                    self._selected_index = len(self._gallery_order) - 1 if self._gallery_order else None
                self._save_gallery_manifest()
                self._build_gallery()
            except Exception as e:
                if Messagebox:
                    Messagebox.show_error(title="Borrado", message=f"No se pudo borrar: {e}", parent=self.root)
                else:
                    messagebox.showerror("Borrado", f"No se pudo borrar: {e}", parent=self.root)
        try:
            self.gallery_container.focus_set()
        except Exception:
            pass
        return 'break'
    
    def detect_cameras(self, max_index: int = 8) -> List[tuple]:
        """Detect available cameras and return list of (index, name, max_width, max_height) tuples"""
        if cv2 is None:
            return []
        
        found = []
        camera_names = {}
        
        # Try to get camera names on Windows
        if hasattr(cv2, 'CAP_DSHOW'):
            try:
                import subprocess
                result = subprocess.run(
                    ['powershell', '-Command', 
                     "Get-PnpDevice -Class Camera | Where-Object {$_.Status -eq 'OK'} | Select-Object -ExpandProperty FriendlyName"],
                    capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    names = [n.strip() for n in result.stdout.strip().split('\n') if n.strip()]
                    # Limit max_index to actual number of cameras detected + 1
                    if names:
                        max_index = min(max_index, len(names) + 1)
                    for idx, name in enumerate(names[:max_index]):
                        camera_names[idx] = name
            except Exception:
                pass
        
        # Test cameras with early exit if consecutive failures
        consecutive_failures = 0
        max_consecutive_failures = 2  # Stop after 2 consecutive failed attempts
        
        for i in range(max_index):
            # Try default backend first (auto-selection)
            cap = cv2.VideoCapture(i)
            if not cap.isOpened() and hasattr(cv2, 'CAP_DSHOW'):
                # Fallback to DSHOW if default fails
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                consecutive_failures = 0  # Reset counter on success
                try:
                    # Test resolutions
                    max_w, max_h = 640, 480
                    test_resolutions = [
                        (1920, 1080),  # Full HD
                        (1280, 720),   # HD
                        (640, 480)     # VGA
                    ]
                    
                    for test_w, test_h in test_resolutions:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, test_w)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, test_h)
                        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        if actual_w >= test_w * 0.9 and actual_h >= test_h * 0.9:
                            max_w, max_h = actual_w, actual_h
                            break
                    
                    name = camera_names.get(i, f"Cámara {i}")
                    found.append((i, f"{name} ({max_w}x{max_h})", max_w, max_h))
                except Exception:
                    name = camera_names.get(i, f"Cámara {i}")
                    found.append((i, name, 640, 480))
                finally:
                    cap.release()
            else:
                # Camera not opened, increment failure counter
                consecutive_failures += 1
                try:
                    cap.release()
                except Exception:
                    pass
                # Early exit if too many consecutive failures
                if consecutive_failures >= max_consecutive_failures:
                    break
        
        return found
    
    def refresh_cameras(self):
        """Refresh camera list"""
        cams = self.detect_cameras()
        self.camera_map = {}
        self.camera_resolutions = {}
        
        if not cams:
            self.cmb_cam["values"] = ["(sin cámara)"]
            self.cmb_cam.current(0)
        else:
            names = [name for idx, name, w, h in cams]
            self.camera_map = {name: idx for idx, name, w, h in cams}
            self.camera_resolutions = {name: (w, h) for idx, name, w, h in cams}
            self.cmb_cam["values"] = names
            self.cmb_cam.current(0)
            
            # Auto-connect to first camera
            self.parent.after(500, self.open_camera)
    
    def open_camera(self):
        """Open and start camera preview"""
        self.close_camera()
        
        if cv2 is None:
            if Messagebox:
                Messagebox.show_warning(title="Cámara", message="OpenCV no está instalado", parent=self.root)
            else:
                messagebox.showwarning("Cámara", "OpenCV no está instalado", parent=self.root)
            return
        
        sel = self.cmb_cam.get()
        if sel not in self.camera_map:
            if Messagebox:
                Messagebox.show_error(title="Cámara", message="Seleccione una cámara válida", parent=self.root)
            else:
                messagebox.showerror("Cámara", "Seleccione una cámara válida", parent=self.root)
            return
        
        idx = self.camera_map[sel]
        max_w, max_h = self.camera_resolutions.get(sel, (1920, 1080))
        
        # Try default backend first (auto-selection)
        self.cap = cv2.VideoCapture(idx)
        if not self.cap.isOpened() and hasattr(cv2, 'CAP_DSHOW'):
            # Fallback to DSHOW if default fails
            self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        
        if not self.cap.isOpened():
            if Messagebox:
                Messagebox.show_error(title="Cámara", message=f"No se pudo abrir la cámara {idx}", parent=self.root)
            else:
                messagebox.showerror("Cámara", f"No se pudo abrir la cámara {idx}", parent=self.root)
            self.cap = None
            return
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, max_w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, max_h)
        
        # Clear "camera off" message
        self.canvas.delete("camera_off_message")
        
        self.current_camera_idx = idx
        self._preview_running = True
        self._start_preview()
    
    def close_camera(self):
        """Stop camera preview and release"""
        self._preview_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self._show_camera_off_screen()
    
    def _start_preview(self):
        """Start preview thread"""
        def preview_loop():
            while self._preview_running and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Apply adjustments and detect page (throttled)
                    adjusted, contour = self._apply_adjustments(frame_rgb)
                    
                    # Stabilize contour detection
                    if contour is not None:
                        self._stabilize_contour(contour)
                    
                    # Detect book split line if in book mode
                    if self.book_mode.get() and self._stable_contour is not None:
                        self._detect_book_split_line(adjusted, self._stable_contour)
                    else:
                        self._book_split_line = None
                    
                    # Draw overlays on frame
                    display_frame = self._draw_overlays(adjusted)
                    
                    # Store frame in buffer (thread-safe)
                    with self._frame_lock:
                        self._current_frame = display_frame
                    
                    # Update detection status (less frequently)
                    if self._detection_frame_counter % 10 == 0:
                        self.parent.after(0, lambda: self._update_detection_status(self._stable_contour))
                    
                    self._detection_frame_counter += 1
                
                time.sleep(0.033)  # ~30 fps
        
        threading.Thread(target=preview_loop, daemon=True).start()
        
        # Start UI update loop
        self._update_canvas_loop()
    
    def _update_canvas_loop(self):
        """Update canvas from buffer (runs in main thread)"""
        if not self._preview_running:
            return
        
        # Get frame from buffer
        with self._frame_lock:
            frame = self._current_frame
        
        # Update canvas if frame available
        if frame is not None:
            self._render_to_canvas(frame)
        
        # Schedule next update
        self.parent.after(33, self._update_canvas_loop)  # ~30 fps
    
    def _stabilize_contour(self, contour):
        """Stabilize contour detection using history"""
        if cv2 is None or np is None:
            self._stable_contour = contour
            return
        
        # Add to history
        self._contour_history.append(contour)
        
        # Keep only last 5 detections
        if len(self._contour_history) > 5:
            self._contour_history.pop(0)
        
        # Average the contours
        if len(self._contour_history) >= 3:
            avg_contour = np.mean(self._contour_history, axis=0).astype(np.int32)
            self._stable_contour = avg_contour
        else:
            self._stable_contour = contour
    
    def _detect_book_split_line(self, img, contour):
        """Detect split line for book mode; not constrained to vertical. Stores either (x1,y1,x2,y2) or int x."""
        if cv2 is None or np is None:
            return

        try:
            # Get bounding box of contour
            x, y, w, h = cv2.boundingRect(contour)

            # Extract book region
            roi = img[y:y+h, x:x+w]
            gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(gray, 50, 150)

            # Hough transform for line segments
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=int(0.5*h), maxLineGap=20)
            best = None
            best_len = 0
            if lines is not None:
                for l in lines[:, 0, :]:
                    x1, y1, x2, y2 = l.tolist()
                    # Compute angle relative to vertical
                    dx, dy = x2 - x1, y2 - y1
                    length = (dx*dx + dy*dy) ** 0.5
                    if length < best_len:
                        # We track only longest
                        pass
                    # Avoid near-horizontal (|angle from vertical| < ~30°)
                    angle = abs(np.degrees(np.arctan2(dy, dx)))
                    angle_from_vertical = abs(90 - angle)
                    if angle_from_vertical > 30:
                        continue
                    # Must pass through middle band of ROI width
                    mid_x = (x1 + x2) / 2.0
                    if not (w * 0.25 <= mid_x <= w * 0.75):
                        continue
                    if length > best_len:
                        best_len = length
                        best = (x + x1, y + y1, x + x2, y + y2)

            if best is not None:
                self._book_split_line = best
                return

            # Fallback to darkest vertical line in center region
            vertical_sum = np.sum(gray, axis=0)
            if len(vertical_sum) > 0:
                start = int(w * 0.3)
                end = int(w * 0.7)
                mid_region = vertical_sum[start:end]
                if len(mid_region) > 0:
                    local_min = int(np.argmin(mid_region))
                    split_x = x + start + local_min
                    self._book_split_line = split_x
                    return
            # Fallback to center of ROI
            self._book_split_line = x + w // 2
        except Exception as e:
            print(f"Error detecting book split: {e}")
            self._book_split_line = img.shape[1] // 2
    
    def _draw_overlays(self, img):
        """Draw all overlays on frame (contours, calibration, book split)"""
        if np is None:
            return img
        
        # Make a copy to draw on
        display_img = img.copy()
        
        # Draw detected page contour
        if self._stable_contour is not None and self.detect_page.get():
            self._draw_contour_on_frame(display_img, self._stable_contour)
        
        # Draw book split line
        if self._book_split_line is not None and self.book_mode.get():
            self._draw_book_split_line(display_img, self._book_split_line)
        
        # Draw calibration area
        if self.calibration_area:
            self._draw_calibration_on_frame(display_img)
        
        return display_img
    
    def _safe_canvas_delete(self, tag):
        """Safely delete canvas items, ignoring if canvas was destroyed"""
        try:
            if hasattr(self, 'canvas') and self.canvas.winfo_exists():
                self.canvas.delete(tag)
        except Exception:
            pass
    
    def _update_detection_status(self, contour):
        """Update detection status indicator"""
        try:
            # Verificar que el widget todavía existe
            if not hasattr(self, 'detection_status_label') or not self.detection_status_label.winfo_exists():
                return
            
            if not self.detect_page.get():
                self.detection_status_label.config(text="", foreground="gray")
            elif contour is not None:
                self.detection_status_label.config(text="✓ Página detectada", foreground="green")
            else:
                self.detection_status_label.config(text="⚠ Sin detección", foreground="orange")
        except Exception:
            # Widget ya destruido, ignorar
            pass
    
    def _apply_adjustments(self, img_array):
        """Apply brightness/contrast adjustments and detect page if enabled"""
        if Image is None:
            return img_array, None
        
        try:
            pil_img = Image.fromarray(img_array)
            
            # Brightness
            brightness = self.s_brightness.get()
            if abs(brightness - 1.0) > 0.01:
                enhancer = ImageEnhance.Brightness(pil_img)
                pil_img = enhancer.enhance(brightness)
            
            # Contrast
            contrast = self.s_contrast.get()
            if abs(contrast - 1.0) > 0.01:
                enhancer = ImageEnhance.Contrast(pil_img)
                pil_img = enhancer.enhance(contrast)
            
            adjusted = np.array(pil_img) if np else img_array
            
            # Detect page contour if enabled (only every 5 frames to reduce CPU load)
            contour = None
            if self.detect_page.get() and cv2 is not None and np is not None:
                if self._detection_frame_counter % 5 == 0:
                    contour = self._detect_page_contour(adjusted)
            
            return adjusted, contour
        except Exception:
            return img_array, None
    
    def _detect_page_contour(self, img):
        """Detect page contour using edge detection"""
        if cv2 is None or np is None:
            return None
        
        try:
            # Resize image for faster processing (scale down to max 800px width)
            h, w = img.shape[:2]
            scale = 1.0
            if w > 800:
                scale = 800.0 / w
                new_w = 800
                new_h = int(h * scale)
                img_small = cv2.resize(img, (new_w, new_h))
            else:
                img_small = img
            
            # Convert to grayscale
            gray = cv2.cvtColor(img_small, cv2.COLOR_RGB2GRAY)
            
            # Use simple blur instead of bilateral (faster)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)
            
            # Dilate edges to close gaps
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Filter contours by area (must be at least 10% of image)
            img_area = img_small.shape[0] * img_small.shape[1]
            min_area = img_area * 0.1
            
            valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
            
            if not valid_contours:
                return None
            
            # Find largest valid contour
            largest = max(valid_contours, key=cv2.contourArea)
            
            # Approximate to polygon
            peri = cv2.arcLength(largest, True)
            approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
            
            # We want a quadrilateral (4 corners)
            if len(approx) == 4:
                # Scale back to original size
                result = approx.reshape(4, 2)
                if scale != 1.0:
                    result = (result / scale).astype(np.int32)
                return result
            
            # If not exactly 4, try with different epsilon
            for epsilon_mult in [0.01, 0.03, 0.04]:
                approx = cv2.approxPolyDP(largest, epsilon_mult * peri, True)
                if len(approx) == 4:
                    result = approx.reshape(4, 2)
                    if scale != 1.0:
                        result = (result / scale).astype(np.int32)
                    return result
            
            return None
        except Exception as e:
            print(f"Error detecting page: {e}")
            return None
    
    def _draw_contour_on_frame(self, img, contour):
        """Draw detected contour on frame"""
        if cv2 is None or np is None:
            return
        
        try:
            # Use cv2 to draw directly on the image
            # Convert points to proper format for cv2.polylines
            points = contour.reshape((-1, 1, 2)).astype(np.int32)
            # Draw green polygon
            cv2.polylines(img, [points], isClosed=True, color=(0, 255, 0), thickness=3)
            # Draw corner circles for better visibility
            for point in contour:
                x, y = int(point[0]), int(point[1])
                cv2.circle(img, (x, y), 8, (0, 255, 0), -1)
        except Exception as e:
            print(f"Error drawing contour: {e}")
    
    def _draw_calibration_on_frame(self, img):
        """Draw calibration area on frame"""
        if cv2 is None or np is None:
            return
        
        try:
            h, w = img.shape[:2]
            tl = self.calibration_area['tl']
            br = self.calibration_area['br']
            
            # Convert normalized coords to pixel coords
            x1 = int(tl[0] * w)
            y1 = int(tl[1] * h)
            x2 = int(br[0] * w)
            y2 = int(br[1] * h)
            
            # Draw red rectangle using cv2
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
            # Draw corner markers
            marker_size = 10
            # Top-left
            cv2.line(img, (x1, y1), (x1 + marker_size, y1), (255, 0, 0), 3)
            cv2.line(img, (x1, y1), (x1, y1 + marker_size), (255, 0, 0), 3)
            # Top-right
            cv2.line(img, (x2, y1), (x2 - marker_size, y1), (255, 0, 0), 3)
            cv2.line(img, (x2, y1), (x2, y1 + marker_size), (255, 0, 0), 3)
            # Bottom-right
            cv2.line(img, (x2, y2), (x2 - marker_size, y2), (255, 0, 0), 3)
            cv2.line(img, (x2, y2), (x2, y2 - marker_size), (255, 0, 0), 3)
            # Bottom-left
            cv2.line(img, (x1, y2), (x1 + marker_size, y2), (255, 0, 0), 3)
            cv2.line(img, (x1, y2), (x1, y2 - marker_size), (255, 0, 0), 3)
        except Exception as e:
            print(f"Error drawing calibration: {e}")
    
    def _draw_book_split_line(self, img, split):
        """Draw split line (vertical or slanted)."""
        if cv2 is None:
            return

        try:
            h = img.shape[0]
            if isinstance(split, int):
                x = split
                cv2.line(img, (x, 0), (x, h), (0, 255, 255), 3)
                label_pos = (max(0, x - 40), 30)
            else:
                x1, y1, x2, y2 = map(int, split)
                cv2.line(img, (x1, y1), (x2, y2), (0, 255, 255), 3)
                label_pos = (min(x1, x2), max(0, min(y1, y2) - 10))

            cv2.putText(
                img,
                "DIVISION",
                label_pos,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2
            )
        except Exception as e:
            print(f"Error drawing split line: {e}")
    
    def _render_to_canvas(self, img_array):
        """Render frame to canvas (called from main thread)"""
        if Image is None or ImageTk is None:
            return
        
        try:
            # Clear any "camera off" message
            self.canvas.delete("camera_off_message")
            
            # Convert to PIL and resize to fit canvas
            pil_img = Image.fromarray(img_array)
            cw = self.canvas.winfo_width() or 960
            ch = self.canvas.winfo_height() or 720
            
            # Calculate scaling to fit
            img_w, img_h = pil_img.size
            scale = min(cw / img_w, ch / img_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Create PhotoImage
            self._tkimg = ImageTk.PhotoImage(pil_img)
            
            # Center on canvas
            x = (cw - new_w) // 2
            y = (ch - new_h) // 2
            
            # Update or create image item
            if self._image_item is None or not self.canvas.coords(self._image_item):
                # Create new image item
                self._image_item = self.canvas.create_image(x, y, anchor="nw", image=self._tkimg)
            else:
                # Update existing image item
                self.canvas.coords(self._image_item, x, y)
                self.canvas.itemconfig(self._image_item, image=self._tkimg)
        except Exception:
            pass
    
    def _show_camera_off_screen(self):
        """Show 'CAMERA OFF' message"""
        self.canvas.delete("all")
        self._image_item = None
        cw = self.canvas.winfo_width() or 960
        ch = self.canvas.winfo_height() or 720
        self.canvas.create_text(
            cw // 2,
            ch // 2,
            text="CÁMARA DESCONECTADA",
            fill="#666666",
            font=("Open Sans", 20, "bold"),
            tags="camera_off_message"
        )
    
    def capture_image(self):
        """Capture current frame and save to output directory"""
        if self.cap is None or cv2 is None:
            if Messagebox:
                Messagebox.show_warning(title="Captura", message="Cámara no disponible", parent=self.root)
            else:
                messagebox.showwarning("Captura", "Cámara no disponible", parent=self.root)
            return
        
        ret, frame = self.cap.read()
        if not ret:
            if Messagebox:
                Messagebox.show_error(title="Captura", message="No se pudo capturar imagen", parent=self.root)
            else:
                messagebox.showerror("Captura", "No se pudo capturar imagen", parent=self.root)
            return
        
        # Convert to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Apply adjustments
        adjusted, _ = self._apply_adjustments(frame_rgb)
        
        # Apply calibration crop if set
        if self.calibration_area and np is not None:
            h, w = adjusted.shape[:2]
            tl = self.calibration_area['tl']
            br = self.calibration_area['br']
            x1, y1 = int(tl[0] * w), int(tl[1] * h)
            x2, y2 = int(br[0] * w), int(br[1] * h)
            adjusted = adjusted[y1:y2, x1:x2]
        
        # Apply perspective transform if page detected (use stable contour)
        if self.detect_page.get() and self._stable_contour is not None and cv2 is not None and np is not None:
            adjusted = self._apply_perspective_transform(adjusted, self._stable_contour)
        
        # Split in book mode (detect split on the final adjusted image for better accuracy)
        if self.book_mode.get() and np is not None:
            split = self._detect_split_on_image(adjusted)
            self._save_book_pages(adjusted, split)
        else:
            self._save_single_page(adjusted)

    def _detect_split_on_image(self, img):
        """Detect split line on a given image (post-transform). Returns tuple(x1,y1,x2,y2) or int x."""
        if cv2 is None or np is None:
            return img.shape[1] // 2
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(gray, 50, 150)
            h, w = img.shape[:2]
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=int(0.5*h), maxLineGap=20)
            best = None
            best_len = 0
            if lines is not None:
                for l in lines[:, 0, :]:
                    x1, y1, x2, y2 = l.tolist()
                    dx, dy = x2 - x1, y2 - y1
                    length = (dx*dx + dy*dy) ** 0.5
                    angle = abs(np.degrees(np.arctan2(dy, dx)))
                    angle_from_vertical = abs(90 - angle)
                    if angle_from_vertical > 30:
                        continue
                    mid_x = (x1 + x2) / 2.0
                    if not (w * 0.25 <= mid_x <= w * 0.75):
                        continue
                    if length > best_len:
                        best_len = length
                        best = (x1, y1, x2, y2)
            if best is not None:
                return best
            # Fallback to darkest vertical column
            vertical_sum = np.sum(gray, axis=0)
            if len(vertical_sum) > 0:
                start = int(w * 0.3)
                end = int(w * 0.7)
                mid_region = vertical_sum[start:end]
                if len(mid_region) > 0:
                    local_min = int(np.argmin(mid_region))
                    return start + local_min
            return w // 2
        except Exception:
            return img.shape[1] // 2
    
    def _apply_perspective_transform(self, img, contour):
        """Apply perspective transform to straighten page"""
        if cv2 is None or np is None:
            return img
        
        try:
            # Order points: top-left, top-right, bottom-right, bottom-left
            rect = np.zeros((4, 2), dtype="float32")
            s = contour.sum(axis=1)
            rect[0] = contour[np.argmin(s)]
            rect[2] = contour[np.argmax(s)]
            diff = np.diff(contour, axis=1)
            rect[1] = contour[np.argmin(diff)]
            rect[3] = contour[np.argmax(diff)]
            
            # Compute width and height of new image
            (tl, tr, br, bl) = rect
            widthA = np.linalg.norm(br - bl)
            widthB = np.linalg.norm(tr - tl)
            maxWidth = max(int(widthA), int(widthB))
            
            heightA = np.linalg.norm(tr - br)
            heightB = np.linalg.norm(tl - bl)
            maxHeight = max(int(heightA), int(heightB))
            
            # Destination points
            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")
            
            # Compute perspective transform
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))
            
            return warped
        except Exception:
            return img
    
    def _save_single_page(self, img):
        """Save single page image"""
        if Image is None:
            return
        
        try:
            self._frame_counter += 1
            filename = f"scan_{self._frame_counter:04d}.jpg"
            output_path = self.output_dir / filename
            
            # Removed white border on save; resize only
            resized = self._resize_page(img)
            pil_img = Image.fromarray(resized)
            pil_img.save(output_path, "JPEG", quality=95)
            
            # Update gallery
            self._gallery_order.append(filename)
            self._selected_index = len(self._gallery_order) - 1
            self._save_gallery_manifest()
            self._build_gallery()
            # Scroll to new item after a short delay to ensure layout is ready
            self.parent.after(50, self._scroll_selected_into_view)

            # Show confirmation
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                30,
                text=f"✓ Guardado: {filename}",
                fill="#00ff00",
                font=("Open Sans", 14, "bold"),
                tags="toast"
            )
            self.parent.after(2000, lambda: self._safe_canvas_delete("toast"))
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(title="Error", message=f"No se pudo guardar: {e}", parent=self.root)
            else:
                messagebox.showerror("Error", f"No se pudo guardar: {e}", parent=self.root)
    
    def _save_book_pages(self, img, split=None):
        """Split and save left/right pages from book"""
        if Image is None or np is None:
            return
        
        try:
            h, w = img.shape[:2]
            
            # Determine split position
            use_split = split if split is not None else self._book_split_line
            if isinstance(use_split, tuple):
                # Exact oblique split: use half-plane masks
                x1, y1, x2, y2 = use_split
                # Reject degenerate lines
                if x1 == x2 and y1 == y2:
                    mid = w // 2
                    left_page = img[:, :mid]
                    right_page = img[:, mid:]
                else:
                    left_page, right_page = self._split_image_by_line(img, x1, y1, x2, y2)
            else:
                # Vertical split (int or fallback)
                mid = int(use_split) if isinstance(use_split, int) else w // 2
                left_page = img[:, :mid]
                right_page = img[:, mid:]
            
            self._frame_counter += 1
            
            # Removed white borders on save; apply resize if configured
            left_page = self._resize_page(left_page)
            right_page = self._resize_page(right_page)

            # Save left page
            left_filename = f"scan_{self._frame_counter:04d}_L.jpg"
            left_path = self.output_dir / left_filename
            Image.fromarray(left_page).save(left_path, "JPEG", quality=95)
            
            # Save right page
            right_filename = f"scan_{self._frame_counter:04d}_R.jpg"
            right_path = self.output_dir / right_filename
            Image.fromarray(right_page).save(right_path, "JPEG", quality=95)
            
            # Update gallery (append in order L then R)
            self._gallery_order.extend([left_filename, right_filename])
            self._selected_index = len(self._gallery_order) - 1
            self._save_gallery_manifest()
            self._build_gallery()
            self.parent.after(50, self._scroll_selected_into_view)

            # Show confirmation
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                30,
                text=f"✓ Guardado: {left_filename}, {right_filename}",
                fill="#00ff00",
                font=("Open Sans", 14, "bold"),
                tags="toast"
            )
            self.parent.after(2000, lambda: self._safe_canvas_delete("toast"))
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(title="Error", message=f"No se pudo guardar: {e}", parent=self.root)
            else:
                messagebox.showerror("Error", f"No se pudo guardar: {e}", parent=self.root)

    def _split_image_by_line(self, img, x1, y1, x2, y2):
        """Split image into two parts along the infinite line passing through (x1,y1)-(x2,y2).
        Returns (left_part, right_part) where 'left' has smaller centroid x.
        Output parts are rectangular crops around the non-zero masked regions.
        """
        try:
            h, w = img.shape[:2]
            # Create coordinate grid
            yy, xx = np.mgrid[0:h, 0:w]
            # Signed area (point vs line): (x - x1)*(y2 - y1) - (y - y1)*(x2 - x1)
            side = (xx - x1) * (y2 - y1) - (yy - y1) * (x2 - x1)
            mask1 = (side <= 0).astype(np.uint8)
            mask2 = (side > 0).astype(np.uint8)

            # Fill background with white instead of black
            part1 = np.full_like(img, 255)
            part2 = np.full_like(img, 255)
            part1[mask1 > 0] = img[mask1 > 0]
            part2[mask2 > 0] = img[mask2 > 0]

            def crop_nonzero(part, mask):
                ys, xs = np.where(mask > 0)
                if len(xs) == 0 or len(ys) == 0:
                    return None, None
                x_min, x_max = xs.min(), xs.max()
                y_min, y_max = ys.min(), ys.max()
                cropped = part[y_min:y_max+1, x_min:x_max+1]
                cx = (x_min + x_max) / 2.0
                return cropped, cx

            c1, cx1 = crop_nonzero(part1, mask1)
            c2, cx2 = crop_nonzero(part2, mask2)

            # Fallback if one side is empty
            if c1 is None or c2 is None:
                mid = w // 2
                return img[:, :mid], img[:, mid:]

            # Order by centroid x (left then right)
            if cx1 <= cx2:
                return c1, c2
            else:
                return c2, c1
        except Exception:
            mid = img.shape[1] // 2
            return img[:, :mid], img[:, mid:]

    def _add_white_border(self, img):
        """Add a white border around the image based on page_margin (% of max dimension)."""
        if cv2 is None or np is None:
            return img
        try:
            ratio = 0.0
            try:
                ratio = max(0.0, min(0.2, float(self.page_margin.get()) / 100.0))
            except Exception:
                ratio = 0.0
            if ratio <= 0.0:
                return img
            h, w = img.shape[:2]
            m = int(max(h, w) * ratio)
            if m <= 0:
                return img
            return cv2.copyMakeBorder(img, m, m, m, m, cv2.BORDER_CONSTANT, value=[255, 255, 255])
        except Exception:
            return img

    def _resize_page(self, img):
        """Resize page to target width/height if enabled. 0 means auto for that dimension."""
        if cv2 is None or np is None:
            return img
        try:
            if not self.resize_enabled.get():
                return img
            tw = max(0, int(self.target_width.get()))
            th = max(0, int(self.target_height.get()))
            h, w = img.shape[:2]
            if tw <= 0 and th <= 0:
                return img
            if tw > 0 and th > 0:
                new_w, new_h = tw, th
            elif tw > 0:
                # preserve aspect from width
                new_w = tw
                new_h = max(1, int(h * (tw / w)))
            else:
                # th > 0, preserve aspect from height
                new_h = th
                new_w = max(1, int(w * (th / h)))
            return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        except Exception:
            return img

    def _toggle_resize_controls(self):
        """Enable/disable resize controls based on the checkbox."""
        try:
            is_on = bool(self.resize_enabled.get())
            state = 'normal' if is_on else 'disabled'
            self.spin_width.config(state=state)
            self.spin_height.config(state=state)
            if is_on:
                # If no size set yet, set default width of 1600
                try:
                    tw = int(self.target_width.get())
                    th = int(self.target_height.get())
                except Exception:
                    tw, th = 0, 0
                if tw == 0 and th == 0:
                    self.target_width.set(1600)
        except Exception:
            pass
    
    def open_calibration(self):
        """Open calibration dialog to set capture area"""
        if self.cap is None or cv2 is None:
            if Messagebox:
                Messagebox.show_warning(title="Calibración", message="Cámara no disponible", parent=self.root)
            else:
                messagebox.showwarning("Calibración", "Cámara no disponible", parent=self.root)
            return
        
        # Capture current frame
        ret, frame = self.cap.read()
        if not ret:
            if Messagebox:
                Messagebox.show_error(title="Calibración", message="No se pudo capturar imagen", parent=self.root)
            else:
                messagebox.showerror("Calibración", "No se pudo capturar imagen", parent=self.root)
            return
        
        # Create modal dialog
        dialog = tk.Toplevel(self.parent)
        try:
            center_to_parent(dialog, self.parent)
        except Exception:
            pass
        dialog.title("Calibrar Área de Captura")
        dialog.geometry("800x650")
        dialog.transient(self.parent)  # Make it a child window
        dialog.grab_set()  # Make it modal
        
        # Convert frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        adjusted, _ = self._apply_adjustments(frame_rgb)
        
        # Instructions at top
        instr_label = tk.Label(
            dialog,
            text="Arrastra el mouse para dibujar el área de captura",
            font=("Open Sans", 10),
            pady=10
        )
        instr_label.pack()
        
        # Canvas for drawing
        canvas = tk.Canvas(dialog, bg="#000000")
        canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Display image
        pil_img = Image.fromarray(adjusted)
        canvas_w = 780
        canvas_h = 500
        pil_img.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(pil_img)
        img_w, img_h = pil_img.size
        
        # Center image
        x_offset = (canvas_w - img_w) // 2
        y_offset = (canvas_h - img_h) // 2
        canvas.create_image(x_offset, y_offset, anchor="nw", image=photo)
        
        # Store reference
        canvas.photo = photo
        canvas.img_size = (img_w, img_h)
        canvas.offset = (x_offset, y_offset)
        canvas.orig_size = adjusted.shape[:2][::-1]  # (w, h)
        
        # Drawing state
        rect_start = [None, None]
        rect_id = [None]
        
        def on_mouse_down(event):
            rect_start[0] = event.x
            rect_start[1] = event.y
        
        def on_mouse_move(event):
            if rect_start[0] is not None:
                if rect_id[0]:
                    canvas.delete(rect_id[0])
                rect_id[0] = canvas.create_rectangle(
                    rect_start[0], rect_start[1],
                    event.x, event.y,
                    outline="#ff0000", width=2
                )
        
        def on_mouse_up(event):
            rect_start[0] = None
            rect_start[1] = None
        
        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_move)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        
        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def save_calibration():
            if rect_id[0]:
                coords = canvas.coords(rect_id[0])
                x1, y1, x2, y2 = coords
                
                # Convert to image coordinates
                x1 -= canvas.offset[0]
                y1 -= canvas.offset[1]
                x2 -= canvas.offset[0]
                y2 -= canvas.offset[1]
                
                # Normalize to original image size
                orig_w, orig_h = canvas.orig_size
                img_w, img_h = canvas.img_size
                
                x1_norm = (x1 / img_w)
                y1_norm = (y1 / img_h)
                x2_norm = (x2 / img_w)
                y2_norm = (y2 / img_h)
                
                # Clamp to [0, 1]
                x1_norm = max(0, min(1, x1_norm))
                y1_norm = max(0, min(1, y1_norm))
                x2_norm = max(0, min(1, x2_norm))
                y2_norm = max(0, min(1, y2_norm))
                
                self.calibration_area = {
                    'tl': (x1_norm, y1_norm),
                    'br': (x2_norm, y2_norm)
                }
                
                if Messagebox:
                    Messagebox.show_info(title="Calibración", message="Área de captura guardada", parent=self.root)
                else:
                    messagebox.showinfo("Calibración", "Área de captura guardada", parent=self.root)
                dialog.grab_release()
                dialog.destroy()
            else:
                if Messagebox:
                    Messagebox.show_warning(title="Calibración", message="Dibuja un rectángulo primero", parent=self.root)
                else:
                    messagebox.showwarning("Calibración", "Dibuja un rectángulo primero", parent=self.root)
        
        def cancel():
            dialog.grab_release()
            dialog.destroy()
        
        tk.Button(btn_frame, text="Guardar", command=save_calibration, width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancelar", command=cancel, width=12).pack(side="left", padx=5)
        
        # Center dialog on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def open_output_folder(self):
        """Open output directory in file explorer"""
        import subprocess
        import sys
        
        try:
            if sys.platform == "win32":
                subprocess.Popen(f'explorer "{self.output_dir}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.output_dir)])
            else:
                subprocess.Popen(["xdg-open", str(self.output_dir)])
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(title="Error", message=f"No se pudo abrir carpeta: {e}", parent=self.root)
            else:
                messagebox.showerror("Error", f"No se pudo abrir carpeta: {e}", parent=self.root)

    # --- Project integration ---
    def _select_project(self):
        """Small selector for project to direct captured images into its 'paginas' folder."""
        top = tk.Toplevel(self.parent)
        top.title("Seleccionar Proyecto")
        top.geometry("520x160")
        top.transient(self.parent)
        top.grab_set()
        try:
            center_to_parent(top, self.parent)
        except Exception:
            pass
        ttk.Label(top, text="Proyecto:").pack(anchor='w', padx=10, pady=(12,4))
        combo = ttk.Combobox(top, state='readonly', width=60)
        combo.pack(fill=tk.X, padx=10)
        base = app_config.get_root_dir()
        rows = db.list_projects(base)
        combo['values'] = [f"{r['id']} · {r['titulo']}" for r in rows]
        if rows:
            combo.current(0)
        btns = ttk.Frame(top); btns.pack(fill=tk.X, padx=10, pady=10)
        def _apply():
            if not rows or not combo.get():
                top.destroy(); return
            pid = int(combo.get().split('·',1)[0])
            row = next((r for r in rows if int(r['id'])==pid), None)
            if not row:
                top.destroy(); return
            self.current_project = row
            self._set_output_dir(Path(row['carpeta_raiz']) / 'paginas')
            top.destroy()
        ttk.Button(btns, text="Cancelar", command=top.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Usar", command=_apply).pack(side=tk.RIGHT, padx=6)

    def _create_project(self):
        """Open project editor to create a new project"""
        if open_metadata_manager:
            # Import EditorProyecto directly
            try:
                from gui.metadata_manager import EditorProyecto
                from utils import app_config
                base_path = app_config.get_root_dir()
                
                # Open project editor in create mode (project_id=None)
                def on_project_saved():
                    # Optionally refresh project list or perform other actions
                    pass
                
                EditorProyecto(self.parent, base_path=base_path, project_id=None, on_saved=on_project_saved)
            except Exception as e:
                print(f"Error opening project editor: {e}")
                # Fallback to opening metadata manager
                open_metadata_manager(self.parent, focus_tab='proyectos')

    def _set_output_dir(self, new_dir: Path):
        """Change output directory and reload gallery and prefs path."""
        try:
            self.output_dir = new_dir
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._prefs_path = self.output_dir / "_ui_prefs.json"
            # Reload gallery state
            self._gallery_order = []
            self._thumb_cache = {}
            self._load_gallery_manifest(); self._build_gallery()
        except Exception as e:
            print(f"Failed to set output dir: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        # Persist UI state on cleanup
        self._save_ui_prefs()
        self.close_camera()

    def _save_ui_prefs(self):
        """Save window geometry, paned sash, and UI options"""
        try:
            geom = None
            sash = None
            try:
                geom = self.parent.geometry()
            except Exception:
                geom = None
            try:
                if hasattr(self, "paned"):
                    sash = self.paned.sashpos(0)
            except Exception:
                sash = None
            # Persist extra UI options
            try:
                pm = float(self.page_margin.get())
            except Exception:
                pm = None
            try:
                resize = {
                    "enabled": bool(self.resize_enabled.get()),
                    "width": int(self.target_width.get()),
                    "height": int(self.target_height.get()),
                }
            except Exception:
                resize = None
            data = {
                "geometry": geom,
                "sash": sash,
                "page_margin": pm,
                "thumb_padding_color": self.thumb_pad_color,
                "resize": resize,
            }
            self._prefs_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            # Ignore save errors silently
            pass


class ScannerWindow(tk.Toplevel):
    """Standalone scanner window"""
    
    def __init__(self, master, project_dir: Optional[Path] = None):
        super().__init__(master)
        self.title("GeoDocs Scanner - Módulo de Captura")
        self.geometry("1000x850")
        
        # Set application icon
        self.set_icon()
        
        # Apply title bar theme automatically from ttkbootstrap
        apply_titlebar_theme(self)
        
        # Set output directory
        if project_dir:
            self.output_dir = project_dir / "paginas"
        else:
            # Default to root_dir/output_scan to keep behavior consistent but root-aware
            self.output_dir = app_config.get_root_dir() / "output_scan"
        
        # Create scanner
        self.scanner = CameraScanner(self, self.output_dir)
        
        # Restore geometry if saved
        try:
            geo = app_config.get_window_geometry("scanner")
            if isinstance(geo, str) and geo:
                self.geometry(geo)
        except Exception:
            pass

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    # Title bar theme handled via utils.theme_titlebar
    
    def set_icon(self):
        """Set application icon"""
        try:
            # Navigate from gui/scanner_module.py to assets/icons
            icon_dir = Path(__file__).resolve().parent.parent / "assets" / "icons"
            ico_path = icon_dir / "app.ico"
            png_path = icon_dir / "app.png"
            
            # Try Windows .ico first (preferred on Windows)
            if ico_path.exists():
                try:
                    self.iconbitmap(default=str(ico_path))
                    return
                except Exception:
                    pass
            
            # Cross-platform PNG fallback
            if png_path.exists():
                try:
                    icon_img = ImageTk.PhotoImage(Image.open(str(png_path)))
                    self.iconphoto(True, icon_img)
                    # Keep reference to prevent garbage collection
                    self._icon_img = icon_img
                except Exception:
                    pass
        except Exception:
            # Icon loading is optional; don't break app if it fails
            pass
    
    def on_close(self):
        """Clean up before closing"""
        try:
            app_config.set_window_geometry("scanner", self.geometry())
        except Exception:
            pass
        self.scanner.cleanup()
        self.destroy()


if __name__ == "__main__":
    # Test standalone
    root = tk.Tk()
    root.withdraw()
    win = ScannerWindow(root)
    root.mainloop()
