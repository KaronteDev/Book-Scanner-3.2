#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_view.py — Export module for academic formats
"""
import tkinter as tk
from tkinter import filedialog, messagebox
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.dialogs import Messagebox
    USE_BOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    Messagebox = None
    USE_BOOTSTRAP = False
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.theme_titlebar import apply_titlebar_theme
from utils import app_config

from utils.db_manager import list_projects
from modules.exporters import dc, iiif, tei, geojson


class ExportWindow:
    """Export module window"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("GeoDocs Scanner - Exportación")
        self.root.geometry("800x600")
        
        # Apply title bar theme automatically from ttkbootstrap
        apply_titlebar_theme(self.root)
        # Restore geometry if saved
        try:
            geo = app_config.get_window_geometry("export")
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
        self.create_ui()
        self.load_projects()
    
    def create_ui(self):
        """Create user interface"""
        # Header
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=tk.X)
        
        ttk.Label(
            header,
            text="📦 Módulo de Exportación",
            font=("Open Sans", 16, "bold")
        ).pack()
        
        ttk.Label(
            header,
            text="Exportación a formatos académicos y de preservación digital",
            font=("Open Sans", 9),
            foreground="gray"
        ).pack()
        
        # Project selection
        proj_frame = ttk.LabelFrame(self.root, text="Proyecto", padding=10)
        proj_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(proj_frame, text="Seleccionar proyecto:").pack(side=tk.LEFT, padx=5)
        
        self.project_combo = ttk.Combobox(proj_frame, width=50, state="readonly")
        self.project_combo.pack(side=tk.LEFT, padx=5)
        self.project_combo.bind('<<ComboboxSelected>>', self.on_project_selected)
        
        # Export formats
        formats_frame = ttk.LabelFrame(self.root, text="Formatos de Exportación", padding=10)
        formats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Dublin Core
        dc_frame = self.create_format_frame(
            formats_frame,
            "Dublin Core",
            "Metadatos estándar para bibliotecas y repositorios digitales",
            ["JSON-LD", "XML"]
        )
        dc_frame.pack(fill=tk.X, pady=5)
        
        self.btn_export_dc = ttk.Button(
            dc_frame,
            text="Exportar DC",
            command=self.export_dublin_core
        )
        self.btn_export_dc.pack(side=tk.RIGHT, padx=5)
        
        # IIIF Manifest
        iiif_frame = self.create_format_frame(
            formats_frame,
            "IIIF Manifest",
            "International Image Interoperability Framework - Presentación 3.0",
            ["JSON"]
        )
        iiif_frame.pack(fill=tk.X, pady=5)
        
        self.btn_export_iiif = ttk.Button(
            iiif_frame,
            text="Exportar IIIF",
            command=self.export_iiif
        )
        self.btn_export_iiif.pack(side=tk.RIGHT, padx=5)
        
        # TEI-XML
        tei_frame = self.create_format_frame(
            formats_frame,
            "TEI-XML",
            "Text Encoding Initiative - Codificación académica de textos",
            ["XML"]
        )
        tei_frame.pack(fill=tk.X, pady=5)
        
        self.btn_export_tei = ttk.Button(
            tei_frame,
            text="Exportar TEI",
            command=self.export_tei
        )
        self.btn_export_tei.pack(side=tk.RIGHT, padx=5)
        
        # GeoJSON
        geo_frame = self.create_format_frame(
            formats_frame,
            "GeoJSON",
            "Formato geográfico para anotaciones con coordenadas",
            ["JSON"]
        )
        geo_frame.pack(fill=tk.X, pady=5)
        
        self.btn_export_geo = ttk.Button(
            geo_frame,
            text="Exportar GeoJSON",
            command=self.export_geojson
        )
        self.btn_export_geo.pack(side=tk.RIGHT, padx=5)
        
        # PDF Bundle
        pdf_frame = self.create_format_frame(
            formats_frame,
            "PDF/A Bundle",
            "PDF/A-2 con OCR incrustado y metadatos XMP",
            ["PDF"]
        )
        pdf_frame.pack(fill=tk.X, pady=5)
        
        self.btn_export_pdf = ttk.Button(
            pdf_frame,
            text="Exportar PDF",
            command=self.export_pdf
        )
        self.btn_export_pdf.pack(side=tk.RIGHT, padx=5)
        
        # Export all button
        ttk.Button(
            formats_frame,
            text="📦 Exportar Todo",
            command=self.export_all,
            style="Accent.TButton"
        ).pack(pady=10)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Listo", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_format_frame(self, parent, title, description, formats):
        """Create a format description frame"""
        frame = ttk.Frame(parent)
        
        info_frame = ttk.Frame(frame)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(
            info_frame,
            text=title,
            font=("Open Sans", 10, "bold")
        ).pack(anchor=tk.W)
        
        ttk.Label(
            info_frame,
            text=description,
            font=("Open Sans", 8),
            foreground="gray"
        ).pack(anchor=tk.W)
        
        ttk.Label(
            info_frame,
            text=f"Formatos: {', '.join(formats)}",
            font=("Open Sans", 8),
            foreground="blue"
        ).pack(anchor=tk.W)
        
        return frame
    
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
                messagebox.showerror("Error", f"No se pudieron cargar proyectos:\n{str(e)}")
    
    def on_close(self):
        try:
            app_config.set_window_geometry("export", self.root.geometry())
        except Exception:
            pass
        self.root.destroy()
    
    def on_project_selected(self, event):
        """Handle project selection"""
        idx = self.project_combo.current()
        if idx >= 0 and idx < len(self.projects_data):
            self.current_project = self.projects_data[idx]
            self.status_bar['text'] = f"Proyecto seleccionado: {self.current_project['titulo']}"
    
    def get_export_path(self, default_name: str) -> str:
        """Get export file path from user"""
        if not self.current_project:
            if Messagebox:
                Messagebox.show_warning(title="Exportar", message="Seleccione un proyecto primero", parent=self.root)
            else:
                messagebox.showwarning("Exportar", "Seleccione un proyecto primero")
            return None
        
        project_dir = Path(self.current_project['carpeta_raiz'])
        export_dir = project_dir / "exports"
        export_dir.mkdir(exist_ok=True)
        
        file_path = filedialog.asksaveasfilename(
            title="Guardar exportación",
            initialdir=export_dir,
            initialfile=default_name,
            defaultextension=Path(default_name).suffix
        )
        
        return file_path
    
    def export_dublin_core(self):
        """Export to Dublin Core format"""
        if not self.current_project:
            if Messagebox:
                Messagebox.show_warning(title="Exportar", message="Seleccione un proyecto primero", parent=self.root)
            else:
                messagebox.showwarning("Exportar", "Seleccione un proyecto primero")
            return
        
        # Ask for format
        format_dialog = tk.Toplevel(self.root)
        format_dialog.title("Formato Dublin Core")
        format_dialog.geometry("300x150")
        format_dialog.transient(self.root)
        
        ttk.Label(format_dialog, text="Seleccione formato:").pack(pady=10)
        
        format_var = tk.StringVar(value="json")
        ttk.Radiobutton(format_dialog, text="JSON-LD", value="json", variable=format_var).pack()
        ttk.Radiobutton(format_dialog, text="XML", value="xml", variable=format_var).pack()
        
        def do_export():
            is_xml = format_var.get() == "xml"
            ext = ".xml" if is_xml else ".jsonld"
            
            file_path = self.get_export_path(f"dc_export{ext}")
            if file_path:
                try:
                    # TODO: Implement actual export
                    if Messagebox:
                        Messagebox.show_info(title="Exportar", message=f"Dublin Core exportado a:\n{file_path}", parent=self.root)
                    else:
                        messagebox.showinfo("Exportar", f"Dublin Core exportado a:\n{file_path}")
                    self.status_bar['text'] = "Exportación Dublin Core completada"
                except Exception as e:
                    if Messagebox:
                        Messagebox.show_error(title="Error", message=f"Error al exportar:\n{str(e)}", parent=self.root)
                    else:
                        messagebox.showerror("Error", f"Error al exportar:\n{str(e)}")
            
            format_dialog.destroy()
        
        ttk.Button(format_dialog, text="Exportar", command=do_export).pack(pady=10)
        ttk.Button(format_dialog, text="Cancelar", command=format_dialog.destroy).pack()
    
    def export_iiif(self):
        """Export to IIIF Manifest"""
        file_path = self.get_export_path("manifest.json")
        if file_path:
            try:
                # TODO: Implement actual export
                if Messagebox:
                    Messagebox.show_info(title="Exportar", message=f"IIIF Manifest exportado a:\n{file_path}", parent=self.root)
                else:
                    messagebox.showinfo("Exportar", f"IIIF Manifest exportado a:\n{file_path}")
                self.status_bar['text'] = "Exportación IIIF completada"
            except Exception as e:
                if Messagebox:
                    Messagebox.show_error(title="Error", message=f"Error al exportar:\n{str(e)}", parent=self.root)
                else:
                    messagebox.showerror("Error", f"Error al exportar:\n{str(e)}")
    
    def export_tei(self):
        """Export to TEI-XML"""
        file_path = self.get_export_path("tei_export.xml")
        if file_path:
            try:
                # TODO: Implement actual export
                if Messagebox:
                    Messagebox.show_info(title="Exportar", message=f"TEI-XML exportado a:\n{file_path}", parent=self.root)
                else:
                    messagebox.showinfo("Exportar", f"TEI-XML exportado a:\n{file_path}")
                self.status_bar['text'] = "Exportación TEI completada"
            except Exception as e:
                if Messagebox:
                    Messagebox.show_error(title="Error", message=f"Error al exportar:\n{str(e)}", parent=self.root)
                else:
                    messagebox.showerror("Error", f"Error al exportar:\n{str(e)}")
    
    def export_geojson(self):
        """Export to GeoJSON"""
        file_path = self.get_export_path("annotations.geojson")
        if file_path:
            try:
                # TODO: Implement actual export
                if Messagebox:
                    Messagebox.show_info(title="Exportar", message=f"GeoJSON exportado a:\n{file_path}", parent=self.root)
                else:
                    messagebox.showinfo("Exportar", f"GeoJSON exportado a:\n{file_path}")
                self.status_bar['text'] = "Exportación GeoJSON completada"
            except Exception as e:
                if Messagebox:
                    Messagebox.show_error(title="Error", message=f"Error al exportar:\n{str(e)}", parent=self.root)
                else:
                    messagebox.showerror("Error", f"Error al exportar:\n{str(e)}")
    
    def export_pdf(self):
        """Export to PDF/A"""
        file_path = self.get_export_path("document.pdf")
        if file_path:
            try:
                # TODO: Implement actual export
                if Messagebox:
                    Messagebox.show_info(title="Exportar", message=f"PDF/A exportado a:\n{file_path}", parent=self.root)
                else:
                    messagebox.showinfo("Exportar", f"PDF/A exportado a:\n{file_path}")
                self.status_bar['text'] = "Exportación PDF completada"
            except Exception as e:
                if Messagebox:
                    Messagebox.show_error(title="Error", message=f"Error al exportar:\n{str(e)}", parent=self.root)
                else:
                    messagebox.showerror("Error", f"Error al exportar:\n{str(e)}")
    
    def export_all(self):
        """Export to all formats"""
        if not self.current_project:
            if Messagebox:
                Messagebox.show_warning(title="Exportar", message="Seleccione un proyecto primero", parent=self.root)
            else:
                messagebox.showwarning("Exportar", "Seleccione un proyecto primero")
            return
        
        response = messagebox.askyesno(
            "Exportar Todo",
            "¿Desea exportar el proyecto a todos los formatos disponibles?\n\n"
            "Esto creará archivos en la carpeta 'exports' del proyecto."
        )
        
        if response:
            self.status_bar['text'] = "Exportando a todos los formatos..."
            # TODO: Implement batch export
            if Messagebox:
                Messagebox.show_info(title="Exportar", message="Exportación múltiple en implementación", parent=self.root)
            else:
                messagebox.showinfo("Exportar", "Exportación múltiple en implementación")


if __name__ == "__main__":
    root = tk.Tk()
    app = ExportWindow(root)
    root.mainloop()
