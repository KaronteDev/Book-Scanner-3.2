#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
advanced_search.py — Advanced multi-project search tool
Search across all projects with filters by date, archive, type, OCR content, etc.
"""
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
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sqlite3
from utils.window_utils import center_to_parent
from utils import db_manager as db


class AdvancedSearchWindow:
    """Advanced search across all projects"""
    
    def __init__(self, parent, global_db_path: Path, projects_root: Path):
        self.parent = parent
        self.global_db_path = global_db_path
        self.projects_root = projects_root
        self.search_results = []
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("🔍 Búsqueda Avanzada Multi-Proyecto")
        self.window.geometry("1200x800")
        
        if parent:
            center_to_parent(self.window, parent)
        
        self._build_ui()
        
    def _build_ui(self):
        """Build the search UI"""
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="🔍 Búsqueda Avanzada Multi-Proyecto",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=(0, 15))
        
        # Search filters panel
        filters_frame = ttk.LabelFrame(main_frame, text="Filtros de Búsqueda", padding=15)
        filters_frame.pack(fill='x', pady=(0, 10))
        
        # Row 1: Text search
        row1 = ttk.Frame(filters_frame)
        row1.pack(fill='x', pady=5)
        
        ttk.Label(row1, text="Texto:").pack(side='left', padx=(0, 10))
        self.var_search_text = tk.StringVar()
        entry_search = ttk.Entry(row1, textvariable=self.var_search_text, width=50)
        entry_search.pack(side='left', padx=5)
        entry_search.focus_set()
        
        self.var_search_in = tk.StringVar(value="all")
        ttk.Radiobutton(row1, text="Todo", variable=self.var_search_in, value="all").pack(side='left', padx=5)
        ttk.Radiobutton(row1, text="OCR", variable=self.var_search_in, value="ocr").pack(side='left', padx=5)
        ttk.Radiobutton(row1, text="Metadatos", variable=self.var_search_in, value="metadata").pack(side='left', padx=5)
        
        # Row 2: Date range
        row2 = ttk.Frame(filters_frame)
        row2.pack(fill='x', pady=5)
        
        ttk.Label(row2, text="Fecha desde:").pack(side='left', padx=(0, 10))
        self.var_date_from = tk.StringVar()
        ttk.Entry(row2, textvariable=self.var_date_from, width=12).pack(side='left', padx=5)
        ttk.Label(row2, text="(AAAA-MM-DD)").pack(side='left', padx=5)
        
        ttk.Label(row2, text="hasta:").pack(side='left', padx=(20, 10))
        self.var_date_to = tk.StringVar()
        ttk.Entry(row2, textvariable=self.var_date_to, width=12).pack(side='left', padx=5)
        ttk.Label(row2, text="(AAAA-MM-DD)").pack(side='left', padx=5)
        
        ttk.Button(
            row2,
            text="Última semana",
            command=self._set_last_week,
            bootstyle="secondary-outline" if USE_BOOTSTRAP else None
        ).pack(side='left', padx=10)
        
        # Row 3: Project/Archive/Fondo filters
        row3 = ttk.Frame(filters_frame)
        row3.pack(fill='x', pady=5)
        
        ttk.Label(row3, text="Proyecto:").pack(side='left', padx=(0, 10))
        self.var_proyecto = tk.StringVar(value="")
        self.cmb_proyecto = ttk.Combobox(row3, textvariable=self.var_proyecto, width=20, state="readonly")
        self.cmb_proyecto.pack(side='left', padx=5)
        
        ttk.Label(row3, text="Archivo:").pack(side='left', padx=(20, 10))
        self.var_archivo = tk.StringVar(value="")
        self.cmb_archivo = ttk.Combobox(row3, textvariable=self.var_archivo, width=20, state="readonly")
        self.cmb_archivo.pack(side='left', padx=5)
        
        ttk.Label(row3, text="Fondo:").pack(side='left', padx=(20, 10))
        self.var_fondo = tk.StringVar(value="")
        self.cmb_fondo = ttk.Combobox(row3, textvariable=self.var_fondo, width=20, state="readonly")
        self.cmb_fondo.pack(side='left', padx=5)
        
        # Row 4: Additional filters
        row4 = ttk.Frame(filters_frame)
        row4.pack(fill='x', pady=5)
        
        ttk.Label(row4, text="Tipo Publicación:").pack(side='left', padx=(0, 10))
        self.var_tipo_pub = tk.StringVar(value="")
        tipo_pub_values = ["", "Libro", "Revista", "Manuscrito", "Mapa", "Fotografía", 
                           "Documento", "Carta", "Cartel", "Grabado", "Partitura", 
                           "Plano", "Periódico", "Otros"]
        ttk.Combobox(row4, textvariable=self.var_tipo_pub, values=tipo_pub_values, 
                     width=15, state="readonly").pack(side='left', padx=5)
        
        ttk.Label(row4, text="Estado OCR:").pack(side='left', padx=(20, 10))
        self.var_ocr_status = tk.StringVar(value="")
        ocr_status_values = ["", "pending", "processing", "completed", "error"]
        ttk.Combobox(row4, textvariable=self.var_ocr_status, values=ocr_status_values, 
                     width=12, state="readonly").pack(side='left', padx=5)
        
        ttk.Label(row4, text="Calidad:").pack(side='left', padx=(20, 10))
        self.var_quality = tk.StringVar(value="")
        quality_values = ["", "excelente", "buena", "regular", "mala"]
        ttk.Combobox(row4, textvariable=self.var_quality, values=quality_values, 
                     width=12, state="readonly").pack(side='left', padx=5)
        
        # Search button
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(
            btn_frame,
            text="🔍 Buscar",
            command=self._execute_search,
            bootstyle="primary" if USE_BOOTSTRAP else None,
            width=20
        ).pack(side='left', padx=5)
        
        ttk.Button(
            btn_frame,
            text="🗑️ Limpiar filtros",
            command=self._clear_filters,
            bootstyle="secondary" if USE_BOOTSTRAP else None,
            width=20
        ).pack(side='left', padx=5)
        
        self.lbl_result_count = ttk.Label(btn_frame, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_result_count.pack(side='left', padx=20)
        
        # Results panel
        results_frame = ttk.LabelFrame(main_frame, text="Resultados", padding=10)
        results_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        # Treeview for results
        columns = ("proyecto", "archivo", "fondo", "pagina", "fecha", "ocr_preview", "calidad")
        self.tree_results = ttk.Treeview(results_frame, columns=columns, show='headings', height=20)
        
        self.tree_results.heading("proyecto", text="Proyecto")
        self.tree_results.heading("archivo", text="Archivo")
        self.tree_results.heading("fondo", text="Fondo")
        self.tree_results.heading("pagina", text="Página")
        self.tree_results.heading("fecha", text="Fecha")
        self.tree_results.heading("ocr_preview", text="Vista Previa OCR")
        self.tree_results.heading("calidad", text="Calidad")
        
        self.tree_results.column("proyecto", width=150)
        self.tree_results.column("archivo", width=120)
        self.tree_results.column("fondo", width=120)
        self.tree_results.column("pagina", width=80)
        self.tree_results.column("fecha", width=100)
        self.tree_results.column("ocr_preview", width=350)
        self.tree_results.column("calidad", width=80)
        
        # Scrollbars
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree_results.yview)
        hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree_results.xview)
        self.tree_results.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree_results.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Double-click to open
        self.tree_results.bind("<Double-1>", self._on_result_double_click)
        
        # Bottom buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(
            bottom_frame,
            text="📋 Exportar Resultados",
            command=self._export_results,
            bootstyle="info" if USE_BOOTSTRAP else None
        ).pack(side='left', padx=5)
        
        ttk.Button(
            bottom_frame,
            text="📂 Abrir Ubicación",
            command=self._open_location,
            bootstyle="success" if USE_BOOTSTRAP else None
        ).pack(side='left', padx=5)
        
        ttk.Button(
            bottom_frame,
            text="Cerrar",
            command=self.window.destroy,
            bootstyle="secondary" if USE_BOOTSTRAP else None
        ).pack(side='right', padx=5)
        
        # Load combo box data
        self._load_filter_data()
        
        # Bind Enter to search
        self.window.bind('<Return>', lambda e: self._execute_search())
        
    def _load_filter_data(self):
        """Load data for filter comboboxes"""
        try:
            conn = sqlite3.connect(self.global_db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # Load proyectos
            proyectos = cur.execute("SELECT nombre FROM proyectos ORDER BY nombre").fetchall()
            self.cmb_proyecto['values'] = [""] + [p[0] for p in proyectos]
            
            # Load archivos
            archivos = cur.execute("SELECT DISTINCT nombre FROM archivos ORDER BY nombre").fetchall()
            self.cmb_archivo['values'] = [""] + [a[0] for a in archivos]
            
            # Load fondos
            fondos = cur.execute("SELECT DISTINCT nombre FROM fondos ORDER BY nombre").fetchall()
            self.cmb_fondo['values'] = [""] + [f[0] for f in fondos]
            
            conn.close()
        except Exception as e:
            print(f"Error loading filter data: {e}")
            
    def _set_last_week(self):
        """Set date range to last 7 days"""
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        self.var_date_from.set(week_ago.strftime("%Y-%m-%d"))
        self.var_date_to.set(today.strftime("%Y-%m-%d"))
        
    def _clear_filters(self):
        """Clear all search filters"""
        self.var_search_text.set("")
        self.var_date_from.set("")
        self.var_date_to.set("")
        self.var_proyecto.set("")
        self.var_archivo.set("")
        self.var_fondo.set("")
        self.var_tipo_pub.set("")
        self.var_ocr_status.set("")
        self.var_quality.set("")
        self.var_search_in.set("all")
        self.tree_results.delete(*self.tree_results.get_children())
        self.lbl_result_count.config(text="")
        
    def _execute_search(self):
        """Execute the search with current filters"""
        self.tree_results.delete(*self.tree_results.get_children())
        self.search_results = []
        
        try:
            # Get all project databases
            project_dbs = list(self.projects_root.rglob("project.db"))
            
            if not project_dbs:
                self.lbl_result_count.config(text="No se encontraron proyectos")
                return
            
            total_results = 0
            search_text = self.var_search_text.get().strip().lower()
            search_in = self.var_search_in.get()
            date_from = self.var_date_from.get().strip()
            date_to = self.var_date_to.get().strip()
            
            # Search in each project
            for project_db in project_dbs:
                try:
                    results = self._search_in_project(
                        project_db,
                        search_text,
                        search_in,
                        date_from,
                        date_to
                    )
                    
                    for result in results:
                        self.search_results.append(result)
                        total_results += 1
                        
                        # Add to treeview
                        ocr_preview = result.get('ocr_preview', '')
                        if len(ocr_preview) > 100:
                            ocr_preview = ocr_preview[:100] + "..."
                        
                        self.tree_results.insert("", "end", values=(
                            result.get('proyecto', '-'),
                            result.get('archivo', '-'),
                            result.get('fondo', '-'),
                            result.get('page_number', '-'),
                            result.get('created_at', '-')[:10],
                            ocr_preview,
                            result.get('quality_level', '-')
                        ), tags=(result.get('project_db_path'),))
                        
                except Exception as e:
                    print(f"Error searching in {project_db}: {e}")
                    continue
            
            self.lbl_result_count.config(
                text=f"✓ {total_results} resultado{'s' if total_results != 1 else ''} encontrado{'s' if total_results != 1 else ''}"
            )
            
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(
                    title="Error",
                    message=f"Error al buscar: {e}",
                    parent=self.window
                )
            else:
                messagebox.showerror("Error", f"Error al buscar: {e}", parent=self.window)
                
    def _search_in_project(self, project_db: Path, search_text: str, search_in: str, 
                           date_from: str, date_to: str) -> List[Dict[str, Any]]:
        """Search in a single project database"""
        results = []
        
        try:
            conn = sqlite3.connect(project_db)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # Build query
            query_parts = ["SELECT * FROM page WHERE 1=1"]
            params = []
            
            # Text search
            if search_text:
                if search_in == "ocr":
                    query_parts.append("AND (LOWER(ocr_original) LIKE ? OR LOWER(ocr_corregido) LIKE ?)")
                    params.extend([f"%{search_text}%", f"%{search_text}%"])
                elif search_in == "metadata":
                    query_parts.append("AND (LOWER(notes) LIKE ? OR LOWER(tags) LIKE ?)")
                    params.extend([f"%{search_text}%", f"%{search_text}%"])
                else:  # all
                    query_parts.append("""
                        AND (LOWER(ocr_original) LIKE ? OR LOWER(ocr_corregido) LIKE ? 
                             OR LOWER(notes) LIKE ? OR LOWER(tags) LIKE ?)
                    """)
                    params.extend([f"%{search_text}%"] * 4)
            
            # Date filters
            if date_from:
                query_parts.append("AND created_at >= ?")
                params.append(date_from)
            if date_to:
                query_parts.append("AND created_at <= ?")
                params.append(date_to + " 23:59:59")
            
            # OCR status filter
            ocr_status = self.var_ocr_status.get()
            if ocr_status:
                query_parts.append("AND ocr_status = ?")
                params.append(ocr_status)
            
            # Quality filter
            quality = self.var_quality.get()
            if quality:
                query_parts.append("AND quality_level = ?")
                params.append(quality)
            
            query = " ".join(query_parts)
            rows = cur.execute(query, params).fetchall()
            
            # Get project metadata from global DB
            project_name = self._get_project_name(project_db)
            
            for row in rows:
                result = {
                    'project_db_path': str(project_db),
                    'proyecto': project_name,
                    'archivo': '-',  # Could be enhanced to fetch from DB
                    'fondo': '-',    # Could be enhanced to fetch from DB
                    'page_number': row['page_number'],
                    'created_at': row['created_at'],
                    'ocr_preview': (row['ocr_corregido'] or row['ocr_original'] or '')[:200],
                    'quality_level': row['quality_level'] or '-',
                    'image_path': row['image_path']
                }
                results.append(result)
            
            conn.close()
            
        except Exception as e:
            print(f"Error in _search_in_project: {e}")
            
        return results
        
    def _get_project_name(self, project_db: Path) -> str:
        """Get project name from path or global DB"""
        # Extract from path
        try:
            # Assuming structure: proyectos/PROJECT_NAME/project.db
            return project_db.parent.name
        except:
            return "Unknown"
            
    def _on_result_double_click(self, event):
        """Handle double-click on result"""
        selection = self.tree_results.selection()
        if not selection:
            return
        
        item = self.tree_results.item(selection[0])
        values = item['values']
        
        if Messagebox:
            Messagebox.show_info(
                title="Resultado Seleccionado",
                message=f"Proyecto: {values[0]}\nPágina: {values[3]}\n\nEsta función abrirá el proyecto en el editor.",
                parent=self.window
            )
        
    def _open_location(self):
        """Open file location of selected result"""
        selection = self.tree_results.selection()
        if not selection:
            if Messagebox:
                Messagebox.show_warning(
                    title="Aviso",
                    message="Selecciona un resultado primero",
                    parent=self.window
                )
            return
        
        # Get project DB path from tags
        item = self.tree_results.item(selection[0])
        tags = item.get('tags', ())
        if tags:
            project_db_path = Path(tags[0])
            project_folder = project_db_path.parent
            
            # Open in file explorer
            import subprocess
            try:
                subprocess.run(['explorer', str(project_folder)])
            except Exception as e:
                if Messagebox:
                    Messagebox.show_error(
                        title="Error",
                        message=f"No se pudo abrir la ubicación: {e}",
                        parent=self.window
                    )
                    
    def _export_results(self):
        """Export search results to CSV"""
        if not self.search_results:
            if Messagebox:
                Messagebox.show_warning(
                    title="Aviso",
                    message="No hay resultados para exportar",
                    parent=self.window
                )
            return
        
        from tkinter import filedialog
        import csv
        
        filepath = filedialog.asksaveasfilename(
            parent=self.window,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="resultados_busqueda.csv"
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Proyecto", "Archivo", "Fondo", "Página", "Fecha", "OCR", "Calidad"])
                
                for result in self.search_results:
                    writer.writerow([
                        result.get('proyecto', '-'),
                        result.get('archivo', '-'),
                        result.get('fondo', '-'),
                        result.get('page_number', '-'),
                        result.get('created_at', '-'),
                        result.get('ocr_preview', ''),
                        result.get('quality_level', '-')
                    ])
            
            if Messagebox:
                Messagebox.show_info(
                    title="Exportación Exitosa",
                    message=f"Resultados exportados a:\n{filepath}",
                    parent=self.window
                )
                
        except Exception as e:
            if Messagebox:
                Messagebox.show_error(
                    title="Error",
                    message=f"Error al exportar: {e}",
                    parent=self.window
                )


def show_advanced_search(parent, global_db_path: Path, projects_root: Path):
    """Show advanced search window"""
    window = AdvancedSearchWindow(parent, global_db_path, projects_root)
    return window
