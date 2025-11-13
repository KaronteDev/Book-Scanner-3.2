#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_manager.py — Gestión de bases de datos (global y por proyecto)
"""
import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# Lazy import to avoid circulars in some environments
try:
    from . import app_config as _app_config
except Exception:
    _app_config = None

GLOBAL_DB = "geodocs.db"

def _exec(cur: sqlite3.Cursor, sql: str, params: Tuple = ()) -> None:
    try:
        cur.execute(sql, params)
    except Exception as e:
        raise


def _has_column(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return column in cols


def _ensure_column(cur: sqlite3.Cursor, table: str, column: str, decl: str) -> None:
    if not _has_column(cur, table, column):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {decl}")


def init_global_db(base_path: Path) -> None:
    """Initialize global database with archivos, fondos, proyectos tables.
    Estructura mejorada según estándares ISAD(G), Dublin Core y EAD."""
    db_path = base_path / "data" / GLOBAL_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Archivos (Instituciones/Repositorios) - Basado en ISAD(G) 5.3
    cur.execute("""
    CREATE TABLE IF NOT EXISTS archivos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_identificacion TEXT UNIQUE,
        nombre_oficial TEXT NOT NULL,
        siglas TEXT,
        tipo_institucion TEXT DEFAULT 'archivo',
        nivel_descripcion TEXT DEFAULT 'repository',
        direccion_completa TEXT,
        codigo_postal TEXT,
        ciudad TEXT,
        provincia TEXT,
        pais TEXT DEFAULT 'España',
        contacto_responsable TEXT,
        email TEXT,
        telefono TEXT,
        fax TEXT,
        url TEXT,
        coordenadas_geograficas TEXT,
        horario_atencion TEXT,
        condiciones_acceso TEXT,
        notas TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Fondos documentales - Basado en ISAD(G) y EAD
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fondos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_referencia TEXT,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        archivo_id INTEGER,
        nivel_descripcion TEXT DEFAULT 'fonds',
        volumen_soporte TEXT,
        fecha_inicial TEXT,
        fecha_final TEXT,
        fecha_inicial_normalizada TEXT,
        fecha_final_normalizada TEXT,
        historia_institucional TEXT,
        historia_archivistica TEXT,
        forma_ingreso TEXT,
        alcance_contenido TEXT,
        valoracion_seleccion TEXT,
        nuevos_ingresos TEXT,
        organizacion TEXT,
        condiciones_acceso TEXT,
        condiciones_reproduccion TEXT,
        lengua_documentos TEXT DEFAULT 'spa',
        caracteristicas_fisicas TEXT,
        instrumentos_descripcion TEXT,
        existencia_originales TEXT,
        existencia_copias TEXT,
        unidades_relacionadas TEXT,
        nota_publicaciones TEXT,
        notas_generales TEXT,
        nota_archivero TEXT,
        reglas_normas TEXT DEFAULT 'ISAD(G)',
        fecha_descripcion TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (archivo_id) REFERENCES archivos(id) ON DELETE CASCADE
    );
    """)

    # Etiquetas (Materias/Descriptores controlados)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS etiquetas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        termino TEXT NOT NULL UNIQUE,
        termino_normalizado TEXT,
        tipo_termino TEXT DEFAULT 'topic',
        vocabulario_fuente TEXT,
        uri TEXT,
        descripcion TEXT,
        terminos_relacionados TEXT,
        termino_preferido_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (termino_preferido_id) REFERENCES etiquetas(id)
    );
    """)
    
    # Proyectos de digitalización - Mejorado con Dublin Core y metadatos archivísticos
    cur.execute("""
    CREATE TABLE IF NOT EXISTS proyectos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_proyecto TEXT UNIQUE,
        titulo TEXT NOT NULL,
        titulo_alternativo TEXT,
        codigo_referencia TEXT,
        signatura TEXT,
        nivel_descripcion TEXT DEFAULT 'item',
        tipo_documento TEXT,
        tipo_material TEXT,
        autor TEXT,
        creador TEXT,
        productor TEXT,
        tema TEXT,
        descripcion TEXT,
        alcance_contenido TEXT,
        resumen TEXT,
        etiquetas TEXT,
        fecha_creacion_doc TEXT,
        fecha_inicial TEXT,
        fecha_final TEXT,
        fecha_normalizadar TEXT,
        lugar_creacion TEXT,
        lengua TEXT DEFAULT 'spa',
        cobertura_temporal TEXT,
        cobertura_geografica TEXT,
        extension TEXT,
        formato TEXT,
        soporte TEXT,
        dimensiones TEXT,
        estado_conservacion TEXT,
        tratamiento_tecnico TEXT,
        derechos TEXT,
        licencia TEXT DEFAULT 'In Copyright',
        titular_derechos TEXT,
        condiciones_acceso TEXT,
        condiciones_uso TEXT,
        fondo_id INTEGER,
        proyecto_padre_id INTEGER,
        carpeta_raiz TEXT NOT NULL,
        db_path TEXT,
        notas TEXT,
        observaciones_tecnicas TEXT,
        responsable_digitalizacion TEXT,
        fecha_digitalizacion TEXT,
        equipamiento_digitalizacion TEXT,
        calidad_digitalizacion TEXT,
        formato_digital TEXT,
        resolucion_dpi INTEGER,
        espacio_color TEXT,
        formato_archivo TEXT,
        tamano_archivo_mb REAL,
        checksum TEXT,
        software_utilizado TEXT,
        metadatos_incrustados BOOLEAN DEFAULT 0,
        identificador_persistente TEXT,
        uri_canonical TEXT,
        fuente_metadatos TEXT,
        esquema_metadatos TEXT DEFAULT 'Dublin Core + ISAD(G)',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fondo_id) REFERENCES fondos(id) ON DELETE SET NULL,
        FOREIGN KEY (proyecto_padre_id) REFERENCES proyectos(id) ON DELETE SET NULL
    );
    """)
    
    # Tabla puente N:M proyecto-etiquetas
    cur.execute("""
    CREATE TABLE IF NOT EXISTS proyecto_etiquetas (
        proyecto_id INTEGER NOT NULL,
        etiqueta_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE,
        FOREIGN KEY (etiqueta_id) REFERENCES etiquetas(id) ON DELETE CASCADE,
        PRIMARY KEY (proyecto_id, etiqueta_id)
    );
    """)

    # App settings stored in DB (key/value)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    
    conn.commit()
    # --- Lightweight migrations ---
    try:
        # Migración campos legacy a nuevos campos normalizados
        _ensure_column(cur, 'archivos', 'codigo_identificacion', 'codigo_identificacion TEXT')
        _ensure_column(cur, 'archivos', 'nombre_oficial', 'nombre_oficial TEXT')
        _ensure_column(cur, 'archivos', 'siglas', 'siglas TEXT')
        _ensure_column(cur, 'archivos', 'tipo_institucion', 'tipo_institucion TEXT DEFAULT "archivo"')
        _ensure_column(cur, 'archivos', 'direccion_completa', 'direccion_completa TEXT')
        _ensure_column(cur, 'archivos', 'ciudad', 'ciudad TEXT')
        _ensure_column(cur, 'archivos', 'provincia', 'provincia TEXT')
        _ensure_column(cur, 'archivos', 'pais', 'pais TEXT DEFAULT "España"')
        _ensure_column(cur, 'archivos', 'contacto_responsable', 'contacto_responsable TEXT')
        _ensure_column(cur, 'archivos', 'email', 'email TEXT')
        _ensure_column(cur, 'archivos', 'telefono', 'telefono TEXT')
        _ensure_column(cur, 'archivos', 'url', 'url TEXT')
        _ensure_column(cur, 'archivos', 'coordenadas_geograficas', 'coordenadas_geograficas TEXT')
        _ensure_column(cur, 'archivos', 'horario_atencion', 'horario_atencion TEXT')
        _ensure_column(cur, 'archivos', 'condiciones_acceso', 'condiciones_acceso TEXT')
        _ensure_column(cur, 'archivos', 'notas', 'notas TEXT')
        _ensure_column(cur, 'archivos', 'updated_at', 'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        
        _ensure_column(cur, 'fondos', 'codigo_referencia', 'codigo_referencia TEXT')
        _ensure_column(cur, 'fondos', 'titulo', 'titulo TEXT')
        _ensure_column(cur, 'fondos', 'descripcion', 'descripcion TEXT')
        _ensure_column(cur, 'fondos', 'archivo_id', 'archivo_id INTEGER')
        _ensure_column(cur, 'fondos', 'nivel_descripcion', 'nivel_descripcion TEXT DEFAULT "fonds"')
        _ensure_column(cur, 'fondos', 'volumen_soporte', 'volumen_soporte TEXT')
        _ensure_column(cur, 'fondos', 'fecha_inicial', 'fecha_inicial TEXT')
        _ensure_column(cur, 'fondos', 'fecha_final', 'fecha_final TEXT')
        _ensure_column(cur, 'fondos', 'fecha_inicial_normalizada', 'fecha_inicial_normalizada TEXT')
        _ensure_column(cur, 'fondos', 'fecha_final_normalizada', 'fecha_final_normalizada TEXT')
        _ensure_column(cur, 'fondos', 'historia_institucional', 'historia_institucional TEXT')
        _ensure_column(cur, 'fondos', 'historia_archivistica', 'historia_archivistica TEXT')
        _ensure_column(cur, 'fondos', 'forma_ingreso', 'forma_ingreso TEXT')
        _ensure_column(cur, 'fondos', 'alcance_contenido', 'alcance_contenido TEXT')
        _ensure_column(cur, 'fondos', 'valoracion_seleccion', 'valoracion_seleccion TEXT')
        _ensure_column(cur, 'fondos', 'nuevos_ingresos', 'nuevos_ingresos TEXT')
        _ensure_column(cur, 'fondos', 'organizacion', 'organizacion TEXT')
        _ensure_column(cur, 'fondos', 'condiciones_acceso', 'condiciones_acceso TEXT')
        _ensure_column(cur, 'fondos', 'condiciones_reproduccion', 'condiciones_reproduccion TEXT')
        _ensure_column(cur, 'fondos', 'lengua_documentos', 'lengua_documentos TEXT DEFAULT "spa"')
        _ensure_column(cur, 'fondos', 'caracteristicas_fisicas', 'caracteristicas_fisicas TEXT')
        _ensure_column(cur, 'fondos', 'instrumentos_descripcion', 'instrumentos_descripcion TEXT')
        _ensure_column(cur, 'fondos', 'existencia_originales', 'existencia_originales TEXT')
        _ensure_column(cur, 'fondos', 'existencia_copias', 'existencia_copias TEXT')
        _ensure_column(cur, 'fondos', 'unidades_relacionadas', 'unidades_relacionadas TEXT')
        _ensure_column(cur, 'fondos', 'nota_publicaciones', 'nota_publicaciones TEXT')
        _ensure_column(cur, 'fondos', 'notas_generales', 'notas_generales TEXT')
        _ensure_column(cur, 'fondos', 'nota_archivero', 'nota_archivero TEXT')
        _ensure_column(cur, 'fondos', 'reglas_normas', 'reglas_normas TEXT DEFAULT "ISAD(G)"')
        _ensure_column(cur, 'fondos', 'fecha_descripcion', 'fecha_descripcion TEXT')
        _ensure_column(cur, 'fondos', 'created_at', 'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        _ensure_column(cur, 'fondos', 'updated_at', 'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        
        _ensure_column(cur, 'etiquetas', 'termino', 'termino TEXT')
        _ensure_column(cur, 'etiquetas', 'termino_normalizado', 'termino_normalizado TEXT')
        _ensure_column(cur, 'etiquetas', 'tipo_termino', 'tipo_termino TEXT DEFAULT "topic"')
        _ensure_column(cur, 'etiquetas', 'vocabulario_fuente', 'vocabulario_fuente TEXT')
        _ensure_column(cur, 'etiquetas', 'uri', 'uri TEXT')
        _ensure_column(cur, 'etiquetas', 'descripcion', 'descripcion TEXT')
        _ensure_column(cur, 'etiquetas', 'terminos_relacionados', 'terminos_relacionados TEXT')
        _ensure_column(cur, 'etiquetas', 'termino_preferido_id', 'termino_preferido_id INTEGER')
        _ensure_column(cur, 'etiquetas', 'created_at', 'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        _ensure_column(cur, 'etiquetas', 'updated_at', 'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        
        _ensure_column(cur, 'proyectos', 'codigo_proyecto', 'codigo_proyecto TEXT')
        _ensure_column(cur, 'proyectos', 'titulo', 'titulo TEXT')
        _ensure_column(cur, 'proyectos', 'titulo_alternativo', 'titulo_alternativo TEXT')
        _ensure_column(cur, 'proyectos', 'codigo_referencia', 'codigo_referencia TEXT')
        _ensure_column(cur, 'proyectos', 'signatura', 'signatura TEXT')
        _ensure_column(cur, 'proyectos', 'nivel_descripcion', 'nivel_descripcion TEXT DEFAULT "item"')
        _ensure_column(cur, 'proyectos', 'tipo_documento', 'tipo_documento TEXT')
        _ensure_column(cur, 'proyectos', 'tipo_material', 'tipo_material TEXT')
        _ensure_column(cur, 'proyectos', 'autor', 'autor TEXT')
        _ensure_column(cur, 'proyectos', 'creador', 'creador TEXT')
        _ensure_column(cur, 'proyectos', 'productor', 'productor TEXT')
        _ensure_column(cur, 'proyectos', 'tema', 'tema TEXT')
        _ensure_column(cur, 'proyectos', 'descripcion', 'descripcion TEXT')
        _ensure_column(cur, 'proyectos', 'alcance_contenido', 'alcance_contenido TEXT')
        _ensure_column(cur, 'proyectos', 'resumen', 'resumen TEXT')
        _ensure_column(cur, 'proyectos', 'etiquetas', 'etiquetas TEXT')
        _ensure_column(cur, 'proyectos', 'fecha_creacion_doc', 'fecha_creacion_doc TEXT')
        _ensure_column(cur, 'proyectos', 'fecha_inicial', 'fecha_inicial TEXT')
        _ensure_column(cur, 'proyectos', 'fecha_final', 'fecha_final TEXT')
        _ensure_column(cur, 'proyectos', 'fecha_normalizadar', 'fecha_normalizadar TEXT')
        _ensure_column(cur, 'proyectos', 'lugar_creacion', 'lugar_creacion TEXT')
        _ensure_column(cur, 'proyectos', 'lengua', 'lengua TEXT DEFAULT "spa"')
        _ensure_column(cur, 'proyectos', 'cobertura_temporal', 'cobertura_temporal TEXT')
        _ensure_column(cur, 'proyectos', 'cobertura_geografica', 'cobertura_geografica TEXT')
        _ensure_column(cur, 'proyectos', 'extension', 'extension TEXT')
        _ensure_column(cur, 'proyectos', 'formato', 'formato TEXT')
        _ensure_column(cur, 'proyectos', 'soporte', 'soporte TEXT')
        _ensure_column(cur, 'proyectos', 'dimensiones', 'dimensiones TEXT')
        _ensure_column(cur, 'proyectos', 'estado_conservacion', 'estado_conservacion TEXT')
        _ensure_column(cur, 'proyectos', 'tratamiento_tecnico', 'tratamiento_tecnico TEXT')
        _ensure_column(cur, 'proyectos', 'derechos', 'derechos TEXT')
        _ensure_column(cur, 'proyectos', 'licencia', 'licencia TEXT DEFAULT "In Copyright"')
        _ensure_column(cur, 'proyectos', 'titular_derechos', 'titular_derechos TEXT')
        _ensure_column(cur, 'proyectos', 'condiciones_acceso', 'condiciones_acceso TEXT')
        _ensure_column(cur, 'proyectos', 'condiciones_uso', 'condiciones_uso TEXT')
        _ensure_column(cur, 'proyectos', 'fondo_id', 'fondo_id INTEGER')
        _ensure_column(cur, 'proyectos', 'proyecto_padre_id', 'proyecto_padre_id INTEGER')
        _ensure_column(cur, 'proyectos', 'carpeta_raiz', 'carpeta_raiz TEXT')
        _ensure_column(cur, 'proyectos', 'db_path', 'db_path TEXT')
        _ensure_column(cur, 'proyectos', 'notas', 'notas TEXT')
        _ensure_column(cur, 'proyectos', 'observaciones_tecnicas', 'observaciones_tecnicas TEXT')
        _ensure_column(cur, 'proyectos', 'responsable_digitalizacion', 'responsable_digitalizacion TEXT')
        _ensure_column(cur, 'proyectos', 'fecha_digitalizacion', 'fecha_digitalizacion TEXT')
        _ensure_column(cur, 'proyectos', 'equipamiento_digitalizacion', 'equipamiento_digitalizacion TEXT')
        _ensure_column(cur, 'proyectos', 'calidad_digitalizacion', 'calidad_digitalizacion TEXT')
        _ensure_column(cur, 'proyectos', 'formato_digital', 'formato_digital TEXT')
        _ensure_column(cur, 'proyectos', 'resolucion_dpi', 'resolucion_dpi INTEGER')
        _ensure_column(cur, 'proyectos', 'espacio_color', 'espacio_color TEXT')
        _ensure_column(cur, 'proyectos', 'formato_archivo', 'formato_archivo TEXT')
        _ensure_column(cur, 'proyectos', 'tamano_archivo_mb', 'tamano_archivo_mb REAL')
        _ensure_column(cur, 'proyectos', 'checksum', 'checksum TEXT')
        _ensure_column(cur, 'proyectos', 'software_utilizado', 'software_utilizado TEXT')
        _ensure_column(cur, 'proyectos', 'metadatos_incrustados', 'metadatos_incrustados BOOLEAN DEFAULT 0')
        _ensure_column(cur, 'proyectos', 'identificador_persistente', 'identificador_persistente TEXT')
        _ensure_column(cur, 'proyectos', 'uri_canonical', 'uri_canonical TEXT')
        _ensure_column(cur, 'proyectos', 'fuente_metadatos', 'fuente_metadatos TEXT')
        _ensure_column(cur, 'proyectos', 'esquema_metadatos', 'esquema_metadatos TEXT DEFAULT "Dublin Core + ISAD(G)"')
        _ensure_column(cur, 'proyectos', 'created_at', 'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        _ensure_column(cur, 'proyectos', 'updated_at', 'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        
        # Copiar datos de campos legacy si existen
        if _has_column(cur, 'archivos', 'nombre') and not _has_column(cur, 'archivos', 'nombre_oficial'):
            cur.execute("UPDATE archivos SET nombre_oficial = nombre WHERE nombre_oficial IS NULL")
        if _has_column(cur, 'fondos', 'nombre') and not _has_column(cur, 'fondos', 'titulo'):
            cur.execute("UPDATE fondos SET titulo = nombre WHERE titulo IS NULL")
        if _has_column(cur, 'etiquetas', 'nombre') and not _has_column(cur, 'etiquetas', 'termino'):
            cur.execute("UPDATE etiquetas SET termino = nombre WHERE termino IS NULL")
            
    except Exception as e:
        print(f"Warning durante migración de columnas: {e}")
    conn.commit()
    conn.close()


def set_setting(base_path: Path, key: str, value: str) -> None:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit(); conn.close()


def get_setting(base_path: Path, key: str) -> Optional[str]:
    db_path = base_path / "data" / GLOBAL_DB
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    row = cur.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row[0] if row else None


def init_project_db(project_path: Path) -> None:
    """Initialize project-specific database.
    Estructura mejorada según Dublin Core, PREMIS y METS."""
    db_path = project_path / "project.db"
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Document metadata - Dublin Core extendido + METS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS document (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT UNIQUE,
        title TEXT NOT NULL,
        alternative_title TEXT,
        creator TEXT,
        contributor TEXT,
        publisher TEXT,
        date_created TEXT,
        date_issued TEXT,
        date_modified TEXT,
        date_normalized TEXT,
        type TEXT,
        format TEXT,
        medium TEXT,
        extent TEXT,
        language TEXT DEFAULT 'spa',
        subject TEXT,
        description TEXT,
        abstract TEXT,
        table_of_contents TEXT,
        spatial_coverage TEXT,
        temporal_coverage TEXT,
        rights TEXT,
        rights_holder TEXT,
        license TEXT,
        access_rights TEXT,
        provenance TEXT,
        source TEXT,
        relation TEXT,
        is_version_of TEXT,
        has_version TEXT,
        is_part_of TEXT,
        has_part TEXT,
        bibliographic_citation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Pages/Folios - PREMIS Object Entity
    cur.execute("""
    CREATE TABLE IF NOT EXISTS page (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        identifier TEXT UNIQUE,
        seq INTEGER NOT NULL,
        folio_number TEXT,
        folio_recto_verso TEXT,
        page_label TEXT,
        original_path TEXT,
        processed_path TEXT,
        thumbnail_path TEXT,
        master_path TEXT,
        derivative_paths TEXT,
        width INTEGER,
        height INTEGER,
        dpi INTEGER,
        bit_depth INTEGER,
        color_space TEXT,
        icc_profile TEXT,
        file_format TEXT,
        mime_type TEXT,
        file_size_bytes INTEGER,
        checksum_md5 TEXT,
        checksum_sha256 TEXT,
        compression TEXT,
        quality_score REAL,
        has_text BOOLEAN DEFAULT 0,
        has_annotations BOOLEAN DEFAULT 0,
        preservation_level TEXT DEFAULT 'full',
        technical_metadata TEXT,
        capture_device TEXT,
        capture_software TEXT,
        capture_settings TEXT,
        captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        captured_by TEXT,
        processing_date TIMESTAMP,
        processing_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE CASCADE
    );
    """)
    
    # OCR versions (original + corrections) - PREMIS Representation
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ocr_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_id INTEGER NOT NULL,
        identifier TEXT UNIQUE,
        version_type TEXT NOT NULL,
        version_number INTEGER DEFAULT 1,
        text_content TEXT,
        html_content TEXT,
        alto_xml TEXT,
        hocr TEXT,
        language TEXT DEFAULT 'spa',
        ocr_engine TEXT,
        ocr_engine_version TEXT,
        confidence REAL,
        word_count INTEGER,
        character_count INTEGER,
        quality_metrics TEXT,
        processing_time REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by TEXT,
        role TEXT,
        provenance_note TEXT,
        is_current BOOLEAN DEFAULT 1,
        supersedes_version_id INTEGER,
        FOREIGN KEY (page_id) REFERENCES page(id) ON DELETE CASCADE,
        FOREIGN KEY (supersedes_version_id) REFERENCES ocr_versions(id)
    );
    """)
    
    # Glossary/abbreviations - Vocabulary control
    cur.execute("""
    CREATE TABLE IF NOT EXISTS glossary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scope TEXT DEFAULT 'project',
        name TEXT NOT NULL,
        language TEXT DEFAULT 'es',
        vocabulary_source TEXT,
        authority_file TEXT,
        terms_json TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by TEXT
    );
    """)
    
    # Annotations - W3C Web Annotation Data Model
    cur.execute("""
    CREATE TABLE IF NOT EXISTS annotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        annotation_id TEXT UNIQUE,
        page_id INTEGER,
        annotation_type TEXT,
        motivation TEXT,
        target_source TEXT,
        target_selector TEXT,
        target_scope TEXT,
        body_type TEXT,
        body_value TEXT,
        body_format TEXT,
        body_language TEXT DEFAULT 'es',
        body_html TEXT,
        body_purpose TEXT,
        creator TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        modified_at TIMESTAMP,
        generator TEXT,
        audience TEXT,
        rights TEXT,
        canonical TEXT,
        via TEXT,
        tags TEXT,
        geo_lat REAL,
        geo_lon REAL,
        geo_place TEXT,
        geo_geonames_id TEXT,
        time_start TEXT,
        time_end TEXT,
        FOREIGN KEY (page_id) REFERENCES page(id) ON DELETE CASCADE
    );
    """)
    
    # Linked entities (persons, places, organizations, concepts) - VIAF/GND/Getty compatible
    cur.execute("""
    CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT UNIQUE,
        entity_type TEXT NOT NULL,
        name TEXT NOT NULL,
        normalized_name TEXT,
        preferred_label TEXT,
        alternative_labels TEXT,
        uri TEXT,
        authority_source TEXT,
        authority_id TEXT,
        viaf_id TEXT,
        gnd_id TEXT,
        loc_id TEXT,
        bnf_id TEXT,
        getty_id TEXT,
        wikidata_id TEXT,
        geodocs_id INTEGER,
        description TEXT,
        biographical_note TEXT,
        birth_date TEXT,
        death_date TEXT,
        birth_place TEXT,
        death_place TEXT,
        occupation TEXT,
        nationality TEXT,
        related_entities TEXT,
        metadata_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by TEXT
    );
    """)
    
    # Entity-annotation linking (N:M)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS annotation_entities (
        annotation_id INTEGER,
        entity_id INTEGER,
        relationship_type TEXT,
        confidence REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (annotation_id) REFERENCES annotations(id) ON DELETE CASCADE,
        FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
        PRIMARY KEY (annotation_id, entity_id)
    );
    """)
    
    # Events (acontecimientos históricos mencionados)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT UNIQUE,
        name TEXT NOT NULL,
        event_type TEXT,
        date_start TEXT,
        date_end TEXT,
        date_normalized TEXT,
        location TEXT,
        geo_lat REAL,
        geo_lon REAL,
        description TEXT,
        participants TEXT,
        related_entities TEXT,
        authority_source TEXT,
        authority_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Provenance/Custody history - PREMIS Event Entity
    cur.execute("""
    CREATE TABLE IF NOT EXISTS provenance_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_type TEXT NOT NULL,
        object_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        event_detail TEXT,
        event_outcome TEXT,
        agent_name TEXT,
        agent_type TEXT,
        agent_identifier TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Quality control checks
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quality_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_id INTEGER,
        check_type TEXT NOT NULL,
        check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT,
        score REAL,
        issues_found TEXT,
        recommendations TEXT,
        checked_by TEXT,
        FOREIGN KEY (page_id) REFERENCES page(id) ON DELETE CASCADE
    );
    """)
    
    # Exports/Deliverables tracking
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        export_format TEXT NOT NULL,
        export_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        output_path TEXT,
        file_size_bytes INTEGER,
        checksum TEXT,
        include_metadata BOOLEAN DEFAULT 1,
        validation_status TEXT,
        validation_report TEXT,
        created_by TEXT,
        notes TEXT
    );
    """)
    
    conn.commit()
    conn.close()

def ensure_project_dirs(project_path: Path) -> None:
    """Create standard directories under a project root."""
    for sub in [
        "paginas",
        "thumbnails",
        "ocr",
        "annotations",
        "glossaries",
        "exports",
        "audio",
    ]:
        (project_path / sub).mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    """Make a filesystem-friendly slug (basic ASCII fallback)."""
    import re
    try:
        import unicodedata
        text_norm = unicodedata.normalize('NFKD', text)
        text_ascii = text_norm.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        text_ascii = text
    text_ascii = re.sub(r"[^A-Za-z0-9\-_. ]+", "", text_ascii).strip()
    text_ascii = re.sub(r"\s+", "_", text_ascii)
    return text_ascii


def normalize_folder_name(siglas: str, signatura: str) -> str:
    """Normaliza nombre de carpeta de proyecto: SIGLAS_SIGNATURA (sin espacios, caracteres seguros)."""
    s = _slugify(siglas).upper()
    sig = _slugify(signatura).upper()
    return f"{s}_{sig}" if sig else s


def validate_signatura(signatura: str) -> tuple[bool, str]:
    """Valida signatura según formato esperado.
    Retorna (es_válida, mensaje_error).
    Formato sugerido: alfanumérico con guiones, barras, puntos. Max 50 chars.
    """
    import re
    if not signatura or not signatura.strip():
        return False, "La signatura no puede estar vacía"
    
    signatura = signatura.strip()
    
    if len(signatura) > 50:
        return False, "La signatura no puede exceder 50 caracteres"
    
    # Permitir letras, números, guiones, barras, puntos, espacios
    if not re.match(r'^[A-Za-z0-9\-/\.\s]+$', signatura):
        return False, "La signatura solo puede contener letras, números, guiones, barras, puntos y espacios"
    
    return True, ""


def _infer_siglas(nombre: str) -> str:
    parts = [p for p in (nombre or "").replace('-', ' ').split() if p]
    if not parts:
        return "ARC"
    # Take first letters up to 4 chars
    sig = ''.join(p[0] for p in parts)[:6].upper()
    return sig or "ARC"


def _projects_root() -> Path:
    """Resolve projects root folder from app config or DB setting; fallback to ./data/proyectos."""
    # Prefer DB setting if available and valid
    try:
        # Use this module's knowledge of base dir to locate DB; but we don't have base_path here.
        # Fall back to app_config to resolve base then read DB setting.
        if _app_config is not None:
            base = _app_config.get_root_dir()
            val = get_setting(base, 'root_dir')
            if val:
                root = Path(val)
                cfg = _app_config.get_config() or {}
                proj_rel = (cfg.get('paths', {}) or {}).get('projects_dir', 'proyectos')
                return Path(root) / proj_rel
    except Exception:
        pass
    # Prefer app_config if available
    try:
        if _app_config is not None:
            root = _app_config.get_root_dir()
            cfg = _app_config.get_config() or {}
            proj_rel = (cfg.get('paths', {}) or {}).get('projects_dir', 'proyectos')
            return Path(root) / proj_rel
    except Exception:
        pass
    # Fallback to repo/data/proyectos relative
    return Path(__file__).resolve().parent.parent / 'data' / 'proyectos'

def get_project_db_path(project_root: Path) -> Path:
    return project_root / "project.db"

def get_or_create_default_document(project_root: Path, title: str = None) -> int:
    """Ensure at least one document exists; return its id."""
    dbp = get_project_db_path(project_root)
    conn = sqlite3.connect(dbp); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM document ORDER BY id LIMIT 1").fetchone()
    if row:
        did = int(row[0]); conn.close(); return did
    cur.execute(
        "INSERT INTO document(title,author,date,doc_type,signature,description) VALUES(?,?,?,?,?,?)",
        (title or project_root.name, None, None, None, None, None)
    )
    did = cur.lastrowid
    conn.commit(); conn.close(); return did

def list_pages(project_root: Path) -> List[Dict[str, Any]]:
    dbp = get_project_db_path(project_root)
    conn = sqlite3.connect(dbp); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM page ORDER BY seq").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def page_exists_for_path(project_root: Path, img_path: Path) -> bool:
    dbp = get_project_db_path(project_root)
    conn = sqlite3.connect(dbp)
    cur = conn.cursor()
    row = cur.execute("SELECT 1 FROM page WHERE original_path=? OR processed_path=?", (str(img_path), str(img_path))).fetchone()
    conn.close()
    return row is not None

def insert_page_record(project_root: Path, document_id: int, seq: int, img_path: Path, width: int = None, height: int = None, dpi: int = None, processed_path: Path = None, thumbnail_path: Path = None) -> int:
    dbp = get_project_db_path(project_root)
    conn = sqlite3.connect(dbp)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO page(document_id, seq, original_path, processed_path, thumbnail_path, width, height, dpi)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (document_id, seq, str(img_path), str(processed_path) if processed_path else None, str(thumbnail_path) if thumbnail_path else None, width, height, dpi)
    )
    pid = cur.lastrowid
    conn.commit(); conn.close(); return pid

def sync_pages_from_folder(project_root: Path) -> int:
    """Scan 'paginas' folder and insert missing pages into project.db with sequential order and thumbnails.
    Returns number of pages inserted."""
    from utils.image_cleaner import imread_auto, create_thumbnail
    ensure_project_dirs(project_root)
    pages_dir = project_root / "paginas"
    thumbs_dir = project_root / "thumbnails"
    thumbs_dir.mkdir(exist_ok=True)

    did = get_or_create_default_document(project_root)

    # Determine next seq
    existing = list_pages(project_root)
    next_seq = (existing[-1]["seq"] + 1) if existing else 1

    count = 0
    for f in sorted(pages_dir.glob("*.jpg")) + sorted(pages_dir.glob("*.png")) + sorted(pages_dir.glob("*.jpeg")) + sorted(pages_dir.glob("*.tif")) + sorted(pages_dir.glob("*.tiff")):
        if page_exists_for_path(project_root, f):
            continue
        # read to get size
        try:
            img = imread_auto(str(f))
            h, w = (img.shape[0], img.shape[1]) if img is not None else (None, None)
        except Exception:
            h, w = None, None
        thumb_path = thumbs_dir / (f.stem + "_thumb.jpg")
        try:
            create_thumbnail(str(f), str(thumb_path), max_size=320)
        except Exception:
            thumb_path = None
        insert_page_record(project_root, did, next_seq, f, width=w, height=h, thumbnail_path=thumb_path)
        next_seq += 1
        count += 1
    return count

def save_ocr_version(project_root: Path, page_id: int, version_type: str, text: str, language: str = 'spa', confidence: float = None, html: str = None, created_by: str = None) -> int:
    dbp = get_project_db_path(project_root)
    conn = sqlite3.connect(dbp)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ocr_versions(page_id, version_type, text_content, html_content, language, confidence, created_by) VALUES (?,?,?,?,?,?,?)",
        (page_id, version_type, text, html, language, confidence, created_by)
    )
    vid = cur.lastrowid
    conn.commit(); conn.close(); return vid

def get_latest_ocr(project_root: Path, page_id: int, version_type: str = None) -> Dict[str, Any]:
    dbp = get_project_db_path(project_root)
    conn = sqlite3.connect(dbp); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if version_type:
        row = cur.execute(
            "SELECT * FROM ocr_versions WHERE page_id=? AND version_type=? ORDER BY created_at DESC LIMIT 1",
            (page_id, version_type)
        ).fetchone()
    else:
        row = cur.execute(
            "SELECT * FROM ocr_versions WHERE page_id=? ORDER BY created_at DESC LIMIT 1",
            (page_id,)
        ).fetchone()
    conn.close()
    return dict(row) if row else None

def list_ocr_versions(project_root: Path, page_id: int) -> List[Dict[str, Any]]:
    """List all OCR versions for a page, newest first."""
    dbp = get_project_db_path(project_root)
    conn = sqlite3.connect(dbp); conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM ocr_versions WHERE page_id=? ORDER BY created_at DESC, id DESC",
        (page_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_project(
    base_path: Path,
    titulo: str,
    **kwargs
) -> int:
    """Create new project in global database and initialize project DB.
    Folder name rule: <ABREV_PROYECTO>/<ABREV_ARCHIVO>/<ABREV_FONDO>_<SIGNATURA>
    """
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    signatura = (kwargs.get('signatura') or '').strip()
    
    # Validar signatura si está presente
    if signatura:
        valid, msg = validate_signatura(signatura)
        if not valid:
            conn.close()
            raise ValueError(f"Signatura inválida: {msg}")
    
    # Obtener abreviaturas de archivo y fondo
    fondo_id = kwargs.get('fondo_id')
    abrev_archivo = None
    abrev_fondo = None
    
    if fondo_id:
        row = cur.execute("""
            SELECT f.abreviatura as fondo_abrev, 
                   a.abreviatura as archivo_abrev,
                   a.siglas
            FROM fondos f 
            LEFT JOIN archivos a ON a.id=f.archivo_id 
            WHERE f.id=?
        """, (fondo_id,)).fetchone()
        if row:
            abrev_fondo = row['fondo_abrev'] or 'FONDO'
            abrev_archivo = row['archivo_abrev'] or row['siglas'] or 'ARC'
    
    abrev_archivo = abrev_archivo or 'ARC'
    abrev_fondo = abrev_fondo or 'FONDO'
    
    # Generar abreviatura del proyecto (usar signatura o título)
    abrev_proyecto = kwargs.get('abreviatura')
    if not abrev_proyecto:
        if signatura:
            abrev_proyecto = _slugify(signatura)[:8].upper()
        else:
            palabras = [p for p in titulo.replace('-', ' ').split() if len(p) > 2]
            if palabras:
                abrev_proyecto = ''.join(p[0] for p in palabras[:6]).upper()
            else:
                abrev_proyecto = _slugify(titulo)[:6].upper()
    
    # Construir ruta jerárquica: proyecto/archivo/fondo_signatura
    project_root = _projects_root()
    folder_name = f"{abrev_fondo}_{_slugify(signatura).upper()}" if signatura else abrev_fondo
    carpeta_raiz = project_root / abrev_proyecto / abrev_archivo / folder_name
    carpeta_raiz.mkdir(parents=True, exist_ok=True)

    # Insert project row
    cur.execute(
        """
        INSERT INTO proyectos 
        (titulo, signatura, abreviatura, tipo_documento, tipo_publicacion_id, 
         autor, tema, etiquetas, fecha, fondo_id, carpeta_raiz, db_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            titulo,
            signatura,
            abrev_proyecto,
            kwargs.get('tipo_documento', ''),
            kwargs.get('tipo_publicacion_id'),
            kwargs.get('autor', ''),
            kwargs.get('tema', ''),
            kwargs.get('etiquetas', ''),  # Campo legacy, mantener por compatibilidad
            kwargs.get('fecha', ''),
            fondo_id,
            str(carpeta_raiz),
            str(carpeta_raiz / "project.db"),
        )
    )

    project_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Initialize project database + dirs
    init_project_db(carpeta_raiz)
    ensure_project_dirs(carpeta_raiz)
    
    # Asociar etiquetas N:M si se especificaron
    etiqueta_ids = kwargs.get('etiqueta_ids', [])
    if etiqueta_ids:
        set_project_tags(base_path, project_id, etiqueta_ids)

    return project_id


