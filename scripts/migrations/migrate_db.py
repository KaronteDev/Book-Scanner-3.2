#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_db.py — Migra geodocs.db del directorio antiguo al nuevo root_dir/data
"""
from pathlib import Path
import shutil
import sys
from datetime import datetime

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))
from utils import app_config


def migrate_database():
    """Migrar geodocs.db del viejo proyecto a root_dir/data con backup"""
    
    # Rutas
    old_location = Path(__file__).parent / "data" / "geodocs.db"
    root_dir = app_config.get_root_dir()
    new_location = root_dir / "data" / "geodocs.db"
    
    print("=" * 70)
    print("MIGRACIÓN DE BASE DE DATOS GEODOCS")
    print("=" * 70)
    print(f"\nUbicación antigua: {old_location}")
    print(f"Ubicación nueva:   {new_location}")
    print(f"Root directory:    {root_dir}")
    
    # Verificar si ya están en el mismo lugar
    if old_location.resolve() == new_location.resolve():
        print("\n✓ Las ubicaciones son idénticas. No se requiere migración.")
        return True
    
    # Verificar si existe la BD antigua
    if not old_location.exists():
        print(f"\n⚠ No se encontró base de datos en la ubicación antigua.")
        print(f"  Ubicación esperada: {old_location}")
        
        if new_location.exists():
            print(f"\n✓ Ya existe una base de datos en la nueva ubicación.")
            return True
        else:
            print(f"\n⚠ Tampoco existe en la nueva ubicación.")
            print(f"  Se creará una nueva cuando ejecute la aplicación.")
            return True
    
    # Verificar si ya existe en el nuevo destino
    if new_location.exists():
        print(f"\n⚠ Ya existe una base de datos en la nueva ubicación.")
        
        # Comparar tamaños
        old_size = old_location.stat().st_size
        new_size = new_location.stat().st_size
        old_mtime = datetime.fromtimestamp(old_location.stat().st_mtime)
        new_mtime = datetime.fromtimestamp(new_location.stat().st_mtime)
        
        print(f"\n  Antigua: {old_size:,} bytes (modificada: {old_mtime})")
        print(f"  Nueva:   {new_size:,} bytes (modificada: {new_mtime})")
        
        respuesta = input("\n¿Desea sobrescribir la base de datos nueva con la antigua? (s/N): ").strip().lower()
        if respuesta not in ('s', 'si', 'sí', 'y', 'yes'):
            print("\n✗ Migración cancelada por el usuario.")
            return False
        
        # Crear backup de la existente
        backup_path = new_location.with_suffix('.db.backup.' + datetime.now().strftime('%Y%m%d_%H%M%S'))
        print(f"\n→ Creando backup: {backup_path}")
        shutil.copy2(new_location, backup_path)
        print(f"✓ Backup creado")
    
    # Crear directorio destino si no existe
    new_location.parent.mkdir(parents=True, exist_ok=True)
    
    # Copiar (no mover, por seguridad)
    print(f"\n→ Copiando base de datos...")
    try:
        shutil.copy2(old_location, new_location)
        print(f"✓ Base de datos copiada exitosamente")
        
        # Verificar integridad
        old_size = old_location.stat().st_size
        new_size = new_location.stat().st_size
        
        if old_size == new_size:
            print(f"✓ Verificación: tamaños coinciden ({old_size:,} bytes)")
        else:
            print(f"⚠ Advertencia: los tamaños difieren (antigua: {old_size}, nueva: {new_size})")
            return False
        
        # Preguntar si eliminar la antigua
        print(f"\n→ La base de datos antigua sigue en: {old_location}")
        respuesta = input("¿Desea eliminar la base de datos antigua? (s/N): ").strip().lower()
        
        if respuesta in ('s', 'si', 'sí', 'y', 'yes'):
            # Crear backup antes de eliminar
            backup_old = old_location.with_suffix('.db.backup.' + datetime.now().strftime('%Y%m%d_%H%M%S'))
            shutil.copy2(old_location, backup_old)
            old_location.unlink()
            print(f"✓ Base de datos antigua eliminada (backup en {backup_old})")
        else:
            print(f"✓ Base de datos antigua conservada como respaldo")
        
        print("\n" + "=" * 70)
        print("MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 70)
        print(f"\nLa base de datos ahora está en: {new_location}")
        print(f"La aplicación usará esta ubicación automáticamente.")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error durante la migración: {e}")
        return False


def main():
    """Punto de entrada principal"""
    print("\nEste script migrará su base de datos geodocs.db a la nueva ubicación\n"
          "configurada en paths.root_dir.\n")
    
    success = migrate_database()
    
    if success:
        print("\n✓ Puede cerrar esta ventana y ejecutar la aplicación normalmente.")
        sys.exit(0)
    else:
        print("\n✗ La migración no se completó. Revise los mensajes anteriores.")
        sys.exit(1)


if __name__ == "__main__":
    main()
