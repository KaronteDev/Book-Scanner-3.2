#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_view.py — Scanner module interface
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# For now, we'll integrate the existing scanner
# In future iterations, this can be refactored further

from utils.db_manager import (
    create_project,
    list_projects,
    get_project,
    ensure_project_dirs,
    sync_pages_from_folder,
)
from utils import app_config


class ScannerWindow:
    """Scanner module window"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("GeoDocs Scanner - Módulo de Escaneo")
        self.root.geometry("1024x768")
        
        # Toolbar
        toolbar = ttk.Frame(root)
        toolbar.pack(fill=tk.X, padx=10, pady=6)

        ttk.Button(toolbar, text="➕ Nuevo proyecto", command=self.new_project_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="🔄 Sincronizar páginas", command=self.sync_pages).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="📂 Abrir carpeta del proyecto", command=self.open_project_folder).pack(side=tk.LEFT, padx=4)

        ttk.Label(toolbar, text="Proyecto:").pack(side=tk.LEFT, padx=(20,4))
        self.project_combo = ttk.Combobox(toolbar, state="readonly", width=50)
        self.project_combo.pack(side=tk.LEFT)
        self.project_combo.bind('<<ComboboxSelected>>', self.on_project_selected)

        # Import existing scanner GUI
        try:
            # For now, show placeholder
            frame = ttk.Frame(root, padding=20)
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(
                frame,
                text="📸 Módulo de Escaneo",
                font=("Open Sans", 18, "bold")
            ).pack(pady=20)
            
            ttk.Label(
                frame,
                text="Funcionalidades:\n\n"
                     "• Captura desde cámara en tiempo real\n"
                     "• Corrección automática de perspectiva\n"
                     "• Modo libro abierto (división automática)\n"
                     "• Eliminación de dedos y soportes\n"
                     "• Calibración A3, A4, A5, A6\n"
                     "• Ajustes de brillo, contraste y nitidez\n\n"
                     "El módulo completo se está integrando...",
                justify=tk.LEFT,
                font=("Open Sans", 11)
            ).pack(pady=20)
            
            ttk.Label(
                frame,
                text="💡 Atajos de teclado:\n"
                     "ESPACIO - Capturar imagen\n"
                     "C - Calibrar cámara\n"
                     "P - Configurar proyecto\n"
                     "ESC - Cerrar",
                justify=tk.LEFT,
                font=("Open Sans", 9),
                foreground="gray"
            ).pack(pady=20)
            
            # Action buttons
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(pady=20)
            
            ttk.Button(
                btn_frame,
                text="Abrir escáner existente",
                command=self.open_existing_scanner
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                btn_frame,
                text="Cerrar",
                command=root.destroy
            ).pack(side=tk.LEFT, padx=5)
            
            # Load initial projects into combobox
            self.reload_projects()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el módulo:\n{str(e)}", parent=self.root)
    
    def open_existing_scanner(self):
        """Launch the new modular scanner"""
        try:
            from gui.scanner_module import ScannerWindow
            
            # Get current project directory if available
            project_dir = None
            if self.current_project:
                project_dir = Path(self.current_project['carpeta_raiz'])
            
            # Open scanner window
            scanner_win = ScannerWindow(self.root, project_dir)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el escáner:\n{str(e)}", parent=self.root)

    # --- Project management ---
    def reload_projects(self):
        try:
            base_path = app_config.get_root_dir()
            projects = list_projects(base_path)
            self._projects = projects
            names = [p['titulo'] for p in projects]
            self.project_combo['values'] = names
            if names:
                self.project_combo.current(0)
                self.on_project_selected(None)
        except Exception as e:
            messagebox.showerror("Proyectos", f"Error listando proyectos: {e}", parent=self.root)

    def on_project_selected(self, _):
        idx = self.project_combo.current()
        if idx >= 0 and idx < len(self._projects):
            self.current_project = self._projects[idx]

    def new_project_dialog(self):
        win = tk.Toplevel(self.root)
        try:
            from utils.window_utils import center_to_parent
            center_to_parent(win, self.root)
        except Exception:
            pass
        win.title("Nuevo proyecto")
        win.geometry("500x320")
        win.transient(self.root)
        frm = ttk.Frame(win, padding=12); frm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frm, text="Título del proyecto:").grid(row=0, column=0, sticky="w")
        var_title = tk.StringVar()
        ttk.Entry(frm, textvariable=var_title, width=40).grid(row=0, column=1, sticky="we")

        ttk.Label(frm, text="Carpeta raíz:").grid(row=1, column=0, sticky="w", pady=(8,0))
        var_dir = tk.StringVar(value=str(app_config.resolve_path("projects_dir", ensure=True) / "Proyecto_nuevo"))
        e_dir = ttk.Entry(frm, textvariable=var_dir, width=40)
        e_dir.grid(row=1, column=1, sticky="we", pady=(8,0))
        def pick_dir():
            p = filedialog.askdirectory(title="Seleccionar carpeta del proyecto")
            if p: var_dir.set(p)
        ttk.Button(frm, text="Elegir...", command=pick_dir).grid(row=1, column=2, padx=6, pady=(8,0))

        ttk.Label(frm, text="Signatura:").grid(row=2, column=0, sticky="w", pady=(8,0))
        var_sig = tk.StringVar(); ttk.Entry(frm, textvariable=var_sig, width=40).grid(row=2, column=1, sticky="we", pady=(8,0))
        ttk.Label(frm, text="Tipo documental:").grid(row=3, column=0, sticky="w", pady=(8,0))
        var_tipo = tk.StringVar(value="libro"); ttk.Entry(frm, textvariable=var_tipo, width=40).grid(row=3, column=1, sticky="we", pady=(8,0))
        ttk.Label(frm, text="Autor:").grid(row=4, column=0, sticky="w", pady=(8,0))
        var_autor = tk.StringVar(); ttk.Entry(frm, textvariable=var_autor, width=40).grid(row=4, column=1, sticky="we", pady=(8,0))
        ttk.Label(frm, text="Fecha:").grid(row=5, column=0, sticky="w", pady=(8,0))
        var_fecha = tk.StringVar(); ttk.Entry(frm, textvariable=var_fecha, width=40).grid(row=5, column=1, sticky="we", pady=(8,0))

        btns = ttk.Frame(frm); btns.grid(row=6, column=0, columnspan=3, sticky="e", pady=12)
        def do_create():
            base = app_config.get_root_dir()
            title = var_title.get().strip() or "Proyecto_sin_nombre"
            root_dir = Path(var_dir.get().strip())
            ensure_project_dirs(root_dir)
            pid = create_project(
                base,
                titulo=title,
                carpeta_raiz=str(root_dir),
                signatura=var_sig.get().strip(),
                tipo_documento=var_tipo.get().strip(),
                autor=var_autor.get().strip(),
                fecha=var_fecha.get().strip(),
            )
            messagebox.showinfo("Proyecto", f"Proyecto creado (ID {pid}) en:\n{root_dir}", parent=self.root)
            win.destroy(); self.reload_projects()
        ttk.Button(btns, text="Crear", command=do_create).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side=tk.RIGHT)

    def sync_pages(self):
        if not getattr(self, 'current_project', None):
            messagebox.showwarning("Sincronizar", "Seleccione un proyecto", parent=self.root)
            return
        root_dir = Path(self.current_project['carpeta_raiz'])
        inserted = sync_pages_from_folder(root_dir)
        messagebox.showinfo("Sincronizar", f"Se agregaron {inserted} páginas nuevas a la base de datos", parent=self.root)

    def open_project_folder(self):
        if not getattr(self, 'current_project', None):
            return
        folder = Path(self.current_project['carpeta_raiz'])
        try:
            import os
            os.startfile(str(folder))  # Windows
        except Exception:
            try:
                import subprocess
                subprocess.Popen(["xdg-open", str(folder)])
            except Exception:
                messagebox.showinfo("Proyecto", str(folder), parent=self.root)
                


if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerWindow(root)
    root.mainloop()
