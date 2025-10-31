#!/usr/bin/env python3
"""Fix remaining syntax errors in export_view.py"""
import re

with open('gui/export_view.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: parent=self.root)else: -> parent=self.root)\n                else:
content = re.sub(
    r'parent=self\.root\)else:',
    'parent=self.root)\n                else:',
    content
)

# Fix 2: str(e)\n at end of line -> str(e)}")\n
content = re.sub(
    r'f"Error al exportar:\\n\{str\(e\)\n',
    r'f"Error al exportar:\n{str(e)}\")\n',
    content
)

# Write back
with open('gui/export_view.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ export_view.py fixed")
