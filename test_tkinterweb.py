#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar que tkinterweb está funcionando
"""
import tkinter as tk
from tkinter import ttk

try:
    from tkinterweb import HtmlFrame
    HAS_TKINTERWEB = True
    print("✓ tkinterweb importado correctamente")
    print(f"✓ HAS_TKINTERWEB = {HAS_TKINTERWEB}")
except Exception as e:
    HAS_TKINTERWEB = False
    print(f"✗ Error importando tkinterweb: {e}")
    print(f"✗ HAS_TKINTERWEB = {HAS_TKINTERWEB}")

def test_basic_map():
    """Prueba básica de un mapa Leaflet"""
    root = tk.Tk()
    root.title("Test Mapa Leaflet - tkinterweb")
    root.geometry("800x600")
    
    if not HAS_TKINTERWEB:
        ttk.Label(root, text="tkinterweb NO está instalado", 
                 font=("", 14, "bold"), foreground="red").pack(pady=50)
        ttk.Label(root, text="Ejecuta: pip install tkinterweb").pack()
    else:
        ttk.Label(root, text="✓ tkinterweb está instalado y funcionando", 
                 font=("", 14, "bold"), foreground="green").pack(pady=10)
        
        # HTML simple para probar primero
        html_simple = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <style>
        body { 
            font-family: Arial; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
        }
        h1 { font-size: 48px; margin-top: 100px; }
        p { font-size: 20px; }
    </style>
</head>
<body>
    <h1>✅ TkinterWeb Funciona</h1>
    <p>El HTML se está renderizando correctamente</p>
    <p>Si ves esto, tkinterweb está operativo</p>
</body>
</html>
"""
        
        # HTML Leaflet completo
        html_leaflet = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""/>
    <style>
        html, body { height: 100%; margin: 0; padding: 0; }
        #map { height: 100%; width: 100%; }
        #status { 
            position: absolute; 
            top: 10px; 
            left: 50%; 
            transform: translateX(-50%);
            background: white; 
            padding: 10px 20px; 
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            z-index: 1000;
            font-family: Arial;
        }
    </style>
</head>
<body>
    <div id="status">⏳ Cargando Leaflet...</div>
    <div id="map"></div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
    <script>
        try {
            document.getElementById('status').innerHTML = '🗺️ Iniciando mapa...';
            var map = L.map('map').setView([40.4168, -3.7038], 13);
            
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { 
                maxZoom: 19, 
                attribution: '&copy; OpenStreetMap' 
            }).addTo(map);
            
            var marker = L.marker([40.4168, -3.7038]).addTo(map);
            marker.bindPopup("<b>¡Madrid!</b><br>Mapa funcionando correctamente.").openPopup();
            
            document.getElementById('status').innerHTML = '✅ Mapa cargado';
            setTimeout(function() {
                document.getElementById('status').style.display = 'none';
            }, 2000);
        } catch(e) {
            document.getElementById('status').innerHTML = '❌ Error: ' + e.message;
            document.getElementById('status').style.background = '#ff4444';
            document.getElementById('status').style.color = 'white';
        }
    </script>
</body>
</html>
"""
        
        frame = HtmlFrame(root, horizontal_scrollbar=False)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        print("\n📋 Cargando HTML con Leaflet...")
        
        # Usar html_leaflet en lugar de html
        frame.load_html(html_leaflet)
        print("✓ HTML cargado en el frame")
        
        ttk.Label(root, text="Si ves un mapa con un marcador en Madrid, ¡todo funciona! 🗺️").pack(pady=5)
    
    ttk.Button(root, text="Cerrar Test", command=root.destroy, width=20).pack(pady=10)
    
    print("\n" + "="*60)
    print("🪟 VENTANA ABIERTA")
    print("   - Deberías ver un mapa de Madrid con un marcador")
    print("   - Puedes hacer zoom con la rueda del ratón")
    print("   - Arrastra el mapa para moverte")
    print("   - Haz clic en 'Cerrar Test' cuando termines")
    print("="*60)
    
    root.mainloop()
    
    print("\n✓ Test finalizado - La ventana se cerró correctamente")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TEST DE TKINTERWEB")
    print("="*60 + "\n")
    
    test_basic_map()
    
    print("\n" + "="*60)
    print("✅ Test completado - Si viste el mapa, todo funciona correctamente")
    print("="*60 + "\n")
