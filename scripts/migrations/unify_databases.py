#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unify_databases.py - Unifica geodocs_scanner.db en geodocs.db

Este script migra todas las tablas operacionales de geodocs_scanner.db
a la base de datos unificada geodocs.db, manteniendo la separación lógica
mediante prefijos de tabla.

IMPORTANTE: Crea backup automático antes de ejecutar.
"""
import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCANNER_DB = BASE_DIR / "geodocs_scanner.db"
GLOBAL_DB = BASE_DIR / "data" / "geodocs.db"
BACKUP_DIR = BASE_DIR / "backups"

def create_backup():
    """Crea backup de ambas bases de datos"""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if SCANNER_DB.exists():
        backup_scanner = BACKUP_DIR / f"geodocs_scanner_{timestamp}.db"
        shutil.copy2(SCANNER_DB, backup_scanner)
        print(f"✓ Backup creado: {backup_scanner}")
    
    if GLOBAL_DB.exists():
        backup_global = BACKUP_DIR / f"geodocs_{timestamp}.db"
        shutil.copy2(GLOBAL_DB, backup_global)
        print(f"✓ Backup creado: {backup_global}")
    
    return timestamp

def add_scanner_tables_to_global_db():
    """Añade las tablas operacionales del scanner a geodocs.db"""
    
    if not GLOBAL_DB.exists():
        print("ERROR: geodocs.db no existe. Ejecuta primero init_global_db()")
        return False
    
    conn = sqlite3.connect(GLOBAL_DB)
    cur = conn.cursor()
    
    print("\n=== Añadiendo tablas operacionales a geodocs.db ===")
    
    # Tabla: scanner_project (proyectos de escaneo operacionales)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS scanner_project (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        base_dir TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        remote_id TEXT,
        proyecto_archivistico_id INTEGER,
        FOREIGN KEY (proyecto_archivistico_id) REFERENCES proyectos(id) ON DELETE SET NULL
    );
    """)
    print("✓ Tabla scanner_project")
    
    # Tabla: scanner_document
    cur.execute("""
    CREATE TABLE IF NOT EXISTS scanner_document (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT,
        signatura TEXT,
        archivo_id INTEGER,
        fondo_id INTEGER,
        tema TEXT,
        etiquetas TEXT,
        tipo TEXT,
        autor TEXT,
        fecha_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        workflow_state TEXT,
        dpi_x REAL,
        dpi_y REAL,
        calibrated_size TEXT,
        calibration_date TEXT,
        remote_id TEXT,
        last_sync TEXT,
        FOREIGN KEY (project_id) REFERENCES scanner_project(id) ON DELETE CASCADE,
        FOREIGN KEY (archivo_id) REFERENCES archivos(id) ON DELETE SET NULL,
        FOREIGN KEY (fondo_id) REFERENCES fondos(id) ON DELETE SET NULL
    );
    """)
    print("✓ Tabla scanner_document")
    
    # Tabla: scanner_page
    cur.execute("""
    CREATE TABLE IF NOT EXISTS scanner_page (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        seq INTEGER NOT NULL,
        src_path TEXT,
        processed_path TEXT,
        ocr_txt_path TEXT,
        ocr_pdf_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        hash_sha256 TEXT,
        status TEXT DEFAULT 'pending',
        ocr_text TEXT,
        face TEXT,
        ocr_html TEXT,
        review_state TEXT,
        enhanced_image_path TEXT,
        enhancement_method TEXT,
        homography_matrix TEXT,
        rectification_angle_error REAL,
        scale_tolerance REAL,
        remote_id TEXT,
        remote_url TEXT,
        ocr_url TEXT,
        downloaded INTEGER DEFAULT 0,
        FOREIGN KEY (document_id) REFERENCES scanner_document(id) ON DELETE CASCADE
    );
    """)
    print("✓ Tabla scanner_page")
    
    # Tabla: annotation
    cur.execute("""
    CREATE TABLE IF NOT EXISTS annotation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        page_id INTEGER,
        user TEXT,
        type TEXT,
        tags TEXT,
        body TEXT,
        target_region TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        latitude REAL,
        longitude REAL,
        toponimo_id INTEGER,
        persona_id INTEGER,
        updated_at TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES scanner_document(id) ON DELETE CASCADE,
        FOREIGN KEY (page_id) REFERENCES scanner_page(id) ON DELETE CASCADE
    );
    """)
    print("✓ Tabla annotation")
    
    # Tabla: glossary
    cur.execute("""
    CREATE TABLE IF NOT EXISTS glossary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scope TEXT DEFAULT 'project',
        name TEXT NOT NULL,
        language TEXT DEFAULT 'es',
        terms_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("✓ Tabla glossary")
    
    # Tabla: style_template
    cur.execute("""
    CREATE TABLE IF NOT EXISTS style_template (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scope TEXT DEFAULT 'project',
        name TEXT NOT NULL,
        language TEXT DEFAULT 'es',
        style_name TEXT,
        rules_json TEXT,
        meta_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("✓ Tabla style_template")
    
    # Tabla: ocr_revision
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ocr_revision (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_id INTEGER NOT NULL,
        version INTEGER NOT NULL,
        user TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ocr_text TEXT,
        ocr_html TEXT,
        signed INTEGER DEFAULT 0,
        signed_at TEXT,
        signature TEXT,
        changes_html TEXT,
        signed_by TEXT,
        role TEXT,
        similarity_score REAL,
        FOREIGN KEY (page_id) REFERENCES scanner_page(id) ON DELETE CASCADE
    );
    """)
    print("✓ Tabla ocr_revision")
    
    # Tabla: version_history
    cur.execute("""
    CREATE TABLE IF NOT EXISTS version_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        page_id INTEGER,
        user TEXT,
        action TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES scanner_document(id) ON DELETE CASCADE,
        FOREIGN KEY (page_id) REFERENCES scanner_page(id) ON DELETE CASCADE
    );
    """)
    print("✓ Tabla version_history")
    
    # Tabla: audit_log
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        user TEXT,
        role TEXT,
        page_id INTEGER,
        revision_id INTEGER,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (page_id) REFERENCES scanner_page(id) ON DELETE SET NULL,
        FOREIGN KEY (revision_id) REFERENCES ocr_revision(id) ON DELETE SET NULL
    );
    """)
    print("✓ Tabla audit_log")
    
    conn.commit()
    conn.close()
    print("\n✓ Todas las tablas operacionales añadidas a geodocs.db")
    return True