def list_projects(base_path: Path) -> List[Dict[str, Any]]:
    """List all projects from global database"""
    db_path = base_path / "data" / GLOBAL_DB
    
    if not db_path.exists():
        init_global_db(base_path)
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    rows = cur.execute("""
    SELECT p.*, f.nombre as fondo_nombre, a.nombre as archivo_nombre
    FROM proyectos p
    LEFT JOIN fondos f ON p.fondo_id = f.id
    LEFT JOIN archivos a ON f.archivo_id = a.id
    ORDER BY p.updated_at DESC
    """).fetchall()
    
    conn.close()
    
    # Añadir etiquetas como lista
    result = []
    for row in rows:
        proj = dict(row)
        proj['etiquetas_list'] = list_project_tags(base_path, proj['id'])
        result.append(proj)
    
    return result


# ---- CRUD: Archivos, Fondos, Etiquetas ----
def list_archivos(base_path: Path) -> List[Dict[str, Any]]:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM archivos ORDER BY COALESCE(nombre_oficial, nombre) COLLATE NOCASE").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        # Compatibilidad con código legacy
        if 'nombre_oficial' in d and d['nombre_oficial']:
            d['nombre'] = d['nombre_oficial']
        elif 'nombre' not in d and 'nombre_oficial' in d:
            d['nombre'] = d['nombre_oficial']
        # Normalizar campos para UI
        if 'direccion_completa' in d and d.get('direccion_completa') is not None:
            d['direccion'] = d['direccion_completa']
        elif 'direccion' not in d and 'direccion_completa' in d:
            d['direccion'] = d.get('direccion_completa')
        if 'contacto_responsable' in d and d.get('contacto_responsable') is not None:
            d['contacto'] = d['contacto_responsable']
        elif 'contacto' not in d and 'contacto_responsable' in d:
            d['contacto'] = d.get('contacto_responsable')
        # Generar abreviatura si no existe
        if not d.get('abreviatura'):
            d['abreviatura'] = _infer_siglas(d.get('nombre', 'ARC'))
        result.append(d)
    return result


