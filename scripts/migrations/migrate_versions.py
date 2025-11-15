#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_versions.py — Añadir sistema de versionado para OCR y anotaciones
"""
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).parent))
from utils import app_config


def _ensure_column(conn, table: str, column: str, col_type: str, default=None):
    """Añadir columna si no existe"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}")
        print(f"  ✓ Columna {table}.{column} añadida")
        return True
    return False


def migrate_project_db(project_db_path: Path):
    """Migrar una base de datos de proyecto"""
    if not project_db_path.exists():
        return
    
    print(f"\n📦 Migrando: {project_db_path.name}")
    
    with sqlite3.connect(project_db_path) as conn:
        cursor = conn.cursor()
        
        # Crear tabla versions si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,  -- 'ocr', 'annotation', 'metadata'
                entity_id INTEGER NOT NULL,  -- ID de page, annotation, etc.
                version INTEGER NOT NULL DEFAULT 1,
                data_json TEXT,  -- Snapshot completo en JSON
                user_notes TEXT,  -- Notas del usuario sobre el cambio
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(entity_type, entity_id, version)
            )
        """)
        print("  ✓ Tabla 'versions' creada/verificada")
        
        # Índices para mejorar performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_versions_entity 
            ON versions(entity_type, entity_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_versions_created 
            ON versions(created_at DESC)
        """)
        print("  ✓ Índices creados")
        
        # Añadir campo current_version a page para tracking rápido
        _ensure_column(conn, 'page', 'current_ocr_version', 'INTEGER', 1)
        
        conn.commit()
        print("  ✅ Migración completada")


def migrate_global_db(global_db_path: Path):
    """Migrar base de datos global (opcional)"""
    if not global_db_path.exists():
        return
    
    print(f"\n🌐 Migrando BD global: {global_db_path.name}")
    
    with sqlite3.connect(global_db_path) as conn:
        cursor = conn.cursor()
        
        # Tabla para tracking de migraciones aplicadas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT UNIQUE NOT NULL,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Registrar esta migración
        cursor.execute("""
            INSERT OR IGNORE INTO schema_migrations (migration_name)
            VALUES ('versions_system_v1')
        """)
        
        conn.commit()
        print("  ✅ BD global actualizada")


def main():
    """Ejecutar migración"""
    print("=" * 60)
    print("🔄 MIGRACIÓN: Sistema de Versionado")
    print("=" * 60)
    
    base_path = app_config.get_root_dir()
    print(f"📂 Directorio raíz: {base_path}")
    
    # Migrar BD global
    global_db = base_path / "geodocs.db"
    if global_db.exists():
        migrate_global_db(global_db)
    
    # Buscar y migrar todas las BDs de proyectos
    projects_dir = base_path / "proyectos"
    if projects_dir.exists():
        count = 0
        for project_db in projects_dir.rglob("project.db"):
            migrate_project_db(project_db)
            count += 1
        print(f"\n✅ {count} proyecto(s) migrado(s)")
    else:
        print("\n⚠️ No se encontró directorio de proyectos")
    
    print("\n" + "=" * 60)
    print("✅ Migración completada con éxito")
    print("=" * 60)


if __name__ == "__main__":
    main()
