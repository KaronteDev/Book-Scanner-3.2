#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_manager.py — CRUD de Proyectos, Archivos, Fondos y Etiquetas
Accesible desde el menú principal y desde Escáner/Anotaciones
"""
from __future__ import annotations

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
from typing import Optional, Dict, Any

from utils.theme_titlebar import apply_titlebar_theme
from utils import app_config
from utils import db_manager as db


class MetadataManager(tk.Toplevel):
    def __init__(self, parent: tk.Misc, focus_tab: str = "proyectos", edit_project_id: Optional[int] = None):
        super().__init__(parent)
        self.title("Gestión de Metadatos · GeoDocs")
        self.geometry("1000x650")
        self.resizable(True, True)
        self.parent = parent

        apply_titlebar_theme(self)

        self.base_path = app_config.get_root_dir()

        # Notebook con 4 pestañas
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True)

        self._build_tab_proyectos()
        self._build_tab_archivos()
        self._build_tab_fondos()
        self._build_tab_etiquetas()

        # Seleccionar pestaña inicial
        tabs = {"proyectos": 0, "archivos": 1, "fondos": 2, "etiquetas": 3}
        self.nb.select(tabs.get(focus_tab, 0))

        # Si nos pasan un proyecto para editar, abrir editor
        if edit_project_id:
            self.after(200, lambda: self._open_project_editor(edit_project_id))

        # Modal-like
        self.transient(parent)
        self.grab_set()
        self.focus_set()

    # ---- PROYECTOS ----
    def _build_tab_proyectos(self):
        tab = ttk.Frame(self.nb); self.nb.add(tab, text="📁 Proyectos")
        top = ttk.Frame(tab); top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(top, text="➕ Nuevo", command=self._new_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="✏️ Editar", command=self._edit_selected_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="🗑 Eliminar", command=self._delete_selected_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="⚙️ Tablas (Archivos/Fondos/Etiquetas)", command=lambda: self.nb.select(1)).pack(side=tk.LEFT, padx=10)

        # Search bar
        search_frame = ttk.Frame(tab); search_frame.pack(fill=tk.X, padx=8, pady=(0,6))
        ttk.Label(search_frame, text="🔍 Buscar:").pack(side=tk.LEFT, padx=(0,6))
        self.var_search_proj = tk.StringVar()
        self.var_search_proj.trace_add('write', lambda *args: self._filter_projects())
        ttk.Entry(search_frame, textvariable=self.var_search_proj, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)

        cols = ("id","titulo","signatura","tipo","autor","tema","etiquetas","fecha","fondo","archivo","carpeta")
        self.tree_proj = ttk.Treeview(tab, columns=cols, show="headings")
        headers = {
            "id": "ID","titulo":"Título","signatura":"Signatura","tipo":"Tipo","autor":"Autor","tema":"Tema",
            "etiquetas":"Etiquetas","fecha":"Fecha","fondo":"Fondo","archivo":"Archivo","carpeta":"Carpeta"
        }
        for c in cols:
            self.tree_proj.heading(c, text=headers[c])
            self.tree_proj.column(c, width=120 if c not in ("titulo","carpeta") else 220, anchor=tk.W)
        self.tree_proj.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.tree_proj.bind('<Double-1>', lambda e: self._edit_selected_project())
        
        # Store unfiltered data
        self._all_projects = []
        self._reload_projects()

    def _reload_projects(self):
        for i in self.tree_proj.get_children():
            self.tree_proj.delete(i)
        self._all_projects = db.list_projects(self.base_path)
        self._filter_projects()
    
    def _filter_projects(self):
        """Filter projects based on search text"""
        search_text = self.var_search_proj.get().lower().strip()
        
        # Clear tree
        for i in self.tree_proj.get_children():
            self.tree_proj.delete(i)
        
        # Re-populate with filtered data
        for r in self._all_projects:
            # Search in titulo, signatura, autor, tema, and tags
            searchable = f"{r.get('titulo','')} {r.get('signatura','')} {r.get('autor','')} {r.get('tema','')} {' '.join(r.get('etiquetas_list',[]))}".lower()
            
            if not search_text or search_text in searchable:
                tags_display = ', '.join(r.get('etiquetas_list', [])) if r.get('etiquetas_list') else ''
                
                self.tree_proj.insert('', tk.END, values=(
                    r.get('id'), r.get('titulo'), r.get('signatura'), r.get('tipo_documento') or '', r.get('autor') or '',
                    r.get('tema') or '', tags_display, r.get('fecha') or '', r.get('fondo_nombre') or '',
                    r.get('archivo_nombre') or '', r.get('carpeta_raiz')
                ))

    def _selected_id(self, tree: ttk.Treeview, col_index: int = 0) -> Optional[int]:
        sel = tree.selection()
        if not sel:
            return None
        vals = tree.item(sel[0], 'values')
        try:
            return int(vals[col_index])
        except Exception:
            return None

    def _new_project(self):
        self._open_project_editor(None)

    def _edit_selected_project(self):
        pid = self._selected_id(self.tree_proj, 0)
        if not pid:
            (Messagebox.show_warning(title="Proyectos", message="Seleccione un proyecto", parent=self) if Messagebox else messagebox.showwarning("Proyectos","Seleccione un proyecto"))
            return
        self._open_project_editor(pid)

    def _delete_selected_project(self):
        pid = self._selected_id(self.tree_proj, 0)
        if not pid:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar el proyecto? (No borra archivos)"):
            return
        db.delete_project(self.base_path, pid)
        self._reload_projects()

    def _open_project_editor(self, project_id: Optional[int]):
        EditorProyecto(self, base_path=self.base_path, project_id=project_id, on_saved=lambda: self._reload_projects())

    # ---- ARCHIVOS ----
    def _build_tab_archivos(self):
        tab = ttk.Frame(self.nb); self.nb.add(tab, text="🏛 Archivos")
        top = ttk.Frame(tab); top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(top, text="➕ Nuevo", command=lambda: self._open_archivo_editor(None)).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="✏️ Editar", command=lambda: self._open_archivo_editor(self._selected_id(self.tree_arch, 0))).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="🗑 Eliminar", command=self._delete_selected_archivo).pack(side=tk.LEFT, padx=3)

        # Search bar
        search_frame = ttk.Frame(tab); search_frame.pack(fill=tk.X, padx=8, pady=(0,6))
        ttk.Label(search_frame, text="🔍 Buscar:").pack(side=tk.LEFT, padx=(0,6))
        self.var_search_arch = tk.StringVar()
        self.var_search_arch.trace_add('write', lambda *args: self._filter_archivos())
        ttk.Entry(search_frame, textvariable=self.var_search_arch, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)

        cols = ("id","nombre","siglas","direccion","contacto","email","telefono","url")
        self.tree_arch = ttk.Treeview(tab, columns=cols, show="headings")
        headers = {"id":"ID","nombre":"Nombre","siglas":"Siglas","direccion":"Dirección","contacto":"Contacto","email":"Email","telefono":"Teléfono","url":"URL"}
        for c in cols:
            self.tree_arch.heading(c, text=headers[c])
            self.tree_arch.column(c, width=140 if c not in ("direccion","url","nombre") else 220, anchor=tk.W)
        self.tree_arch.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.tree_arch.bind('<Double-1>', lambda e: self._open_archivo_editor(self._selected_id(self.tree_arch, 0)))
        
        self._all_archivos = []
        self._reload_archivos()

    def _reload_archivos(self):
        for i in getattr(self, 'tree_arch', []).get_children():
            self.tree_arch.delete(i)
        self._all_archivos = db.list_archivos(self.base_path)
        self._filter_archivos()
    
    def _filter_archivos(self):
        """Filter archivos based on search text"""
        search_text = self.var_search_arch.get().lower().strip()
        
        # Clear tree
        for i in self.tree_arch.get_children():
            self.tree_arch.delete(i)
        
        # Re-populate with filtered data
        for r in self._all_archivos:
            searchable = f"{r.get('nombre','')} {r.get('siglas','')} {r.get('direccion','')} {r.get('contacto','')}".lower()
            
            if not search_text or search_text in searchable:
                self.tree_arch.insert('', tk.END, values=(
                    r.get('id'), r.get('nombre'), r.get('siglas') or '', r.get('direccion') or '', 
                    r.get('contacto') or '', r.get('email') or '', r.get('telefono') or '', r.get('url') or ''
                ))

    def _open_archivo_editor(self, archivo_id: Optional[int]):
        EditorArchivo(self, self.base_path, archivo_id, on_saved=self._reload_archivos)

    def _delete_selected_archivo(self):
        aid = self._selected_id(self.tree_arch, 0)
        if not aid:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar el archivo (institución)?"):
            return
        db.delete_archivo(self.base_path, aid)
        self._reload_archivos()

    # ---- FONDOS ----
    def _build_tab_fondos(self):
        tab = ttk.Frame(self.nb); self.nb.add(tab, text="🗃 Fondos")
        top = ttk.Frame(tab); top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(top, text="➕ Nuevo", command=lambda: self._open_fondo_editor(None)).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="✏️ Editar", command=lambda: self._open_fondo_editor(self._selected_id(self.tree_fond, 0))).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="🗑 Eliminar", command=self._delete_selected_fondo).pack(side=tk.LEFT, padx=3)

        # Search bar
        search_frame = ttk.Frame(tab); search_frame.pack(fill=tk.X, padx=8, pady=(0,6))
        ttk.Label(search_frame, text="🔍 Buscar:").pack(side=tk.LEFT, padx=(0,6))
        self.var_search_fond = tk.StringVar()
        self.var_search_fond.trace_add('write', lambda *args: self._filter_fondos())
        ttk.Entry(search_frame, textvariable=self.var_search_fond, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)

        cols = ("id","nombre","archivo","siglas","descripcion","periodo_inicio","periodo_fin")
        self.tree_fond = ttk.Treeview(tab, columns=cols, show="headings")
        headers = {"id":"ID","nombre":"Nombre","archivo":"Archivo","siglas":"Siglas","descripcion":"Descripción","periodo_inicio":"Desde","periodo_fin":"Hasta"}
        for c in cols:
            self.tree_fond.heading(c, text=headers[c])
            self.tree_fond.column(c, width=140 if c not in ("descripcion","nombre") else 220, anchor=tk.W)
        self.tree_fond.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.tree_fond.bind('<Double-1>', lambda e: self._open_fondo_editor(self._selected_id(self.tree_fond, 0)))
        
        self._all_fondos = []
        self._reload_fondos()

    def _reload_fondos(self):
        for i in getattr(self, 'tree_fond', []).get_children():
            self.tree_fond.delete(i)
        self._all_fondos = db.list_fondos(self.base_path)
        self._filter_fondos()
    
    def _filter_fondos(self):
        """Filter fondos based on search text"""
        search_text = self.var_search_fond.get().lower().strip()
        
        # Clear tree
        for i in self.tree_fond.get_children():
            self.tree_fond.delete(i)
        
        # Re-populate with filtered data
        for r in self._all_fondos:
            searchable = f"{r.get('nombre','')} {r.get('descripcion','')} {r.get('archivo_nombre','')}".lower()
            
            if not search_text or search_text in searchable:
                self.tree_fond.insert('', tk.END, values=(
                    r.get('id'), r.get('nombre'), r.get('archivo_nombre') or '', r.get('archivo_siglas') or '', 
                    r.get('descripcion') or '', r.get('periodo_inicio') or '', r.get('periodo_fin') or ''
                ))

    def _open_fondo_editor(self, fondo_id: Optional[int]):
        EditorFondo(self, self.base_path, fondo_id, on_saved=self._reload_fondos)

    def _delete_selected_fondo(self):
        fid = self._selected_id(self.tree_fond, 0)
        if not fid:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar el fondo?"):
            return
        db.delete_fondo(self.base_path, fid)
        self._reload_fondos()

    # ---- ETIQUETAS ----
    def _build_tab_etiquetas(self):
        tab = ttk.Frame(self.nb); self.nb.add(tab, text="🏷 Etiquetas")
        top = ttk.Frame(tab); top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(top, text="➕ Nuevo", command=lambda: self._open_etiqueta_editor(None)).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="✏️ Editar", command=lambda: self._open_etiqueta_editor(self._selected_id(self.tree_tags, 0))).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="🗑 Eliminar", command=self._delete_selected_etiqueta).pack(side=tk.LEFT, padx=3)

        # Search bar
        search_frame = ttk.Frame(tab); search_frame.pack(fill=tk.X, padx=8, pady=(0,6))
        ttk.Label(search_frame, text="🔍 Buscar:").pack(side=tk.LEFT, padx=(0,6))
        self.var_search_tags = tk.StringVar()
        self.var_search_tags.trace_add('write', lambda *args: self._filter_etiquetas())
        ttk.Entry(search_frame, textvariable=self.var_search_tags, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)

        cols = ("id","nombre","descripcion")
        self.tree_tags = ttk.Treeview(tab, columns=cols, show="headings")
        headers = {"id":"ID","nombre":"Nombre","descripcion":"Descripción"}
        for c in cols:
            self.tree_tags.heading(c, text=headers[c])
            self.tree_tags.column(c, width=220 if c == "descripcion" else 200, anchor=tk.W)
        self.tree_tags.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.tree_tags.bind('<Double-1>', lambda e: self._open_etiqueta_editor(self._selected_id(self.tree_tags, 0)))
        
        self._all_etiquetas = []
        self._reload_etiquetas()

    def _reload_etiquetas(self):
        for i in getattr(self, 'tree_tags', []).get_children():
            self.tree_tags.delete(i)
        self._all_etiquetas = db.list_etiquetas(self.base_path)
        self._filter_etiquetas()
    
    def _filter_etiquetas(self):
        """Filter etiquetas based on search text"""
        search_text = self.var_search_tags.get().lower().strip()
        
        # Clear tree
        for i in self.tree_tags.get_children():
            self.tree_tags.delete(i)
        
        # Re-populate with filtered data
        for r in self._all_etiquetas:
            searchable = f"{r.get('nombre','')} {r.get('descripcion','')}".lower()
            
            if not search_text or search_text in searchable:
                self.tree_tags.insert('', tk.END, values=(r.get('id'), r.get('nombre'), r.get('descripcion') or ''))

    def _open_etiqueta_editor(self, tag_id: Optional[int]):
        EditorEtiqueta(self, self.base_path, tag_id, on_saved=self._reload_etiquetas)

    def _delete_selected_etiqueta(self):
        tid = self._selected_id(self.tree_tags, 0)
        if not tid:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar la etiqueta?"):
            return
        db.delete_etiqueta(self.base_path, tid)
        self._reload_etiquetas()


# ---- Editors ----
class EditorProyecto(tk.Toplevel):
    def __init__(self, parent: tk.Misc, base_path: Path, project_id: Optional[int], on_saved=None):
        super().__init__(parent)
        self.title("Proyecto")
        self.geometry("720x520")
        apply_titlebar_theme(self)
        self.base_path = base_path
        self.project_id = project_id
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # Campos
        self.var_titulo = tk.StringVar()
        self.var_autor = tk.StringVar()
        self.var_tipo = tk.StringVar()
        self.var_sign = tk.StringVar()
        self.var_archivo = tk.StringVar()
        self.var_fondo = tk.StringVar()
        self.var_tema = tk.StringVar()
        self.var_fecha = tk.StringVar()

        row = 0
        def add_label(text):
            nonlocal row
            ttk.Label(frm, text=text).grid(row=row, column=0, sticky='e', padx=6, pady=4)
        def add_entry(var, width=50):
            nonlocal row
            e = ttk.Entry(frm, textvariable=var, width=width)
            e.grid(row=row, column=1, sticky='w', padx=6, pady=4)
            row += 1
            return e

        add_label("Título:"); add_entry(self.var_titulo)
        add_label("Autor:"); add_entry(self.var_autor)
        add_label("Tipo:"); add_entry(self.var_tipo)
        add_label("Signatura:"); add_entry(self.var_sign)

        # Archivo + Fondo combos
        add_label("Archivo (institución):")
        archivo_frame = ttk.Frame(frm)
        archivo_frame.grid(row=row, column=1, sticky='w', padx=6, pady=4); row += 1
        self.cmb_arch = ttk.Combobox(archivo_frame, textvariable=self.var_archivo, state='readonly', width=44)
        self.cmb_arch.pack(side=tk.LEFT)
        ttk.Button(archivo_frame, text="➕", width=3, command=self._quick_create_archivo).pack(side=tk.LEFT, padx=(6,0))
        self.cmb_arch.bind('<<ComboboxSelected>>', lambda e: self._refresh_fondos())

        add_label("Fondo:")
        fondo_frame = ttk.Frame(frm)
        fondo_frame.grid(row=row, column=1, sticky='w', padx=6, pady=4); row += 1
        self.cmb_fondo = ttk.Combobox(fondo_frame, textvariable=self.var_fondo, state='readonly', width=44)
        self.cmb_fondo.pack(side=tk.LEFT)
        ttk.Button(fondo_frame, text="➕", width=3, command=self._quick_create_fondo).pack(side=tk.LEFT, padx=(6,0))

        # Tema / Fecha
        add_label("Tema:"); add_entry(self.var_tema)
        add_label("Fecha (año o rango):"); add_entry(self.var_fecha)
        
        # Etiquetas (multi-select Listbox)
        add_label("Etiquetas:")
        tag_container = ttk.Frame(frm)
        tag_container.grid(row=row, column=1, sticky='w', padx=6, pady=4); row += 1
        
        tag_frame = ttk.Frame(tag_container)
        tag_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Listbox with scrollbar for multi-select
        tag_scroll = ttk.Scrollbar(tag_frame, orient=tk.VERTICAL)
        self.lst_tags = tk.Listbox(tag_frame, selectmode=tk.MULTIPLE, height=5, width=45, yscrollcommand=tag_scroll.set, exportselection=False)
        tag_scroll.config(command=self.lst_tags.yview)
        self.lst_tags.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tag_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Quick create button for tags
        tag_btn_frame = ttk.Frame(tag_container)
        tag_btn_frame.pack(side=tk.LEFT, padx=(6,0), anchor='n')
        ttk.Button(tag_btn_frame, text="➕", width=3, command=self._quick_create_etiqueta).pack()
        
        # Store tag data for reference
        self._all_tags = []

        # Accesos rápidos a tablas
        bar = ttk.Frame(frm); bar.grid(row=row, column=0, columnspan=2, sticky='w', padx=6, pady=(10,4)); row += 1
        ttk.Button(bar, text="Gestionar Archivos/Fondos/Etiquetas", command=lambda: MetadataManager(self, focus_tab='archivos')).pack(side=tk.LEFT)

        # Botonera guardar/cancelar
        btns = ttk.Frame(frm); btns.grid(row=row, column=0, columnspan=2, sticky='e', pady=(20, 4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)

        # Cargar datos
        self._load_tags()
        self._load_archivos_fondos()
        if project_id:
            self._load_project(project_id)

    def _load_tags(self):
        """Load all available tags into listbox"""
        self._all_tags = db.list_etiquetas(self.base_path)
        self.lst_tags.delete(0, tk.END)
        for tag in self._all_tags:
            self.lst_tags.insert(tk.END, tag.get('nombre', ''))

    def _load_archivos_fondos(self):
        self._arch_rows = db.list_archivos(self.base_path)
        arch_opts = [f"{r['id']} · {r['nombre']} ({(r.get('siglas') or '').upper()})" for r in self._arch_rows]
        self.cmb_arch['values'] = arch_opts
        if arch_opts:
            self.cmb_arch.current(0)
            self._refresh_fondos()

    def _refresh_fondos(self):
        sel = self.var_archivo.get()
        aid = int(sel.split('·',1)[0]) if sel else None
        self._fond_rows = [f for f in db.list_fondos(self.base_path) if not aid or f.get('archivo_id') == aid]
        fond_opts = [f"{r['id']} · {r['nombre']}" for r in self._fond_rows]
        self.cmb_fondo['values'] = fond_opts
        if fond_opts:
            self.cmb_fondo.current(0)
    
    def _quick_create_archivo(self):
        """Quick create archivo without leaving project editor"""
        # Open compact archivo editor
        QuickEditorArchivo(self, self.base_path, on_saved=lambda new_archivo_id: self._on_archivo_created(new_archivo_id))
    
    def _on_archivo_created(self, new_archivo_id: int):
        """Callback after creating a new archivo - refresh combo and select it"""
        # Reload archivos
        self._load_archivos_fondos()
        
        # Select the newly created archivo
        for i, a in enumerate(self._arch_rows):
            if a.get('id') == new_archivo_id:
                self.cmb_arch.current(i)
                self._refresh_fondos()
                break
    
    def _quick_create_fondo(self):
        """Quick create fondo without leaving project editor"""
        # Get selected archivo
        sel = self.var_archivo.get()
        if not sel:
            messagebox.showwarning("Crear Fondo", "Seleccione primero un Archivo (institución)")
            return
        aid = int(sel.split('·',1)[0])
        
        # Open compact fondo editor
        QuickEditorFondo(self, self.base_path, archivo_id=aid, on_saved=lambda new_fondo_id: self._on_fondo_created(new_fondo_id))
    
    def _on_fondo_created(self, new_fondo_id: int):
        """Callback after creating a new fondo - refresh combo and select it"""
        # Reload fondos for current archivo
        self._refresh_fondos()
        
        # Select the newly created fondo
        for i, f in enumerate(self._fond_rows):
            if f.get('id') == new_fondo_id:
                self.cmb_fondo.current(i)
                break
    
    def _quick_create_etiqueta(self):
        """Quick create etiqueta without leaving project editor"""
        # Open compact etiqueta editor
        QuickEditorEtiqueta(self, self.base_path, on_saved=lambda new_etiqueta_id: self._on_etiqueta_created(new_etiqueta_id))
    
    def _on_etiqueta_created(self, new_etiqueta_id: int):
        """Callback after creating a new etiqueta - refresh list and select it"""
        # Reload tags
        self._load_tags()
        
        # Select the newly created tag
        for i, tag in enumerate(self._all_tags):
            if tag.get('id') == new_etiqueta_id:
                self.lst_tags.selection_set(i)
                self.lst_tags.see(i)  # Scroll to make it visible
                break

    def _load_project(self, project_id: int):
        row = db.get_project(self.base_path, project_id)
        if not row:
            return
        self.project_id = project_id
        self.var_titulo.set(row.get('titulo') or '')
        self.var_autor.set(row.get('autor') or '')
        self.var_tipo.set(row.get('tipo_documento') or '')
        self.var_sign.set(row.get('signatura') or '')
        self.var_tema.set(row.get('tema') or '')
        self.var_fecha.set(row.get('fecha') or '')
        
        # Load selected tags from N:M relationship
        project_tags = db.list_project_tags(self.base_path, project_id)
        selected_tag_ids = {tag.get('id') for tag in project_tags}
        
        # Pre-select tags in listbox
        for i, tag in enumerate(self._all_tags):
            if tag.get('id') in selected_tag_ids:
                self.lst_tags.selection_set(i)
        
        # Select fondo/archivo
        try:
            f_id = row.get('fondo_id')
            if f_id:
                fond_row = None
                for f in self._fond_rows:
                    if f.get('id') == f_id:
                        fond_row = f; break
                if not fond_row:
                    # Ensure fondos reloaded to include current
                    self._fond_rows = db.list_fondos(self.base_path)
                    for f in self._fond_rows:
                        if f.get('id') == f_id:
                            fond_row = f; break
                if fond_row:
                    # Select archivo
                    a_id = fond_row.get('archivo_id')
                    for i, a in enumerate(self._arch_rows):
                        if a.get('id') == a_id:
                            self.cmb_arch.current(i)
                            break
                    # Refresh fondos for that archivo
                    self._refresh_fondos()
                    for i, f in enumerate(self._fond_rows):
                        if f.get('id') == f_id:
                            self.cmb_fondo.current(i)
                            break
        except Exception:
            pass

    def _save(self):
        titulo = self.var_titulo.get().strip()
        if not titulo:
            messagebox.showwarning("Proyecto", "El título es obligatorio")
            return
        
        signatura = self.var_sign.get().strip()
        
        # Validate signatura if provided
        if signatura:
            valid, error_msg = db.validate_signatura(signatura)
            if not valid:
                messagebox.showerror("Proyecto", f"Signatura inválida:\n{error_msg}")
                return
        
        # Get selected tag IDs
        selected_indices = self.lst_tags.curselection()
        etiqueta_ids = [self._all_tags[i].get('id') for i in selected_indices]
        
        # Fondo
        fid = None
        if self.var_fondo.get():
            try:
                fid = int(self.var_fondo.get().split('·',1)[0])
            except Exception:
                fid = None
        
        data = dict(
            titulo=titulo,
            signatura=signatura,
            tipo_documento=self.var_tipo.get().strip(),
            autor=self.var_autor.get().strip(),
            tema=self.var_tema.get().strip(),
            fecha=self.var_fecha.get().strip(),
            fondo_id=fid,
            etiqueta_ids=etiqueta_ids,
        )
        
        try:
            if self.project_id:
                # Update existing project
                ok = db.update_project(self.base_path, self.project_id, **data)
                if ok:
                    # Update tag relationships
                    db.set_project_tags(self.base_path, self.project_id, etiqueta_ids)
                    if self.on_saved:
                        self.on_saved()
                self.destroy()
            else:
                # Create new project (create_project handles tags internally)
                pid = db.create_project(self.base_path, titulo=data.pop('titulo'), **data)
                if self.on_saved:
                    self.on_saved()
                (Messagebox.show_info(title="Proyecto", message=f"Proyecto creado (ID {pid})", parent=self) if Messagebox else messagebox.showinfo("Proyecto", f"Proyecto creado (ID {pid})"))
                self.destroy()
        except ValueError as e:
            messagebox.showerror("Proyecto", f"Error de validación:\n{str(e)}")
        except Exception as e:
            messagebox.showerror("Proyecto", f"Error al guardar:\n{str(e)}")


class EditorArchivo(tk.Toplevel):
    def __init__(self, parent: tk.Misc, base_path: Path, archivo_id: Optional[int], on_saved=None):
        super().__init__(parent)
        self.title("Archivo (institución)")
        self.geometry("520x420")
        apply_titlebar_theme(self)
        self.base_path = base_path
        self.archivo_id = archivo_id
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=10); frm.pack(fill=tk.BOTH, expand=True)
        self.v_nombre = tk.StringVar(); self.v_siglas = tk.StringVar(); self.v_dir = tk.StringVar(); self.v_cont = tk.StringVar(); self.v_email = tk.StringVar(); self.v_tel = tk.StringVar(); self.v_url = tk.StringVar()
        labels = [
            ("Nombre:", self.v_nombre),
            ("Siglas:", self.v_siglas),
            ("Dirección:", self.v_dir),
            ("Contacto:", self.v_cont),
            ("Email:", self.v_email),
            ("Teléfono:", self.v_tel),
            ("URL:", self.v_url),
        ]
        for i,(txt,var) in enumerate(labels):
            ttk.Label(frm, text=txt).grid(row=i, column=0, sticky='e', padx=6, pady=4)
            ttk.Entry(frm, textvariable=var, width=48).grid(row=i, column=1, sticky='w', padx=6, pady=4)
        btns = ttk.Frame(frm); btns.grid(row=len(labels), column=0, columnspan=2, sticky='e', pady=(14,4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)

        if archivo_id:
            self._load()

    def _load(self):
        rows = db.list_archivos(self.base_path)
        row = next((r for r in rows if r.get('id') == self.archivo_id), None)
        if not row:
            return
        self.v_nombre.set(row.get('nombre') or '')
        self.v_siglas.set(row.get('siglas') or '')
        self.v_dir.set(row.get('direccion') or '')
        self.v_cont.set(row.get('contacto') or '')
        self.v_email.set(row.get('email') or '')
        self.v_tel.set(row.get('telefono') or '')
        self.v_url.set(row.get('url') or '')

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Archivo", "Nombre requerido")
            return
        if self.archivo_id:
            db.update_archivo(self.base_path, self.archivo_id, nombre=nombre, siglas=self.v_siglas.get().strip(), direccion=self.v_dir.get().strip(), contacto=self.v_cont.get().strip(), email=self.v_email.get().strip(), telefono=self.v_tel.get().strip(), url=self.v_url.get().strip())
        else:
            db.create_archivo(self.base_path, nombre=nombre, siglas=self.v_siglas.get().strip() or None, direccion=self.v_dir.get().strip() or None, contacto=self.v_cont.get().strip() or None, email=self.v_email.get().strip() or None, telefono=self.v_tel.get().strip() or None, url=self.v_url.get().strip() or None)
        if self.on_saved:
            self.on_saved()
        self.destroy()


class EditorFondo(tk.Toplevel):
    def __init__(self, parent: tk.Misc, base_path: Path, fondo_id: Optional[int], on_saved=None):
        super().__init__(parent)
        self.title("Fondo documental")
        self.geometry("520x420")
        apply_titlebar_theme(self)
        self.base_path = base_path
        self.fondo_id = fondo_id
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=10); frm.pack(fill=tk.BOTH, expand=True)
        self.v_nombre = tk.StringVar(); self.v_desc = tk.StringVar(); self.v_desde = tk.StringVar(); self.v_hasta = tk.StringVar(); self.v_arch = tk.StringVar()
        # Archivo combo
        ttk.Label(frm, text="Archivo (institución):").grid(row=0, column=0, sticky='e', padx=6, pady=4)
        self.cmb_arch = ttk.Combobox(frm, textvariable=self.v_arch, state='readonly', width=46)
        self.cmb_arch.grid(row=0, column=1, sticky='w', padx=6, pady=4)
        self._arch_rows = db.list_archivos(self.base_path)
        self.cmb_arch['values'] = [f"{r['id']} · {r['nombre']} ({(r.get('siglas') or '').upper()})" for r in self._arch_rows]
        if self._arch_rows:
            self.cmb_arch.current(0)
        # Resto campos
        labels = [
            ("Nombre:", self.v_nombre),
            ("Descripción:", self.v_desc),
            ("Periodo desde:", self.v_desde),
            ("Periodo hasta:", self.v_hasta),
        ]
        base = 1
        for i,(txt,var) in enumerate(labels):
            ttk.Label(frm, text=txt).grid(row=base+i, column=0, sticky='e', padx=6, pady=4)
            ttk.Entry(frm, textvariable=var, width=48).grid(row=base+i, column=1, sticky='w', padx=6, pady=4)
        btns = ttk.Frame(frm); btns.grid(row=base+len(labels), column=0, columnspan=2, sticky='e', pady=(14,4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)

        if fondo_id:
            self._load()

    def _load(self):
        row = next((r for r in db.list_fondos(self.base_path) if r.get('id') == self.fondo_id), None)
        if not row:
            return
        self.v_nombre.set(row.get('nombre') or '')
        self.v_desc.set(row.get('descripcion') or '')
        self.v_desde.set(row.get('periodo_inicio') or '')
        self.v_hasta.set(row.get('periodo_fin') or '')
        a_id = row.get('archivo_id')
        if a_id:
            for i, a in enumerate(self._arch_rows):
                if a.get('id') == a_id:
                    self.cmb_arch.current(i); break

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Fondo", "Nombre requerido")
            return
        a_id = None
        if self.v_arch.get():
            try:
                a_id = int(self.v_arch.get().split('·',1)[0])
            except Exception:
                a_id = None
        data = dict(nombre=nombre, descripcion=self.v_desc.get().strip() or None, archivo_id=a_id, periodo_inicio=self.v_desde.get().strip() or None, periodo_fin=self.v_hasta.get().strip() or None)
        if self.fondo_id:
            db.update_fondo(self.base_path, self.fondo_id, **data)
        else:
            db.create_fondo(self.base_path, **data)
        if self.on_saved:
            self.on_saved()
        self.destroy()


class EditorEtiqueta(tk.Toplevel):
    def __init__(self, parent: tk.Misc, base_path: Path, tag_id: Optional[int], on_saved=None):
        super().__init__(parent)
        self.title("Etiqueta")
        self.geometry("420x260")
        apply_titlebar_theme(self)
        self.base_path = base_path
        self.tag_id = tag_id
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=10); frm.pack(fill=tk.BOTH, expand=True)
        self.v_nombre = tk.StringVar(); self.v_desc = tk.StringVar()
        ttk.Label(frm, text="Nombre:").grid(row=0, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.v_nombre, width=42).grid(row=0, column=1, sticky='w', padx=6, pady=4)
        ttk.Label(frm, text="Descripción:").grid(row=1, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.v_desc, width=42).grid(row=1, column=1, sticky='w', padx=6, pady=4)
        btns = ttk.Frame(frm); btns.grid(row=2, column=0, columnspan=2, sticky='e', pady=(14,4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)

        if tag_id:
            self._load()

    def _load(self):
        row = next((r for r in db.list_etiquetas(self.base_path) if r.get('id') == self.tag_id), None)
        if not row:
            return
        self.v_nombre.set(row.get('nombre') or '')
        self.v_desc.set(row.get('descripcion') or '')

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Etiqueta", "Nombre requerido")
            return
        if self.tag_id:
            db.update_etiqueta(self.base_path, self.tag_id, nombre=nombre, descripcion=self.v_desc.get().strip() or None)
        else:
            db.create_etiqueta(self.base_path, nombre=nombre, descripcion=self.v_desc.get().strip() or None)
        if self.on_saved:
            self.on_saved()
        self.destroy()


class QuickEditorArchivo(tk.Toplevel):
    """Compact archivo editor for quick creation from project editor"""
    def __init__(self, parent: tk.Misc, base_path: Path, on_saved=None):
        super().__init__(parent)
        self.title("Crear Archivo")
        self.geometry("480x280")
        apply_titlebar_theme(self)
        self.base_path = base_path
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=10); frm.pack(fill=tk.BOTH, expand=True)
        self.v_nombre = tk.StringVar()
        self.v_siglas = tk.StringVar()
        
        ttk.Label(frm, text="Nombre:").grid(row=0, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.v_nombre, width=42).grid(row=0, column=1, sticky='w', padx=6, pady=4)
        ttk.Label(frm, text="Siglas:").grid(row=1, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.v_siglas, width=42).grid(row=1, column=1, sticky='w', padx=6, pady=4)
        
        ttk.Label(frm, text="(Campos adicionales se pueden editar después)", font=('', 9, 'italic')).grid(row=2, column=0, columnspan=2, pady=(10,0))
        
        btns = ttk.Frame(frm); btns.grid(row=3, column=0, columnspan=2, sticky='e', pady=(20,4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)
        
        # Modal
        self.transient(parent)
        self.grab_set()
        self.focus_set()

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Archivo", "Nombre requerido")
            return
        
        siglas = self.v_siglas.get().strip()
        
        new_id = db.create_archivo(
            self.base_path, 
            nombre=nombre,
            siglas=siglas if siglas else None
        )
        
        if self.on_saved:
            self.on_saved(new_id)
        
        self.destroy()


class QuickEditorFondo(tk.Toplevel):
    """Compact fondo editor for quick creation from project editor"""
    def __init__(self, parent: tk.Misc, base_path: Path, archivo_id: int, on_saved=None):
        super().__init__(parent)
        self.title("Crear Fondo")
        self.geometry("480x240")
        apply_titlebar_theme(self)
        self.base_path = base_path
        self.archivo_id = archivo_id
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=10); frm.pack(fill=tk.BOTH, expand=True)
        self.v_nombre = tk.StringVar()
        self.v_desc = tk.StringVar()
        
        ttk.Label(frm, text="Nombre:").grid(row=0, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.v_nombre, width=42).grid(row=0, column=1, sticky='w', padx=6, pady=4)
        ttk.Label(frm, text="Descripción:").grid(row=1, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.v_desc, width=42).grid(row=1, column=1, sticky='w', padx=6, pady=4)
        
        btns = ttk.Frame(frm); btns.grid(row=2, column=0, columnspan=2, sticky='e', pady=(20,4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)
        
        # Modal
        self.transient(parent)
        self.grab_set()
        self.focus_set()

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Fondo", "Nombre requerido")
            return
        
        data = dict(
            nombre=nombre,
            descripcion=self.v_desc.get().strip() or None,
            archivo_id=self.archivo_id
        )
        
        new_id = db.create_fondo(self.base_path, **data)
        
        if self.on_saved:
            self.on_saved(new_id)
        
        self.destroy()


class QuickEditorEtiqueta(tk.Toplevel):
    """Compact etiqueta editor for quick creation from project editor"""
    def __init__(self, parent: tk.Misc, base_path: Path, on_saved=None):
        super().__init__(parent)
        self.title("Crear Etiqueta")
        self.geometry("420x200")
        apply_titlebar_theme(self)
        self.base_path = base_path
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=10); frm.pack(fill=tk.BOTH, expand=True)
        self.v_nombre = tk.StringVar()
        self.v_desc = tk.StringVar()
        
        ttk.Label(frm, text="Nombre:").grid(row=0, column=0, sticky='e', padx=6, pady=4)
        e_nombre = ttk.Entry(frm, textvariable=self.v_nombre, width=38)
        e_nombre.grid(row=0, column=1, sticky='w', padx=6, pady=4)
        e_nombre.focus_set()
        
        ttk.Label(frm, text="Descripción:").grid(row=1, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.v_desc, width=38).grid(row=1, column=1, sticky='w', padx=6, pady=4)
        
        btns = ttk.Frame(frm); btns.grid(row=2, column=0, columnspan=2, sticky='e', pady=(20,4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)
        
        # Modal
        self.transient(parent)
        self.grab_set()
        
        # Bind Enter key to save
        e_nombre.bind('<Return>', lambda e: self._save())

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Etiqueta", "Nombre requerido")
            return
        
        new_id = db.create_etiqueta(
            self.base_path, 
            nombre=nombre,
            descripcion=self.v_desc.get().strip() or None
        )
        
        if self.on_saved:
            self.on_saved(new_id)
        
        self.destroy()


def open_metadata_manager(parent: tk.Misc, focus_tab: str = "proyectos", edit_project_id: Optional[int] = None):
    win = MetadataManager(parent, focus_tab=focus_tab, edit_project_id=edit_project_id)
    parent.wait_window(win)

