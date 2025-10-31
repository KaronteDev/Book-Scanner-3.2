#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de renderizado HTML - Diagnóstico de tkinterweb
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys

print("\n" + "="*60)
print("🔍 DIAGNÓSTICO DE RENDERIZADO")
print("="*60)

# Test 1: Verificar importación
try:
    from tkinterweb import HtmlFrame
    print("✅ tkinterweb importado correctamente")
except ImportError as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)

# Test 2: Crear ventana básica
root = tk.Tk()
root.title("Test Renderizado tkinterweb")
root.geometry("800x600")

print("✅ Ventana Tkinter creada")

# Test 3: Crear widget de texto para debug
text_frame = ttk.Frame(root)
text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

debug_text = tk.Text(text_frame, height=10, wrap=tk.WORD)
debug_text.pack(fill=tk.BOTH, expand=True)

def log(msg):
    """Añadir mensaje al área de debug"""
    debug_text.insert(tk.END, msg + "\n")
    debug_text.see(tk.END)
    print(msg)

log("🔧 Área de debug inicializada")
log("="*50)

# Test 4: Crear HtmlFrame con callbacks
log("⏳ Creando HtmlFrame...")

try:
    html_widget = HtmlFrame(root, messages_enabled=False)
    html_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    log("✅ HtmlFrame creado")
except Exception as e:
    log(f"❌ ERROR al crear HtmlFrame: {e}")
    root.mainloop()
    sys.exit(1)

# Test 5: Probar con HTML ultra-simple
html_ultra_simple = """<!DOCTYPE html>
<html><body style="background:red;color:white;font-size:48px;text-align:center;padding:100px;">
TEXTO VISIBLE
</body></html>"""

html_simple_styled = """<!DOCTYPE html>
<html>
<head>
<style>
body {
    background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
    color: white;
    font-family: Arial;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    margin: 0;
}
h1 { font-size: 48px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
</style>
</head>
<body>
<h1>✅ HTML FUNCIONA</h1>
</body>
</html>"""

current_test = [0]

def test_ultra_simple():
    log("\n🧪 Test 1: HTML ultra-simple (fondo rojo)")
    try:
        html_widget.load_html(html_ultra_simple)
        log("✅ load_html() ejecutado")
        log("👀 ¿Ves un fondo ROJO con texto blanco?")
        current_test[0] = 1
    except Exception as e:
        log(f"❌ ERROR: {e}")

def test_styled():
    log("\n🧪 Test 2: HTML con gradiente")
    try:
        html_widget.load_html(html_simple_styled)
        log("✅ load_html() ejecutado")
        log("👀 ¿Ves un gradiente azul con '✅ HTML FUNCIONA'?")
        current_test[0] = 2
    except Exception as e:
        log(f"❌ ERROR: {e}")

def test_url():
    log("\n🧪 Test 3: Cargar desde archivo local")
    try:
        html_widget.load_file("mapa.html")
        log("✅ load_file('mapa.html') ejecutado")
        log("👀 ¿Ves un mapa de Leaflet?")
        current_test[0] = 3
    except Exception as e:
        log(f"❌ ERROR: {e}")

def test_blank():
    log("\n🔄 Limpiando - cargando página en blanco")
    try:
        html_widget.load_html("<html><body style='background:white;'></body></html>")
        log("✅ Página en blanco cargada")
    except Exception as e:
        log(f"❌ ERROR: {e}")

def report_issue():
    result = []
    result.append("REPORTE DE DIAGNÓSTICO\n")
    result.append("="*50)
    result.append(f"\n✅ tkinterweb instalado: SÍ")
    result.append(f"✅ HtmlFrame creado: SÍ")
    result.append(f"✅ load_html() ejecuta sin errores: SÍ")
    result.append(f"\n❌ PROBLEMA: El HTML no se renderiza visualmente")
    result.append(f"\nPOSIBLES CAUSAS:")
    result.append(f"1. Versión de tkinterweb incompatible con Python 3.14")
    result.append(f"2. Problema con tkhtml en Windows")
    result.append(f"3. Falta de soporte para ciertos estilos CSS")
    result.append(f"\nRECOMENDACIÓN:")
    result.append(f"Usar método alternativo: abrir HTML en navegador del sistema")
    
    msg = "\n".join(result)
    log("\n" + msg)
    messagebox.showinfo("Diagnóstico", msg)

# Botones de control
btn_frame = ttk.Frame(root)
btn_frame.pack(fill=tk.X, padx=10, pady=5)

ttk.Button(btn_frame, text="Test 1: Ultra Simple", command=test_ultra_simple).pack(side=tk.LEFT, padx=2)
ttk.Button(btn_frame, text="Test 2: Gradiente", command=test_styled).pack(side=tk.LEFT, padx=2)
ttk.Button(btn_frame, text="Test 3: Archivo", command=test_url).pack(side=tk.LEFT, padx=2)
ttk.Button(btn_frame, text="Limpiar", command=test_blank).pack(side=tk.LEFT, padx=2)
ttk.Button(btn_frame, text="📋 Reporte", command=report_issue).pack(side=tk.LEFT, padx=10)
ttk.Button(btn_frame, text="❌ Cerrar", command=root.destroy).pack(side=tk.RIGHT, padx=2)

log("\n" + "="*50)
log("📋 INSTRUCCIONES:")
log("1. Haz clic en 'Test 1: Ultra Simple'")
log("2. Observa si aparece un fondo ROJO debajo de esta área")
log("3. Si NO ves nada, haz clic en '📋 Reporte'")
log("="*50)

print("\n🪟 Ventana abierta - Ejecuta los tests con los botones")
print("="*60 + "\n")

root.mainloop()

print("✅ Test finalizado")
