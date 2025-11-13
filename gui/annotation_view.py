#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
annotation_view.py — Annotation and OCR module
"""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
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
import json
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_manager import (
    list_projects,
    get_project,
    list_pages,
    sync_pages_from_folder,
    save_ocr_version,
    get_latest_ocr,
    list_ocr_versions,
    get_project_db_path,
)
from utils.ocr_tools import perform_ocr, preprocess_for_ocr
from utils.tts_manager import get_tts_manager
from utils.rest_api import get_api_client
from PIL import Image, ImageTk
from modules import spellcheck as sp
from modules import glossary_manager as gm
from modules import diff_engine as de
from utils.theme_titlebar import apply_titlebar_theme
from utils.window_utils import center_to_parent
from utils import app_config
try:
    from gui.metadata_manager import open_metadata_manager
except Exception:
    open_metadata_manager = None


class AnnotationWindow:
    """Annotation and OCR processing window"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("GeoDocs Scanner - Anotación y OCR")
        self.root.geometry("1400x900")
        
        # Apply title bar theme automatically from ttkbootstrap
        apply_titlebar_theme(self.root)
        # Restore geometry if saved
        try:
            geo = app_config.get_window_geometry("annotation")
            if isinstance(geo, str) and geo:
                self.root.geometry(geo)
        except Exception:
            pass
        # Save on close
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        except Exception:
            pass
        
        self.current_project = None
        self.current_page = None
        self.tts = get_tts_manager()
        
        self.create_ui()
        # If window geometry not restored, center over parent if available
        try:
            geo = app_config.get_window_geometry("annotation")
        except Exception:
            geo = None
        if not geo:
            try:
                center_to_parent(self.root, self.root.master if hasattr(self.root, 'master') else None)
            except Exception:
                pass
        self.load_projects()
    
    # Title bar theme handled via utils.theme_titlebar
    
    def create_ui(self):
        """Create the user interface"""
        # Top toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="Proyecto:").pack(side=tk.LEFT, padx=5)
        
        self.project_combo = ttk.Combobox(toolbar, width=40, state="readonly")
        self.project_combo.pack(side=tk.LEFT, padx=5)
        self.project_combo.bind('<<ComboboxSelected>>', self.on_project_selected)
        
        ttk.Button(
            toolbar,
            text="📂 Abrir Proyecto",
            command=self.load_projects
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            toolbar,
            text="✏️ Metadatos",
            command=self.edit_current_project
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            toolbar,
            text="⚙️ Tablas…",
            command=lambda: (open_metadata_manager(self.root, focus_tab='archivos') if open_metadata_manager else None)
        ).pack(side=tk.LEFT, padx=5)

        # Coordinates picker (browser-based interactive map)
        ttk.Button(
            toolbar,
            text="📍 Coordenadas",
            command=self.pick_coordinates
        ).pack(side=tk.LEFT, padx=5)
        
        self.lang_var = tk.StringVar(value="spa")
        ttk.Label(toolbar, text="Idioma:").pack(side=tk.LEFT, padx=(10,2))
        self.lang_combo = ttk.Combobox(toolbar, width=8, state="readonly", values=["spa","lat","eng"], textvariable=self.lang_var)
        self.lang_combo.pack(side=tk.LEFT)
        ttk.Button(toolbar, text="▶️ OCR", command=self.run_ocr).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar,
            text="🔊 Reproducir",
            command=self.play_tts
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar,
            text="⏹️ Detener",
            command=self.stop_tts
        ).pack(side=tk.LEFT, padx=5)
        
        # Main content area - PanedWindow for resizable sections
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel: Image viewer
        self.left_panel = ttk.Frame(paned)
        paned.add(self.left_panel, weight=1)
        
        ttk.Label(self.left_panel, text="📷 Vista de Imagen", font=("Open Sans", 11, "bold")).pack()
        
        self.image_canvas = tk.Canvas(self.left_panel, bg="#1a1a1a")
        self.image_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Image controls
        img_controls = ttk.Frame(self.left_panel)
        img_controls.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(img_controls, text="⬅️ Anterior", command=self.prev_page).pack(side=tk.LEFT, padx=2)
        ttk.Button(img_controls, text="➡️ Siguiente", command=self.next_page).pack(side=tk.LEFT, padx=2)
        ttk.Button(img_controls, text="🔄 Sincronizar páginas", command=self.sync_pages).pack(side=tk.LEFT, padx=8)
        
        self.page_label = ttk.Label(img_controls, text="Página: -/-")
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        # Right panel: OCR and annotations - Notebook with tabs
        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=1)
        
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: OCR Original
        ocr_original_tab = ttk.Frame(self.notebook)
        self.notebook.add(ocr_original_tab, text="📄 OCR Original")
        
        ttk.Label(ocr_original_tab, text="Texto reconocido (Tesseract):", 
                 font=("Open Sans", 10, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        self.text_ocr_original = scrolledtext.ScrolledText(
            ocr_original_tab,
            wrap=tk.WORD,
            font=("Courier New", 10),
            bg="#f5f5f5"
        )
        self.text_ocr_original.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ocr_info_frame = ttk.Frame(ocr_original_tab)
        ocr_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.lbl_ocr_info = ttk.Label(ocr_info_frame, text="", foreground="gray")
        self.lbl_ocr_info.pack(side=tk.LEFT)

        # OCR version picker
        ver_frame = ttk.Frame(ocr_original_tab)
        ver_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(ver_frame, text="Historial OCR:").pack(side=tk.LEFT)
        self.ocr_version_var = tk.StringVar()
        self.ocr_version_combo = ttk.Combobox(ver_frame, width=50, state="readonly", textvariable=self.ocr_version_var)
        self.ocr_version_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(ver_frame, text="Cargar", command=self.load_selected_ocr).pack(side=tk.LEFT, padx=2)
        ttk.Button(ver_frame, text="Cargar último", command=self.load_latest_ocr_for_page).pack(side=tk.LEFT, padx=2)
        ttk.Button(ver_frame, text="Historial detallado", command=self.open_version_history).pack(side=tk.LEFT, padx=2)
        
        # Tab 2: OCR Corregido
        ocr_corrected_tab = ttk.Frame(self.notebook)
        self.notebook.add(ocr_corrected_tab, text="✏️ OCR Corregido")
        
        ttk.Label(ocr_corrected_tab, text="Texto corregido manualmente:", 
                 font=("Open Sans", 10, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        self.text_ocr_corrected = scrolledtext.ScrolledText(
            ocr_corrected_tab,
            wrap=tk.WORD,
            font=("Courier New", 10)
        )
        self.text_ocr_corrected.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        corrected_buttons = ttk.Frame(ocr_corrected_tab)
        corrected_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            corrected_buttons,
            text="💾 Guardar Corrección",
            command=self.save_correction
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            corrected_buttons,
            text="✓ Revisar Ortografía",
            command=self.check_spelling
        ).pack(side=tk.LEFT, padx=2)
        
        # Tab 3: Comparador Visual
        comparator_tab = ttk.Frame(self.notebook)
        self.notebook.add(comparator_tab, text="🔍 Comparador")
        
        ttk.Label(comparator_tab, text="Comparador Imagen ↔ Texto (scroll sincronizado)", 
                 font=("Open Sans", 10, "bold")).pack(padx=5, pady=5)
        
        comp_paned = ttk.PanedWindow(comparator_tab, orient=tk.HORIZONTAL)
        comp_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: image
        comp_img_frame = ttk.Frame(comp_paned)
        comp_paned.add(comp_img_frame, weight=1)
        
        self.comp_canvas = tk.Canvas(comp_img_frame, bg="#1a1a1a")
        self.comp_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Right: text
        comp_text_frame = ttk.Frame(comp_paned)
        comp_paned.add(comp_text_frame, weight=1)
        
        self.comp_text = scrolledtext.ScrolledText(
            comp_text_frame,
            wrap=tk.WORD,
            font=("Courier New", 9)
        )
        self.comp_text.pack(fill=tk.BOTH, expand=True)
        # Sync comparator scroll with image canvas
        self.comp_text.configure(yscrollcommand=self._on_comp_text_scroll)
        self.comp_canvas.bind_all('<MouseWheel>', self._on_comp_canvas_wheel)
        
        # Tab 4: Anotaciones
        annotations_tab = ttk.Frame(self.notebook)
        self.notebook.add(annotations_tab, text="📝 Anotaciones")
        
        ttk.Label(annotations_tab, text="Anotaciones académicas:", 
                 font=("Open Sans", 10, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        # Annotation list
        self.annotations_tree = ttk.Treeview(
            annotations_tab,
            columns=("type", "text", "creator"),
            show="tree headings",
            height=10
        )
        self.annotations_tree.heading("type", text="Tipo")
        self.annotations_tree.heading("text", text="Texto")
        self.annotations_tree.heading("creator", text="Creador")
        self.annotations_tree.column("type", width=100)
        self.annotations_tree.column("text", width=300)
        self.annotations_tree.column("creator", width=100)
        
        self.annotations_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        anno_buttons = ttk.Frame(annotations_tab)
        anno_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            anno_buttons,
            text="➕ Nueva Anotación",
            command=self.new_annotation
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            anno_buttons,
            text="✏️ Editar",
            command=self.edit_annotation
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            anno_buttons,
            text="🗑️ Eliminar",
            command=self.delete_annotation
        ).pack(side=tk.LEFT, padx=2)
        
        # Tab 5: Glosario
        glossary_tab = ttk.Frame(self.notebook)
        self.notebook.add(glossary_tab, text="📚 Glosario")
        
        ttk.Label(glossary_tab, text="Glosario y Abreviaturas:", 
                 font=("Open Sans", 10, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        self.glossary_tree = ttk.Treeview(
            glossary_tab,
            columns=("abbr", "expansion"),
            show="tree headings"
        )
        self.glossary_tree.heading("abbr", text="Abreviatura")
        self.glossary_tree.heading("expansion", text="Expansión")
        self.glossary_tree.column("abbr", width=150)
        self.glossary_tree.column("expansion", width=400)
        
        self.glossary_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        gloss_buttons = ttk.Frame(glossary_tab)
        gloss_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            gloss_buttons,
            text="📥 Importar CSV",
            command=self.import_glossary
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            gloss_buttons,
            text="🔄 Expandir en Texto",
            command=self.expand_abbreviations
        ).pack(side=tk.LEFT, padx=2)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Listo", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Keyboard shortcuts
        self.root.bind('<Control-r>', lambda e: self.play_tts())
        self.root.bind('<Control-p>', lambda e: self.stop_tts())
        self.root.bind('<Control-s>', lambda e: self.save_correction())
        self.root.bind('<F5>', lambda e: self.run_ocr())

    def pick_coordinates(self):
        try:
            # Lazy import to avoid hard dependency at module import time
            from gui.widgets.coords_picker import open_coords_picker
        except Exception:
            if Messagebox:
                Messagebox.show_error(title="Coordenadas", message="No se pudo cargar el selector de coordenadas.")
            else:
                messagebox.showerror("Coordenadas", "No se pudo cargar el selector de coordenadas.")
            return

        # Use Madrid center as default if no project metadata is present
        res = open_coords_picker(self.root, initial_lat=40.4168, initial_lon=-3.7038)
        if res:
            lat, lon = res
            # For now, just show in status bar; wiring to DB/annotations can be added later
            self.status_bar['text'] = f"Coordenadas seleccionadas: {lat:.6f}, {lon:.6f}"
            if Messagebox:
                Messagebox.show_info(title="Coordenadas", message=f"{lat:.6f}, {lon:.6f}")
            else:
                messagebox.showinfo("Coordenadas", f"{lat:.6f}, {lon:.6f}")

    # --- Version history dialog with diff view ---
    def open_version_history(self):
        if not getattr(self, 'pages', None) or self.page_index < 0:
            if Messagebox:
                Messagebox.show_warning(title="Historial", message="No hay página seleccionada", parent=self.root)
            else:
                messagebox.showwarning("Historial", "No hay página seleccionada", parent=self.root)
            return
        project_dir = Path(self.current_project['carpeta_raiz'])
        page = self.pages[self.page_index]
        vers = list_ocr_versions(project_dir, page['id'])
        if not vers:
            if Messagebox:
                Messagebox.show_info(title="Historial", message="No hay versiones de OCR para esta página", parent=self.root)
            else:
                messagebox.showinfo("Historial", "No hay versiones de OCR para esta página", parent=self.root)
            return
        top = tk.Toplevel(self.root)
        try:
            center_to_parent(top, self.root)
        except Exception:
            pass
        top.title("Historial de versiones · Diff")
        top.geometry("1100x700")

        # Selectors
        sel_frame = ttk.Frame(top)
        sel_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(sel_frame, text="Versión A (izquierda):").pack(side=tk.LEFT)
        self._vh_var_a = tk.StringVar()
        self._vh_combo_a = ttk.Combobox(sel_frame, width=60, state="readonly", textvariable=self._vh_var_a)
        ttk.Label(sel_frame, text="  Versión B (derecha):").pack(side=tk.LEFT)
        self._vh_var_b = tk.StringVar()
        self._vh_combo_b = ttk.Combobox(sel_frame, width=60, state="readonly", textvariable=self._vh_var_b)
        self._vh_combo_a.pack(side=tk.LEFT, padx=5)
        self._vh_combo_b.pack(side=tk.LEFT, padx=5)
        ttk.Button(sel_frame, text="Comparar", command=lambda: self._vh_update_diff(top)).pack(side=tk.LEFT, padx=6)
        ttk.Button(sel_frame, text="Aplicar B a OCR Original", command=lambda: self._vh_apply_b_to_editor(top)).pack(side=tk.LEFT, padx=6)
        ttk.Button(sel_frame, text="Aplicar B a OCR Corregido", command=lambda: self._vh_apply_b_to_corrected(top)).pack(side=tk.LEFT, padx=6)
        ttk.Button(sel_frame, text="Cerrar", command=top.destroy).pack(side=tk.RIGHT)

        # Build versions values
        self._vh_versions = {str(v['id']): v for v in vers}
        values = [f"{v['id']} · {v['version_type']} · {v.get('language') or ''} · {v.get('confidence') or ''} · {v['created_at']}" for v in vers]
        self._vh_combo_a['values'] = values
        self._vh_combo_b['values'] = values
        if len(values) >= 2:
            self._vh_combo_a.current(1)
            self._vh_combo_b.current(0)
        else:
            self._vh_combo_a.current(0)
            self._vh_combo_b.current(0)

        # Diff view area: Notebook with Inline and Side-by-Side
        nb = ttk.Notebook(top)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Inline tab
        inline_tab = ttk.Frame(nb)
        nb.add(inline_tab, text="Inline")
        info = ttk.Label(inline_tab, text="Diff tokenizado: Rojo=del, Verde=ins, Sustitución=rojo→verde", foreground="gray")
        info.pack(anchor=tk.W, padx=6, pady=4)
        self._vh_text_inline = scrolledtext.ScrolledText(inline_tab, wrap=tk.WORD, font=("Courier New", 10))
        self._vh_text_inline.pack(fill=tk.BOTH, expand=True)
        self._vh_text_inline.tag_config('ins', foreground='#0a7d00')
        self._vh_text_inline.tag_config('del', foreground='#a30d0d', background='#ffecec')
        self._vh_text_inline.tag_config('sub_old', foreground='#a30d0d', background='#ffecec')
        self._vh_text_inline.tag_config('sub_new', foreground='#0a7d00')

        # Side-by-side tab
        side_tab = ttk.Frame(nb)
        nb.add(side_tab, text="Lado a lado")
        side_paned = ttk.PanedWindow(side_tab, orient=tk.HORIZONTAL)
        side_paned.pack(fill=tk.BOTH, expand=True)
        left_frame = ttk.Frame(side_paned)
        right_frame = ttk.Frame(side_paned)
        side_paned.add(left_frame, weight=1)
        side_paned.add(right_frame, weight=1)
        ttk.Label(left_frame, text="A (izquierda)", foreground="#555").pack(anchor=tk.W, padx=6, pady=2)
        ttk.Label(right_frame, text="B (derecha)", foreground="#555").pack(anchor=tk.W, padx=6, pady=2)
        self._vh_text_left = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, font=("Courier New", 10))
        self._vh_text_right = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, font=("Courier New", 10))
        self._vh_text_left.pack(fill=tk.BOTH, expand=True)
        self._vh_text_right.pack(fill=tk.BOTH, expand=True)
        # Tags
        for w in (self._vh_text_left, self._vh_text_right):
            w.tag_config('ins', foreground='#0a7d00')
            w.tag_config('del', foreground='#a30d0d', background='#ffecec')
            w.tag_config('sub_old', foreground='#a30d0d', background='#ffecec')
            w.tag_config('sub_new', foreground='#0a7d00')

        # Initial diff
        self._vh_update_diff(top)

    def _vh_update_diff(self, top):
        a = self._vh_combo_a.get()
        b = self._vh_combo_b.get()
        if not a or not b:
            return
        ida = a.split('·',1)[0].strip(); idb = b.split('·',1)[0].strip()
        row_a = self._vh_versions.get(ida); row_b = self._vh_versions.get(idb)
        ta = (row_a.get('text_content') or '') if row_a else ''
        tb = (row_b.get('text_content') or '') if row_b else ''
        dif = de.diff_text(ta, tb)
        # Inline
        self._render_diff(self._vh_text_inline, dif)
        # Side-by-side
        self._render_side_by_side(self._vh_text_left, self._vh_text_right, dif)

    def _render_diff(self, widget: tk.Text, dif):
        widget.config(state=tk.NORMAL)
        widget.delete('1.0', tk.END)
        for kind, token in dif:
            if kind == 'keep':
                widget.insert(tk.END, token)
            elif kind == 'ins':
                widget.insert(tk.END, token, ('ins',))
            elif kind == 'del':
                widget.insert(tk.END, token, ('del',))
            elif kind == 'sub':
                old, new = token
                widget.insert(tk.END, old, ('sub_old',))
                widget.insert(tk.END, new, ('sub_new',))
        widget.config(state=tk.NORMAL)

    def _render_side_by_side(self, left: tk.Text, right: tk.Text, dif):
        left.config(state=tk.NORMAL); right.config(state=tk.NORMAL)
        left.delete('1.0', tk.END); right.delete('1.0', tk.END)
        for kind, token in dif:
            if kind == 'keep':
                left.insert(tk.END, token)
                right.insert(tk.END, token)
            elif kind == 'ins':
                # only on right
                right.insert(tk.END, token, ('ins',))
            elif kind == 'del':
                # only on left
                left.insert(tk.END, token, ('del',))
            elif kind == 'sub':
                old, new = token
                left.insert(tk.END, old, ('sub_old',))
                right.insert(tk.END, new, ('sub_new',))
        left.config(state=tk.NORMAL); right.config(state=tk.NORMAL)

    def _vh_apply_b_to_corrected(self, top):
        """Load the selected B version into the OCR Corregido editor and save automatically."""
        b = self._vh_combo_b.get()
        if not b:
            return
        idb = b.split('·',1)[0].strip()
        row_b = self._vh_versions.get(idb)
        if not row_b:
            return
        text = row_b.get('text_content') or ''
        # Confirm with user
        if not messagebox.askyesno(
            "Aplicar y guardar",
            f"¿Aplicar versión {row_b.get('version_type')} a OCR Corregido y guardar automáticamente?\n\n"
            f"Idioma: {row_b.get('language') or ''}\n"
            f"Fecha: {row_b.get('created_at')}",
            parent=top
        ):
            return
        # Load into editor
        self.text_ocr_corrected.delete('1.0', tk.END)
        self.text_ocr_corrected.insert('1.0', text)
        # Save to database
        if getattr(self, 'pages', None) and self.page_index >= 0:
            page = self.pages[self.page_index]
            project_dir = Path(self.current_project['carpeta_raiz'])
            vid = save_ocr_version(project_dir, page['id'], 'ocr_corregido', text)
            self.status_bar['text'] = f"Versión aplicada y guardada (v{vid})"
            self.refresh_ocr_versions()
            if Messagebox:
                Messagebox.show_info(title="Guardado", message=f"Corrección guardada como versión {vid}", parent=self.root)
            else:
                messagebox.showinfo("Guardado", f"Corrección guardada como versión {vid}", parent=self.root)
        else:
            if Messagebox:
                Messagebox.show_warning(title="Guardar", message="No se pudo guardar: página no válida", parent=self.root)
            else:
                messagebox.showwarning("Guardar", "No se pudo guardar: página no válida", parent=self.root)

    def _vh_apply_b_to_editor(self, top):
        """Load the selected B version into the main OCR Original editor and refresh labels/comparator."""
        b = self._vh_combo_b.get()
        if not b:
            return
        idb = b.split('·',1)[0].strip()
        row_b = self._vh_versions.get(idb)
        if not row_b:
            return
        text = row_b.get('text_content') or ''
        # Confirm with user
        if not messagebox.askyesno(
            "Aplicar versión",
            f"¿Cargar versión {row_b.get('version_type')} en OCR Original?\n\n"
            f"Idioma: {row_b.get('language') or ''}\n"
            f"Fecha: {row_b.get('created_at')}\n\n"
            f"Nota: Esto NO guardará automáticamente.",
            parent=top
        ):
            return
        self.text_ocr_original.delete('1.0', tk.END)
        self.text_ocr_original.insert('1.0', text)
        info = f"Versión: {row_b.get('version_type')} · {row_b.get('language') or ''} · {row_b.get('confidence') or ''} · {row_b.get('created_at')}"
        self.lbl_ocr_info['text'] = info
        self.comp_text.delete('1.0', tk.END)
        self.comp_text.insert('1.0', text)
    
    def load_projects(self):
        """Load available projects"""
        try:
            base_path = app_config.get_root_dir()
            projects = list_projects(base_path)
            
            self.projects_data = projects
            project_names = [p['titulo'] for p in projects]
            
            self.project_combo['values'] = project_names
            
            if project_names:
                self.project_combo.current(0)
                self.on_project_selected(None)
            
            self.status_bar['text'] = f"Cargados {len(projects)} proyectos"
        
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(title="Error", message=f"No se pudieron cargar proyectos:\n{str(e)}", parent=self.root)
            else:
                messagebox.showerror("Error", f"No se pudieron cargar proyectos:\n{str(e)}", parent=self.root)

    def on_close(self):
        try:
            app_config.set_window_geometry("annotation", self.root.geometry())
        except Exception:
            pass
        self.root.destroy()
    
    def on_project_selected(self, event):
        """Handle project selection"""
        idx = self.project_combo.current()
        if idx >= 0 and idx < len(self.projects_data):
            self.current_project = self.projects_data[idx]
            self.status_bar['text'] = f"Proyecto: {self.current_project['titulo']}"
            # Ensure DB reflects folder pages, then load
            self.sync_pages()
            self.load_pages()

    def edit_current_project(self):
        if not self.current_project:
            return
        if open_metadata_manager:
            open_metadata_manager(self.root, focus_tab='proyectos', edit_project_id=int(self.current_project.get('id')))
            # Refresh list as metadata might have changed
            self.load_projects()
    
    def load_pages(self):
        """Load pages metadata from project.db and show first page"""
        if not self.current_project:
            return
        try:
            project_dir = Path(self.current_project['carpeta_raiz'])
            self.pages = list_pages(project_dir)
            self.page_index = 0 if self.pages else -1
            self.build_thumbnails()
            self.show_current_page()
            self.status_bar['text'] = f"{len(self.pages)} páginas cargadas"
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(title="Páginas", message=f"No se pudieron cargar: {e}", parent=self.root)
            else:
                messagebox.showerror("Páginas", f"No se pudieron cargar: {e}", parent=self.root)
    
    def prev_page(self):
        """Navigate to previous page"""
        if getattr(self, 'pages', None) and self.page_index > 0:
            self.page_index -= 1
            self.show_current_page()
    
    def next_page(self):
        """Navigate to next page"""
        if getattr(self, 'pages', None) and self.page_index < len(self.pages)-1:
            self.page_index += 1
            self.show_current_page()

    def show_current_page(self):
        if not getattr(self, 'pages', None) or self.page_index < 0:
            self.image_canvas.delete("all")
            self.page_label['text'] = "Página: -/-"
            return
        p = self.pages[self.page_index]
        self.page_label['text'] = f"Página: {self.page_index+1}/{len(self.pages)} (seq {p['seq']})"
        img_path = p['processed_path'] or p['original_path']
        try:
            with Image.open(img_path) as im:
                # Fit to canvas
                self.root.update_idletasks()
                cw = self.image_canvas.winfo_width() or 800
                ch = self.image_canvas.winfo_height() or 600
                im.thumbnail((cw-20, ch-20))
                self._tk_img = ImageTk.PhotoImage(im)
                self.image_canvas.delete("all")
                self.image_canvas.create_image(cw//2, ch//2, image=self._tk_img)
            # Also draw in comparator canvas
            with Image.open(img_path) as im2:
                comp_w = self.comp_canvas.winfo_width() or 600
                comp_h = self.comp_canvas.winfo_height() or 600
                im2.thumbnail((comp_w-20, comp_h-20))
                self._tk_comp_img = ImageTk.PhotoImage(im2)
                self.comp_canvas.delete("all")
                self.comp_canvas.create_image((comp_w)//2, (comp_h)//2, image=self._tk_comp_img)
                self.comp_canvas.configure(scrollregion=(0,0,im2.width,im2.height))
        except Exception:
            self.image_canvas.delete("all")
            self.image_canvas.create_text(10,10, anchor="nw", fill="white", text=str(img_path))
        # Load latest OCR
        self.refresh_ocr_versions()
        self.load_latest_ocr_for_page()
    
    def run_ocr(self):
        """Run OCR on current page and save original text version"""
        if not getattr(self, 'pages', None) or self.page_index < 0:
            if Messagebox:
                Messagebox.show_warning(title="OCR", message="No hay página seleccionada", parent=self.root)
            else:
                messagebox.showwarning("OCR", "No hay página seleccionada", parent=self.root)
            return
        page = self.pages[self.page_index]
        img_path = page['processed_path'] or page['original_path']
        lang = self.lang_var.get() or 'spa'
        try:
            self.status_bar['text'] = "Preprocesando..."
            prep = preprocess_for_ocr(img_path)
            self.status_bar['text'] = f"OCR en progreso ({lang})..."
            res = perform_ocr(prep, lang=lang)
            if not res.get('success'):
                if Messagebox:
                    Messagebox.show_error(title="OCR", message=res.get('error') or 'Fallo de OCR', parent=self.root)
                else:
                    messagebox.showerror("OCR", res.get('error') or 'Fallo de OCR', parent=self.root)
                return
            text = res.get('text') or ''
            conf = float(res.get('confidence') or 0)
            # Save to DB
            project_dir = Path(self.current_project['carpeta_raiz'])
            save_ocr_version(project_dir, page['id'], 'ocr_original', text, language=lang, confidence=conf)
            # Update UI
            self.text_ocr_original.delete('1.0', tk.END)
            self.text_ocr_original.insert('1.0', text)
            self.lbl_ocr_info['text'] = f"Idioma: {lang} · Confianza media: {conf:.1f} · Palabras: {len(text.split())}"
            self.status_bar['text'] = "OCR completado"
            # Refresh versions and comparator
            self.refresh_ocr_versions()
            self.comp_text.delete('1.0', tk.END)
            self.comp_text.insert('1.0', text)
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(title="OCR", message=str(e), parent=self.root)
            else:
                messagebox.showerror("OCR", str(e), parent=self.root)
    
    def play_tts(self):
        """Play text-to-speech"""
        text = self.text_ocr_corrected.get("1.0", tk.END).strip()
        if not text:
            text = self.text_ocr_original.get("1.0", tk.END).strip()
        
        if text:
            self.tts.speak(text)
            self.status_bar['text'] = "Reproduciendo texto..."
        else:
            if Messagebox:
                Messagebox.show_warning(title="TTS", message="No hay texto para reproducir", parent=self.root)
            else:
                messagebox.showwarning("TTS", "No hay texto para reproducir", parent=self.root)
    
    def stop_tts(self):
        """Stop text-to-speech"""
        self.tts.stop()
        self.status_bar['text'] = "Reproducción detenida"
    
    def save_correction(self):
        """Save corrected OCR text to ocr_versions"""
        if not getattr(self, 'pages', None) or self.page_index < 0:
            return
        page = self.pages[self.page_index]
        text = self.text_ocr_corrected.get('1.0', tk.END).strip()
        if not text:
            if Messagebox:
                Messagebox.show_warning(title="Guardar", message="No hay texto corregido", parent=self.root)
            else:
                messagebox.showwarning("Guardar", "No hay texto corregido", parent=self.root)
            return
        project_dir = Path(self.current_project['carpeta_raiz'])
        vid = save_ocr_version(project_dir, page['id'], 'ocr_corregido', text)
        self.status_bar['text'] = f"Corrección guardada (v{vid})"
        self.refresh_ocr_versions()
    
    def check_spelling(self):
        """Run spellcheck on corrected text and show issues."""
        txt = self.text_ocr_corrected.get('1.0', tk.END)
        project_dir = Path(self.current_project['carpeta_raiz']) if self.current_project else None
        res = sp.check_text_with_custom(txt, 'es', str(project_dir) if project_dir else None)
        issues = res.get('issues') or []
        if not issues:
            if Messagebox:
                Messagebox.show_info(title="Ortografía", message="Sin problemas detectados", parent=self.root)
            else:
                messagebox.showinfo("Ortografía", "Sin problemas detectados", parent=self.root)
            return
        # Simple viewer
        top = tk.Toplevel(self.root); top.title("Revisión ortográfica")
        try:
            center_to_parent(top, self.root)
        except Exception:
            pass
        lb = tk.Listbox(top, width=120, height=20)
        lb.pack(fill=tk.BOTH, expand=True)
        for m in issues[:200]:
            if res.get('tool') == 'language_tool_python':
                lb.insert(tk.END, f"{m.get('message')} · Sugerencias: {', '.join([r for r in m.get('replacements', [])])}")
            else:
                lb.insert(tk.END, f"Palabra: {m.get('word')} · Sugerencia: {m.get('suggestion')}")
        ttk.Button(top, text="Cerrar", command=top.destroy).pack(pady=5)
    
    def new_annotation(self):
        """Create new annotation"""
        if Messagebox:
            Messagebox.show_info(title="Anotación", message="Función de anotación en implementación", parent=self.root)
        else:
            messagebox.showinfo("Anotación", "Función de anotación en implementación", parent=self.root)
    
    def edit_annotation(self):
        """Edit selected annotation"""
        pass
    
    def delete_annotation(self):
        """Delete selected annotation"""
        pass
    
    def import_glossary(self):
        """Import glossary from CSV"""
        file_path = filedialog.askopenfilename(
            title="Importar Glosario",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            if Messagebox:
                Messagebox.show_info(title="Importar", message=f"Importación desde {file_path} en implementación", parent=self.root)
            else:
                messagebox.showinfo("Importar", f"Importación desde {file_path} en implementación", parent=self.root)
    
    def expand_abbreviations(self):
        """Expand abbreviations/glossary terms in corrected text."""
        if not self.current_project:
            return
        project_dir = Path(self.current_project['carpeta_raiz'])
        dbp = get_project_db_path(project_dir)
        terms = gm.get_terms(str(dbp), language='es')
        if not terms:
            if Messagebox:
                Messagebox.show_warning(title="Glosario", message="No hay términos en el glosario", parent=self.root)
            else:
                messagebox.showwarning("Glosario", "No hay términos en el glosario", parent=self.root)
            return
        txt = self.text_ocr_corrected.get('1.0', tk.END)
        hints = gm.apply_abbreviation_hints(txt, terms)
        if not hints:
            if Messagebox:
                Messagebox.show_info(title="Expandir", message="No se encontraron abreviaturas para expandir", parent=self.root)
            else:
                messagebox.showinfo("Expandir", "No se encontraron abreviaturas para expandir", parent=self.root)
            return
        if not messagebox.askyesno("Expandir", f"Se encontraron {len(hints)} ocurrencias. ¿Aplicar expansión?", parent=self.root):
            return
        # Apply replacements (whole word)
        import re
        for abbr, exp in terms.items():
            txt = re.sub(rf"\b{re.escape(abbr)}\b", exp, txt)
        self.text_ocr_corrected.delete('1.0', tk.END)
        self.text_ocr_corrected.insert('1.0', txt)
        self.status_bar['text'] = "Abreviaturas expandidas"

    # --- OCR versions helpers ---
    def refresh_ocr_versions(self):
        if not getattr(self, 'pages', None) or self.page_index < 0:
            self.ocr_version_combo['values'] = []
            return
        project_dir = Path(self.current_project['carpeta_raiz'])
        page = self.pages[self.page_index]
        vers = list_ocr_versions(project_dir, page['id'])
        self._ocr_versions = {str(v['id']): v for v in vers}
        values = [f"{v['id']} · {v['version_type']} · {v.get('language') or ''} · {v.get('confidence') or ''} · {v['created_at']}" for v in vers]
        self.ocr_version_combo['values'] = values
        if values:
            self.ocr_version_combo.current(0)

    def load_selected_ocr(self):
        sel = self.ocr_version_combo.get()
        if not sel:
            return
        vid = sel.split('·',1)[0].strip()
        row = self._ocr_versions.get(vid)
        if not row:
            return
        text = row.get('text_content') or ''
        self.text_ocr_original.delete('1.0', tk.END)
        self.text_ocr_original.insert('1.0', text)
        self.lbl_ocr_info['text'] = f"Versión: {row.get('version_type')} · {row.get('language') or ''} · {row.get('confidence') or ''} · {row.get('created_at')}"
        # update comparator text as well
        self.comp_text.delete('1.0', tk.END)
        self.comp_text.insert('1.0', text)

    def load_latest_ocr_for_page(self):
        if not getattr(self, 'pages', None) or self.page_index < 0:
            return
        project_dir = Path(self.current_project['carpeta_raiz'])
        page = self.pages[self.page_index]
        row_corr = get_latest_ocr(project_dir, page['id'], 'ocr_corregido')
        row_orig = get_latest_ocr(project_dir, page['id'], 'ocr_original')
        # Populate widgets
        if row_orig:
            txt_o = row_orig.get('text_content') or ''
            self.text_ocr_original.delete('1.0', tk.END)
            self.text_ocr_original.insert('1.0', txt_o)
            self.lbl_ocr_info['text'] = f"Último OCR: {row_orig.get('language') or ''} · {row_orig.get('confidence') or ''} · {row_orig.get('created_at')}"
            self.comp_text.delete('1.0', tk.END)
            self.comp_text.insert('1.0', txt_o)
        if row_corr:
            txt_c = row_corr.get('text_content') or ''
            self.text_ocr_corrected.delete('1.0', tk.END)
            self.text_ocr_corrected.insert('1.0', txt_c)

    # --- Comparator scroll sync handlers ---
    def _on_comp_text_scroll(self, first, last):
        try:
            f = float(first)
            self.comp_canvas.yview_moveto(f)
        except Exception:
            pass

    def _on_comp_canvas_wheel(self, event):
        # Scroll text when mouse over canvas
        delta = -1 if event.delta > 0 else 1
        self.comp_text.yview_scroll(delta, 'units')
        return 'break'

    # --- Thumbnails strip ---
    def build_thumbnails(self):
        # Create strip once
        if not hasattr(self, 'thumb_container'):
            self.thumb_container = ttk.Frame(self.root)
            self.thumb_container.pack(side=tk.BOTTOM, fill=tk.X)
            self.thumb_canvas = tk.Canvas(self.thumb_container, height=96)
            self.thumb_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.thumb_scroll = ttk.Scrollbar(self.thumb_container, orient=tk.HORIZONTAL, command=self.thumb_canvas.xview)
            self.thumb_scroll.pack(side=tk.BOTTOM, fill=tk.X)
            self.thumb_canvas.configure(xscrollcommand=self.thumb_scroll.set)
            self.thumb_inner = ttk.Frame(self.thumb_canvas)
            self.thumb_canvas.create_window((0,0), window=self.thumb_inner, anchor='nw')
            self.thumb_inner.bind('<Configure>', lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox('all')))
        # Populate
        for w in getattr(self, '_thumb_widgets', []):
            try: w.destroy()
            except Exception: pass
        self._thumb_widgets = []
        self._thumb_imgs = []
        if not getattr(self, 'pages', None):
            return
        for idx, p in enumerate(self.pages):
            path = p.get('thumbnail_path') or p.get('processed_path') or p.get('original_path')
            try:
                im = Image.open(path)
                im.thumbnail((120, 90))
                img = ImageTk.PhotoImage(im)
                lbl = ttk.Label(self.thumb_inner, image=img, relief=tk.SUNKEN if idx==self.page_index else tk.FLAT)
                lbl.image = img
                lbl.grid(row=0, column=idx, padx=3, pady=3)
                lbl.bind('<Button-1>', lambda e, i=idx: self._on_thumb_click(i))
                self._thumb_widgets.append(lbl)
                self._thumb_imgs.append(img)
            except Exception:
                pass

    def _on_thumb_click(self, idx):
        self.page_index = idx
        self.show_current_page()

    def sync_pages(self):
        if not self.current_project:
            return
        project_dir = Path(self.current_project['carpeta_raiz'])
        inserted = sync_pages_from_folder(project_dir)
        if inserted:
            self.load_pages()
        else:
            self.status_bar['text'] = "Páginas ya sincronizadas"


if __name__ == "__main__":
    root = tk.Tk()
    app = AnnotationWindow(root)
    root.mainloop()
