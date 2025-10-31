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
from utils.window_utils import center_to_parent


class ToolTip:
    """Tooltip personalizado para mostrar ayuda en campos"""
    def __init__(self, widget, text: str, delay: int = 500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.after_id = None
        
        widget.bind('<Enter>', self.on_enter)
        widget.bind('<Leave>', self.on_leave)
    
    def on_enter(self, event=None):
        self.after_id = self.widget.after(self.delay, self.show_tip)
    
    def on_leave(self, event=None):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        self.hide_tip()
    
    def show_tip(self):
        if self.tip_window:
            return
        
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        frame = ttk.Frame(tw, relief=tk.SOLID, borderwidth=1)
        frame.pack()
        
        label = ttk.Label(
            frame, 
            text=self.text, 
            justify=tk.LEFT,
            background="#ffffdd" if not USE_BOOTSTRAP else None,
            foreground="#000000" if not USE_BOOTSTRAP else None,
            relief=tk.FLAT,
            padding=(5, 3)
        )
        label.pack()
    
    def hide_tip(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


def create_field_with_help(parent: ttk.Frame, row: int, label_text: str, help_text: str, 
                           entry_var: tk.Variable = None, entry_width: int = 50,
                           required: bool = False) -> tuple[ttk.Label, ttk.Entry, ttk.Label]:
    """Crea un campo con etiqueta, entry y icono de ayuda con tooltip.
    
    Returns:
        tuple: (label_widget, entry_widget, help_icon_widget)
    """
    # Frame contenedor para la fila
    row_frame = ttk.Frame(parent)
    row_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=4)
    
    # Etiqueta
    label_final = label_text + (" *" if required else "")
    lbl = ttk.Label(row_frame, text=label_final, width=20, anchor=tk.W)
    lbl.pack(side=tk.LEFT, padx=(0, 5))
    
    # Entry
    entry = ttk.Entry(row_frame, textvariable=entry_var, width=entry_width)
    entry.pack(side=tk.LEFT, padx=(0, 5))
    
    # Icono de ayuda (sin color forzado para usar el del tema)
    help_icon = ttk.Label(row_frame, text="ℹ️", cursor="question_arrow")
    help_icon.pack(side=tk.LEFT)
    
    # Tooltip
    ToolTip(help_icon, help_text)
    
    return lbl, entry, help_icon


# Diccionario de ayudas por campo (basado en estándares ISAD(G), Dublin Core, etc.)
FIELD_HELP = {
    # Archivos
    'archivo_nombre': 'Nombre oficial completo de la institución o archivo. Según ISAD(G) 3.1.2.',
    'archivo_siglas': 'Siglas o acrónimo oficial del archivo (ej: AHN, AGI, BNE). Max 6 caracteres.',
    'archivo_codigo': 'Código único de identificación del repositorio según estándares nacionales.',
    'archivo_tipo': 'Tipo de institución: archivo, biblioteca, museo, centro de documentación.',
    'archivo_direccion': 'Dirección postal completa de la sede principal.',
    'archivo_ciudad': 'Ciudad o localidad donde se ubica el archivo.',
    'archivo_provincia': 'Provincia o región administrativa.',
    'archivo_pais': 'País sede del archivo. Por defecto: España.',
    'archivo_contacto': 'Persona responsable o cargo de contacto principal.',
    'archivo_email': 'Correo electrónico oficial de contacto.',
    'archivo_telefono': 'Teléfono principal de contacto con prefijo internacional.',
    'archivo_url': 'URL del sitio web oficial del archivo.',
    'archivo_horario': 'Horario de atención al público (ej: L-V 9:00-14:00).',
    'archivo_acceso': 'Condiciones y restricciones de acceso a los fondos.',
    'archivo_coordenadas': 'Coordenadas geográficas (lat, lon) para geolocalización.',
    'archivo_notas': 'Información adicional o notas sobre el archivo.',
    
    # Fondos
    'fondo_nombre': 'Título o nombre del fondo documental según ISAD(G) 3.1.2.',
    'fondo_codigo': 'Código de referencia del fondo según ISAD(G) 3.1.1 (ej: ES.28079.AHN/1.1).',
    'fondo_titulo': 'Título formal del fondo documental según ISAD(G) 3.1.2.',
    'fondo_nivel': 'Nivel de descripción: fonds, series, file, item según ISAD(G) 3.1.4.',
    'fondo_descripcion': 'Descripción general del contenido y contexto del fondo.',
    'fondo_archivo': 'Archivo o institución que custodia este fondo.',
    'fondo_fecha_inicio': 'Fecha inicial del periodo cubierto (YYYY, YYYY-MM-DD).',
    'fondo_fecha_fin': 'Fecha final del periodo cubierto (YYYY, YYYY-MM-DD).',
    'fondo_fecha_ini': 'Fecha inicial del periodo cubierto (YYYY, YYYY-MM-DD).',
    'fondo_volumen': 'Extensión y soporte del fondo (ej: 150 cajas, 300 libros).',
    'fondo_historia': 'Historia institucional o biográfica del productor según ISAD(G) 3.2.2.',
    'fondo_archivistica': 'Historia archivística del fondo según ISAD(G) 3.2.3.',
    'fondo_ingreso': 'Forma de ingreso al archivo según ISAD(G) 3.2.4.',
    'fondo_alcance': 'Alcance y contenido según ISAD(G) 3.3.1.',
    'fondo_valoracion': 'Criterios de valoración y selección según ISAD(G) 3.3.2.',
    'fondo_organizacion': 'Sistema de organización según ISAD(G) 3.3.4.',
    'fondo_acceso_cond': 'Condiciones de acceso según ISAD(G) 3.4.1.',
    'fondo_reproduccion': 'Condiciones de reproducción según ISAD(G) 3.4.2.',
    'fondo_lengua': 'Lengua/escritura de los documentos según ISAD(G) 3.4.3 (ISO 639-2).',
    'fondo_instrumentos': 'Instrumentos de descripción disponibles según ISAD(G) 3.4.5.',
    
    # Etiquetas
    'etiqueta_nombre': 'Término o descriptor controlado para clasificación temática.',
    'etiqueta_termino': 'Término o descriptor controlado para clasificación temática.',
    'etiqueta_tipo': 'Tipo: topic (tema), person (persona), place (lugar), temporal (periodo).',
    'etiqueta_vocabulario': 'Fuente del vocabulario controlado (LCSH, AAT, UNESCO, etc.).',
    'etiqueta_uri': 'URI del término en vocabularios externos (Wikidata, GeoNames, etc.).',
    'etiqueta_descripcion': 'Nota de alcance o definición del término.',
    
    # Proyectos
    'proyecto_codigo': 'Código único del proyecto de digitalización (generado automáticamente).',
    'proyecto_titulo': 'Título Dublin Core del documento o unidad documental.',
    'proyecto_titulo_alt': 'Título alternativo o variante según Dublin Core.',
    'proyecto_codigo_ref': 'Código de referencia archivístico completo (ej: ES.28079.AHN/1.1/25).',
    'proyecto_signatura': 'Signatura topográfica del documento original.',
    'proyecto_nivel': 'Nivel de descripción: collection, file, item según ISAD(G).',
    'proyecto_tipo_doc': 'Tipo de documento (carta, manuscrito, registro, etc.).',
    'proyecto_tipo_mat': 'Tipo de material (papel, pergamino, textil, etc.).',
    'proyecto_autor': 'Autor o creador principal del documento según Dublin Core.',
    'proyecto_creador': 'Creador(es) del documento (puede ser distinto del autor).',
    'proyecto_productor': 'Entidad productora del documento.',
    'proyecto_tema': 'Materia o tema principal del documento.',
    'proyecto_descripcion': 'Descripción libre del contenido.',
    'proyecto_alcance': 'Alcance y contenido según ISAD(G) 3.3.1.',
    'proyecto_resumen': 'Resumen ejecutivo del contenido.',
    'proyecto_fecha_creacion': 'Fecha de creación del documento original.',
    'proyecto_fecha_ini': 'Fecha inicial del periodo cubierto.',
    'proyecto_fecha_fin': 'Fecha final del periodo cubierto.',
    'proyecto_lugar': 'Lugar de creación o producción del documento.',
    'proyecto_lengua': 'Lengua del documento según ISO 639-2 (spa, cat, lat, etc.).',
    'proyecto_cobertura_temp': 'Cobertura temporal del contenido.',
    'proyecto_cobertura_geo': 'Cobertura geográfica del contenido.',
    'proyecto_extension': 'Extensión física (número de páginas, folios, etc.).',
    'proyecto_formato': 'Formato físico (libro, legajo, rollo, etc.).',
    'proyecto_soporte': 'Soporte material (papel, pergamino, etc.).',
    'proyecto_dimensiones': 'Dimensiones físicas en mm (alto x ancho x grosor).',
    'proyecto_conservacion': 'Estado de conservación (bueno, regular, malo, restaurado).',
    'proyecto_tratamiento': 'Tratamiento técnico aplicado (limpieza, restauración, etc.).',
    'proyecto_derechos': 'Declaración de derechos de autor.',
    'proyecto_licencia': 'Licencia de uso (In Copyright, CC-BY, Public Domain, etc.).',
    'proyecto_titular': 'Titular de los derechos de autor.',
    'proyecto_acceso': 'Condiciones de acceso al documento digital.',
    'proyecto_uso': 'Condiciones de uso y reproducción.',
    'proyecto_fondo': 'Fondo documental al que pertenece.',
    'proyecto_responsable': 'Responsable del proyecto de digitalización.',
    'proyecto_fecha_digit': 'Fecha de la digitalización.',
    'proyecto_equipamiento': 'Equipamiento utilizado para la digitalización.',
    'proyecto_resolucion': 'Resolución de captura en DPI (300, 400, 600).',
    'proyecto_espacio_color': 'Espacio de color (RGB, CMYK, Grayscale).',
    'proyecto_formato_archivo': 'Formato de archivo digital (TIFF, JPEG2000, PNG).',
    'proyecto_checksum': 'Suma de verificación para integridad (MD5, SHA256).',
    'proyecto_software': 'Software utilizado en el proceso.',
}


class MetadataManager(tk.Toplevel):
    def __init__(self, parent: tk.Misc, focus_tab: str = "proyectos", edit_project_id: Optional[int] = None):
        super().__init__(parent)
        self.title("Gestión de Metadatos · GeoDocs")
        self.geometry("1050x650")
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
        # Center over parent
        center_to_parent(self, parent)

    # ---- PROYECTOS ----
    def _build_tab_proyectos(self):
        tab = ttk.Frame(self.nb); self.nb.add(tab, text="📁 Proyectos")
        top = ttk.Frame(tab); top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(top, text="➕ Nuevo", command=self._new_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="✏️ Editar", command=self._edit_selected_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="🗑 Eliminar", command=self._delete_selected_project).pack(side=tk.LEFT, padx=3)
        # ttk.Button(top, text="⚙️ Tablas (Archivos/Fondos/Etiquetas)", command=lambda: self.nb.select(1)).pack(side=tk.LEFT, padx=10)

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
            (Messagebox.show_warning(title="Proyectos", message="Seleccione un proyecto", parent=self) if Messagebox else messagebox.showwarning("Proyectos","Seleccione un proyecto", parent=self))
            return
        self._open_project_editor(pid)

    def _delete_selected_project(self):
        pid = self._selected_id(self.tree_proj, 0)
        if not pid:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar el proyecto? (No borra archivos)", parent=self):
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
        if not messagebox.askyesno("Eliminar", "¿Eliminar el archivo (institución)?", parent=self):
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
        if not messagebox.askyesno("Eliminar", "¿Eliminar el fondo?", parent=self):
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
        if not messagebox.askyesno("Eliminar", "¿Eliminar la etiqueta?", parent=self):
            return
        db.delete_etiqueta(self.base_path, tid)
        self._reload_etiquetas()


# ---- Editors ----
class EditorProyecto(tk.Toplevel):
    def __init__(self, parent: tk.Misc, base_path: Path, project_id: Optional[int], on_saved=None):
        super().__init__(parent)
        self.title("Proyecto")
        self.geometry("800x580")
        apply_titlebar_theme(self)
        
        # Ocultar ventana temporalmente para evitar parpadeo
        self.withdraw()
        
        # Modal and center
        self.transient(parent)
        center_to_parent(self, parent)
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
        def add_entry(var, width=56):
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
        self.cmb_arch = ttk.Combobox(archivo_frame, textvariable=self.var_archivo, state='readonly', width=50)
        self.cmb_arch.pack(side=tk.LEFT)
        ttk.Button(archivo_frame, text="➕", width=3, command=self._quick_create_archivo).pack(side=tk.LEFT, padx=(6,0))
        self.cmb_arch.bind('<<ComboboxSelected>>', lambda e: self._refresh_fondos())

        add_label("Fondo:")
        fondo_frame = ttk.Frame(frm)
        fondo_frame.grid(row=row, column=1, sticky='w', padx=6, pady=4); row += 1
        self.cmb_fondo = ttk.Combobox(fondo_frame, textvariable=self.var_fondo, state='readonly', width=50)
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
        self.lst_tags = tk.Listbox(tag_frame, selectmode=tk.MULTIPLE, height=5, width=51, yscrollcommand=tag_scroll.set, exportselection=False)
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
        # bar = ttk.Frame(frm); bar.grid(row=row, column=0, columnspan=2, sticky='w', padx=6, pady=(10,4)); row += 1
        # ttk.Button(bar, text="Gestionar Archivos/Fondos/Etiquetas", command=lambda: MetadataManager(self, focus_tab='archivos')).pack(side=tk.LEFT)

        # Botonera guardar/cancelar
        btns = ttk.Frame(frm); btns.grid(row=row, column=0, columnspan=2, sticky='e', pady=(20, 4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)

        # Cargar datos
        self._load_tags()
        self._load_archivos_fondos()
        if project_id:
            self._load_project(project_id)
        
        # Mostrar ventana después de construir todo
        self.deiconify()
        self.grab_set()

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
            messagebox.showwarning("Crear Fondo", "Seleccione primero un Archivo (institución)", parent=self)
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
            messagebox.showwarning("Proyecto", "El título es obligatorio", parent=self)
            return
        
        signatura = self.var_sign.get().strip()
        
        # Validate signatura if provided
        if signatura:
            valid, error_msg = db.validate_signatura(signatura)
            if not valid:
                messagebox.showerror("Proyecto", f"Signatura inválida:\n{error_msg}", parent=self)
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
            messagebox.showerror("Proyecto", f"Error de validación:\n{str(e)}", parent=self)
        except Exception as e:
            messagebox.showerror("Proyecto", f"Error al guardar:\n{str(e)}", parent=self)


class EditorArchivo(tk.Toplevel):
    def __init__(self, parent: tk.Misc, base_path: Path, archivo_id: Optional[int], on_saved=None):
        super().__init__(parent)
        self.title("Archivo (Institución) · Editor")
        self.geometry("750x930")
        apply_titlebar_theme(self)
        
        # Ocultar ventana temporalmente para evitar parpadeo
        self.withdraw()
        
        # Modal and center
        self.transient(parent)
        center_to_parent(self, parent)
        self.base_path = base_path
        self.archivo_id = archivo_id
        self.on_saved = on_saved

        # Frame principal sin scroll
        frm = ttk.Frame(self, padding=15)
        frm.pack(fill=tk.BOTH, expand=True)
        
        # Variables
        self.v_nombre = tk.StringVar()
        self.v_siglas = tk.StringVar()
        self.v_codigo = tk.StringVar()
        self.v_tipo = tk.StringVar(value='archivo')
        self.v_dir = tk.StringVar()
        self.v_ciudad = tk.StringVar()
        self.v_provincia = tk.StringVar()
        self.v_pais = tk.StringVar(value='España')
        self.v_cont = tk.StringVar()
        self.v_email = tk.StringVar()
        self.v_tel = tk.StringVar()
        self.v_url = tk.StringVar()
        self.v_horario = tk.StringVar()
        self.v_acceso = tk.StringVar()
        self.v_notas = tk.StringVar()
        
        # Título
        ttk.Label(frm, text="Información del Archivo o Institución", 
                 font=("", 12, "bold")).grid(row=0, column=0, columnspan=3, pady=(0,15))
        
        row = 1
        
        # Usar la función helper para crear campos con ayuda
        create_field_with_help(frm, row, "Nombre oficial *", FIELD_HELP['archivo_nombre'], 
                              self.v_nombre, entry_width=50, required=True)
        row += 1
        
        create_field_with_help(frm, row, "Siglas", FIELD_HELP['archivo_siglas'], 
                              self.v_siglas, entry_width=15)
        row += 1
        
        create_field_with_help(frm, row, "Código ID", FIELD_HELP['archivo_codigo'], 
                              self.v_codigo, entry_width=25)
        row += 1
        
        # Tipo (combobox)
        row_frame = ttk.Frame(frm)
        row_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=4)
        ttk.Label(row_frame, text="Tipo institución", width=20, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))
        tipo_combo = ttk.Combobox(row_frame, textvariable=self.v_tipo, width=28, 
                                 values=['archivo', 'biblioteca', 'museo', 'centro documentación'])
        tipo_combo.pack(side=tk.LEFT, padx=(0, 5))
        help_icon = ttk.Label(row_frame, text="ℹ️", cursor="question_arrow")
        help_icon.pack(side=tk.LEFT)
        ToolTip(help_icon, FIELD_HELP['archivo_tipo'])
        row += 1
        
        ttk.Separator(frm, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=3, 
                                                       sticky="ew", pady=10)
        row += 1
        
        ttk.Label(frm, text="📍 Ubicación", font=("", 10, "bold")).grid(row=row, column=0, 
                                                                          columnspan=3, sticky=tk.W, pady=(0,5))
        row += 1
        
        create_field_with_help(frm, row, "Dirección", FIELD_HELP['archivo_direccion'], 
                              self.v_dir, entry_width=50)
        row += 1
        
        create_field_with_help(frm, row, "Ciudad", FIELD_HELP['archivo_ciudad'], 
                              self.v_ciudad, entry_width=30)
        row += 1
        
        create_field_with_help(frm, row, "Provincia", FIELD_HELP['archivo_provincia'], 
                              self.v_provincia, entry_width=30)
        row += 1
        
        create_field_with_help(frm, row, "País", FIELD_HELP['archivo_pais'], 
                              self.v_pais, entry_width=30)
        row += 1
        
        ttk.Separator(frm, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=3, 
                                                       sticky="ew", pady=10)
        row += 1
        
        ttk.Label(frm, text="📞 Contacto", font=("", 10, "bold")).grid(row=row, column=0, 
                                                                         columnspan=3, sticky=tk.W, pady=(0,5))
        row += 1
        
        create_field_with_help(frm, row, "Responsable", FIELD_HELP['archivo_contacto'], 
                              self.v_cont, entry_width=40)
        row += 1
        
        create_field_with_help(frm, row, "Email", FIELD_HELP['archivo_email'], 
                              self.v_email, entry_width=40)
        row += 1
        
        create_field_with_help(frm, row, "Teléfono", FIELD_HELP['archivo_telefono'], 
                              self.v_tel, entry_width=25)
        row += 1
        
        create_field_with_help(frm, row, "URL", FIELD_HELP['archivo_url'], 
                              self.v_url, entry_width=50)
        row += 1
        
        create_field_with_help(frm, row, "Horario", FIELD_HELP['archivo_horario'], 
                              self.v_horario, entry_width=40)
        row += 1
        
        ttk.Separator(frm, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=3, 
                                                       sticky="ew", pady=10)
        row += 1
        
        create_field_with_help(frm, row, "Condiciones acceso", FIELD_HELP['archivo_acceso'], 
                              self.v_acceso, entry_width=50)
        row += 1
        
        create_field_with_help(frm, row, "Notas", FIELD_HELP['archivo_notas'], 
                              self.v_notas, entry_width=50)
        row += 1
        
        # Botonera
        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=3, sticky='e', pady=(20,4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)

        if archivo_id:
            self._load()
        
        # Mostrar ventana después de construir todo
        self.deiconify()
        self.grab_set()

    def _load(self):
        rows = db.list_archivos(self.base_path)
        row = next((r for r in rows if r.get('id') == self.archivo_id), None)
        if not row:
            return
        self.v_nombre.set(row.get('nombre') or row.get('nombre_oficial') or '')
        self.v_siglas.set(row.get('siglas') or '')
        self.v_codigo.set(row.get('codigo_identificacion') or '')
        self.v_tipo.set(row.get('tipo_institucion') or 'archivo')
        self.v_dir.set(row.get('direccion') or row.get('direccion_completa') or '')
        self.v_ciudad.set(row.get('ciudad') or '')
        self.v_provincia.set(row.get('provincia') or '')
        self.v_pais.set(row.get('pais') or 'España')
        self.v_cont.set(row.get('contacto') or row.get('contacto_responsable') or '')
        self.v_email.set(row.get('email') or '')
        self.v_tel.set(row.get('telefono') or '')
        self.v_url.set(row.get('url') or '')
        self.v_horario.set(row.get('horario_atencion') or '')
        self.v_acceso.set(row.get('condiciones_acceso') or '')
        self.v_notas.set(row.get('notas') or '')

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Archivo", "Nombre oficial es obligatorio", parent=self)
            return
        
        data = {
            'nombre': nombre,
            'siglas': self.v_siglas.get().strip() or None,
            'codigo_identificacion': self.v_codigo.get().strip() or None,
            'tipo_institucion': self.v_tipo.get().strip() or 'archivo',
            'direccion': self.v_dir.get().strip() or None,
            'ciudad': self.v_ciudad.get().strip() or None,
            'provincia': self.v_provincia.get().strip() or None,
            'pais': self.v_pais.get().strip() or 'España',
            'contacto': self.v_cont.get().strip() or None,
            'email': self.v_email.get().strip() or None,
            'telefono': self.v_tel.get().strip() or None,
            'url': self.v_url.get().strip() or None,
            'horario_atencion': self.v_horario.get().strip() or None,
            'condiciones_acceso': self.v_acceso.get().strip() or None,
            'notas': self.v_notas.get().strip() or None,
        }
        
        if self.archivo_id:
            db.update_archivo(self.base_path, self.archivo_id, **data)
        else:
            db.create_archivo(self.base_path, **data)
        
        if self.on_saved:
            self.on_saved()
        self.destroy()