def migrate_data():
    """Migra los datos de geodocs_scanner.db a geodocs.db"""
    
    if not SCANNER_DB.exists():
        print("AVISO: geodocs_scanner.db no existe, no hay datos que migrar")
        return True
    
    print("\n=== Migrando datos de geodocs_scanner.db a geodocs.db ===")
    
    # Conectar a ambas bases de datos
    conn_scanner = sqlite3.connect(SCANNER_DB)
    conn_scanner.row_factory = sqlite3.Row
    conn_global = sqlite3.connect(GLOBAL_DB)
    
    cur_scanner = conn_scanner.cursor()
    cur_global = conn_global.cursor()
    
    # Mapeo de IDs antiguos a nuevos
    project_id_map = {}
    document_id_map = {}
    page_id_map = {}
    
    # 1. Migrar proyectos
    print("\nMigrando scanner_project...")
    cur_scanner.execute("SELECT * FROM project")
    projects = cur_scanner.fetchall()
    for proj in projects:
        cur_global.execute("""
            INSERT INTO scanner_project (name, base_dir, created_at, remote_id)
            VALUES (?, ?, ?, ?)
        """, (proj['name'], proj['base_dir'], proj['created_at'], proj['remote_id']))
        new_id = cur_global.lastrowid
        project_id_map[proj['id']] = new_id
        print(f"  Proyecto #{proj['id']} → #{new_id}: {proj['name']}")
    
    # 2. Migrar documentos
    print("\nMigrando scanner_document...")
    cur_scanner.execute("SELECT * FROM document")
    documents = cur_scanner.fetchall()
    for doc in documents:
        new_project_id = project_id_map.get(doc['project_id'])
        if new_project_id is None:
            print(f"  AVISO: Documento #{doc['id']} referencia proyecto inexistente #{doc['project_id']}, saltando...")
            continue
        
        cur_global.execute("""
            INSERT INTO scanner_document (
                project_id, title, signatura, archivo_id, fondo_id, tema, etiquetas,
                tipo, autor, fecha_text, created_at, workflow_state, dpi_x, dpi_y,
                calibrated_size, calibration_date, remote_id, last_sync
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_project_id, doc['title'], doc['signatura'], doc['archivo_id'],
            doc['fondo_id'], doc['tema'], doc['etiquetas'], doc['tipo'],
            doc['autor'], doc['fecha_text'], doc['created_at'], doc['workflow_state'],
            doc['dpi_x'], doc['dpi_y'], doc['calibrated_size'], doc['calibration_date'],
            doc['remote_id'], doc['last_sync']
        ))
        new_id = cur_global.lastrowid
        document_id_map[doc['id']] = new_id
        print(f"  Documento #{doc['id']} → #{new_id}: {doc['title']}")
    
    # 3. Migrar páginas
    print("\nMigrando scanner_page...")
    cur_scanner.execute("SELECT * FROM page")
    pages = cur_scanner.fetchall()
    migrated_pages = 0
    for page in pages:
        new_document_id = document_id_map.get(page['document_id'])
        if new_document_id is None:
            continue
        
        cur_global.execute("""
            INSERT INTO scanner_page (
                document_id, seq, src_path, processed_path, ocr_txt_path, ocr_pdf_path,
                created_at, hash_sha256, status, ocr_text, face, ocr_html, review_state,
                enhanced_image_path, enhancement_method, homography_matrix,
                rectification_angle_error, scale_tolerance, remote_id, remote_url,
                ocr_url, downloaded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_document_id, page['seq'], page['src_path'], page['processed_path'],
            page['ocr_txt_path'], page['ocr_pdf_path'], page['created_at'],
            page['hash_sha256'], page['status'], page['ocr_text'], page['face'],
            page['ocr_html'], page['review_state'], page['enhanced_image_path'],
            page['enhancement_method'], page['homography_matrix'],
            page['rectification_angle_error'], page['scale_tolerance'],
            page['remote_id'], page['remote_url'], page['ocr_url'], page['downloaded']
        ))
        new_id = cur_global.lastrowid
        page_id_map[page['id']] = new_id
        migrated_pages += 1
    print(f"  {migrated_pages} páginas migradas")
    
    # 4. Migrar anotaciones
    print("\nMigrando annotation...")
    cur_scanner.execute("SELECT * FROM annotation")
    annotations = cur_scanner.fetchall()
    migrated_annot = 0
    for annot in annotations:
        new_document_id = document_id_map.get(annot['document_id']) if annot['document_id'] else None
        new_page_id = page_id_map.get(annot['page_id']) if annot['page_id'] else None
        
        cur_global.execute("""
            INSERT INTO annotation (
                document_id, page_id, user, type, tags, body, target_region,
                created_at, latitude, longitude, toponimo_id, persona_id, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_document_id, new_page_id, annot['user'], annot['type'],
            annot['tags'], annot['body'], annot['target_region'],
            annot['created_at'], annot['latitude'], annot['longitude'],
            annot['toponimo_id'], annot['persona_id'], annot['updated_at']
        ))
        migrated_annot += 1
    print(f"  {migrated_annot} anotaciones migradas")
    
    # 5. Migrar glosarios
    print("\nMigrando glossary...")
    cur_scanner.execute("SELECT * FROM glossary")
    glossaries = cur_scanner.fetchall()
    for gloss in glossaries:
        cur_global.execute("""
            INSERT INTO glossary (scope, name, language, terms_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (gloss['scope'], gloss['name'], gloss['language'], gloss['terms_json'],
              gloss['created_at'], gloss['updated_at']))
    print(f"  {len(glossaries)} glosarios migrados")
    
    # 6. Migrar plantillas de estilo
    print("\nMigrando style_template...")
    cur_scanner.execute("SELECT * FROM style_template")
    templates = cur_scanner.fetchall()
    for tpl in templates:
        cur_global.execute("""
            INSERT INTO style_template (
                scope, name, language, style_name, rules_json, meta_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (tpl['scope'], tpl['name'], tpl['language'], tpl['style_name'],
              tpl['rules_json'], tpl['meta_json'], tpl['created_at'], tpl['updated_at']))
    print(f"  {len(templates)} plantillas migradas")
    
    # 7. Migrar revisiones OCR
    print("\nMigrando ocr_revision...")
    cur_scanner.execute("SELECT * FROM ocr_revision")
    revisions = cur_scanner.fetchall()
    migrated_rev = 0
    for rev in revisions:
        new_page_id = page_id_map.get(rev['page_id'])
        if new_page_id is None:
            continue
        
        cur_global.execute("""
            INSERT INTO ocr_revision (
                page_id, version, user, created_at, ocr_text, ocr_html, signed,
                signed_at, signature, changes_html, signed_by, role, similarity_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_page_id, rev['version'], rev['user'], rev['created_at'],
            rev['ocr_text'], rev['ocr_html'], rev['signed'], rev['signed_at'],
            rev['signature'], rev['changes_html'], rev['signed_by'],
            rev['role'], rev['similarity_score']
        ))
        migrated_rev += 1
    print(f"  {migrated_rev} revisiones OCR migradas")
    
    # 8. Migrar historial de versiones
    print("\nMigrando version_history...")
    cur_scanner.execute("SELECT * FROM version_history")
    versions = cur_scanner.fetchall()
    migrated_ver = 0
    for ver in versions:
        new_document_id = document_id_map.get(ver['document_id']) if ver['document_id'] else None
        new_page_id = page_id_map.get(ver['page_id']) if ver['page_id'] else None
        
        cur_global.execute("""
            INSERT INTO version_history (document_id, page_id, user, action, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (new_document_id, new_page_id, ver['user'], ver['action'], ver['details'],
              ver.get('created_at')))
        migrated_ver += 1
    print(f"  {migrated_ver} entradas de historial migradas")
    
    # 9. Migrar audit_log
    print("\nMigrando audit_log...")
    cur_scanner.execute("SELECT * FROM audit_log")
    audits = cur_scanner.fetchall()
    migrated_audit = 0
    for audit in audits:
        new_page_id = page_id_map.get(audit['page_id']) if audit['page_id'] else None
        
        cur_global.execute("""
            INSERT INTO audit_log (action, user, role, page_id, revision_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            audit['action'], audit['user'], audit['role'], new_page_id,
            audit['revision_id'], audit['details'], audit['created_at']
        ))
        migrated_audit += 1
    print(f"  {migrated_audit} entradas de auditoría migradas")
    
    # Commit y cerrar
    conn_global.commit()
    conn_scanner.close()
    conn_global.close()
    
    print("\n✓ Migración de datos completada")
    return True

def update_code_references():
    """Genera un informe de archivos que necesitan actualización"""
    
    files_to_update = [
        "web_viewer/server.py",
        "scanner_gui.py",
        "processor_queue.py",
        "modules/scheduler.py",
    ]
    
    print("\n=== ARCHIVOS QUE REQUIEREN ACTUALIZACIÓN ===")
    print("\nCambiar:")
    print("  DB = BASE_DIR / 'geodocs_scanner.db'")
    print("Por:")
    print("  DB = BASE_DIR / 'data' / 'geodocs.db'")
    print("\nArchivos afectados:")
    for f in files_to_update:
        filepath = BASE_DIR / f
        if filepath.exists():
            print(f"  ✓ {f}")
        else:
            print(f"  ? {f} (no encontrado)")
    
    print("\nCambiar nombres de tabla:")
    print("  project → scanner_project")
    print("  document → scanner_document")
    print("  page → scanner_page")
    
    print("\nNOTA: Las tablas archivo y fondo de geodocs_scanner.db")
    print("      ya existen como 'archivos' y 'fondos' en geodocs.db")

def main():
    """Ejecuta la migración completa"""
    print("=" * 60)
    print("UNIFICACIÓN DE BASES DE DATOS")
    print("geodocs_scanner.db → geodocs.db")
    print("=" * 60)
    
    # 1. Crear backup
    print("\n[1/4] Creando backups...")
    timestamp = create_backup()
    
    # 2. Añadir tablas
    print("\n[2/4] Añadiendo tablas a geodocs.db...")
    if not add_scanner_tables_to_global_db():
        print("\nERROR: No se pudieron añadir las tablas")
        return False
    
    # 3. Migrar datos
    print("\n[3/4] Migrando datos...")
    if not migrate_data():
        print("\nERROR: No se pudieron migrar los datos")
        return False
    
    # 4. Informe de actualización de código
    print("\n[4/4] Generando informe de actualización...")
    update_code_references()
    
    print("\n" + "=" * 60)
    print("✓ MIGRACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 60)
    print(f"\nBackups guardados en: {BACKUP_DIR}")
    print(f"  - geodocs_scanner_{timestamp}.db")
    print(f"  - geodocs_{timestamp}.db")
    print("\nPróximos pasos:")
    print("  1. Revisar que geodocs.db contenga todos los datos")
    print("  2. Actualizar las referencias en el código (ver lista arriba)")
    print("  3. Probar la aplicación con la nueva base de datos")
    print("  4. Una vez verificado, puedes archivar geodocs_scanner.db")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
