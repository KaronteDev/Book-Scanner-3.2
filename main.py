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
    import ttkbootstrap as ttk
    from ttkbootstrap.dialogs import Messagebox
    USE_BOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    Messagebox = None
    USE_BOOTSTRAP = False
from pathlib import Path
import socket
import tempfile

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
from utils.theme_titlebar import apply_titlebar_theme
from utils.window_utils import center_to_parent
from utils import app_config
try:
    from gui.settings_dialog import open_settings_dialog
except Exception:
    open_settings_dialog = None

APP_NAME = "GeoDocs Scanner"
APP_VERSION = "v32.3 PLUS"
LOCK_SOCKET = None  # Variable global para mantener el socket activo


def check_single_instance():
    """Verifica que solo haya una instancia de la aplicación ejecutándose"""
    global LOCK_SOCKET
    try:
        # Crear un socket en un puerto específico
        LOCK_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Intentar vincular al puerto local
        LOCK_SOCKET.bind(('127.0.0.1', 47200))  # Puerto específico para esta app
        return True
    except socket.error:
        # El puerto ya está en uso, otra instancia está ejecutándose
        return False


class ModuleSelectorApp:
    """Pantalla inicial para seleccionar el módulo de trabajo"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("650x600")
        self.root.resizable(False, False)
        
        # Set application icon
        self.set_icon()
        
        # Apply title bar theme automatically from ttkbootstrap
        apply_titlebar_theme(self.root)
        
        # Center window
        self.center_window()
        
        # Configure button font styles for bootstrap
        if USE_BOOTSTRAP:
            self.configure_button_styles()
        
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
    
    def configure_button_styles(self):
        """Configure custom font styles for buttons when using ttkbootstrap"""
        if USE_BOOTSTRAP:
            style = ttk.Style()
            # Configure larger font for module buttons
            style.configure("primary.TButton", font=("Open Sans", 11, "normal"))
            style.configure("info.TButton", font=("Open Sans", 11, "normal"))
            style.configure("success.TButton", font=("Open Sans", 11, "normal"))
            style.configure("secondary.TButton", font=("Open Sans", 11, "normal"))
    
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
        header_frame = ttk.Frame(self.root, padding=20) if USE_BOOTSTRAP else tk.Frame(self.root, padx=20, pady=20)
        header_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            header_frame,
            text=f"{APP_NAME} {APP_VERSION}",
            font=("Open Sans", 18, "bold")
        ) if USE_BOOTSTRAP else tk.Label(
            header_frame,
            text=f"{APP_NAME} {APP_VERSION}",
            font=("Open Sans", 18, "bold")
        )
        title_label.pack()

        subtitle_label = ttk.Label(
            header_frame,
            text="Sistema Avanzado de Digitalización y Anotación Documental",
            font=("Open Sans", 10)
        ) if USE_BOOTSTRAP else tk.Label(
            header_frame,
            text="Sistema Avanzado de Digitalización y Anotación Documental",
            font=("Open Sans", 10)
        )
        subtitle_label.pack()

        # Separator
        if USE_BOOTSTRAP:
            ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=10)
        else:
            tk.Frame(self.root, height=2, bg="gray").pack(fill=tk.X, padx=20, pady=10)

        # Module selection frame
        modules_frame = ttk.Frame(self.root, padding=20) if USE_BOOTSTRAP else tk.Frame(self.root, padx=20, pady=20)
        modules_frame.pack(fill=tk.BOTH, expand=True)

        modules_label = ttk.Label(
            modules_frame,
            text="Seleccione un módulo:",
            font=("Open Sans", 12, "bold")
        ) if USE_BOOTSTRAP else tk.Label(
            modules_frame,
            text="Seleccione un módulo:",
            font=("Open Sans", 12, "bold")
        )
        modules_label.pack(pady=(0, 15))

        # Grid container for two columns
        grid_container = ttk.Frame(modules_frame) if USE_BOOTSTRAP else tk.Frame(modules_frame)
        grid_container.pack(fill=tk.BOTH, expand=True)

        # Configure columns to have equal weight
        grid_container.columnconfigure(0, weight=1)
        grid_container.columnconfigure(1, weight=1)

        # Column 1 - Row 1: Scanner
        col1_frame = ttk.Frame(grid_container, padding=10) if USE_BOOTSTRAP else tk.Frame(grid_container, padx=10, pady=10)
        col1_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        btn_scanner = ttk.Button(
            col1_frame,
            text="📸 Módulo de Escaneo",
            command=self.open_scanner,
            width=28,
            bootstyle="primary" if USE_BOOTSTRAP else None
        ) if USE_BOOTSTRAP else tk.Button(
            col1_frame,
            text="📸 Módulo de Escaneo",
            command=self.open_scanner,
            width=28,
            height=2,
            font=("Open Sans", 11, "bold")
        )
        if USE_BOOTSTRAP:
            btn_scanner.configure(style="primary.TButton")
        btn_scanner.pack(pady=(0, 5), ipady=8)

        label1 = ttk.Label(
            col1_frame,
            text="Captura y procesamiento\nde imágenes",
            font=("Open Sans", 7),
            foreground="gray" if not USE_BOOTSTRAP else None,
            justify=tk.CENTER
        ) if USE_BOOTSTRAP else tk.Label(
            col1_frame,
            text="Captura y procesamiento\nde imágenes",
            font=("Open Sans", 7),
            foreground="gray",
            justify=tk.CENTER
        )
        label1.pack()

        # Column 2 - Row 1: Annotation
        col2_frame = ttk.Frame(grid_container, padding=10) if USE_BOOTSTRAP else tk.Frame(grid_container, padx=10, pady=10)
        col2_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        btn_annotation = ttk.Button(
            col2_frame,
            text="📝 Anotación y OCR",
            command=self.open_annotation,
            width=28,
            bootstyle="info" if USE_BOOTSTRAP else None
        ) if USE_BOOTSTRAP else tk.Button(
            col2_frame,
            text="📝 Anotación y OCR",
            command=self.open_annotation,
            width=28,
            height=2,
            font=("Open Sans", 11, "bold")
        )
        if USE_BOOTSTRAP:
            btn_annotation.configure(style="info.TButton")
        btn_annotation.pack(pady=(0, 5), ipady=8)

        label2 = ttk.Label(
            col2_frame,
            text="Transcripción, corrección\ny anotación académica",
            font=("Open Sans", 7),
            foreground="gray" if not USE_BOOTSTRAP else None,
            justify=tk.CENTER
        ) if USE_BOOTSTRAP else tk.Label(
            col2_frame,
            text="Transcripción, corrección\ny anotación académica",
            font=("Open Sans", 7),
            foreground="gray",
            justify=tk.CENTER
        )
        label2.pack()

        # Column 1 - Row 2: Export
        col3_frame = ttk.Frame(grid_container, padding=10) if USE_BOOTSTRAP else tk.Frame(grid_container, padx=10, pady=10)
        col3_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        btn_export = ttk.Button(
            col3_frame,
            text="📦 Exportación",
            command=self.open_export,
            width=28,
            bootstyle="success" if USE_BOOTSTRAP else None
        ) if USE_BOOTSTRAP else tk.Button(
            col3_frame,
            text="📦 Exportación",
            command=self.open_export,
            width=28,
            height=2,
            font=("Open Sans", 11, "bold")
        )
        if USE_BOOTSTRAP:
            btn_export.configure(style="success.TButton")
        btn_export.pack(pady=(0, 5), ipady=8)

        label3 = ttk.Label(
            col3_frame,
            text="Dublin Core, IIIF,\nTEI-XML, GeoJSON",
            font=("Open Sans", 7),
            foreground="gray" if not USE_BOOTSTRAP else None,
            justify=tk.CENTER
        ) if USE_BOOTSTRAP else tk.Label(
            col3_frame,
            text="Dublin Core, IIIF,\nTEI-XML, GeoJSON",
            font=("Open Sans", 7),
            foreground="gray",
            justify=tk.CENTER
        )
        label3.pack()

        # Column 2 - Row 2: Metadata
        col4_frame = ttk.Frame(grid_container, padding=10) if USE_BOOTSTRAP else tk.Frame(grid_container, padx=10, pady=10)
        col4_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        btn_meta = ttk.Button(
            col4_frame,
            text="📁 Proyectos y Metadatos",
            command=self.open_metadata_manager,
            width=28,
            bootstyle="secondary" if USE_BOOTSTRAP else None
        ) if USE_BOOTSTRAP else tk.Button(
            col4_frame,
            text="📁 Proyectos y Metadatos",
            command=self.open_metadata_manager,
            width=28,
            height=2,
            font=("Open Sans", 11, "bold")
        )
        if USE_BOOTSTRAP:
            btn_meta.configure(style="secondary.TButton")
        btn_meta.pack(pady=(0, 5), ipady=8)

        label4 = ttk.Label(
            col4_frame,
            text="Gestión de proyectos,\narchivos, fondos y etiquetas",
            font=("Open Sans", 7),
            foreground="gray" if not USE_BOOTSTRAP else None,
            justify=tk.CENTER
        ) if USE_BOOTSTRAP else tk.Label(
            col4_frame,
            text="Gestión de proyectos,\narchivos, fondos y etiquetas",
            font=("Open Sans", 7),
            foreground="gray",
            justify=tk.CENTER
        )
        label4.pack()

        # Footer
        footer_frame = ttk.Frame(self.root, padding=10) if USE_BOOTSTRAP else tk.Frame(self.root, padx=10, pady=10)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)

        btn_settings = ttk.Button(
            footer_frame,
            text="⚙️ Configuración",
            command=self.open_settings,
            bootstyle="secondary" if USE_BOOTSTRAP else None
        ) if USE_BOOTSTRAP else tk.Button(
            footer_frame,
            text="⚙️ Configuración",
            command=self.open_settings
        )
        btn_settings.pack(side=tk.LEFT, padx=5)

        btn_help = ttk.Button(
            footer_frame,
            text="❓ Ayuda",
            command=self.open_help,
            bootstyle="secondary" if USE_BOOTSTRAP else None
        ) if USE_BOOTSTRAP else tk.Button(
            footer_frame,
            text="❓ Ayuda",
            command=self.open_help
        )
        btn_help.pack(side=tk.LEFT, padx=5)

        btn_exit = ttk.Button(
            footer_frame,
            text="Salir",
            command=self.root.quit,
            bootstyle="danger" if USE_BOOTSTRAP else None
        ) if USE_BOOTSTRAP else tk.Button(
            footer_frame,
            text="Salir",
            command=self.root.quit
        )
        btn_exit.pack(side=tk.RIGHT, padx=5)
    
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
                messagebox.showerror("Error", f"No se pudo abrir el módulo de escaneo:\n{str(e)}", parent=self.root)
    
    def open_annotation(self):
        """Launch annotation/OCR module"""
        try:
            from gui.annotation_view import AnnotationWindow
            # Center only when no saved geometry
            saved = None
            try:
                saved = app_config.get_window_geometry("annotation")
            except Exception:
                saved = None
            annotation_win = ttk.Toplevel(self.root) if USE_BOOTSTRAP else tk.Toplevel(self.root)
            AnnotationWindow(annotation_win)
            if not saved:
                center_to_parent(annotation_win, self.root)
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(
                    message=f"No se pudo abrir el módulo de anotación:\n{str(e)}",
                    title="Error",
                    parent=self.root
                )
            else:
                messagebox.showerror("Error", f"No se pudo abrir el módulo de anotación:\n{str(e)}", parent=self.root)
    
    def open_export(self):
        """Launch export module"""
        try:
            from gui.export_view import ExportWindow
            saved = None
            try:
                saved = app_config.get_window_geometry("export")
            except Exception:
                saved = None
            export_win = ttk.Toplevel(self.root) if USE_BOOTSTRAP else tk.Toplevel(self.root)
            ExportWindow(export_win)
            if not saved:
                center_to_parent(export_win, self.root)
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(
                    message=f"No se pudo abrir el módulo de exportación:\n{str(e)}",
                    title="Error",
                    parent=self.root
                )
            else:
                messagebox.showerror("Error", f"No se pudo abrir el módulo de exportación:\n{str(e)}", parent=self.root)
    
    def open_settings(self):
        """Open settings dialog with live preview and persistence"""
        if open_settings_dialog and USE_BOOTSTRAP:
            def on_applied(theme_name, root_dir_path, apply_all=False):
                # Refrescar barra de título de ventanas hijas abiertas
                try:
                    if apply_all:
                        # Walk through all children and nested toplevels
                        queue = [self.root]
                        seen = set()
                        while queue:
                            win = queue.pop(0)
                            if id(win) in seen:
                                continue
                            seen.add(id(win))
                            try:
                                apply_titlebar_theme(win)
                            except Exception:
                                pass
                            try:
                                for ch in win.winfo_children():
                                    if isinstance(ch, (tk.Toplevel,)):
                                        queue.append(ch)
                            except Exception:
                                pass
                    else:
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
                messagebox.showinfo("Configuración", "Para configurar tema y directorio raíz, edite data/app_config.json", parent=self.root)

    def open_metadata_manager(self):
        try:
            from gui.metadata_manager import MetadataManager
            MetadataManager(self.root)
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(
                    message=f"No se pudo abrir la gestión de metadatos:\n{str(e)}",
                    title="Error",
                    parent=self.root
                )
            else:
                messagebox.showerror("Error", f"No se pudo abrir la gestión de metadatos:\n{str(e)}", parent=self.root)
    
    def open_help(self):
        """Open help/documentation"""
        if Messagebox:
            Messagebox.show_info(
                message=f"{APP_NAME} {APP_VERSION}\n\nConsulte README.md para documentación completa.\n\nAtajos de teclado:\n- F1: Ayuda\n- F5: Recargar\n- Ctrl+Q: Salir",
                title="Ayuda",
                parent=self.root
            )
        else:
            messagebox.showinfo("Ayuda", f"{APP_NAME} {APP_VERSION}\n\n"
                                 "Consulte README.md para documentación completa.\n\n"
                                 "Atajos de teclado:\n"
                                 "- F1: Ayuda\n"
                                 "- F5: Recargar\n"
                                 "- Ctrl+Q: Salir", parent=self.root)


def main():
    """Main entry point"""
    # Verificar que solo haya una instancia ejecutándose
    if not check_single_instance():
        # Mostrar mensaje de error
        root_temp = tk.Tk()
        root_temp.withdraw()  # Ocultar ventana principal
        messagebox.showerror(
            "Instancia ya en ejecución",
            f"{APP_NAME} ya está ejecutándose.\n\nSolo puede haber una instancia activa a la vez.",
            parent=root_temp
        )
        root_temp.destroy()
        sys.exit(1)
    
    if USE_BOOTSTRAP:
        # Lee el tema desde la configuración con reserva a 'superhero'
        chosen = app_config.get_theme("superhero")
        try:
            root = ttk.Window(themename=chosen)
        except Exception:
            root = ttk.Window(themename="superhero")
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
        global LOCK_SOCKET
        try:
            app_config.set_window_geometry("main", root.geometry())
        except Exception:
            pass
        # Cerrar el socket de bloqueo
        if LOCK_SOCKET:
            try:
                LOCK_SOCKET.close()
            except Exception:
                pass
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