class EditorFondo(tk.Toplevel):
    def __init__(self, parent: tk.Misc, base_path: Path, fondo_id: Optional[int], on_saved=None):
        super().__init__(parent)
        self.title("Fondo Documental · Editor")
        self.geometry("750x570")
        apply_titlebar_theme(self)
        
        # Ocultar ventana temporalmente para evitar parpadeo
        self.withdraw()
        
        # Modal and center
        self.transient(parent)
        center_to_parent(self, parent)
        self.base_path = base_path
        self.fondo_id = fondo_id
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=15); frm.pack(fill=tk.BOTH, expand=True)
        
        # Variables
        self.v_nombre = tk.StringVar()
        self.v_codigo = tk.StringVar()
        self.v_desc = tk.StringVar()
        self.v_desde = tk.StringVar()
        self.v_hasta = tk.StringVar()
        self.v_arch = tk.StringVar()
        self.v_alcance = tk.StringVar()
        self.v_organizacion = tk.StringVar()
        
        # Título
        ttk.Label(frm, text="Información del Fondo Documental", 
                 font=("", 12, "bold")).grid(row=0, column=0, columnspan=3, pady=(0,15))
        
        row = 1
        
        # Archivo (institución) - con tooltip
        row_frame = ttk.Frame(frm)
        row_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=4)
        ttk.Label(row_frame, text="Archivo (institución)", width=20, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))
        self.cmb_arch = ttk.Combobox(row_frame, textvariable=self.v_arch, state='readonly', width=42)
        self.cmb_arch.pack(side=tk.LEFT, padx=(0, 5))
        self._arch_rows = db.list_archivos(self.base_path)
        self.cmb_arch['values'] = [f"{r['id']} · {r['nombre']} ({(r.get('siglas') or '').upper()})" for r in self._arch_rows]
        if self._arch_rows:
            self.cmb_arch.current(0)
        help_icon = ttk.Label(row_frame, text="ℹ️", cursor="question_arrow")
        help_icon.pack(side=tk.LEFT)
        ToolTip(help_icon, FIELD_HELP['fondo_archivo'])
        row += 1
        
        create_field_with_help(frm, row, "Título/Nombre *", FIELD_HELP['fondo_nombre'], 
                              self.v_nombre, entry_width=50, required=True)
        row += 1
        
        create_field_with_help(frm, row, "Código referencia", FIELD_HELP['fondo_codigo'], 
                              self.v_codigo, entry_width=30)
        row += 1
        
        create_field_with_help(frm, row, "Descripción", FIELD_HELP['fondo_descripcion'], 
                              self.v_desc, entry_width=50)
        row += 1
        
        ttk.Separator(frm, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=3, 
                                                       sticky="ew", pady=10)
        row += 1
        
        ttk.Label(frm, text="📅 Fechas", font=("", 10, "bold")).grid(row=row, column=0, 
                                                                       columnspan=3, sticky=tk.W, pady=(0,5))
        row += 1
        
        create_field_with_help(frm, row, "Periodo desde", FIELD_HELP['fondo_fecha_inicio'], 
                              self.v_desde, entry_width=20)
        row += 1
        
        create_field_with_help(frm, row, "Periodo hasta", FIELD_HELP['fondo_fecha_fin'], 
                              self.v_hasta, entry_width=20)
        row += 1
        
        ttk.Separator(frm, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=3, 
                                                       sticky="ew", pady=10)
        row += 1
        
        create_field_with_help(frm, row, "Alcance y contenido", FIELD_HELP['fondo_alcance'], 
                              self.v_alcance, entry_width=50)
        row += 1
        
        create_field_with_help(frm, row, "Organización", FIELD_HELP['fondo_organizacion'], 
                              self.v_organizacion, entry_width=50)
        row += 1
        
        # Botonera
        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=3, sticky='e', pady=(20,4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)

        if fondo_id:
            self._load()
        
        # Mostrar ventana después de construir todo
        self.deiconify()
        self.grab_set()

    def _load(self):
        row = next((r for r in db.list_fondos(self.base_path) if r.get('id') == self.fondo_id), None)
        if not row:
            return
        self.v_nombre.set(row.get('nombre') or row.get('titulo') or '')
        self.v_codigo.set(row.get('codigo_referencia') or '')
        self.v_desc.set(row.get('descripcion') or '')
        self.v_desde.set(row.get('periodo_inicio') or row.get('fecha_inicial') or '')
        self.v_hasta.set(row.get('periodo_fin') or row.get('fecha_final') or '')
        self.v_alcance.set(row.get('alcance_contenido') or '')
        self.v_organizacion.set(row.get('organizacion') or '')
        a_id = row.get('archivo_id')
        if a_id:
            for i, a in enumerate(self._arch_rows):
                if a.get('id') == a_id:
                    self.cmb_arch.current(i); break

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Fondo", "Título/Nombre es obligatorio", parent=self)
            return
        a_id = None
        if self.v_arch.get():
            try:
                a_id = int(self.v_arch.get().split('·',1)[0])
            except Exception:
                a_id = None
        
        data = {
            'nombre': nombre,
            'codigo_referencia': self.v_codigo.get().strip() or None,
            'descripcion': self.v_desc.get().strip() or None,
            'archivo_id': a_id,
            'periodo_inicio': self.v_desde.get().strip() or None,
            'periodo_fin': self.v_hasta.get().strip() or None,
            'alcance_contenido': self.v_alcance.get().strip() or None,
            'organizacion': self.v_organizacion.get().strip() or None,
        }
        
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
        self.title("Etiqueta/Descriptor · Editor")
        self.geometry("650x350")
        apply_titlebar_theme(self)
        
        # Ocultar ventana temporalmente para evitar parpadeo
        self.withdraw()
        
        # Modal and center
        self.transient(parent)
        center_to_parent(self, parent)
        self.base_path = base_path
        self.tag_id = tag_id
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=15); frm.pack(fill=tk.BOTH, expand=True)
        
        # Variables
        self.v_nombre = tk.StringVar()
        self.v_tipo = tk.StringVar(value='topic')
        self.v_desc = tk.StringVar()
        self.v_vocabulario = tk.StringVar()
        
        # Título
        ttk.Label(frm, text="Información de la Etiqueta/Descriptor", 
                 font=("", 12, "bold")).grid(row=0, column=0, columnspan=3, pady=(0,15))
        
        row = 1
        
        create_field_with_help(frm, row, "Término *", FIELD_HELP['etiqueta_nombre'], 
                              self.v_nombre, entry_width=40, required=True)
        row += 1
        
        # Tipo (combobox)
        row_frame = ttk.Frame(frm)
        row_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=4)
        ttk.Label(row_frame, text="Tipo", width=20, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))
        tipo_combo = ttk.Combobox(row_frame, textvariable=self.v_tipo, width=28, 
                                 values=['topic', 'geographic', 'temporal', 'genre', 'person', 'corporate'])
        tipo_combo.pack(side=tk.LEFT, padx=(0, 5))
        help_icon = ttk.Label(row_frame, text="ℹ️", cursor="question_arrow")
        help_icon.pack(side=tk.LEFT)
        ToolTip(help_icon, FIELD_HELP['etiqueta_tipo'])
        row += 1
        
        create_field_with_help(frm, row, "Descripción", FIELD_HELP['etiqueta_descripcion'], 
                              self.v_desc, entry_width=40)
        row += 1
        
        create_field_with_help(frm, row, "Vocabulario fuente", FIELD_HELP['etiqueta_vocabulario'], 
                              self.v_vocabulario, entry_width=35)
        row += 1
        
        ttk.Label(frm, text="💡 Las etiquetas permiten clasificar y buscar proyectos", 
                 font=("", 9, "italic"), foreground="gray").grid(row=row, column=0, 
                                                                   columnspan=3, pady=(10,0))
        row += 1
        
        # Botonera
        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=3, sticky='e', pady=(20,4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)

        if tag_id:
            self._load()
        
        # Mostrar ventana después de construir todo
        self.deiconify()
        self.grab_set()

    def _load(self):
        row = next((r for r in db.list_etiquetas(self.base_path) if r.get('id') == self.tag_id), None)
        if not row:
            return
        self.v_nombre.set(row.get('nombre') or row.get('termino') or '')
        self.v_tipo.set(row.get('tipo_termino') or 'topic')
        self.v_desc.set(row.get('descripcion') or '')
        self.v_vocabulario.set(row.get('vocabulario_fuente') or '')

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Etiqueta", "Término es obligatorio", parent=self)
            return
        
        data = {
            'nombre': nombre,
            'tipo_termino': self.v_tipo.get().strip() or 'topic',
            'descripcion': self.v_desc.get().strip() or None,
            'vocabulario_fuente': self.v_vocabulario.get().strip() or None,
        }
        
        if self.tag_id:
            db.update_etiqueta(self.base_path, self.tag_id, **data)
        else:
            db.create_etiqueta(self.base_path, **data)
        if self.on_saved:
            self.on_saved()
        self.destroy()


