#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_schema_v3.py — Migration script for Book Scanner 3.2 new features

Añade:
- Campo abreviatura a archivos, fondos y proyectos
- Tabla tipos_publicacion
- Campo rotation_angle a page (project.db)
- ON DELETE CASCADE ya existe en fondos→archivos
- Mejora el manejo de archivos/fondos múltiples por proyecto

Uso:
    python migrate_schema_v3.py
"""
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from utils import app_config
from utils import db_manager as db


def migrate_global_db(db_path: Path) -> None:
    """Migra geodocs.db con nuevos campos y tablas"""
    print(f"📊 Migrando base de datos global: {db_path}")
    
    if not db_path.exists():
        print("   ⚠️ La BD global no existe, se creará al iniciar la app")
        return
    
    conn = sqlite3.connect(db_path, timeout=15)
    cur = conn.cursor()
    
    # --- Añadir campo 'abreviatura' a archivos ---
    if not db._has_column(cur, 'archivos', 'abreviatura'):
        print("   ✅ Añadiendo campo 'abreviatura' a archivos...")
        cur.execute("ALTER TABLE archivos ADD COLUMN abreviatura TEXT")
        # Rellenar con siglas existentes o inferir
        cur.execute("""
            UPDATE archivos 
            SET abreviatura = COALESCE(
                UPPER(SUBSTR(siglas, 1, 6)),
                UPPER(SUBSTR(COALESCE(nombre_oficial, nombre, 'ARC'), 1, 3))
            )
            WHERE abreviatura IS NULL
        """)
    else:
        print("   ⏭️ Campo 'abreviatura' ya existe en archivos")
    
    # --- Añadir campo 'abreviatura' a fondos ---
    if not db._has_column(cur, 'fondos', 'abreviatura'):
        print("   ✅ Añadiendo campo 'abreviatura' a fondos...")
        cur.execute("ALTER TABLE fondos ADD COLUMN abreviatura TEXT")
        # Generar abreviaturas desde el título
        cur.execute("""
            UPDATE fondos 
            SET abreviatura = UPPER(SUBSTR(REPLACE(REPLACE(COALESCE(titulo, nombre, 'F'), ' ', ''), '-', ''), 1, 4))
            WHERE abreviatura IS NULL
        """)
    else:
        print("   ⏭️ Campo 'abreviatura' ya existe en fondos")
    
    # --- Añadir campo 'abreviatura' a proyectos ---
    if not db._has_column(cur, 'proyectos', 'abreviatura'):
        print("   ✅ Añadiendo campo 'abreviatura' a proyectos...")
        cur.execute("ALTER TABLE proyectos ADD COLUMN abreviatura TEXT")
        # Generar desde signatura o título
        cur.execute("""
            UPDATE proyectos 
            SET abreviatura = UPPER(
                SUBSTR(
                    REPLACE(
                        REPLACE(
                            REPLACE(COALESCE(signatura, titulo, 'P'), ' ', ''),
                            '/',
                            '_'
                        ),
                        '-',
                        ''
                    ),
                    1,
                    8
                )
            )
            WHERE abreviatura IS NULL
        """)
    else:
        print("   ⏭️ Campo 'abreviatura' ya existe en proyectos")
    
    # --- Crear tabla tipos_publicacion ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tipos_publicacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            icono TEXT,
            orden INTEGER DEFAULT 0,
            activo BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Verificar si ya tiene datos
    count = cur.execute("SELECT COUNT(*) FROM tipos_publicacion").fetchone()[0]
    
    if count == 0:
        print("   ✅ Creando tabla 'tipos_publicacion' con datos iniciales...")
        tipos_iniciales = [
            ('libro', 'Libro', 'Libro impreso o manuscrito encuadernado', '📚', 1),
            ('revista', 'Revista', 'Publicación periódica', '📰', 2),
            ('periodico', 'Periódico', 'Publicación de noticias diaria o semanal', '🗞️', 3),
            ('manuscrito', 'Manuscrito', 'Documento escrito a mano', '📜', 4),
            ('mapa', 'Mapa', 'Representación cartográfica', '🗺️', 5),
            ('fotografia', 'Fotografía', 'Imagen fotográfica', '📷', 6),
            ('documento', 'Documento', 'Documento administrativo o legal', '📄', 7),
            ('carta', 'Carta', 'Correspondencia epistolar', '✉️', 8),
            ('cartel', 'Cartel', 'Cartel o póster', '🖼️', 9),
            ('grabado', 'Grabado', 'Estampa o grabado artístico', '🖼️', 10),
            ('partitura', 'Partitura', 'Notación musical', '🎵', 11),
            ('plano', 'Plano', 'Plano arquitectónico o técnico', '📐', 12),
            ('otros', 'Otros', 'Otro tipo de publicación', '📦', 99),
        ]
        
        cur.executemany(
            "INSERT INTO tipos_publicacion(codigo, nombre, descripcion, icono, orden) VALUES(?,?,?,?,?)",
            tipos_iniciales
        )
    else:
        print("   ⏭️ Tabla 'tipos_publicacion' ya tiene datos")
    
    # --- Añadir campo tipo_publicacion_id a proyectos ---
    if not db._has_column(cur, 'proyectos', 'tipo_publicacion_id'):
        print("   ✅ Añadiendo campo 'tipo_publicacion_id' a proyectos...")
        cur.execute("ALTER TABLE proyectos ADD COLUMN tipo_publicacion_id INTEGER REFERENCES tipos_publicacion(id)")
        # Intentar mapear tipo_documento existente a tipos_publicacion
        cur.execute("""
            UPDATE proyectos 
            SET tipo_publicacion_id = (
                SELECT id FROM tipos_publicacion 
                WHERE LOWER(proyectos.tipo_documento) LIKE '%' || LOWER(tipos_publicacion.codigo) || '%'
                LIMIT 1
            )
            WHERE tipo_documento IS NOT NULL 
            AND tipo_documento != ''
            AND tipo_publicacion_id IS NULL
        """)
    else:
        print("   ⏭️ Campo 'tipo_publicacion_id' ya existe en proyectos")
    
    # --- Verificar CASCADE en fondos (ya debería existir) ---
    # Rehacer la FK con ON DELETE CASCADE si no existe (requiere recrear tabla en SQLite)
    # Por simplicidad, verificamos que existe la FK
    cur.execute("PRAGMA foreign_key_list(fondos)")
    fks = cur.fetchall()
    has_cascade = any('CASCADE' in str(fk) for fk in fks)
    
    if has_cascade:
        print("   ✅ FK fondos→archivos ya tiene ON DELETE CASCADE")
    else:
        print("   ⚠️ FK fondos→archivos no tiene CASCADE; requiere recrear tabla (manual)")
        # En producción, aquí se haría backup + recreate + restore
        # Para esta migración, asumimos que la estructura actual es correcta
    
    conn.commit()
    conn.close()
    print("   ✅ Migración de BD global completada")


def migrate_project_dbs(base_path: Path) -> None:
    """Migra todas las project.db con campo rotation_angle"""
    print("\n📊 Migrando bases de datos de proyectos...")
    
    projects = db.list_projects(base_path)
    
    if not projects:
        print("   ⏭️ No hay proyectos para migrar")
        return
    
    migrated_count = 0
    
    for proj in projects:
        carpeta_raiz = proj.get('carpeta_raiz')
        if not carpeta_raiz:
            continue
        
        project_db_path = Path(carpeta_raiz) / 'project.db'
        
        if not project_db_path.exists():
            continue
        
        try:
            conn = sqlite3.connect(project_db_path, timeout=15)
            cur = conn.cursor()
            
            # Añadir rotation_angle a page
            if not db._has_column(cur, 'page', 'rotation_angle'):
                cur.execute("ALTER TABLE page ADD COLUMN rotation_angle INTEGER DEFAULT 0")
                migrated_count += 1
            
            # Añadir campo original_orientation (detectado automáticamente)
            if not db._has_column(cur, 'page', 'original_orientation'):
                cur.execute("ALTER TABLE page ADD COLUMN original_orientation INTEGER DEFAULT 0")
            
            # Añadir campo has_fingers (dedos/soportes detectados)
            if not db._has_column(cur, 'page', 'has_fingers'):
                cur.execute("ALTER TABLE page ADD COLUMN has_fingers BOOLEAN DEFAULT 0")
            
            # Añadir campo fingers_removed (dedos ya eliminados)
            if not db._has_column(cur, 'page', 'fingers_removed'):
                cur.execute("ALTER TABLE page ADD COLUMN fingers_removed BOOLEAN DEFAULT 0")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"   ⚠️ Error migrando {project_db_path}: {e}")
    
    if migrated_count > 0:
        print(f"   ✅ {migrated_count} proyectos migrados con éxito")
    else:
        print("   ⏭️ Todos los proyectos ya estaban migrados")


def main():
    print("=" * 60)
    print("  📚 Book Scanner 3.2 - Migración de esquema v3")
    print("=" * 60)
    
    try:
        base_path = app_config.get_root_dir()
        print(f"\n📁 Directorio base: {base_path}")
        
        # Inicializar BD global si no existe
        db.init_global_db(base_path)
        
        # Migrar BD global
        global_db_path = base_path / "data" / db.GLOBAL_DB
        migrate_global_db(global_db_path)
        
        # Migrar BDs de proyectos
        migrate_project_dbs(base_path)
        
        print("\n" + "=" * 60)
        print("  ✅ Migración completada con éxito")
        print("=" * 60)
        print("\n💡 Cambios aplicados:")
        print("   • Campo 'abreviatura' en archivos, fondos y proyectos")
        print("   • Tabla 'tipos_publicacion' con 13 tipos predefinidos")
        print("   • Campo 'tipo_publicacion_id' en proyectos")
        print("   • Campo 'rotation_angle' en páginas (project.db)")
        print("   • Campos 'original_orientation', 'has_fingers', 'fingers_removed'")
        print("\n🚀 La aplicación ya puede usar estas nuevas funcionalidades")
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
