#!/usr/bin/env python3
"""
Script simplificado para convertir messagebox a Messagebox con fallback
"""
import re
from pathlib import Path

def convert_file(filepath):
    """Convierte todos los messagebox.* a Messagebox.* con fallback"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Patrón 1: messagebox.showerror("Title", message)
    pattern1 = r'(\s+)messagebox\.showerror\(("[^"]+"),\s*([^)]+)\)'
    replacement1 = r'\1if Messagebox:\n\1    Messagebox.show_error(title=\2, message=\3, parent=self.root)\n\1else:\n\1    messagebox.showerror(\2, \3)'
    content = re.sub(pattern1, replacement1, content)
    
    # Patrón 2: messagebox.showinfo("Title", message)
    pattern2 = r'(\s+)messagebox\.showinfo\(("[^"]+"),\s*([^)]+)\)'
    replacement2 = r'\1if Messagebox:\n\1    Messagebox.show_info(title=\2, message=\3, parent=self.root)\n\1else:\n\1    messagebox.showinfo(\2, \3)'
    content = re.sub(pattern2, replacement2, content)
    
    # Patrón 3: messagebox.showwarning("Title", message)
    pattern3 = r'(\s+)messagebox\.showwarning\(("[^"]+"),\s*([^)]+)\)'
    replacement3 = r'\1if Messagebox:\n\1    Messagebox.show_warning(title=\2, message=\3, parent=self.root)\n\1else:\n\1    messagebox.showwarning(\2, \3)'
    content = re.sub(pattern3, replacement3, content)
    
    # Patrón 4: if messagebox.askyesno("Title", message):
    # Nota: Este patrón es más complicado porque está en un if
    pattern4 = r'if\s+(not\s+)?messagebox\.askyesno\(("[^"]+"),\s*([^)]+)\):'
    replacement4 = r'if \1(Messagebox.yesno(title=\2, message=\3, parent=self.root) if Messagebox else messagebox.askyesno(\2, \3)):'
    content = re.sub(pattern4, replacement4, content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ {filepath.name} - cambios aplicados")
        return True
    else:
        print(f"- {filepath.name} - sin cambios")
        return False

if __name__ == '__main__':
    base = Path(__file__).parent / 'gui'
    files = [
        base / 'scanner_module.py',
        base / 'annotation_view.py',
        base / 'export_view.py',
    ]
    
    total = 0
    for f in files:
        if f.exists():
            if convert_file(f):
                total += 1
    
    print(f"\nTotal archivos modificados: {total}")