def create_archivo(base_path: Path, nombre: str, siglas: str = None, direccion: str = None, contacto: str = None, email: str = None, telefono: str = None, url: str = None, **kwargs) -> int:
    """Crea un registro en 'archivos' compatible con esquemas legacy.

    - Controla duplicados por nombre (case-insensitive).
    - Rellena tanto 'nombre_oficial' como 'nombre' si esta última existe (DB antigua).
    - Cierra siempre la conexión aunque haya errores para evitar 'database is locked'.
    """
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path, timeout=15)
    try:
        cur = conn.cursor()

        # Detectar columnas (para compatibilidad con DB antiguas)
        has_nombre_oficial = True
        has_nombre_legacy = False
        try:
            has_nombre_oficial = _has_column(cur, 'archivos', 'nombre_oficial')
            has_nombre_legacy = _has_column(cur, 'archivos', 'nombre')
        except Exception:
            # Si algo falla, asumimos al menos esquema nuevo
            has_nombre_oficial = True
            has_nombre_legacy = False

        # Verificar duplicados por nombre (case-insensitive)
        check_duplicates = kwargs.get('check_duplicates', True)
        if check_duplicates:
            if has_nombre_oficial:
                cur.execute("SELECT id FROM archivos WHERE LOWER(nombre_oficial) = LOWER(?)", (nombre,))
            elif has_nombre_legacy:
                cur.execute("SELECT id FROM archivos WHERE LOWER(nombre) = LOWER(?)", (nombre,))
            else:
                cur.execute("SELECT id FROM archivos WHERE 1=0")  # no-op
            if cur.fetchone():
                raise ValueError(f"Ya existe un archivo con el nombre '{nombre}'")

        # Generar código de identificación único
        codigo = kwargs.get('codigo_identificacion') or f"ARC{int(time.time())}"
        siglas_final = siglas or _infer_siglas(nombre)
        
        # Abreviatura para carpetas (usar kwargs o inferir desde siglas)
        abreviatura = kwargs.get('abreviatura') or siglas_final[:6].upper()

        # Mapeo de campos legacy: direccion puede venir como direccion_completa en kwargs
        direccion_final = kwargs.get('direccion_completa') or direccion
        contacto_final = kwargs.get('contacto_responsable') or contacto
        url_final = kwargs.get('url_web') or url

        # Insertar considerando columnas legacy
        if has_nombre_legacy:
            # Algunas DB antiguas tienen 'nombre' NOT NULL. Insertamos en ambas.
            cur.execute(
                """INSERT INTO archivos(
                    codigo_identificacion, nombre, nombre_oficial, siglas, abreviatura, tipo_institucion,
                    direccion_completa, ciudad, provincia, pais,
                    contacto_responsable, email, telefono, url,
                    coordenadas_geograficas, horario_atencion, condiciones_acceso, notas
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    codigo, nombre, nombre, siglas_final, abreviatura, kwargs.get('tipo_institucion', 'archivo'),
                    direccion_final, kwargs.get('ciudad'), kwargs.get('provincia'), kwargs.get('pais', 'España'),
                    contacto_final, email, telefono, url_final,
                    kwargs.get('coordenadas_geograficas'), kwargs.get('horario_atencion'),
                    kwargs.get('condiciones_acceso'), kwargs.get('notas')
                )
            )
        else:
            cur.execute(
                """INSERT INTO archivos(
                    codigo_identificacion, nombre_oficial, siglas, abreviatura, tipo_institucion,
                    direccion_completa, ciudad, provincia, pais,
                    contacto_responsable, email, telefono, url, 
                    coordenadas_geograficas, horario_atencion, condiciones_acceso, notas
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    codigo, nombre, siglas_final, abreviatura, kwargs.get('tipo_institucion', 'archivo'),
                    direccion_final, kwargs.get('ciudad'), kwargs.get('provincia'), kwargs.get('pais', 'España'),
                    contacto_final, email, telefono, url_final,
                    kwargs.get('coordenadas_geograficas'), kwargs.get('horario_atencion'), 
                    kwargs.get('condiciones_acceso'), kwargs.get('notas')
                )
            )

        rid = cur.lastrowid
        conn.commit()
        return rid
    finally:
        try:
            conn.close()
        except Exception:
            pass


