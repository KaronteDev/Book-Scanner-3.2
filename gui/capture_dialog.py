#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capture_dialog.py — Quick metadata dialog before capturing images
Allows users to fill metadata or reuse previous capture settings
"""
import tkinter as tk
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.dialogs import Messagebox
    USE_BOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    Messagebox = None
    USE_BOOTSTRAP = False
from pathlib import Path
from typing import Optional, Dict, Any
from utils.window_utils import center_to_parent
from utils import db_manager as db


class CaptureMetadataDialog:
    """Simple dialog to enter metadata before capture"""
    
    def __init__(self, parent, output_dir: Path, previous_settings: Optional[Dict[str, Any]] = None):
        self.parent = parent
        self.output_dir = output_dir
        self.previous_settings = previous_settings
        self.result = None  # Will contain the settings if user confirms
        
        # Create modal dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Metadatos de Captura")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Variables for metadata fields
        self.var_titulo = tk.StringVar(value="")
        self.var_autor = tk.StringVar(value="")
        self.var_fecha = tk.StringVar(value="")
        self.var_notas = tk.StringVar(value="")
        self.var_signatura = tk.StringVar(value="")
        
        self._build_ui()
        center_to_parent(self.dialog, parent)
        
    def _build_ui(self):
        """Build the dialog UI"""
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="📝 Metadatos de Captura", 
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack(pady=(0, 15))
        
        # Button to load previous settings
        if self.previous_settings:
            btn_load_prev = ttk.Button(
                main_frame,
                text="⏮ Usar datos anteriores",
                command=self._load_previous_settings,
                bootstyle="info-outline" if USE_BOOTSTRAP else None
            )
            btn_load_prev.pack(pady=(0, 10))
        
        # Form fields
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill='both', expand=True, pady=10)
        
        # Título
        ttk.Label(fields_frame, text="Título:").grid(row=0, column=0, sticky='w', pady=5, padx=(0, 10))
        entry_titulo = ttk.Entry(fields_frame, textvariable=self.var_titulo, width=40)
        entry_titulo.grid(row=0, column=1, sticky='ew', pady=5)
        entry_titulo.focus_set()
        
        # Autor
        ttk.Label(fields_frame, text="Autor:").grid(row=1, column=0, sticky='w', pady=5, padx=(0, 10))
        ttk.Entry(fields_frame, textvariable=self.var_autor, width=40).grid(row=1, column=1, sticky='ew', pady=5)
        
        # Fecha
        ttk.Label(fields_frame, text="Fecha:").grid(row=2, column=0, sticky='w', pady=5, padx=(0, 10))
        ttk.Entry(fields_frame, textvariable=self.var_fecha, width=40).grid(row=2, column=1, sticky='ew', pady=5)
        
        # Signatura
        ttk.Label(fields_frame, text="Signatura:").grid(row=3, column=0, sticky='w', pady=5, padx=(0, 10))
        ttk.Entry(fields_frame, textvariable=self.var_signatura, width=40).grid(row=3, column=1, sticky='ew', pady=5)
        
        # Notas
        ttk.Label(fields_frame, text="Notas:").grid(row=4, column=0, sticky='w', pady=5, padx=(0, 10))
        ttk.Entry(fields_frame, textvariable=self.var_notas, width=40).grid(row=4, column=1, sticky='ew', pady=5)
        
        fields_frame.columnconfigure(1, weight=1)
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=(15, 0))
        
        btn_ok = ttk.Button(
            buttons_frame,
            text="✓ Capturar",
            command=self._on_ok,
            bootstyle="success" if USE_BOOTSTRAP else None,
            width=15
        )
        btn_ok.pack(side='left', padx=5)
        
        btn_skip = ttk.Button(
            buttons_frame,
            text="⏭ Capturar sin metadatos",
            command=self._on_skip,
            bootstyle="secondary" if USE_BOOTSTRAP else None,
            width=20
        )
        btn_skip.pack(side='left', padx=5)
        
        btn_cancel = ttk.Button(
            buttons_frame,
            text="✕ Cancelar",
            command=self._on_cancel,
            bootstyle="danger" if USE_BOOTSTRAP else None,
            width=15
        )
        btn_cancel.pack(side='left', padx=5)
        
        # Bind Enter key to OK
        self.dialog.bind('<Return>', lambda e: self._on_ok())
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        
    def _load_previous_settings(self):
        """Load previous capture settings into form"""
        if not self.previous_settings:
            return
        
        self.var_titulo.set(self.previous_settings.get('titulo', ''))
        self.var_autor.set(self.previous_settings.get('autor', ''))
        self.var_fecha.set(self.previous_settings.get('fecha', ''))
        self.var_signatura.set(self.previous_settings.get('signatura', ''))
        self.var_notas.set(self.previous_settings.get('notas', ''))
        
        if Messagebox:
            Messagebox.show_info(
                title="Datos Cargados",
                message="Se han cargado los datos de la última captura",
                parent=self.dialog
            )
        
    def _on_ok(self):
        """User confirmed - save settings and close"""
        self.result = {
            'titulo': self.var_titulo.get().strip(),
            'autor': self.var_autor.get().strip(),
            'fecha': self.var_fecha.get().strip(),
            'signatura': self.var_signatura.get().strip(),
            'notas': self.var_notas.get().strip()
        }
        
        # Save settings for next time
        db.save_capture_settings(self.output_dir, self.result)
        
        self.dialog.destroy()
        
    def _on_skip(self):
        """User wants to capture without metadata"""
        self.result = {}  # Empty dict signals "skip metadata but continue"
        self.dialog.destroy()
        
    def _on_cancel(self):
        """User cancelled - don't capture"""
        self.result = None
        self.dialog.destroy()
        
    def show(self) -> Optional[Dict[str, Any]]:
        """Show dialog and return result (None if cancelled)"""
        self.dialog.wait_window()
        return self.result


def show_capture_dialog(parent, output_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Show capture metadata dialog.
    Returns:
        - Dict with metadata if user filled form
        - Empty dict {} if user skipped metadata
        - None if user cancelled
    """
    previous = db.get_last_capture_settings(output_dir)
    dialog = CaptureMetadataDialog(parent, output_dir, previous)
    return dialog.show()
