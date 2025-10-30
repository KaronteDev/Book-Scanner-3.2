#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — GeoDocs Scanner v32.3 PLUS
Punto de entrada principal con selector de módulos
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

APP_NAME = "GeoDocs Scanner"
APP_VERSION = "v32.3 PLUS"

class ModuleSelectorApp:
    """Pantalla inicial para seleccionar el módulo de trabajo"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # Center window
        self.center_window()
        
        # Setup UI
        self.create_widgets()
        
        # Initialize database
        self.init_database()
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """Create the UI elements"""
        # Header
        header_frame = ttk.Frame(self.root, padding="20")
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            header_frame,
            text=f"{APP_NAME} {APP_VERSION}",
            font=("Open Sans", 18, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            header_frame,
            text="Sistema Avanzado de Digitalización y Anotación Documental",
            font=("Open Sans", 10)
        )
        subtitle_label.pack()
        
        # Separator
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=10)
        
        # Module selection frame
        modules_frame = ttk.Frame(self.root, padding="20")
        modules_frame.pack(fill=tk.BOTH, expand=True)
        
        modules_label = ttk.Label(
            modules_frame,
            text="Seleccione un módulo:",
            font=("Open Sans", 12, "bold")
        )
        modules_label.pack(pady=(0, 15))
        
        # Module buttons
        btn_scanner = ttk.Button(
            modules_frame,
            text="📸 Módulo de Escaneo",
            command=self.open_scanner,
            width=30
        )
        btn_scanner.pack(pady=5)
        
        ttk.Label(
            modules_frame,
            text="Captura y procesamiento de imágenes",
            font=("Open Sans", 8),
            foreground="gray"
        ).pack()
        
        btn_annotation = ttk.Button(
            modules_frame,
            text="📝 Módulo de Anotación y OCR",
            command=self.open_annotation,
            width=30
        )
        btn_annotation.pack(pady=(15, 5))
        
        ttk.Label(
            modules_frame,
            text="Transcripción, corrección y anotación académica",
            font=("Open Sans", 8),
            foreground="gray"
        ).pack()
        
        btn_export = ttk.Button(
            modules_frame,
            text="📦 Módulo de Exportación",
            command=self.open_export,
            width=30
        )
        btn_export.pack(pady=(15, 5))
        
        ttk.Label(
            modules_frame,
            text="Dublin Core, IIIF, TEI-XML, GeoJSON",
            font=("Open Sans", 8),
            foreground="gray"
        ).pack()
        
        # Footer
        footer_frame = ttk.Frame(self.root, padding="10")
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Button(
            footer_frame,
            text="⚙️ Configuración",
            command=self.open_settings
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            footer_frame,
            text="❓ Ayuda",
            command=self.open_help
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            footer_frame,
            text="Salir",
            command=self.root.quit
        ).pack(side=tk.RIGHT, padx=5)
    
    def init_database(self):
        """Initialize global database"""
        from utils.db_manager import init_global_db
        base_path = Path(__file__).parent
        init_global_db(base_path)
    
    def open_scanner(self):
        """Launch scanner module"""
        try:
            from gui.scanner_module import ScannerWindow
            scanner_win = ScannerWindow(self.root)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el módulo de escaneo:\n{str(e)}"
            )
    
    def open_annotation(self):
        """Launch annotation/OCR module"""
        try:
            from gui.annotation_view import AnnotationWindow
            annotation_win = tk.Toplevel(self.root)
            AnnotationWindow(annotation_win)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el módulo de anotación:\n{str(e)}"
            )
    
    def open_export(self):
        """Launch export module"""
        try:
            from gui.export_view import ExportWindow
            export_win = tk.Toplevel(self.root)
            ExportWindow(export_win)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el módulo de exportación:\n{str(e)}"
            )
    
    def open_settings(self):
        """Open settings dialog"""
        messagebox.showinfo(
            "Configuración",
            "Módulo de configuración en desarrollo.\n\n"
            "Por ahora, edite los archivos JSON en la carpeta /data"
        )
    
    def open_help(self):
        """Open help/documentation"""
        messagebox.showinfo(
            "Ayuda",
            f"{APP_NAME} {APP_VERSION}\n\n"
            "Consulte README.md para documentación completa.\n\n"
            "Atajos de teclado:\n"
            "- F1: Ayuda\n"
            "- F5: Recargar\n"
            "- Ctrl+Q: Salir"
        )


def main():
    """Main entry point"""
    root = tk.Tk()
    
    # Try to use ttkbootstrap for better styling (optional)
    try:
        import importlib
        ttkb = importlib.import_module("ttkbootstrap")  # optional dependency
        root = ttkb.Window(themename="flatly")
    except Exception:
        # Fallback to standard Tk if ttkbootstrap is unavailable
        pass
    
    app = ModuleSelectorApp(root)
    
    # Keyboard shortcuts
    root.bind('<F1>', lambda e: app.open_help())
    root.bind('<Control-q>', lambda e: root.quit())
    
    root.mainloop()


if __name__ == "__main__":
    main()