def update_archivo(base_path: Path, archivo_id: int, **kwargs) -> bool:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path, timeout=15)
    try:
        cur = conn.cursor()
        fields = []
        values = []

        # Mapear campos legacy a nuevos campos
        field_mapping = {
            'nombre': 'nombre_oficial',
            'direccion': 'direccion_completa',
            'contacto': 'contacto_responsable'
        }

        for k in ("nombre", "nombre_oficial", "siglas", "abreviatura", "codigo_identificacion", "tipo_institucion",
                  "direccion", "direccion_completa", "ciudad", "provincia", "pais",
                  "contacto", "contacto_responsable", "email", "telefono", "url",
                  "coordenadas_geograficas", "horario_atencion", "condiciones_acceso", "notas"):
            if k in kwargs:
                field_name = field_mapping.get(k, k)
                fields.append(f"{field_name}=?")
                values.append(kwargs[k])

        if not fields:
            return False

        fields.append("updated_at=CURRENT_TIMESTAMP")
        values.append(archivo_id)
        cur.execute(f"UPDATE archivos SET {', '.join(fields)} WHERE id=?", values)
        conn.commit();
        return True
    finally:
        try:
            conn.close()
        except Exception:
            pass


def delete_archivo(base_path: Path, archivo_id: int) -> bool:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    cur.execute("DELETE FROM archivos WHERE id=?", (archivo_id,))
    conn.commit(); conn.close(); return True


