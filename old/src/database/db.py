#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
from datetime import datetime

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        
    def connect(self):
        return sqlite3.connect(self.db_path)
    
    def ensure_schema(self):
        with self.connect() as con:
            cur = con.cursor()
            # Crear tablas principales
            cur.execute("""CREATE TABLE IF NOT EXISTS archivo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                sigla TEXT, ubicacion TEXT, direccion TEXT,
                contacto TEXT, telefono TEXT, email TEXT,
                web TEXT, descripcion TEXT
            )""")
            
            cur.execute("""CREATE TABLE IF NOT EXISTS fondo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                archivo_id INTEGER REFERENCES archivo(id),
                nombre TEXT NOT NULL,
                rango_fechas TEXT, volumen TEXT,
                nivel_descripcion TEXT, descripcion TEXT, 
                notas TEXT,
                UNIQUE(archivo_id, nombre)
            )""")
            
            cur.execute("""CREATE TABLE IF NOT EXISTS project (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, base_dir TEXT,
                created_at TEXT, remote_id TEXT
            )""")
            
            cur.execute("""CREATE TABLE IF NOT EXISTS document (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES project(id),
                title TEXT, signatura TEXT,
                archivo_id INTEGER, fondo_id INTEGER,
                tema TEXT, etiquetas TEXT, tipo TEXT,
                autor TEXT, fecha_text TEXT,
                lugar TEXT, idioma TEXT, derechos TEXT,
                referencia_bibliografica TEXT, resumen TEXT,
                notas_internas TEXT, remote_id TEXT,
                last_sync TEXT, created_at TEXT,
                nivel_descripcion TEXT, productor TEXT,
                alcance_y_contenido TEXT
            )""")
            
            cur.execute("""CREATE TABLE IF NOT EXISTS page (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER REFERENCES document(id),
                seq INTEGER, src_path TEXT,
                processed_path TEXT,
                ocr_txt_path TEXT, ocr_pdf_path TEXT,
                created_at TEXT, remote_id TEXT,
                remote_url TEXT, ocr_url TEXT,
                downloaded INTEGER DEFAULT 0,
                hash_sha256 TEXT
            )""")
            
            cur.execute("""CREATE TABLE IF NOT EXISTS version_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER, page_id INTEGER,
                user TEXT, action TEXT, details TEXT,
                created_at TEXT
            )""")
            
            cur.execute("""CREATE TABLE IF NOT EXISTS annotation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER REFERENCES document(id),
                page_id INTEGER REFERENCES page(id),
                user TEXT, type TEXT, tags TEXT,
                body TEXT, target_region TEXT,
                latitude REAL, longitude REAL,
                toponimo_id TEXT, persona_id TEXT,
                created_at TEXT, updated_at TEXT
            )""")
            
            # Asegurar que existan todas las columnas
            def ensure_column(table, col, decl):
                cur.execute(f"PRAGMA table_info({table})")
                cols = [c[1] for c in cur.fetchall()]
                if col not in cols:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
            
            ensure_column("project", "remote_id", "TEXT")
            for t,c in [
                ("document", "remote_id TEXT"),
                ("document", "last_sync TEXT"),
                ("page", "remote_id TEXT"),
                ("page", "remote_url TEXT"),
                ("page", "ocr_url TEXT"),
                ("page", "downloaded INTEGER DEFAULT 0"),
                ("page", "hash_sha256 TEXT")
            ]:
                parts = c.split()
                ensure_column(t, parts[0], " ".join(parts[1:]))
            
            con.commit()
    
    def add_version_entry(self, document_id=None, page_id=None, user="local", action="update", details=""):
        with self.connect() as con:
            con.execute(
                """INSERT INTO version_history 
                   (document_id, page_id, user, action, details, created_at) 
                   VALUES (?,?,?,?,?,datetime('now'))""",
                (document_id, page_id, user, action, details)
            )
            con.commit()
    
    def get_document(self, doc_id):
        with self.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute("""
                SELECT d.*, a.nombre as archivo_nombre, f.nombre as fondo_nombre 
                FROM document d
                LEFT JOIN archivo a ON a.id=d.archivo_id 
                LEFT JOIN fondo f ON f.id=d.fondo_id
                WHERE d.id=?""", (doc_id,))
            return cur.fetchone()
    
    def get_pages(self, doc_id):
        with self.connect() as con:
            con.row_factory = sqlite3.Row
            return list(con.execute(
                "SELECT * FROM page WHERE document_id=? ORDER BY seq", 
                (doc_id,)
            ))
    
    def create_project(self, name, base_dir):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute(
                """INSERT INTO project (name, base_dir, created_at)
                   VALUES (?,?,?)""",
                (name, str(base_dir), datetime.now().isoformat())
            )
            return cur.lastrowid
            
    def create_document(self, project_id, **fields):
        with self.connect() as con:
            cur = con.cursor()
            cols = ["project_id"] + list(fields.keys())
            placeholders = ",".join("?" * len(cols))
            values = [project_id] + list(fields.values())
            
            cur.execute(
                f"""INSERT INTO document ({','.join(cols)}, created_at)
                    VALUES ({placeholders}, datetime('now'))""",
                values
            )
            return cur.lastrowid
    
    def add_page(self, doc_id, seq, processed_path=None, src_path=None, 
                 ocr_txt_path=None, ocr_pdf_path=None, hash_sha256=None):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute(
                """INSERT INTO page 
                   (document_id, seq, processed_path, src_path,
                    ocr_txt_path, ocr_pdf_path, created_at,
                    downloaded, hash_sha256)
                   VALUES (?,?,?,?,?,?,datetime('now'),1,?)""",
                (doc_id, seq, processed_path, src_path,
                 ocr_txt_path, ocr_pdf_path, hash_sha256)
            )
            return cur.lastrowid