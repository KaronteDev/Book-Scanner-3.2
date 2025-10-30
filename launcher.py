
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, sys
from pathlib import Path
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except Exception as ex:
    print("Tkinter requerido:", ex); sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent

def launch_scanner():
    subprocess.Popen([sys.executable, str(BASE_DIR/"scanner_gui.py")])

def launch_annotator():
    subprocess.Popen([sys.executable, str(BASE_DIR/"annotator_gui.py")])

def main():
    root = tk.Tk()
    root.title("GeoDocs Scanner v23 — Selector")
    root.geometry("480x240")
    frm = ttk.Frame(root, padding=20)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="GeoDocs Research Suite", font=("TkDefaultFont", 14, "bold")).pack(pady=8)
    ttk.Label(frm, text="Elige un módulo:").pack(pady=6)
    row = ttk.Frame(frm); row.pack(pady=12)
    ttk.Button(row, text="🎥 Escanear (cámara)", width=24, command=launch_scanner).pack(side="left", padx=10)
    ttk.Button(row, text="📝 Anotar / Exportar", width=24, command=launch_annotator).pack(side="left", padx=10)
    ttk.Label(frm, text="Sugerencia: usa 'Escanear' solo cuando vayas a capturar.\nPara describir, anotar o exportar, usa 'Anotar / Exportar'.", justify="center").pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    main()
