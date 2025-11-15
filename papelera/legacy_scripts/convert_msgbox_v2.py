#!/usr/bin/env python3
"""
Script para convertir messagebox a Messagebox con fallback - versión segura
"""
import re
from pathlib import Path

def process_line(line, indent_base):
    """Procesa una línea y devuelve lista de líneas de reemplazo"""
    
    # Solo procesar si la línea contiene messagebox. (no if)
    if 'messagebox.' not in line or line.strip().startswith('if'):
        return [line]
    
    # Detectar indentación
    match = re.match(r'^(\s*)', line)
    indent = match.group(1) if match else ''
    
    # messagebox.showerror
    if 'messagebox.showerror(' in line:
        m = re.search(r'messagebox\.showerror\(("[^"]+"),\s*([^)]+)\)', line)
        if m:
            title, message = m.groups()
            return [
                f'{indent}if Messagebox:\n',
                f'{indent}    Messagebox.show_error(title={title}, message={message}, parent=self.root)\n',
                f'{indent}else:\n',
                f'{indent}    messagebox.showerror({title}, {message})\n'
            ]
    
    # messagebox.showinfo
    if 'messagebox.showinfo(' in line:
        m = re.search(r'messagebox\.showinfo\(("[^"]+"),\s*([^)]+)\)', line)
        if m:
            title, message = m.groups()
            return [
                f'{indent}if Messagebox:\n',
                f'{indent}    Messagebox.show_info(title={title}, message={message}, parent=self.root)\n',
                f'{indent}else:\n',
                f'{indent}    messagebox.showinfo({title}, {message})\n'
            ]
    
    # messagebox.showwarning
    if 'messagebox.showwarning(' in line:
        m = re.search(r'messagebox\.showwarning\(("[^"]+"),\s*([^)]+)\)', line)
        if m:
            title, message = m.groups()
            return [
                f'{indent}if Messagebox:\n',
                f'{indent}    Messagebox.show_warning(title={title}, message={message}, parent=self.root)\n',
                f'{indent}else:\n',
                f'{indent}    messagebox.showwarning({title}, {message})\n'
            ]
    
    return [line]

def convert_file(filepath):
    """Convierte archivo línea por línea"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    changed = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Procesar if statements con messagebox.askyesno
        if 'if' in line and 'messagebox.askyesno(' in line:
            # Reemplazar inline
            m = re.search(r'(if\s+)(not\s+)?messagebox\.askyesno\(("[^"]+"),\s*([^)]+)\):', line)
            if m:
                if_part, not_part, title, message = m.groups()
                not_str = not_part if not_part else ''
                indent = re.match(r'^(\s*)', line).group(1)
                new_line = f'{indent}if {not_str}(Messagebox.yesno(title={title}, message={message}, parent=self.root) if Messagebox else messagebox.askyesno({title}, {message})):\n'
                new_lines.append(new_line)
                changed = True
                i += 1
                continue
        
        # Procesar otros messageboxes
        result = process_line(line, '')
        if len(result) > 1:
            changed = True
        new_lines.extend(result)
        i += 1
    
    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
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