def list_fondos(base_path: Path) -> List[Dict[str, Any]]:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT f.*, 
               COALESCE(a.nombre_oficial, a.nombre) as archivo_nombre, 
               a.siglas as archivo_siglas
        FROM fondos f 
        LEFT JOIN archivos a ON a.id=f.archivo_id
        ORDER BY COALESCE(f.titulo, f.nombre) COLLATE NOCASE
    """).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        # Compatibilidad con código legacy
        if 'titulo' in d and d['titulo']:
            d['nombre'] = d['titulo']
        elif 'nombre' not in d and 'titulo' in d:
            d['nombre'] = d['titulo']
        # Mapear fechas legacy
        if 'fecha_inicial' in d:
            d['periodo_inicio'] = d['fecha_inicial']
        if 'fecha_final' in d:
            d['periodo_fin'] = d['fecha_final']
        result.append(d)
    return result


def create_fondo(base_path: Path, nombre: str, archivo_id: int = None, descripcion: str = None, periodo_inicio: str = None, periodo_fin: str = None, **kwargs) -> int:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    
    # Generar código de referencia
    codigo_ref = kwargs.get('codigo_referencia')
    if not codigo_ref and archivo_id:
        row = cur.execute("SELECT siglas FROM archivos WHERE id=?", (archivo_id,)).fetchone()
        siglas = (row[0] if row else 'FONDO').upper()
        codigo_ref = f"{siglas}/F{int(time.time() % 100000)}"
    
    # Generar abreviatura desde nombre o kwargs
    abreviatura = kwargs.get('abreviatura')
    if not abreviatura:
        # Tomar primeras letras significativas del nombre
        palabras = [p for p in nombre.replace('-', ' ').split() if len(p) > 2]
        if palabras:
            abreviatura = ''.join(p[0] for p in palabras[:4]).upper()
        else:
            abreviatura = _slugify(nombre)[:4].upper()
    
    cur.execute(
        """INSERT INTO fondos(
            codigo_referencia, titulo, descripcion, archivo_id,
            nivel_descripcion, fecha_inicial, fecha_final,
            alcance_contenido, lengua_documentos, abreviatura
        ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (
            codigo_ref, nombre, descripcion, archivo_id,
            kwargs.get('nivel_descripcion', 'fonds'),
            periodo_inicio, periodo_fin,
            kwargs.get('alcance_contenido'),
            kwargs.get('lengua_documentos', 'spa'),
            abreviatura
        )
    )
    rid = cur.lastrowid; conn.commit(); conn.close(); return rid


