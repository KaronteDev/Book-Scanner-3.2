#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de CEFPython con Leaflet - Navegador embebido Chromium
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

print("\n" + "="*60)
print("🌐 TEST DE CEFPYTHON CON LEAFLET")
print("="*60)

try:
    from cefpython3 import cefpython as cef
    print("✅ cefpython3 importado correctamente")
except ImportError as e:
    print(f"❌ Error: {e}")
    print("   Instala con: pip install cefpython3")
    sys.exit(1)

# HTML con Leaflet
HTML_LEAFLET = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Mapa Interactivo - CEFPython</title>
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
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
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
        console.log('Iniciando Leaflet...');
        
        try {
            document.getElementById('status').innerHTML = '🗺️ Inicializando mapa...';
            
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
            
            // Marcador arrastrable
            var marker = L.marker([40.4168, -3.7038], {draggable: true}).addTo(map);
            marker.bindPopup("<b>¡Madrid!</b><br>Puerta del Sol<br><small>Arrastra el marcador</small>").openPopup();
            console.log('Marcador añadido');
            
            marker.on('dragend', function(e) {
                var pos = marker.getLatLng();
                console.log('Marcador movido a:', pos);
                marker.setPopupContent(
                    '<b>Nueva posición</b><br>' + 
                    'Lat: ' + pos.lat.toFixed(6) + '<br>' +
                    'Lng: ' + pos.lng.toFixed(6)
                ).openPopup();
            });
            
            document.getElementById('status').innerHTML = '✅ Mapa cargado correctamente';
            
            setTimeout(function() {
                document.getElementById('status').style.display = 'none';
            }, 3000);
            
            console.log('Mapa completamente inicializado');
            
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

class BrowserFrame(tk.Frame):
    """Frame que contiene el navegador CEF embebido"""
    
    def __init__(self, parent, url=None, html=None):
        tk.Frame.__init__(self, parent)
        self.browser = None
        self.url = url
        self.html = html
        
        # Configuración de CEF
        sys.excepthook = cef.ExceptHook
        settings = {
            "debug": False,
            "log_severity": cef.LOGSEVERITY_INFO,
            "log_file": "cef_debug.log",
        }
        cef.Initialize(settings)
        
        self.bind("<Configure>", self.on_configure)
        self.bind("<FocusIn>", self.on_focus_in)
        
    def embed_browser(self):
        """Embeber el navegador en el frame"""
        window_info = cef.WindowInfo()
        rect = [0, 0, self.winfo_width(), self.winfo_height()]
        window_info.SetAsChild(self.get_window_handle(), rect)
        
        if self.html:
            # Cargar HTML directo
            self.browser = cef.CreateBrowserSync(window_info, url="data:text/html," + self.html)
        elif self.url:
            # Cargar URL
            self.browser = cef.CreateBrowserSync(window_info, url=self.url)
        else:
            self.browser = cef.CreateBrowserSync(window_info, url="about:blank")
    
    def get_window_handle(self):
        """Obtener handle de la ventana para Windows"""
        return self.winfo_id()
    
    def on_configure(self, event):
        """Redimensionar el navegador"""
        if self.browser:
            self.browser.SetBounds(0, 0, event.width, event.height)
    
    def on_focus_in(self, event):
        """Dar foco al navegador"""
        if self.browser:
            self.browser.SetFocus(True)
    
    def destroy(self):
        """Limpiar recursos"""
        if self.browser:
            self.browser.CloseBrowser(True)
        tk.Frame.destroy(self)

def main():
    print("✅ Inicializando ventana Tkinter...")
    
    root = tk.Tk()
    root.title("Test CEFPython + Leaflet")
    root.geometry("900x700")
    
    # Etiqueta de información
    info_frame = ttk.Frame(root)
    info_frame.pack(fill=tk.X, padx=10, pady=10)
    
    ttk.Label(info_frame, 
              text="🗺️ Mapa de Madrid con Leaflet (CEFPython/Chromium)", 
              font=("", 12, "bold")).pack()
    
    ttk.Label(info_frame, 
              text="Deberías ver un mapa interactivo con un marcador arrastrable", 
              font=("", 9)).pack()
    
    # Frame del navegador
    print("✅ Creando navegador embebido...")
    browser_frame = BrowserFrame(root, html=HTML_LEAFLET)
    browser_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    
    # Botón de cierre
    btn_frame = ttk.Frame(root)
    btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    ttk.Label(btn_frame, text="Estado: ").pack(side=tk.LEFT)
    status_label = ttk.Label(btn_frame, text="Inicializando...", foreground="blue")
    status_label.pack(side=tk.LEFT, padx=5)
    
    ttk.Button(btn_frame, text="❌ Cerrar", command=root.quit).pack(side=tk.RIGHT)
    
    def on_ready():
        """Callback cuando el frame está listo"""
        browser_frame.embed_browser()
        status_label.config(text="✅ Navegador cargado", foreground="green")
        print("✅ Navegador embebido correctamente")
        print("\n" + "="*60)
        print("🪟 VENTANA ABIERTA")
        print("   - Deberías ver un mapa interactivo de Madrid")
        print("   - Puedes hacer zoom con la rueda del ratón")
        print("   - Arrastra el mapa para moverte")
        print("   - Arrastra el marcador rojo para cambiar posición")
        print("="*60 + "\n")
    
    # Esperar a que el frame esté renderizado
    root.after(100, on_ready)
    
    # Timer de CEF
    def message_loop():
        cef.MessageLoopWork()
        root.after(10, message_loop)
    
    root.after(10, message_loop)
    
    # Cleanup al cerrar
    def on_closing():
        if browser_frame.browser:
            browser_frame.browser.CloseBrowser(True)
        cef.Shutdown()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    print("✅ Entrando en mainloop...")
    root.mainloop()
    
    print("\n✅ Test finalizado correctamente")

if __name__ == "__main__":
    print("\nNOTA: CEFPython usa Chromium embebido, por lo que:")
    print("   • Renderiza HTML/CSS/JS perfectamente")
    print("   • Soporta Leaflet sin problemas")
    print("   • Es más pesado que tkinterweb (~100MB)")
    print("   • Requiere más memoria\n")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
