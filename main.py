#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — GeoDocs Scanner v32.3 PLUS
Punto de entrada principal con selector de módulos
"""
import os
import sys
import tkinter as tk
from tkinter import messagebox
try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.dialogs import Messagebox
except ImportError:
    ttkb = None
    Messagebox = None
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
from utils.theme_titlebar import apply_titlebar_theme
from utils import app_config
try:
    from gui.settings_dialog import open_settings_dialog
except Exception:
    open_settings_dialog = None

APP_NAME = "GeoDocs Scanner"
APP_VERSION = "v32.3 PLUS"

class ModuleSelectorApp:
    """Pantalla inicial para seleccionar el módulo de trabajo"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("600x550")
        self.root.resizable(False, False)
        
        # Set application icon
        self.set_icon()
        
        # Apply title bar theme automatically from ttkbootstrap
        apply_titlebar_theme(self.root)
        
        # Center window
        self.center_window()
        
        # Setup UI
        self.create_widgets()
        
        # Initialize database
        self.init_database()
    
    # Title bar theme handled via utils.theme_titlebar
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def set_icon(self):
        """Set application icon"""
        try:
            icon_dir = Path(__file__).resolve().parent / "assets" / "icons"
            ico_path = icon_dir / "app.ico"
            png_path = icon_dir / "app.png"
            
            # Try Windows .ico first (preferred on Windows)
            if ico_path.exists():
                try:
                    self.root.iconbitmap(default=str(ico_path))
                    return
                except Exception:
                    pass
            
            # Cross-platform PNG fallback
            if png_path.exists():
                try:
                    from PIL import Image, ImageTk
                    icon_img = ImageTk.PhotoImage(Image.open(str(png_path)))
                    self.root.iconphoto(True, icon_img)
                    # Keep reference to prevent garbage collection
                    self.root._icon_img = icon_img
                except Exception:
                    pass
        except Exception:
            # Icon loading is optional; don't break app if it fails
            pass
    
    def create_widgets(self):
        """Create the UI elements"""
        # Header
        header_frame = ttkb.Frame(self.root, padding=20)
        header_frame.pack(fill=tk.X)

        title_label = ttkb.Label(
            header_frame,
            text=f"{APP_NAME} {APP_VERSION}",
            font=("Open Sans", 18, "bold")
        )
        title_label.pack()

        subtitle_label = ttkb.Label(
            header_frame,
            text="Sistema Avanzado de Digitalización y Anotación Documental",
            font=("Open Sans", 10)
        )
        subtitle_label.pack()

        # Separator
        ttkb.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=10)

        # Module selection frame
        modules_frame = ttkb.Frame(self.root, padding=20)
        modules_frame.pack(fill=tk.BOTH, expand=True)

        modules_label = ttkb.Label(
            modules_frame,
            text="Seleccione un módulo:",
            font=("Open Sans", 12, "bold")
        )
        modules_label.pack(pady=(0, 15))

        # Module buttons
        btn_scanner = ttkb.Button(
            modules_frame,
            text="📸 Módulo de Escaneo",
            command=self.open_scanner,
            width=30,
            bootstyle="primary"
        )
        btn_scanner.pack(pady=5)

        ttkb.Label(
            modules_frame,
            text="Captura y procesamiento de imágenes",
            font=("Open Sans", 8),
            foreground="gray"
        ).pack()

        btn_annotation = ttkb.Button(
            modules_frame,
            text="📝 Módulo de Anotación y OCR",
            command=self.open_annotation,
            width=30,
            bootstyle="info"
        )
        btn_annotation.pack(pady=(15, 5))

        ttkb.Label(
            modules_frame,
            text="Transcripción, corrección y anotación académica",
            font=("Open Sans", 8),
            foreground="gray"
        ).pack()

        btn_export = ttkb.Button(
            modules_frame,
            text="📦 Módulo de Exportación",
            command=self.open_export,
            width=30,
            bootstyle="success"
        )
        btn_export.pack(pady=(15, 5))

        ttkb.Label(
            modules_frame,
            text="Dublin Core, IIIF, TEI-XML, GeoJSON",
            font=("Open Sans", 8),
            foreground="gray"
        ).pack()

        # Footer
        footer_frame = ttkb.Frame(self.root, padding=10)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttkb.Button(
            footer_frame,
            text="⚙️ Configuración",
            command=self.open_settings,
            bootstyle="secondary"
        ).pack(side=tk.LEFT, padx=5)

        ttkb.Button(
            footer_frame,
            text="❓ Ayuda",
            command=self.open_help,
            bootstyle="secondary"
        ).pack(side=tk.LEFT, padx=5)

        ttkb.Button(
            footer_frame,
            text="Salir",
            command=self.root.quit,
            bootstyle="danger"
        ).pack(side=tk.RIGHT, padx=5)
    
    def init_database(self):
        """Initialize global database"""
        from utils.db_manager import init_global_db
        base_path = app_config.get_root_dir()
        init_global_db(base_path)
    
    def open_scanner(self):
        """Launch scanner module"""
        try:
            from gui.scanner_module import ScannerWindow
            scanner_win = ScannerWindow(self.root)
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(
                    message=f"No se pudo abrir el módulo de escaneo:\n{str(e)}",
                    title="Error",
                    parent=self.root
                )
            else:
                messagebox.showerror(
                    "Error",
                    f"No se pudo abrir el módulo de escaneo:\n{str(e)}"
                )
    
    def open_annotation(self):
        """Launch annotation/OCR module"""
        try:
            from gui.annotation_view import AnnotationWindow
            annotation_win = ttkb.Toplevel(self.root) if ttkb else tk.Toplevel(self.root)
            AnnotationWindow(annotation_win)
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(
                    message=f"No se pudo abrir el módulo de anotación:\n{str(e)}",
                    title="Error",
                    parent=self.root
                )
            else:
                messagebox.showerror(
                    "Error",
                    f"No se pudo abrir el módulo de anotación:\n{str(e)}"
                )
    
    def open_export(self):
        """Launch export module"""
        try:
            from gui.export_view import ExportWindow
            export_win = ttkb.Toplevel(self.root) if ttkb else tk.Toplevel(self.root)
            ExportWindow(export_win)
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(
                    message=f"No se pudo abrir el módulo de exportación:\n{str(e)}",
                    title="Error",
                    parent=self.root
                )
            else:
                messagebox.showerror(
                    "Error",
                    f"No se pudo abrir el módulo de exportación:\n{str(e)}"
                )
    
    def open_settings(self):
        """Open settings dialog with live preview and persistence"""
        if open_settings_dialog and ttkb:
            def on_applied(theme_name, root_dir_path):
                # Refrescar barra de título de ventanas hijas abiertas
                try:
                    for child in self.root.winfo_children():
                        try:
                            apply_titlebar_theme(child)
                        except Exception:
                            continue
                except Exception:
                    pass
            open_settings_dialog(self.root, on_applied=on_applied)
        else:
            if Messagebox:
                Messagebox.show_info(
                    message="Para configurar tema y directorio raíz, instale ttkbootstrap o edite data/app_config.json",
                    title="Configuración",
                    parent=self.root
                )
            else:
                messagebox.showinfo(
                    "Configuración",
                    "Para configurar tema y directorio raíz, edite data/app_config.json"
                )
    
    def open_help(self):
        """Open help/documentation"""
        if Messagebox:
            Messagebox.show_info(
                message=f"{APP_NAME} {APP_VERSION}\n\nConsulte README.md para documentación completa.\n\nAtajos de teclado:\n- F1: Ayuda\n- F5: Recargar\n- Ctrl+Q: Salir",
                title="Ayuda",
                parent=self.root
            )
        else:
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
    if ttkb:
        # Lee el tema desde la configuración con reserva a 'superhero'
        chosen = app_config.get_theme("superhero")
        try:
            root = ttkb.Window(themename=chosen)
        except Exception:
            root = ttkb.Window(themename="superhero")
    else:
        root = tk.Tk()
    # Aplicar preferencias de UI (tamaño de fuente)
    try:
        import tkinter.font as tkfont
        ui = app_config.get_ui_prefs()
        fs = int(ui.get("font_size") or 10)
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(name).configure(size=fs)
            except Exception:
                pass
    except Exception:
        pass

    app = ModuleSelectorApp(root)
    # Restaurar geometría guardada del main
    try:
        geo = app_config.get_window_geometry("main")
        if isinstance(geo, str) and geo:
            root.geometry(geo)
    except Exception:
        pass
    # Keyboard shortcuts
    root.bind('<F1>', lambda e: app.open_help())
    root.bind('<Control-q>', lambda e: root.quit())
    # Guardar geometría al cerrar
    def _on_close():
        try:
            app_config.set_window_geometry("main", root.geometry())
        except Exception:
            pass
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
