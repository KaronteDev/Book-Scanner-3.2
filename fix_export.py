#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

# Read file
with open('gui/export_view.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix import
content = re.sub(
    r'try:\\n    import ttkbootstrap as ttkb\\nexcept ImportError:\\n    ttkb = None, filedialog, messagebox',
    'from tkinter import filedialog, messagebox\ntry:\n    import ttkbootstrap as ttkb\nexcept ImportError:\n    ttkb = None',
    content
)

# Fix style to bootstyle
content = content.replace("style=\"Accent.TButton\"", "bootstyle=\"primary\"")

# Add bootstyle to buttons that don't have it
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'ttkb.Button(' in line and 'bootstyle=' not in line:
        # Find the closing parenthesis and add bootstyle before command
        if 'command=' in line:
            lines[i] = line.replace('command=', 'bootstyle="primary",\n            command=')

content = '\n'.join(lines)

# Write back
with open('gui/export_view.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed export_view.py")