def update_fondo(base_path: Path, fondo_id: int, **kwargs) -> bool:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    fields = []
    values = []
    
    # Mapear campos legacy
    field_mapping = {
        'nombre': 'titulo'
    }
    
    for k in ("nombre", "titulo", "codigo_referencia", "descripcion", "archivo_id", 
              "periodo_inicio", "periodo_fin", "alcance_contenido", "organizacion",
              "nivel_descripcion", "lengua_documentos", "abreviatura"):
        if k in kwargs:
            field_name = field_mapping.get(k, k)
            fields.append(f"{field_name}=?")
            values.append(kwargs[k])
    
    if not fields:
        conn.close(); return False
    
    fields.append("updated_at=CURRENT_TIMESTAMP")
    values.append(fondo_id)
    cur.execute(f"UPDATE fondos SET {', '.join(fields)} WHERE id=?", values)
    conn.commit(); conn.close(); return True


def delete_fondo(base_path: Path, fondo_id: int) -> bool:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    cur.execute("DELETE FROM fondos WHERE id=?", (fondo_id,))
    conn.commit(); conn.close(); return True


def list_etiquetas(base_path: Path) -> List[Dict[str, Any]]:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM etiquetas ORDER BY COALESCE(termino, nombre) COLLATE NOCASE").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        # Compatibilidad con código legacy
        if 'termino' in d and d['termino']:
            d['nombre'] = d['termino']
        elif 'nombre' not in d and 'termino' in d:
            d['nombre'] = d['termino']
        result.append(d)
    return result