class QuickEditorArchivo(tk.Toplevel):
    """Compact archivo editor for quick creation from project editor"""
    def __init__(self, parent: tk.Misc, base_path: Path, on_saved=None):
        super().__init__(parent)
        self.title("⚡ Nuevo Archivo")
        self.geometry("600x300")
        apply_titlebar_theme(self)
        
        # Ocultar ventana temporalmente para evitar parpadeo
        self.withdraw()
        
        # Center before making modal
        self.transient(parent)
        center_to_parent(self, parent)
        self.base_path = base_path
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=15); frm.pack(fill=tk.BOTH, expand=True)
        
        self.v_nombre = tk.StringVar()
        self.v_siglas = tk.StringVar()
        self.v_ciudad = tk.StringVar()
        
        ttk.Label(frm, text="Crear Archivo (datos básicos)", 
                 font=("", 11, "bold")).grid(row=0, column=0, columnspan=3, pady=(0,12))
        
        create_field_with_help(frm, 1, "Nombre oficial *", FIELD_HELP['archivo_nombre'], 
                              self.v_nombre, entry_width=40, required=True)
        
        create_field_with_help(frm, 2, "Siglas", FIELD_HELP['archivo_siglas'], 
                              self.v_siglas, entry_width=15)
        
        create_field_with_help(frm, 3, "Ciudad", FIELD_HELP['archivo_ciudad'], 
                              self.v_ciudad, entry_width=30)
        
        ttk.Label(frm, text="💡 Podrás completar más campos después", 
                 font=("", 9, "italic"), foreground="gray").grid(row=4, column=0, 
                                                                   columnspan=3, pady=(10,0))
        
        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=3, sticky='e', pady=(20,0))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Crear", command=self._save).pack(side=tk.RIGHT, padx=6)
        
        # Mostrar ventana después de construir todo
        self.deiconify()
        self.grab_set()
        self.focus_set()

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Archivo", "Nombre oficial es obligatorio", parent=self)
            return
        
        new_id = db.create_archivo(
            self.base_path, 
            nombre=nombre,
            siglas=self.v_siglas.get().strip() or None,
            ciudad=self.v_ciudad.get().strip() or None
        )
        
        if self.on_saved:
            self.on_saved(new_id)
        
        self.destroy()


