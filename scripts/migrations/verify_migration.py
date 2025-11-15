#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_migration.py - Verifica que la migración se completó correctamente
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GLOBAL_DB = BASE_DIR / "data" / "geodocs.db"
SCANNER_DB = BASE_DIR / "geodocs_scanner.db"

REQUIRED_TABLES = [
    # Módulo archivístico
    'archivos', 'fondos', 'proyectos', 'etiquetas', 'proyecto_etiquetas', 'settings',
    # Módulo scanner
    'scanner_project', 'scanner_document', 'scanner_page',
    'annotation', 'glossary', 'style_template', 'ocr_revision', 
    'version_history', 'audit_log'
]

def check_database_exists():
    """Verifica que geodocs.db existe"""
    if not GLOBAL_DB.exists():
        print(f"❌ ERROR: {GLOBAL_DB} no existe")
        return False
    print(f"✓ Base de datos existe: {GLOBAL_DB}")
    return True

def check_tables():
    """Verifica que todas las tablas necesarias existen"""
    print("\n=== Verificando tablas ===")
    conn = sqlite3.connect(GLOBAL_DB)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    existing_tables = {row[0] for row in cursor.fetchall()}
    
    missing = []
    for table in REQUIRED_TABLES:
        if table in existing_tables:
            print(f"  ✓ {table}")
        else:
            print(f"  ❌ {table} - FALTA")
            missing.append(table)
    
    conn.close()
    
    if missing:
        print(f"\n❌ Faltan {len(missing)} tablas: {', '.join(missing)}")
        return False
    
    print(f"\n✓ Todas las {len(REQUIRED_TABLES)} tablas requeridas existen")
    return True

def check_data():
    """Verifica que se migraron los datos"""
    print("\n=== Verificando datos migrados ===")
    conn = sqlite3.connect(GLOBAL_DB)
    cursor = conn.cursor()
    
    checks = [
        ('glossary', 'glosarios'),
        ('style_template', 'plantillas de estilo'),
        ('scanner_project', 'proyectos'),
        ('scanner_document', 'documentos'),
        ('scanner_page', 'páginas'),
    ]
    
    for table, name in checks:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  ✓ {table}: {count} {name}")
        except Exception as e:
            print(f"  ❌ {table}: Error - {e}")
    
    conn.close()
    return True

def check_integrity():
    """Verifica la integridad de la base de datos"""
    print("\n=== Verificando integridad ===")
    conn = sqlite3.connect(GLOBAL_DB)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        if result == "ok":
            print("  ✓ Integridad OK")
            return True
        else:
            print(f"  ❌ Problema de integridad: {result}")
            return False
    except Exception as e:
        print(f"  ❌ Error al verificar integridad: {e}")
        return False
    finally:
        conn.close()

def check_code_files():
    """Verifica que los archivos de código fueron actualizados"""
    print("\n=== Verificando archivos de código ===")
    
    files_to_check = [
        'web_viewer/server.py',
        'scanner_gui.py',
        'processor_queue.py',
        'modules/scheduler.py'
    ]
    
    all_ok = True
    for filepath in files_to_check:
        full_path = BASE_DIR / filepath
        if not full_path.exists():
            print(f"  ⚠ {filepath} - no encontrado")
            continue
        
        content = full_path.read_text(encoding='utf-8')
        
        # Verificar que usa geodocs.db y no geodocs_scanner.db
        if 'geodocs_scanner.db' in content:
            print(f"  ❌ {filepath} - todavía usa geodocs_scanner.db")
            all_ok = False
        elif 'geodocs.db' in content:
            print(f"  ✓ {filepath} - actualizado correctamente")
        else:
            print(f"  ? {filepath} - no usa base de datos")
    
    return all_ok

def check_scanner_db_status():
    """Verifica el estado de la antigua base de datos"""
    print("\n=== Estado de geodocs_scanner.db ===")
    
    if SCANNER_DB.exists():
        size_mb = SCANNER_DB.stat().st_size / (1024 * 1024)
        print(f"  ⚠ geodocs_scanner.db todavía existe ({size_mb:.2f} MB)")
        print(f"    Puede archivarse o eliminarse una vez verificado todo")
        print(f"    Ubicación: {SCANNER_DB}")
    else:
        print(f"  ✓ geodocs_scanner.db no existe (ya fue archivada)")
    
    return True

def main():
    """Ejecuta todas las verificaciones"""
    print("=" * 60)
    print("VERIFICACIÓN DE MIGRACIÓN DE BASE DE DATOS")
    print("=" * 60)
    
    checks = [
        ("Base de datos", check_database_exists),
        ("Tablas", check_tables),
        ("Datos", check_data),
        ("Integridad", check_integrity),
        ("Código", check_code_files),
        ("BD antigua", check_scanner_db_status),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error en verificación '{name}': {e}")
            results.append((name, False))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE VERIFICACIÓN")
    print("=" * 60)
    
    all_ok = all(r[1] for r in results)
    
    for name, result in results:
        status = "✓" if result else "❌"
        print(f"{status} {name}")
    
    print("=" * 60)
    
    if all_ok:
        print("✅ MIGRACIÓN VERIFICADA - TODO CORRECTO")
        print("\nPuedes proceder a probar la aplicación.")
        return True
    else:
        print("⚠️ ADVERTENCIAS O ERRORES ENCONTRADOS")
        print("\nRevisa los mensajes anteriores para más detalles.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