def create_etiqueta(base_path: Path, nombre: str, descripcion: str = None, **kwargs) -> int:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    cur.execute(
        """INSERT INTO etiquetas(termino, descripcion, tipo_termino, vocabulario_fuente) 
           VALUES(?,?,?,?)""",
        (nombre, descripcion, kwargs.get('tipo_termino', 'topic'), kwargs.get('vocabulario_fuente'))
    )
    rid = cur.lastrowid; conn.commit(); conn.close(); return rid


def update_etiqueta(base_path: Path, etiqueta_id: int, **kwargs) -> bool:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    fields = []
    values = []
    
    # Mapear campo legacy
    if 'nombre' in kwargs:
        kwargs['termino'] = kwargs['nombre']
    
    for k in ("termino", "descripcion", "tipo_termino", "vocabulario_fuente"):
        if k in kwargs:
            fields.append(f"{k}=?"); values.append(kwargs[k])
    
    if not fields:
        conn.close(); return False
    
    fields.append("updated_at=CURRENT_TIMESTAMP")
    values.append(etiqueta_id)
    cur.execute(f"UPDATE etiquetas SET {', '.join(fields)} WHERE id=?", values)
    conn.commit(); conn.close(); return True


def delete_etiqueta(base_path: Path, etiqueta_id: int) -> bool:
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    cur.execute("DELETE FROM etiquetas WHERE id=?", (etiqueta_id,))
    conn.commit(); conn.close(); return True