class QuickEditorFondo(tk.Toplevel):
    """Compact fondo editor for quick creation from project editor"""
    def __init__(self, parent: tk.Misc, base_path: Path, archivo_id: int, on_saved=None):
        super().__init__(parent)
        self.title("Crear Fondo")
        self.geometry("680x220")
        apply_titlebar_theme(self)
        
        # Ocultar ventana temporalmente para evitar parpadeo
        self.withdraw()
        
        # Center before making modal
        self.transient(parent)
        center_to_parent(self, parent)
        self.base_path = base_path
        self.archivo_id = archivo_id
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=10); frm.pack(fill=tk.BOTH, expand=True)
        self.v_nombre = tk.StringVar()
        self.v_desc = tk.StringVar()
        
        ttk.Label(frm, text="Nombre:").grid(row=0, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.v_nombre, width=46).grid(row=0, column=1, sticky='w', padx=6, pady=4)
        ttk.Label(frm, text="Descripción:").grid(row=1, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.v_desc, width=46).grid(row=1, column=1, sticky='w', padx=6, pady=4)
        
        btns = ttk.Frame(frm); btns.grid(row=2, column=0, columnspan=2, sticky='e', pady=(20,4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)
        
        # Mostrar ventana después de construir todo
        self.deiconify()
        self.grab_set()
        self.focus_set()

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Fondo", "Nombre requerido", parent=self)
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
        self.geometry("580x200")
        apply_titlebar_theme(self)
        
        # Ocultar ventana temporalmente para evitar parpadeo
        self.withdraw()
        
        # Center before making modal
        self.transient(parent)
        center_to_parent(self, parent)
        self.base_path = base_path
        self.on_saved = on_saved

        frm = ttk.Frame(self, padding=10); frm.pack(fill=tk.BOTH, expand=True)
        self.v_nombre = tk.StringVar()
        self.v_desc = tk.StringVar()
        
        ttk.Label(frm, text="Nombre:").grid(row=0, column=0, sticky='e', padx=6, pady=4)
        e_nombre = ttk.Entry(frm, textvariable=self.v_nombre, width=44)
        e_nombre.grid(row=0, column=1, sticky='w', padx=6, pady=4)
        e_nombre.focus_set()
        
        ttk.Label(frm, text="Descripción:").grid(row=1, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.v_desc, width=44).grid(row=1, column=1, sticky='w', padx=6, pady=4)
        
        btns = ttk.Frame(frm); btns.grid(row=2, column=0, columnspan=2, sticky='e', pady=(20,4))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=6)
        
        # Bind Enter key to save
        e_nombre.bind('<Return>', lambda e: self._save())
        
        # Mostrar ventana después de construir todo
        self.deiconify()
        self.grab_set()
        e_nombre.focus_set()

    def _save(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Etiqueta", "Nombre requerido", parent=self)
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

