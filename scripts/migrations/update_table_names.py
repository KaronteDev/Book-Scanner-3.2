#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_table_names.py - Actualiza nombres de tablas en archivos Python

Cambia:
  - project → scanner_project
  - document → scanner_document
  - page → scanner_page
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

FILES_TO_UPDATE = [
    "web_viewer/server.py",
    "scanner_gui.py",
    "processor_queue.py",
]

def update_table_names(filepath):
    """Actualiza los nombres de tabla en un archivo SQL"""
    content = filepath.read_text(encoding='utf-8')
    original = content
    
    # Reemplazos específicos para SQL - solo en contextos SQL
    # FROM, INTO, UPDATE, JOIN, etc.
    patterns = [
        (r'\bFROM page\b', 'FROM scanner_page'),
        (r'\bINTO page\b', 'INTO scanner_page'),
        (r'\bUPDATE page\b', 'UPDATE scanner_page'),
        (r'\bJOIN page\b', 'JOIN scanner_page'),
        
        (r'\bFROM document\b', 'FROM scanner_document'),
        (r'\bINTO document\b', 'INTO scanner_document'),
        (r'\bUPDATE document\b', 'UPDATE scanner_document'),
        (r'\bJOIN document\b', 'JOIN scanner_document'),
        
        (r'\bFROM project\b', 'FROM scanner_project'),
        (r'\bINTO project\b', 'INTO scanner_project'),
        (r'\bUPDATE project\b', 'UPDATE scanner_project'),
        (r'\bJOIN project\b', 'JOIN scanner_project'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return True
    return False

def main():
    print("=== Actualizando nombres de tablas ===\n")
    
    updated = 0
    for rel_path in FILES_TO_UPDATE:
        filepath = BASE_DIR / rel_path
        if not filepath.exists():
            print(f"⚠ {rel_path} no encontrado")
            continue
        
        if update_table_names(filepath):
            print(f"✓ {rel_path} - actualizado")
            updated += 1
        else:
            print(f"- {rel_path} - sin cambios")
    
    print(f"\n✓ {updated} archivos actualizados")

if __name__ == "__main__":
    main()