# ---- Gestión de etiquetas N:M proyecto ----
def list_project_tags(base_path: Path, project_id: int) -> List[Dict[str, Any]]:
    """Listar etiquetas asociadas a un proyecto"""
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT e.* FROM etiquetas e
        INNER JOIN proyecto_etiquetas pe ON e.id = pe.etiqueta_id
        WHERE pe.proyecto_id = ?
        ORDER BY e.nombre
    """, (project_id,)).fetchall()
    conn.close(); return [dict(r) for r in rows]


def add_project_tag(base_path: Path, project_id: int, etiqueta_id: int) -> bool:
    """Asociar etiqueta a proyecto"""
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO proyecto_etiquetas(proyecto_id, etiqueta_id) VALUES(?,?)", (project_id, etiqueta_id))
        conn.commit(); conn.close(); return True
    except Exception:
        conn.close(); return False


def remove_project_tag(base_path: Path, project_id: int, etiqueta_id: int) -> bool:
    """Desasociar etiqueta de proyecto"""
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    cur.execute("DELETE FROM proyecto_etiquetas WHERE proyecto_id=? AND etiqueta_id=?", (project_id, etiqueta_id))
    conn.commit(); conn.close(); return True


def set_project_tags(base_path: Path, project_id: int, etiqueta_ids: List[int]) -> None:
    """Reemplazar todas las etiquetas de un proyecto"""
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); cur = conn.cursor()
    # Borrar existentes
    cur.execute("DELETE FROM proyecto_etiquetas WHERE proyecto_id=?", (project_id,))
    # Insertar nuevas
    for eid in etiqueta_ids:
        try:
            cur.execute("INSERT INTO proyecto_etiquetas(proyecto_id, etiqueta_id) VALUES(?,?)", (project_id, eid))
        except Exception:
            pass
    conn.commit(); conn.close()


def migrate_text_tags_to_relations(base_path: Path) -> int:
    """Migración: convertir etiquetas textuales (campo etiquetas) a relaciones N:M.
    Retorna número de proyectos migrados."""
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Obtener proyectos con etiquetas textuales
    rows = cur.execute("SELECT id, etiquetas FROM proyectos WHERE etiquetas IS NOT NULL AND etiquetas != ''").fetchall()
    migrated = 0
    
    for row in rows:
        pid = row['id']
        tags_text = row['etiquetas'] or ''
        tag_names = [t.strip() for t in tags_text.split(',') if t.strip()]
        
        for tname in tag_names:
            # Buscar o crear etiqueta
            etiq_row = cur.execute("SELECT id FROM etiquetas WHERE nombre=?", (tname,)).fetchone()
            if etiq_row:
                eid = etiq_row['id']
            else:
                cur.execute("INSERT INTO etiquetas(nombre) VALUES(?)", (tname,))
                eid = cur.lastrowid
            
            # Asociar
            try:
                cur.execute("INSERT INTO proyecto_etiquetas(proyecto_id, etiqueta_id) VALUES(?,?)", (pid, eid))
            except Exception:
                pass  # Ya existe
        
        migrated += 1
    
    conn.commit(); conn.close()
    return migrated


def get_project(base_path: Path, project_id: int) -> Optional[Dict[str, Any]]:
    """Get project by ID"""
    db_path = base_path / "data" / GLOBAL_DB
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    row = cur.execute("""
    SELECT p.*, f.nombre as fondo_nombre
    FROM proyectos p
    LEFT JOIN fondos f ON p.fondo_id = f.id
    WHERE p.id = ?
    """, (project_id,)).fetchone()
    
    conn.close()
    
    return dict(row) if row else None


def update_project(base_path: Path, project_id: int, **kwargs) -> bool:
    """Update project metadata"""
    db_path = base_path / "data" / GLOBAL_DB
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Build update query dynamically
    fields = []
    values = []
    
    for key in ['titulo', 'signatura', 'abreviatura', 'tipo_documento', 'tipo_publicacion_id',
                'autor', 'tema', 'etiquetas', 'fecha', 'fondo_id']:
        if key in kwargs:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    
    if not fields:
        return False
    
    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(project_id)
    
    query = f"UPDATE proyectos SET {', '.join(fields)} WHERE id = ?"
    cur.execute(query, values)
    
    conn.commit()
    conn.close()
    
    return True


def delete_project(base_path: Path, project_id: int) -> bool:
    """Delete project from database (does not delete files)"""
    db_path = base_path / "data" / GLOBAL_DB
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("DELETE FROM proyectos WHERE id = ?", (project_id,))
    
    conn.commit()
    conn.close()
    
    return True


# ===== NUEVAS FUNCIONES PARA MEJORAS V3 =====

def list_tipos_publicacion(base_path: Path) -> List[Dict[str, Any]]:
    """Listar tipos de publicación disponibles"""
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM tipos_publicacion WHERE activo=1 ORDER BY orden, nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tipo_publicacion(base_path: Path, tipo_id: int) -> Optional[Dict[str, Any]]:
    """Obtener un tipo de publicación por ID"""
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM tipos_publicacion WHERE id=?", (tipo_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_fondos_bulk(base_path: Path, fondo_ids: List[int]) -> int:
    """Eliminar múltiples fondos en batch. Retorna número de fondos eliminados."""
    if not fondo_ids:
        return 0
    
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    placeholders = ','.join('?' * len(fondo_ids))
    cur.execute(f"DELETE FROM fondos WHERE id IN ({placeholders})", fondo_ids)
    deleted = cur.rowcount
    
    conn.commit()
    conn.close()
    return deleted


def rotate_page_image(project_root: Path, page_id: int, angle: int) -> bool:
    """
    Rotar imagen de página y guardar el ángulo en BD.
    
    Args:
        project_root: Ruta raíz del proyecto
        page_id: ID de la página
        angle: Ángulo de rotación (90, 180, 270, -90, -180, -270)
    
    Returns:
        True si se rotó correctamente
    """
    from PIL import Image
    
    dbp = get_project_db_path(project_root)
    conn = sqlite3.connect(dbp); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Obtener info de página
    row = cur.execute("SELECT * FROM page WHERE id=?", (page_id,)).fetchone()
    if not row:
        conn.close()
        return False
    
    page = dict(row)
    img_path = page.get('processed_path') or page.get('original_path')
    if not img_path or not Path(img_path).exists():
        conn.close()
        return False
    
    try:
        # Cargar imagen
        img = Image.open(img_path)
        
        # Rotar (PIL usa ángulos positivos en sentido antihorario)
        # Normalizamos a 0, 90, 180, 270
        angle = angle % 360
        if angle == 90:
            img_rotated = img.rotate(270, expand=True)  # PIL inverso
        elif angle == 180:
            img_rotated = img.rotate(180, expand=True)
        elif angle == 270:
            img_rotated = img.rotate(90, expand=True)
        else:
            img_rotated = img
        
        # Guardar sobre la misma imagen
        img_rotated.save(img_path)
        
        # Actualizar ángulo acumulado en BD
        current_angle = page.get('rotation_angle', 0) or 0
        new_angle = (current_angle + angle) % 360
        
        cur.execute("UPDATE page SET rotation_angle=?, width=?, height=? WHERE id=?",
                   (new_angle, img_rotated.width, img_rotated.height, page_id))
        
        # Regenerar thumbnail si existe
        thumb_path = page.get('thumbnail_path')
        if thumb_path and Path(thumb_path).exists():
            from utils.image_cleaner import create_thumbnail
            create_thumbnail(img_path, thumb_path, max_size=320)
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error rotando imagen: {e}")
        conn.close()
        return False


def get_last_capture_settings(base_path: Path) -> Optional[Dict[str, Any]]:
    """Recuperar la configuración de la última captura realizada"""
    settings_str = get_setting(base_path, 'last_capture_settings')
    if settings_str:
        import json
        try:
            return json.loads(settings_str)
        except Exception:
            return None
    return None


def save_capture_settings(base_path: Path, settings: Dict[str, Any]) -> None:
    """Guardar configuración de captura para reutilizar en siguiente sesión"""
    import json
    settings_str = json.dumps(settings, ensure_ascii=False, indent=2)
    set_setting(base_path, 'last_capture_settings', settings_str)


def build_project_folder_path(
    base_path: Path,
    proyecto_id: int = None,
    abrev_proyecto: str = None,
    abrev_archivo: str = None,
    abrev_fondo: str = None,
    signatura: str = None
) -> Path:
    """
    Construir ruta de carpeta de proyecto usando abreviaturas:
    <abrev_proyecto>/<abrev_archivo>/<abrev_fondo>_<signatura>
    
    Si proyecto_id se proporciona, consulta BD para obtener abreviaturas.
    """
    projects_root = _projects_root()
    
    if proyecto_id:
        # Consultar BD para obtener datos
        db_path = base_path / "data" / GLOBAL_DB
        conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        row = cur.execute("""
            SELECT p.abreviatura as proj_abrev, p.signatura,
                   f.abreviatura as fondo_abrev,
                   a.abreviatura as archivo_abrev
            FROM proyectos p
            LEFT JOIN fondos f ON p.fondo_id = f.id
            LEFT JOIN archivos a ON f.archivo_id = a.id
            WHERE p.id = ?
        """, (proyecto_id,)).fetchone()
        conn.close()
        
        if row:
            abrev_proyecto = abrev_proyecto or row['proj_abrev'] or 'PROJ'
            abrev_fondo = abrev_fondo or row['fondo_abrev'] or 'FONDO'
            abrev_archivo = abrev_archivo or row['archivo_abrev'] or 'ARC'
            signatura = signatura or row['signatura'] or ''
    
    # Valores por defecto
    abrev_archivo = _slugify(abrev_archivo or 'ARC').upper()
    abrev_fondo = _slugify(abrev_fondo or 'FONDO').upper()
    abrev_proyecto = _slugify(abrev_proyecto or 'PROJ').upper()
    signatura_slug = _slugify(signatura or '').upper()
    
    # Construir ruta: proyecto/archivo/fondo_signatura
    folder_name = f"{abrev_fondo}_{signatura_slug}" if signatura_slug else abrev_fondo
    
    return projects_root / abrev_proyecto / abrev_archivo / folder_name

