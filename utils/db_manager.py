#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_manager.py — Gestión de bases de datos (global y por proyecto)
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

GLOBAL_DB = "geodocs.db"

def init_global_db(base_path: Path) -> None:
    """Initialize global database with archivos, fondos, proyectos tables"""
    db_path = base_path / "data" / GLOBAL_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Archivos (Instituciones/Archivos históricos)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS archivos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        direccion TEXT,
        contacto TEXT,
        email TEXT,
        telefono TEXT,
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Fondos documentales
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fondos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        archivo_id INTEGER,
        periodo_inicio TEXT,
        periodo_fin TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (archivo_id) REFERENCES archivos(id)
    );
    """)
    
    # Proyectos de digitalización
    cur.execute("""
    CREATE TABLE IF NOT EXISTS proyectos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        signatura TEXT,
        tipo_documento TEXT,
        autor TEXT,
        tema TEXT,
        etiquetas TEXT,
        fecha TEXT,
        fondo_id INTEGER,
        carpeta_raiz TEXT NOT NULL,
        db_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fondo_id) REFERENCES fondos(id)
    );
    """)
    
    conn.commit()
    conn.close()


def init_project_db(project_path: Path) -> None:
    """Initialize project-specific database"""
    db_path = project_path / "project.db"
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Document metadata
    cur.execute("""
    CREATE TABLE IF NOT EXISTS document (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT,
        date TEXT,
        doc_type TEXT,
        signature TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Pages
    cur.execute("""
    CREATE TABLE IF NOT EXISTS page (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        seq INTEGER NOT NULL,
        original_path TEXT,
        processed_path TEXT,
        thumbnail_path TEXT,
        width INTEGER,
        height INTEGER,
        dpi INTEGER,
        captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES document(id)
    );
    """)
    
    # OCR versions (original + corrections)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ocr_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_id INTEGER NOT NULL,
        version_type TEXT NOT NULL,
        text_content TEXT,
        html_content TEXT,
        language TEXT DEFAULT 'spa',
        confidence REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by TEXT,
        FOREIGN KEY (page_id) REFERENCES page(id)
    );
    """)
    
    # Glossary/abbreviations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS glossary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scope TEXT DEFAULT 'project',
        name TEXT NOT NULL,
        language TEXT DEFAULT 'es',
        terms_json TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Annotations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS annotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_id INTEGER,
        annotation_type TEXT,
        target_selector TEXT,
        body_text TEXT,
        body_html TEXT,
        creator TEXT,
        motivation TEXT,
        tags TEXT,
        geo_lat REAL,
        geo_lon REAL,
        geo_place TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (page_id) REFERENCES page(id)
    );
    """)
    
    # Linked entities (persons, places, etc.)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        name TEXT NOT NULL,
        normalized_name TEXT,
        uri TEXT,
        geodocs_id INTEGER,
        description TEXT,
        metadata_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Entity-annotation linking
    cur.execute("""
    CREATE TABLE IF NOT EXISTS annotation_entities (
        annotation_id INTEGER,
        entity_id INTEGER,
        FOREIGN KEY (annotation_id) REFERENCES annotations(id),
        FOREIGN KEY (entity_id) REFERENCES entities(id),
        PRIMARY KEY (annotation_id, entity_id)
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
    carpeta_raiz: str,
    **kwargs
) -> int:
    """Create new project in global database and initialize project DB"""
    db_path = base_path / "data" / GLOBAL_DB
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Insert project
    cur.execute("""
    INSERT INTO proyectos 
    (titulo, signatura, tipo_documento, autor, tema, etiquetas, fecha, fondo_id, carpeta_raiz, db_path)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        titulo,
        kwargs.get('signatura', ''),
        kwargs.get('tipo_documento', ''),
        kwargs.get('autor', ''),
        kwargs.get('tema', ''),
        kwargs.get('etiquetas', ''),
        kwargs.get('fecha', ''),
        kwargs.get('fondo_id'),
        carpeta_raiz,
        str(Path(carpeta_raiz) / "project.db")
    ))
    
    project_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    # Initialize project database
    project_path = Path(carpeta_raiz)
    project_path.mkdir(parents=True, exist_ok=True)
    init_project_db(project_path)
    
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
    
    return [dict(row) for row in rows]


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
    
    for key in ['titulo', 'signatura', 'tipo_documento', 'autor', 'tema', 'etiquetas', 'fecha', 'fondo_id']:
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
