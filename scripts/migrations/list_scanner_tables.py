#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script temporal para listar tablas de geodocs_scanner.db"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB = BASE_DIR / "geodocs_scanner.db"

if not DB.exists():
    print(f"ERROR: {DB} no existe")
    exit(1)

conn = sqlite3.connect(DB)
cursor = conn.cursor()

# Listar tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("=== TABLAS EN geodocs_scanner.db ===")
for table in tables:
    print(f"\n{table[0]}:")
    # Mostrar esquema de cada tabla
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  - {col[1]} {col[2]}")

conn.close()
