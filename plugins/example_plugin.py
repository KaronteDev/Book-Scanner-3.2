#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
example_plugin.py — Plugin de ejemplo para Book Scanner
"""
from pathlib import Path
from typing import Dict, Any
import tkinter as tk
from tkinter import messagebox

try:
    import ttkbootstrap as ttk
except ImportError:
    from tkinter import ttk

from plugins.base_plugin import BasePlugin


class ExamplePlugin(BasePlugin):
    """
    Plugin de ejemplo que demuestra cómo crear un plugin personalizado.
    """
    
    @property
    def name(self) -> str:
        return "Ejemplo de Plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Plugin de demostración con funcionalidades básicas"
    
    @property
    def author(self) -> str:
        return "Book Scanner Team"
    
    def initialize(self, app_context: Dict[str, Any]) -> bool:
        """Inicializar el plugin"""
        self.app_context = app_context
        self.root = app_context.get('root')
        self.base_path = app_context.get('base_path')
        
        print(f"✓ {self.name} v{self.version} inicializado")
        return True
    
    def shutdown(self) -> None:
        """Limpiar recursos"""
        print(f"✓ {self.name} descargado")
    
    def get_menu_items(self) -> list:
        """Items de menú"""
        return [
            {
                'label': 'Acción de Ejemplo',
                'command': self.example_action,
                'icon': '🔧',
                'accelerator': 'Ctrl+Shift+E'
            },
            {
                'label': 'Abrir Configuración',
                'command': self.open_settings,
                'icon': '⚙️'
            }
        ]
    
    def get_toolbar_buttons(self) -> list:
        """Botones de toolbar"""
        return [
            {
                'text': '🔧 Ejemplo',
                'command': self.example_action,
                'tooltip': 'Ejecutar acción de ejemplo'
            }
        ]
    
    def example_action(self):
        """Acción de ejemplo"""
        messagebox.showinfo(
            "Plugin de Ejemplo",
            f"{self.name} v{self.version}\n\nEsta es una acción de ejemplo.",
            parent=self.root
        )
    
    def open_settings(self):
        """Abrir ventana de configuración"""
        win = tk.Toplevel(self.root)
        win.title(f"{self.name} - Configuración")
        win.geometry("400x300")
        
        ttk.Label(
            win,
            text="Configuración del Plugin de Ejemplo",
            font=('', 12, 'bold')
        ).pack(pady=20)
        
        # Ejemplo de configuración
        frame = ttk.Frame(win, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Opción 1:").grid(row=0, column=0, sticky='w', pady=5)
        var1 = tk.BooleanVar(value=self.config.get('option1', False))
        ttk.Checkbutton(frame, variable=var1).grid(row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(frame, text="Valor:").grid(row=1, column=0, sticky='w', pady=5)
        var2 = tk.StringVar(value=self.config.get('value', ''))
        ttk.Entry(frame, textvariable=var2, width=30).grid(row=1, column=1, sticky='w', pady=5)
        
        def save_config():
            self.config['option1'] = var1.get()
            self.config['value'] = var2.get()
            messagebox.showinfo("Configuración", "Configuración guardada", parent=win)
            win.destroy()
        
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Button(btn_frame, text="Guardar", command=save_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=win.destroy).pack(side=tk.RIGHT, padx=5)
    
    def process_image(self, image_path: Path):
        """Procesar imagen (ejemplo: añadir marca de agua)"""
        # Aquí podrías procesar la imagen
        # Por ahora solo loguear
        print(f"[{self.name}] Procesando imagen: {image_path}")
        return image_path
    
    def process_ocr_text(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Procesar texto OCR (ejemplo: limpiar espacios extra)"""
        # Ejemplo: normalizar espacios en blanco
        import re
        cleaned = re.sub(r'\s+', ' ', text).strip()
        return cleaned
    
    def on_project_opened(self, project_path: Path) -> None:
        """Hook: proyecto abierto"""
        print(f"[{self.name}] Proyecto abierto: {project_path}")
    
    def on_page_captured(self, page_path: Path, metadata: Dict[str, Any]) -> None:
        """Hook: página capturada"""
        print(f"[{self.name}] Página capturada: {page_path}")
    
    def on_ocr_completed(self, page_id: int, text: str) -> None:
        """Hook: OCR completado"""
        print(f"[{self.name}] OCR completado para página {page_id}")
