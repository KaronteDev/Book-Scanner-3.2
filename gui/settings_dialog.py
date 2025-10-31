#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
settings_dialog.py — Diálogo de configuración con pestañas para todos los apartados de app_config.json
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.dialogs import Messagebox
    USE_BOOTSTRAP = True
except ImportError:  # Fallbacks
    from tkinter import ttk
    Messagebox = None
    USE_BOOTSTRAP = False

from pathlib import Path

from utils.theme_titlebar import apply_titlebar_theme
from utils import app_config
try:
    from utils import db_manager as db
except Exception:
    db = None


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, on_applied=None):
        super().__init__(parent)

        self.parent = parent
        self.on_applied = on_applied
        self.title("Configuración")
        self.geometry("850x550")
        self.resizable(True, True)

        # Cargar configuración actual
        self.config = app_config.load_config() or {}
        
        # Contenedor principal
        main_container = ttk.Frame(self, padding=10) if USE_BOOTSTRAP else tk.Frame(self, padx=10, pady=10)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Crear notebook (pestañas)
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Crear las pestañas
        self._create_paths_tab()
        self._create_camera_tab()
        self._create_ocr_tab()
        self._create_tts_tab()
        self._create_processing_tab()
        self._create_export_tab()
        self._create_ui_tab()

        # Botonera inferior
        btns_frame = ttk.Frame(main_container) if USE_BOOTSTRAP else tk.Frame(main_container)
        btns_frame.pack(fill=tk.X, pady=(10, 0))
        
        apply_btn = ttk.Button(btns_frame, text="Aplicar", command=self.apply_changes, bootstyle="primary" if USE_BOOTSTRAP else None) if USE_BOOTSTRAP else tk.Button(btns_frame, text="Aplicar", command=self.apply_changes)
        apply_btn.pack(side=tk.RIGHT, padx=5)
        
        cancel_btn = ttk.Button(btns_frame, text="Cancelar", command=self.destroy, bootstyle="secondary" if USE_BOOTSTRAP else None) if USE_BOOTSTRAP else tk.Button(btns_frame, text="Cancelar", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT)

        # Aplicar estilo de barra de título
        apply_titlebar_theme(self)

        # Centrar la ventana respecto al padre
        self.center_window()

        # Modal-like
        self.transient(parent)
        self.grab_set()
        self.focus_set()

    def center_window(self):
        """Centra la ventana respecto a la ventana padre"""
        self.update_idletasks()
        
        # Obtener dimensiones de esta ventana
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Obtener posición y dimensiones de la ventana padre
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calcular posición centrada
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        # Asegurar que la ventana no salga de la pantalla
        x = max(0, x)
        y = max(0, y)
        
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _create_scrollable_frame(self, parent):
        """Crea un frame con scrollbar"""
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding=15) if USE_BOOTSTRAP else tk.Frame(canvas, padx=15, pady=15)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        return scrollable_frame

    def _create_paths_tab(self):
        """Pestaña: Rutas"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Rutas")
        frame = self._create_scrollable_frame(tab)
        
        paths_cfg = self.config.get("paths", {})
        
        # Directorio raíz
        self._add_label(frame, "Directorio raíz de trabajo:", bold=True)
        current_root = str(app_config.get_root_dir())
        self.root_dir_var = tk.StringVar(value=current_root)
        self._add_entry_with_browse(frame, self.root_dir_var, lambda: self._browse_directory(self.root_dir_var))
        
        # Data dir
        self._add_label(frame, "Directorio de datos:", bold=True)
        self.paths_data_var = tk.StringVar(value=paths_cfg.get("data_dir", "data"))
        self._add_entry_with_browse(frame, self.paths_data_var, lambda: self._browse_directory(self.paths_data_var))
        
        # Projects dir
        self._add_label(frame, "Directorio de proyectos:", bold=True)
        self.paths_projects_var = tk.StringVar(value=paths_cfg.get("projects_dir", "proyectos"))
        self._add_entry_with_browse(frame, self.paths_projects_var, lambda: self._browse_directory(self.paths_projects_var))
        
        # Temp dir
        self._add_label(frame, "Directorio temporal:", bold=True)
        self.paths_temp_var = tk.StringVar(value=paths_cfg.get("temp_dir", "temp"))
        self._add_entry_with_browse(frame, self.paths_temp_var, lambda: self._browse_directory(self.paths_temp_var))
        
        # Exports dir
        self._add_label(frame, "Directorio de exportaciones:", bold=True)
        self.paths_exports_var = tk.StringVar(value=paths_cfg.get("exports_dir", "exports"))
        self._add_entry_with_browse(frame, self.paths_exports_var, lambda: self._browse_directory(self.paths_exports_var))

    def _create_camera_tab(self):
        """Pestaña: Cámara"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Cámara")
        frame = self._create_scrollable_frame(tab)
        
        camera_cfg = self.config.get("camera", {})
        
        # Resolución por defecto
        self._add_label(frame, "Resolución por defecto:", bold=True)
        default_res = camera_cfg.get("default_resolution", [1920, 1080])
        res_frame = ttk.Frame(frame) if USE_BOOTSTRAP else tk.Frame(frame)
        res_frame.pack(fill=tk.X, pady=(2, 5))
        
        # Ancho
        (ttk.Label(res_frame, text="Ancho:", width=10) if USE_BOOTSTRAP else tk.Label(res_frame, text="Ancho:", width=10)).pack(side=tk.LEFT, padx=(0, 5))
        self.camera_width_var = tk.IntVar(value=default_res[0])
        width_spin = ttk.Spinbox(res_frame, from_=640, to=7680, textvariable=self.camera_width_var, width=10, increment=1) if USE_BOOTSTRAP else tk.Spinbox(res_frame, from_=640, to=7680, textvariable=self.camera_width_var, width=10, increment=1)
        width_spin.pack(side=tk.LEFT, padx=5)
        
        # Alto
        (ttk.Label(res_frame, text="Alto:", width=10) if USE_BOOTSTRAP else tk.Label(res_frame, text="Alto:", width=10)).pack(side=tk.LEFT, padx=(20, 5))
        self.camera_height_var = tk.IntVar(value=default_res[1])
        height_spin = ttk.Spinbox(res_frame, from_=480, to=4320, textvariable=self.camera_height_var, width=10, increment=1) if USE_BOOTSTRAP else tk.Spinbox(res_frame, from_=480, to=4320, textvariable=self.camera_height_var, width=10, increment=1)
        height_spin.pack(side=tk.LEFT, padx=5)
        
        # Calidad de captura
        self._add_label(frame, "Calidad de captura (%):", bold=True)
        self.camera_quality_var = tk.IntVar(value=camera_cfg.get("capture_quality", 95))
        self._add_spinbox(frame, self.camera_quality_var, 1, 100)
        
        # Auto focus
        self._add_label(frame, "Enfoque automático:", bold=True)
        self.camera_autofocus_var = tk.BooleanVar(value=camera_cfg.get("auto_focus", True))
        self._add_checkbutton(frame, "Activar enfoque automático", self.camera_autofocus_var)
        
        # Formato por defecto
        self._add_label(frame, "Formato por defecto:", bold=True)
        self.camera_format_var = tk.StringVar(value=camera_cfg.get("default_format", "A4"))
        self._add_combobox(frame, self.camera_format_var, ["A4", "A3", "Letter", "Legal"])

    def _create_ocr_tab(self):
        """Pestaña: OCR"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="OCR")
        frame = self._create_scrollable_frame(tab)
        
        ocr_cfg = self.config.get("ocr", {})
        
        # Idioma por defecto
        self._add_label(frame, "Idioma por defecto:", bold=True)
        self.ocr_language_var = tk.StringVar(value=ocr_cfg.get("default_language", "spa"))
        self._add_entry(frame, self.ocr_language_var)
        
        # PSM mode
        self._add_label(frame, "Modo PSM:", bold=True)
        self.ocr_psm_var = tk.IntVar(value=ocr_cfg.get("psm_mode", 3))
        self._add_spinbox(frame, self.ocr_psm_var, 0, 13)
        
        # Idiomas disponibles
        self._add_label(frame, "Idiomas disponibles (separados por comas):", bold=True)
        languages = ocr_cfg.get("languages", ["spa", "lat", "eng"])
        self.ocr_languages_var = tk.StringVar(value=", ".join(languages))
        self._add_entry(frame, self.ocr_languages_var)
        
        # Preprocesado
        self._add_label(frame, "Opciones de preprocesado:", bold=True)
        self.ocr_preprocess_var = tk.BooleanVar(value=ocr_cfg.get("preprocess", True))
        self._add_checkbutton(frame, "Preprocesar imagen", self.ocr_preprocess_var)
        
        self.ocr_autorotate_var = tk.BooleanVar(value=ocr_cfg.get("auto_rotate", True))
        self._add_checkbutton(frame, "Rotación automática", self.ocr_autorotate_var)
        
        self.ocr_denoise_var = tk.BooleanVar(value=ocr_cfg.get("denoise", True))
        self._add_checkbutton(frame, "Reducción de ruido", self.ocr_denoise_var)
        
        # Umbral de confianza
        self._add_label(frame, "Umbral de confianza (%):", bold=True)
        self.ocr_confidence_var = tk.DoubleVar(value=ocr_cfg.get("confidence_threshold", 60.0))
        self._add_spinbox(frame, self.ocr_confidence_var, 0.0, 100.0, increment=0.1)

    def _create_tts_tab(self):
        """Pestaña: TTS (Text-to-Speech)"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="TTS")
        frame = self._create_scrollable_frame(tab)
        
        tts_cfg = self.config.get("tts", {})
        
        # Velocidad por defecto
        self._add_label(frame, "Velocidad de lectura (palabras/min):", bold=True)
        self.tts_rate_var = tk.IntVar(value=tts_cfg.get("default_rate", 150))
        self._add_spinbox(frame, self.tts_rate_var, 50, 400)
        
        # Volumen
        self._add_label(frame, "Volumen (0.0 - 1.0):", bold=True)
        self.tts_volume_var = tk.DoubleVar(value=tts_cfg.get("default_volume", 0.9))
        self._add_spinbox(frame, self.tts_volume_var, 0.0, 1.0, increment=0.1)
        
        # Idioma de voz
        self._add_label(frame, "Idioma de voz:", bold=True)
        self.tts_voice_lang_var = tk.StringVar(value=tts_cfg.get("default_voice_lang", "es"))
        self._add_entry(frame, self.tts_voice_lang_var)
        
        # Formato de guardado
        self._add_label(frame, "Formato de guardado:", bold=True)
        self.tts_format_var = tk.StringVar(value=tts_cfg.get("save_format", "wav"))
        self._add_combobox(frame, self.tts_format_var, ["wav", "mp3", "ogg"])

    def _create_processing_tab(self):
        """Pestaña: Procesamiento"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Procesamiento")
        frame = self._create_scrollable_frame(tab)
        
        proc_cfg = self.config.get("processing", {})
        
        self._add_label(frame, "Opciones de procesamiento automático:", bold=True)
        
        # Auto crop
        self.proc_autocrop_var = tk.BooleanVar(value=proc_cfg.get("auto_crop", True))
        self._add_checkbutton(frame, "Recorte automático", self.proc_autocrop_var)
        
        # Remove fingers
        self.proc_remove_fingers_var = tk.BooleanVar(value=proc_cfg.get("remove_fingers", True))
        self._add_checkbutton(frame, "Eliminar dedos", self.proc_remove_fingers_var)
        
        # Auto brightness
        self.proc_auto_brightness_var = tk.BooleanVar(value=proc_cfg.get("auto_brightness", True))
        self._add_checkbutton(frame, "Brillo automático", self.proc_auto_brightness_var)
        
        # Dewarp
        self.proc_dewarp_var = tk.BooleanVar(value=proc_cfg.get("dewarp", False))
        self._add_checkbutton(frame, "Corrección de deformación", self.proc_dewarp_var)
        
        # Split double page
        self.proc_split_double_var = tk.BooleanVar(value=proc_cfg.get("split_double_page", False))
        self._add_checkbutton(frame, "Dividir páginas dobles", self.proc_split_double_var)

    def _create_export_tab(self):
        """Pestaña: Exportación"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Exportación")
        frame = self._create_scrollable_frame(tab)
        
        export_cfg = self.config.get("export", {})
        
        # Formatos
        self._add_label(frame, "Formatos de exportación (separados por comas):", bold=True)
        formats = export_cfg.get("formats", ["dc", "iiif", "tei", "geojson", "pdf"])
        self.export_formats_var = tk.StringVar(value=", ".join(formats))
        self._add_entry(frame, self.export_formats_var)
        
        # PDF quality
        self._add_label(frame, "Calidad PDF (%):", bold=True)
        self.export_pdf_quality_var = tk.IntVar(value=export_cfg.get("pdf_quality", 95))
        self._add_spinbox(frame, self.export_pdf_quality_var, 1, 100)
        
        # Embed metadata
        self._add_label(frame, "Opciones:", bold=True)
        self.export_embed_metadata_var = tk.BooleanVar(value=export_cfg.get("embed_metadata", True))
        self._add_checkbutton(frame, "Incrustar metadatos", self.export_embed_metadata_var)
        
        # Validate output
        self.export_validate_var = tk.BooleanVar(value=export_cfg.get("validate_output", True))
        self._add_checkbutton(frame, "Validar salida", self.export_validate_var)

    def _create_ui_tab(self):
        """Pestaña: Interfaz de Usuario"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Interfaz")
        frame = self._create_scrollable_frame(tab)
        
        ui_cfg = self.config.get("ui", {})
        
        # Tema
        self._add_label(frame, "Tema de interfaz:", bold=True)
        self.style = (self.master.style if hasattr(self.master, 'style') else (ttk.Style() if USE_BOOTSTRAP else None))
        themes = []
        if self.style:
            try:
                themes = list(self.style.theme_names())
            except Exception:
                themes = []
        current_theme = ui_cfg.get("theme", "superhero")
        self.ui_theme_var = tk.StringVar(value=current_theme)
        
        theme_frame = self._add_frame(frame)
        combo = self._add_combobox(theme_frame, self.ui_theme_var, themes)
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        preview_btn = ttk.Button(theme_frame, text="Previsualizar", command=self.preview_theme, bootstyle="secondary" if USE_BOOTSTRAP else None) if USE_BOOTSTRAP else tk.Button(theme_frame, text="Previsualizar", command=self.preview_theme)
        preview_btn.pack(side=tk.LEFT, padx=5)
        
        # Preview area
        self._add_label(frame, "Vista previa:", bold=True)
        self.preview_frame = ttk.Labelframe(frame, text="Ejemplo", padding=10) if USE_BOOTSTRAP else tk.LabelFrame(frame, text="Ejemplo", padx=10, pady=10)
        self.preview_frame.pack(fill=tk.X, pady=(5, 10))
        self._build_preview(self.preview_frame)
        
        # Font family
        self._add_label(frame, "Familia de fuente:", bold=True)
        self.ui_font_family_var = tk.StringVar(value=ui_cfg.get("font_family", "Open Sans"))
        self._add_entry(frame, self.ui_font_family_var)
        
        # Font size
        self._add_label(frame, "Tamaño de fuente:", bold=True)
        self.ui_font_size_var = tk.IntVar(value=ui_cfg.get("font_size", 10))
        self._add_spinbox(frame, self.ui_font_size_var, 8, 22)
        
        # Show tooltips
        self._add_label(frame, "Opciones:", bold=True)
        self.ui_tooltips_var = tk.BooleanVar(value=ui_cfg.get("show_tooltips", True))
        self._add_checkbutton(frame, "Mostrar tooltips", self.ui_tooltips_var)
        
        # Confirm actions
        self.ui_confirm_var = tk.BooleanVar(value=ui_cfg.get("confirm_actions", True))
        self._add_checkbutton(frame, "Confirmar acciones", self.ui_confirm_var)
        
        # Aplicar a todas las ventanas
        self.apply_all_var = tk.BooleanVar(value=False)
        self._add_checkbutton(frame, "Aplicar a todas las ventanas ahora", self.apply_all_var)

    # Métodos auxiliares para crear widgets
    def _add_label(self, parent, text, bold=False):
        font = ("Open Sans", 10, "bold") if bold else ("Open Sans", 10)
        lbl = (ttk.Label(parent, text=text, font=font) if USE_BOOTSTRAP else tk.Label(parent, text=text, font=font))
        lbl.pack(anchor=tk.W, pady=(8, 2))
        return lbl

    def _add_frame(self, parent):
        frame = ttk.Frame(parent) if USE_BOOTSTRAP else tk.Frame(parent)
        frame.pack(fill=tk.X, pady=(2, 5))
        return frame

    def _add_entry(self, parent, var):
        entry = ttk.Entry(parent, textvariable=var) if USE_BOOTSTRAP else tk.Entry(parent, textvariable=var)
        entry.pack(fill=tk.X, pady=(2, 5))
        return entry

    def _add_entry_with_browse(self, parent, var, command):
        frame = self._add_frame(parent)
        entry = ttk.Entry(frame, textvariable=var, width=60) if USE_BOOTSTRAP else tk.Entry(frame, textvariable=var, width=60)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        btn = ttk.Button(frame, text="Examinar…", command=command, width=12, bootstyle="secondary" if USE_BOOTSTRAP else None) if USE_BOOTSTRAP else tk.Button(frame, text="Examinar…", command=command, width=12)
        btn.pack(side=tk.LEFT, padx=5)
        return frame

    def _add_combobox(self, parent, var, values):
        combo = ttk.Combobox(parent, textvariable=var, values=values, state="readonly")
        combo.pack(fill=tk.X, pady=(2, 5))
        return combo

    def _add_spinbox(self, parent, var, from_, to, increment=1):
        spinbox = ttk.Spinbox(parent, from_=from_, to=to, textvariable=var, increment=increment) if USE_BOOTSTRAP else tk.Spinbox(parent, from_=from_, to=to, textvariable=var, increment=increment)
        spinbox.pack(fill=tk.X, pady=(2, 5))
        return spinbox

    def _add_checkbutton(self, parent, text, var):
        cb = ttk.Checkbutton(parent, text=text, variable=var) if USE_BOOTSTRAP else tk.Checkbutton(parent, text=text, variable=var)
        cb.pack(anchor=tk.W, pady=(2, 5))
        return cb

    def _build_preview(self, parent):
        """Construye la vista previa del tema"""
        (ttk.Label(parent, text="Texto de ejemplo") if USE_BOOTSTRAP else tk.Label(parent, text="Texto de ejemplo")).pack(anchor=tk.W)
        row = ttk.Frame(parent) if USE_BOOTSTRAP else tk.Frame(parent)
        row.pack(fill=tk.X, pady=(6, 0))
        (ttk.Button(row, text="Primario", bootstyle="primary") if USE_BOOTSTRAP else tk.Button(row, text="Primario")).pack(side=tk.LEFT, padx=3)
        (ttk.Button(row, text="Info", bootstyle="info") if USE_BOOTSTRAP else tk.Button(row, text="Info")).pack(side=tk.LEFT, padx=3)
        (ttk.Button(row, text="Éxito", bootstyle="success") if USE_BOOTSTRAP else tk.Button(row, text="Éxito")).pack(side=tk.LEFT, padx=3)
        (ttk.Button(row, text="Peligro", bootstyle="danger") if USE_BOOTSTRAP else tk.Button(row, text="Peligro")).pack(side=tk.LEFT, padx=3)

    def _browse_directory(self, var):
        """Abre un diálogo para seleccionar directorio y actualiza la variable"""
        directory = filedialog.askdirectory(parent=self, title="Seleccione un directorio")
        if directory:
            var.set(directory)

    def preview_theme(self):
        """Previsualiza el tema seleccionado"""
        if not USE_BOOTSTRAP or not self.style:
            if Messagebox:
                Messagebox.show_info(message="La previsualización de tema requiere ttkbootstrap.", title="Información", parent=self)
            return
        theme = self.ui_theme_var.get().strip()
        try:
            self.style.theme_use(theme)
            apply_titlebar_theme(self)
            if isinstance(self.parent, (tk.Tk, tk.Toplevel)):
                apply_titlebar_theme(self.parent)
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(message=f"No se pudo aplicar el tema: {e}", title="Error", parent=self)

    def apply_changes(self):
        """Aplica y guarda todos los cambios de configuración"""
        try:
            # Cargar configuración actual para preservar secciones no editadas
            current_config = app_config.load_config() or {}
            
            # Actualizar solo las secciones editadas
            current_config["paths"] = {
                "data_dir": self.paths_data_var.get(),
                "projects_dir": self.paths_projects_var.get(),
                "temp_dir": self.paths_temp_var.get(),
                "exports_dir": self.paths_exports_var.get()
            }
            
            current_config["camera"] = {
                "default_resolution": [self.camera_width_var.get(), self.camera_height_var.get()],
                "capture_quality": self.camera_quality_var.get(),
                "auto_focus": self.camera_autofocus_var.get(),
                "default_format": self.camera_format_var.get()
            }
            
            current_config["ocr"] = {
                "default_language": self.ocr_language_var.get(),
                "psm_mode": self.ocr_psm_var.get(),
                "languages": [lang.strip() for lang in self.ocr_languages_var.get().split(",")],
                "preprocess": self.ocr_preprocess_var.get(),
                "auto_rotate": self.ocr_autorotate_var.get(),
                "denoise": self.ocr_denoise_var.get(),
                "confidence_threshold": self.ocr_confidence_var.get()
            }
            
            current_config["tts"] = {
                "default_rate": self.tts_rate_var.get(),
                "default_volume": self.tts_volume_var.get(),
                "default_voice_lang": self.tts_voice_lang_var.get(),
                "save_format": self.tts_format_var.get()
            }
            
            current_config["processing"] = {
                "auto_crop": self.proc_autocrop_var.get(),
                "remove_fingers": self.proc_remove_fingers_var.get(),
                "auto_brightness": self.proc_auto_brightness_var.get(),
                "dewarp": self.proc_dewarp_var.get(),
                "split_double_page": self.proc_split_double_var.get()
            }
            
            current_config["export"] = {
                "formats": [fmt.strip() for fmt in self.export_formats_var.get().split(",")],
                "pdf_quality": self.export_pdf_quality_var.get(),
                "embed_metadata": self.export_embed_metadata_var.get(),
                "validate_output": self.export_validate_var.get()
            }
            
            current_config["ui"] = {
                "theme": self.ui_theme_var.get(),
                "font_family": self.ui_font_family_var.get(),
                "font_size": self.ui_font_size_var.get(),
                "show_tooltips": self.ui_tooltips_var.get(),
                "confirm_actions": self.ui_confirm_var.get()
            }
            
            # Guardar la configuración
            if not app_config.save_config(current_config):
                if Messagebox:
                    Messagebox.show_error(message="Error al guardar la configuración", title="Error", parent=self)
                return
            
            # Guardar el directorio raíz
            root_dir = Path(self.root_dir_var.get())
            app_config.set_root_dir(root_dir)
            # Persistir también en GeoDocs.db (tabla settings)
            try:
                if db is not None:
                    base = app_config.get_root_dir()
                    db.set_setting(base, 'root_dir', str(root_dir))
            except Exception:
                pass
            
            # Validar y aplicar el tema
            theme = self.ui_theme_var.get().strip()
            if USE_BOOTSTRAP and self.style:
                try:
                    self.style.theme_use(theme)
                    if isinstance(self.parent, (tk.Tk, tk.Toplevel)):
                        apply_titlebar_theme(self.parent)
                except Exception as e:
                    if Messagebox:
                        Messagebox.show_warning(message=f"No se pudo aplicar el tema en vivo: {e}", title="Advertencia", parent=self)
            
            # Aplicar tamaño de fuente
            try:
                import tkinter.font as tkfont
                fs = int(self.ui_font_size_var.get())
                for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
                    try:
                        tkfont.nametofont(name).configure(size=fs)
                    except Exception:
                        pass
            except Exception:
                pass
            
            # Callback personalizado
            if self.on_applied:
                try:
                    self.on_applied(theme, Path(self.root_dir_var.get()), bool(self.apply_all_var.get()))
                except Exception:
                    pass
            
            if Messagebox:
                Messagebox.ok(message="Configuración aplicada correctamente.", title="Configuración", parent=self)
            self.destroy()
            
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(message=f"Error al aplicar cambios: {e}", title="Error", parent=self)


def open_settings_dialog(parent: tk.Tk, on_applied=None):
    """Abre el diálogo de configuración de forma modal"""
    dlg = SettingsDialog(parent, on_applied=on_applied)
    parent.wait_window(dlg)
