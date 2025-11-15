#!/usr/bin/env python3
"""
Script para convertir messagebox en export_view.py únicamente
"""
import re
from pathlib import Path

def convert_file(filepath):
    """Convierte todos los messagebox.* a Messagebox.* con fallback"""
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
        
        # Procesar messagebox.showerror
        if 'messagebox.showerror(' in line and line.strip() and not line.strip().startswith('if'):
            m = re.search(r'(\s*)messagebox\.showerror\(("[^"]+"),\s*([^)]+)\)', line)
            if m:
                indent, title, message = m.groups()
                new_lines.extend([
                    f'{indent}if Messagebox:\n',
                    f'{indent}    Messagebox.show_error(title={title}, message={message}, parent=self.root)\n',
                    f'{indent}else:\n',
                    f'{indent}    messagebox.showerror({title}, {message})\n'
                ])
                changed = True
                i += 1
                continue
        
        # Procesar messagebox.showinfo
        if 'messagebox.showinfo(' in line and line.strip() and not line.strip().startswith('if'):
            m = re.search(r'(\s*)messagebox\.showinfo\(("[^"]+"),\s*([^)]+)\)', line)
            if m:
                indent, title, message = m.groups()
                new_lines.extend([
                    f'{indent}if Messagebox:\n',
                    f'{indent}    Messagebox.show_info(title={title}, message={message}, parent=self.root)\n',
                    f'{indent}else:\n',
                    f'{indent}    messagebox.showinfo({title}, {message})\n'
                ])
                changed = True
                i += 1
                continue
        
        # Procesar messagebox.showwarning
        if 'messagebox.showwarning(' in line and line.strip() and not line.strip().startswith('if'):
            m = re.search(r'(\s*)messagebox\.showwarning\(("[^"]+"),\s*([^)]+)\)', line)
            if m:
                indent, title, message = m.groups()
                new_lines.extend([
                    f'{indent}if Messagebox:\n',
                    f'{indent}    Messagebox.show_warning(title={title}, message={message}, parent=self.root)\n',
                    f'{indent}else:\n',
                    f'{indent}    messagebox.showwarning({title}, {message})\n'
                ])
                changed = True
                i += 1
                continue
        
        new_lines.append(line)
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
    f = Path('gui') / 'export_view.py'
    if f.exists():
        convert_file(f)
