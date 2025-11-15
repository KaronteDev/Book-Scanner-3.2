#!/usr/bin/env python3
"""
Script para convertir todos los messagebox.* a Messagebox.* con fallback
"""
import re
from pathlib import Path

def fix_messagebox_calls(filepath):
    """Convierte llamadas de messagebox a Messagebox con fallback"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Patrones a reemplazar con parent
    replacements = [
        # messagebox.showerror -> Messagebox.show_error
        (r'messagebox\.showerror\(', 
         r'(Messagebox.show_error(parent=self.root, ' if 'self.root' in content else r'(Messagebox.show_error('),
        
        # messagebox.showinfo -> Messagebox.show_info
        (r'messagebox\.showinfo\(',
         r'(Messagebox.show_info(parent=self.root, ' if 'self.root' in content else r'(Messagebox.show_info('),
        
        # messagebox.showwarning -> Messagebox.show_warning
        (r'messagebox\.showwarning\(',
         r'(Messagebox.show_warning(parent=self.root, ' if 'self.root' in content else r'(Messagebox.show_warning('),
        
        # messagebox.askyesno -> Messagebox.yesno
        (r'messagebox\.askyesno\(',
         r'(Messagebox.yesno(parent=self.root, ' if 'self.root' in content else r'(Messagebox.yesno('),
    ]
    
    # Aplicar reemplazos manualmente para mantener la lógica de fallback
    # En su lugar, simplemente reemplazamos las llamadas directas
    
    # Patrón 1: messagebox.showerror("Title", "Message") 
    # -> if Messagebox: Messagebox.show_error(title="Title", message="Message", parent=...) else: messagebox.showerror(...)
    
    print(f"Procesando {filepath.name}...")
    
    # Buscar todas las llamadas a messagebox y reemplazarlas
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        new_line = line
        
        # Detectar si hay un if con messagebox.askyesno
        if 'if' in line and 'messagebox.askyesno' in line:
            # Formato: if messagebox.askyesno("Title", "Message"):
            match = re.search(r'if\s+(not\s+)?messagebox\.askyesno\(([^)]+)\)', line)
            if match:
                not_prefix = match.group(1) or ''
                args = match.group(2)
                indent = re.match(r'^(\s*)', line).group(1)
                new_line = f'{indent}if {not_prefix}(Messagebox.yesno({args}, parent=self.root) if Messagebox else messagebox.askyesno({args})):'
        
        elif 'messagebox.showerror' in line:
            # Formato: messagebox.showerror("Title", "Message")
            match = re.search(r'messagebox\.showerror\(([^)]+)\)', line)
            if match:
                args = match.group(1)
                indent = re.match(r'^(\s*)', line).group(1)
                # Parsear argumentos
                parts = args.split(',', 1)
                if len(parts) == 2:
                    title = parts[0].strip()
                    message = parts[1].strip()
                    new_line = f'{indent}if Messagebox:\n{indent}    Messagebox.show_error(title={title}, message={message}, parent=self.root)\n{indent}else:\n{indent}    messagebox.showerror({args})'
        
        elif 'messagebox.showinfo' in line:
            match = re.search(r'messagebox\.showinfo\(([^)]+)\)', line)
            if match:
                args = match.group(1)
                indent = re.match(r'^(\s*)', line).group(1)
                parts = args.split(',', 1)
                if len(parts) == 2:
                    title = parts[0].strip()
                    message = parts[1].strip()
                    new_line = f'{indent}if Messagebox:\n{indent}    Messagebox.show_info(title={title}, message={message}, parent=self.root)\n{indent}else:\n{indent}    messagebox.showinfo({args})'
        
        elif 'messagebox.showwarning' in line:
            match = re.search(r'messagebox\.showwarning\(([^)]+)\)', line)
            if match:
                args = match.group(1)
                indent = re.match(r'^(\s*)', line).group(1)
                parts = args.split(',', 1)
                if len(parts) == 2:
                    title = parts[0].strip()
                    message = parts[1].strip()
                    new_line = f'{indent}if Messagebox:\n{indent}    Messagebox.show_warning(title={title}, message={message}, parent=self.root)\n{indent}else:\n{indent}    messagebox.showwarning({args})'
        
        new_lines.append(new_line)
    
    new_content = '\n'.join(new_lines)
    
    if new_content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✓ {filepath.name} actualizado")
    else:
        print(f"- {filepath.name} sin cambios")

if __name__ == '__main__':
    base = Path(__file__).parent / 'gui'
    files = [
        base / 'scanner_module.py',
        base / 'annotation_view.py',
        base / 'export_view.py',
    ]
    
    for f in files:
        if f.exists():
            fix_messagebox_calls(f)
