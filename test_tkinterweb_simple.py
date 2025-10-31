#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test simple de tkinterweb - Diagnóstico paso a paso
"""

import tkinter as tk
from tkinter import ttk

print("\n" + "="*60)
print("🧪 TEST DIAGNÓSTICO DE TKINTERWEB")
print("="*60)

# Paso 1: Verificar importación
try:
    from tkinterweb import HtmlFrame
    print("\n✅ Paso 1: tkinterweb importado correctamente")
except ImportError as e:
    print(f"\n❌ ERROR: No se pudo importar tkinterweb: {e}")
    exit(1)

# Paso 2: Crear ventana
print("✅ Paso 2: Creando ventana Tkinter...")
root = tk.Tk()
root.title("Test TkinterWeb - Diagnóstico")
root.geometry("900x700")

# Paso 3: Crear frame de información
info_frame = ttk.Frame(root)
info_frame.pack(fill=tk.X, padx=10, pady=10)

status_label = ttk.Label(info_frame, text="⏳ Inicializando...", 
                         font=("", 12, "bold"))
status_label.pack()

# Paso 4: Crear HtmlFrame
print("✅ Paso 3: Creando HtmlFrame...")
html_frame = HtmlFrame(root, messages_enabled=True)
html_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

# Paso 5: HTML de prueba MUY SIMPLE
html_test1 = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <style>
        body { 
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            padding: 50px;
        }
        h1 { font-size: 48px; margin: 0; }
        p { font-size: 24px; }
        .box {
            background: rgba(255,255,255,0.2);
            padding: 20px;
            border-radius: 10px;
            margin: 20px auto;
            max-width: 600px;
        }
    </style>
</head>
<body>
    <h1>✅ HTML Renderizando</h1>
    <div class="box">
        <p>Si ves este mensaje con gradiente de color,</p>
        <p><strong>TkinterWeb está funcionando correctamente</strong></p>
    </div>
    <p>Haz clic en "Test Leaflet" para probar el mapa</p>
</body>
</html>
"""

# HTML con Leaflet
html_leaflet = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" 
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" 
          crossorigin=""/>
    <style>
        html, body { height: 100%; margin: 0; padding: 0; }
        #map { height: 100%; width: 100%; }
        .status { 
            position: absolute; 
            top: 10px; 
            left: 50%; 
            transform: translateX(-50%);
            background: white; 
            padding: 10px 20px; 
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            z-index: 1000;
            font-family: Arial, sans-serif;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div id="status" class="status">⏳ Cargando mapa...</div>
    <div id="map"></div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" 
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" 
            crossorigin=""></script>
    <script>
        console.log('Iniciando script de Leaflet...');
        
        try {
            document.getElementById('status').innerHTML = '🗺️ Inicializando mapa...';
            console.log('Creando mapa...');
            
            // Madrid, España
            var map = L.map('map').setView([40.4168, -3.7038], 13);
            console.log('Mapa creado');
            
            document.getElementById('status').innerHTML = '📥 Descargando teselas...';
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { 
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                maxZoom: 19,
                subdomains: ['a','b','c']
            }).addTo(map);
            console.log('Capa de teselas añadida');
            
            // Marcador
            var marker = L.marker([40.4168, -3.7038], {draggable: true}).addTo(map);
            marker.bindPopup("<b>¡Madrid!</b><br>Puerta del Sol<br>Lat: 40.4168, Lng: -3.7038").openPopup();
            console.log('Marcador añadido');
            
            document.getElementById('status').innerHTML = '✅ Mapa cargado correctamente';
            
            setTimeout(function() {
                document.getElementById('status').style.display = 'none';
            }, 3000);
            
        } catch(error) {
            console.error('Error:', error);
            document.getElementById('status').innerHTML = '❌ Error: ' + error.message;
            document.getElementById('status').style.background = '#ff4444';
            document.getElementById('status').style.color = 'white';
        }
    </script>
</body>
</html>
"""

# Control de qué mostrar
current_view = [1]  # 1=simple, 2=leaflet

def load_simple():
    print("\n🔄 Cargando HTML simple...")
    status_label.config(text="📄 HTML Simple")
    html_frame.load_html(html_test1)
    btn_simple.config(state=tk.DISABLED)
    btn_leaflet.config(state=tk.NORMAL)
    current_view[0] = 1

def load_leaflet():
    print("\n🔄 Cargando mapa Leaflet...")
    status_label.config(text="🗺️ Mapa Leaflet (puede tardar unos segundos...)")
    html_frame.load_html(html_leaflet)
    btn_leaflet.config(state=tk.DISABLED)
    btn_simple.config(state=tk.NORMAL)
    current_view[0] = 2
    root.after(3000, lambda: status_label.config(text="🗺️ Mapa Leaflet"))

# Botones
btn_frame = ttk.Frame(root)
btn_frame.pack(fill=tk.X, padx=10, pady=5)

btn_simple = ttk.Button(btn_frame, text="▶ Test HTML Simple", command=load_simple)
btn_simple.pack(side=tk.LEFT, padx=5)

btn_leaflet = ttk.Button(btn_frame, text="▶ Test Leaflet", command=load_leaflet)
btn_leaflet.pack(side=tk.LEFT, padx=5)

ttk.Button(btn_frame, text="❌ Cerrar", command=root.destroy).pack(side=tk.RIGHT, padx=5)

# Cargar HTML simple por defecto
print("✅ Paso 4: Cargando HTML de prueba...")
load_simple()

print("\n" + "="*60)
print("🪟 VENTANA ABIERTA")
print("   1. Deberías ver un gradiente morado con texto blanco")
print("   2. Haz clic en 'Test Leaflet' para probar el mapa")
print("   3. El mapa puede tardar 5-10 segundos en cargar")
print("="*60 + "\n")

root.mainloop()

print("\n✅ Test finalizado correctamente")
