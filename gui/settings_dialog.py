#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
settings_dialog.py — Diálogo de configuración con previsualización de tema y selección de directorio raíz
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog
try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.dialogs import Messagebox
except ImportError:  # Fallbacks
    ttkb = None
    Messagebox = None

from pathlib import Path

from utils.theme_titlebar import apply_titlebar_theme
from utils import app_config


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, on_applied=None):
        # Usamos Toplevel de ttkbootstrap si está disponible para heredar estilo
        toplevel_cls = ttkb.Toplevel if ttkb else tk.Toplevel
        super().__init__(parent) if toplevel_cls is tk.Toplevel else toplevel_cls.__init__(self, parent)

        self.parent = parent
        self.on_applied = on_applied
        self.title("Configuración")
        self.geometry("520x360")
        self.resizable(False, False)

        # Estructura del diálogo
        container = (ttkb.Frame(self, padding=15) if ttkb else tk.Frame(self, padx=15, pady=15))
        container.pack(fill=tk.BOTH, expand=True)

        # Sección: Tema
        (ttkb.Label(container, text="Tema de interfaz:", font=("Open Sans", 10, "bold")) if ttkb else tk.Label(container, text="Tema de interfaz:")).pack(anchor=tk.W)

        self.style = (self.master.style if hasattr(self.master, 'style') else (ttkb.Style() if ttkb else None))
        themes = []
        if self.style:
            try:
                themes = list(self.style.theme_names())
            except Exception:
                themes = []
        current_theme = app_config.get_theme()

        theme_frame = ttkb.Frame(container) if ttkb else tk.Frame(container)
        theme_frame.pack(fill=tk.X, pady=(5, 10))
        self.theme_var = tk.StringVar(value=current_theme)

        if ttkb:
            self.theme_combo = ttkb.Combobox(theme_frame, textvariable=self.theme_var, values=themes, state="readonly")
        else:
            self.theme_combo = tk.OptionMenu(theme_frame, self.theme_var, *themes) if themes else tk.Entry(theme_frame, textvariable=self.theme_var)

        self.theme_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        preview_btn = ttkb.Button(theme_frame, text="Previsualizar", bootstyle="secondary", command=self.preview_theme) if ttkb else tk.Button(theme_frame, text="Previsualizar", command=self.preview_theme)
        preview_btn.pack(side=tk.LEFT, padx=6)

        # Preview area
        preview_label = ttkb.Label(container, text="Vista previa:") if ttkb else tk.Label(container, text="Vista previa:")
        preview_label.pack(anchor=tk.W)
        self.preview_frame = ttkb.Labelframe(container, text="Ejemplo") if ttkb else tk.LabelFrame(container, text="Ejemplo")
        self.preview_frame.pack(fill=tk.X, pady=(5, 15))

        self._build_preview(self.preview_frame)

    # Sección: Directorio raíz
        (ttkb.Label(container, text="Directorio raíz de trabajo:", font=("Open Sans", 10, "bold")) if ttkb else tk.Label(container, text="Directorio raíz de trabajo:")).pack(anchor=tk.W)
        root_frame = ttkb.Frame(container) if ttkb else tk.Frame(container)
        root_frame.pack(fill=tk.X, pady=(5, 0))

        current_root = str(app_config.get_root_dir())
        self.root_dir_var = tk.StringVar(value=current_root)
        entry = ttkb.Entry(root_frame, textvariable=self.root_dir_var) if ttkb else tk.Entry(root_frame, textvariable=self.root_dir_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        browse_btn = (ttkb.Button(root_frame, text="Examinar…", command=self.browse_root, bootstyle="secondary")
                      if ttkb else tk.Button(root_frame, text="Examinar…", command=self.browse_root))
        browse_btn.pack(side=tk.LEFT, padx=6)

        # Sección: Preferencias de UI
        (ttkb.Label(container, text="Preferencias de UI:", font=("Open Sans", 10, "bold")) if ttkb else tk.Label(container, text="Preferencias de UI:")).pack(anchor=tk.W, pady=(12, 0))
        prefs_frame = ttkb.Frame(container) if ttkb else tk.Frame(container)
        prefs_frame.pack(fill=tk.X, pady=(6, 0))
        # Tamaño de fuente
        (ttkb.Label(prefs_frame, text="Tamaño de fuente:") if ttkb else tk.Label(prefs_frame, text="Tamaño de fuente:")).pack(side=tk.LEFT)
        self.font_size_var = tk.IntVar(value=int((app_config.get_ui_prefs() or {}).get("font_size") or 10))
        if ttkb:
            fs = ttkb.Spinbox(prefs_frame, from_=8, to=22, width=5, textvariable=self.font_size_var)
        else:
            fs = tk.Spinbox(prefs_frame, from_=8, to=22, width=5, textvariable=self.font_size_var)
        fs.pack(side=tk.LEFT, padx=(6, 18))
        # Tooltips
        self.tooltips_var = tk.BooleanVar(value=bool((app_config.get_ui_prefs() or {}).get("show_tooltips", True)))
        (ttkb.Checkbutton(prefs_frame, text="Mostrar tooltips", variable=self.tooltips_var) if ttkb else tk.Checkbutton(prefs_frame, text="Mostrar tooltips", variable=self.tooltips_var)).pack(side=tk.LEFT)

        # Toggle: aplicar a todas las ventanas
        self.apply_all_var = tk.BooleanVar(value=False)
        (ttkb.Checkbutton(container, text="Aplicar a todas las ventanas ahora", variable=self.apply_all_var)
         if ttkb else tk.Checkbutton(container, text="Aplicar a todas las ventanas ahora", variable=self.apply_all_var)).pack(anchor=tk.W, pady=(8, 0))

        # Botonera inferior
        btns = ttkb.Frame(container) if ttkb else tk.Frame(container)
        btns.pack(fill=tk.X, pady=(18, 0))
        apply_btn = (ttkb.Button(btns, text="Aplicar", bootstyle="primary", command=self.apply_changes)
                     if ttkb else tk.Button(btns, text="Aplicar", command=self.apply_changes))
        apply_btn.pack(side=tk.RIGHT, padx=5)
        cancel_btn = (ttkb.Button(btns, text="Cancelar", bootstyle="secondary", command=self.destroy)
                      if ttkb else tk.Button(btns, text="Cancelar", command=self.destroy))
        cancel_btn.pack(side=tk.RIGHT)

        # Aplicar estilo de barra de título
        apply_titlebar_theme(self)

        # Modal-like
        self.transient(parent)
        self.grab_set()
        self.focus_set()

    def _build_preview(self, parent):
        frame = ttkb.Frame(parent, padding=10) if ttkb else tk.Frame(parent, padx=10, pady=10)
        frame.pack(fill=tk.X)
        (ttkb.Label(frame, text="Texto de ejemplo") if ttkb else tk.Label(frame, text="Texto de ejemplo")).pack(anchor=tk.W)
        row = ttkb.Frame(frame) if ttkb else tk.Frame(frame)
        row.pack(fill=tk.X, pady=(6, 0))
        (ttkb.Button(row, text="Primario", bootstyle="primary") if ttkb else tk.Button(row, text="Primario")).pack(side=tk.LEFT, padx=3)
        (ttkb.Button(row, text="Info", bootstyle="info") if ttkb else tk.Button(row, text="Info")).pack(side=tk.LEFT, padx=3)
        (ttkb.Button(row, text="Éxito", bootstyle="success") if ttkb else tk.Button(row, text="Éxito")).pack(side=tk.LEFT, padx=3)
        (ttkb.Button(row, text="Peligro", bootstyle="danger") if ttkb else tk.Button(row, text="Peligro")).pack(side=tk.LEFT, padx=3)

    def browse_root(self):
        directory = filedialog.askdirectory(parent=self, title="Seleccione el directorio raíz")
        if directory:
            self.root_dir_var.set(directory)

    def preview_theme(self):
        if not ttkb or not self.style:
            if Messagebox:
                Messagebox.show_info(message="La previsualización de tema requiere ttkbootstrap.", title="Información", parent=self)
            return
        theme = self.theme_var.get().strip()
        try:
            self.style.theme_use(theme)
            # Actualizamos barra de título del diálogo y del parent para apreciar el cambio
            apply_titlebar_theme(self)
            if isinstance(self.parent, (tk.Tk, tk.Toplevel)):
                apply_titlebar_theme(self.parent)
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(message=f"No se pudo aplicar el tema: {e}", title="Error", parent=self)

    def apply_changes(self):
        # Guardar configuración y aplicar en vivo
        chosen_theme = self.theme_var.get().strip()
        chosen_root = Path(self.root_dir_var.get().strip()) if self.root_dir_var.get().strip() else app_config.get_root_dir()

        # Validar tema antes de guardar para evitar inconsistencias
        if ttkb and self.style:
            try:
                self.style.theme_use(chosen_theme)
            except Exception as e:
                if Messagebox:
                    Messagebox.show_error(message=f"Tema inválido: {e}", title="Error", parent=self)
                return

        ok_theme = app_config.set_theme(chosen_theme)
        ok_root = app_config.set_root_dir(chosen_root)
        # Guardar preferencias de UI
        try:
            app_config.set_ui_prefs(font_size=int(self.font_size_var.get()), show_tooltips=bool(self.tooltips_var.get()))
        except Exception:
            pass

        # Aplicación en vivo del tema al root (ya validado)
        if isinstance(self.parent, (tk.Tk, tk.Toplevel)):
            apply_titlebar_theme(self.parent)
        # Aplicación en vivo del tamaño de fuente
        try:
            import tkinter.font as tkfont
            fs = int(self.font_size_var.get())
            for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
                try:
                    tkfont.nametofont(name).configure(size=fs)
                except Exception:
                    pass
        except Exception:
            pass

        if self.on_applied:
            try:
                self.on_applied(chosen_theme, Path(chosen_root), bool(self.apply_all_var.get()))
            except Exception:
                pass

        if Messagebox:
            Messagebox.ok(message="Configuración aplicada correctamente.", title="Configuración", parent=self)
        self.destroy()


def open_settings_dialog(parent: tk.Tk, on_applied=None):
    # Abrir modal y esperar
    dlg = SettingsDialog(parent, on_applied=on_applied)
    parent.wait_window(dlg)
