#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Abrir mapa interactivo (Leaflet) en el navegador del sistema y devolver
las coordenadas seleccionadas a la aplicación vía un servidor HTTP local.

Alternativa ligera y robusta para entornos donde no se puede embeber
un navegador (tkinterweb/cef/pywebview).
"""

import json
import webbrowser
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

def crear_mapa_html(lat=40.4168, lon=-3.7038, tiene_marcador=False, server_port=8765):
    """Genera HTML con Leaflet para el mapa interactivo"""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Mapa Interactivo - GeoDocs Scanner</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" 
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" 
          crossorigin=""/>
    <style>
        html, body {{
            height: 100%;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
        
        #map {{
            height: 100%;
            width: 100%;
            cursor: crosshair;
        }}
        
        #coords-display {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: white;
            padding: 10px 15px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            z-index: 1000;
            font-size: 14px;
            min-width: 200px;
        }}
        
        #coords-display strong {{
            color: #2c5aa0;
        }}
        
        .control-panel {{
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.4);
            z-index: 1000;
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        
        .control-panel button {{
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: background 0.3s;
        }}
        
        .control-panel button:hover {{
            background: #45a049;
        }}
        
        .control-panel button.secondary {{
            background: #2196F3;
        }}
        
        .control-panel button.secondary:hover {{
            background: #0b7dda;
        }}
        
        #status {{
            color: #666;
            font-size: 12px;
            margin-right: 10px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="coords-display">
        <div>📍 <strong>Coordenadas seleccionadas:</strong></div>
        <div id="coords-text" style="margin-top: 5px;">Click en el mapa para seleccionar</div>
    </div>
    
    <div class="control-panel">
        <span id="status">Haz click en el mapa o arrastra el marcador</span>
        <button class="secondary" onclick="copiarCoordenadas()">📋 Copiar</button>
        <button onclick="usarCoordenadas()">✅ Usar estas coordenadas</button>
    </div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" 
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" 
            crossorigin=""></script>
    <script>
        // Inicializar mapa
        var map = L.map('map').setView([{lat}, {lon}], 14);
        
        // Capa de teselas
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19
        }}).addTo(map);
        
        // Marcador
        var marker = null;
        var selectedLat = null;
        var selectedLon = null;
        
        function setMarker(lat, lon) {{
            selectedLat = lat;
            selectedLon = lon;
            
            // Remover marcador anterior
            if (marker) {{
                map.removeLayer(marker);
            }}
            
            // Crear nuevo marcador arrastrable
            marker = L.marker([lat, lon], {{
                draggable: true,
                autoPan: true
            }}).addTo(map);
            
            // Actualizar al arrastrar
            marker.on('dragend', function(e) {{
                var pos = e.target.getLatLng();
                selectedLat = pos.lat;
                selectedLon = pos.lng;
                updateDisplay();
            }});
            
            updateDisplay();
        }}
        
        function updateDisplay() {{
            var coords = selectedLat.toFixed(6) + ', ' + selectedLon.toFixed(6);
            document.getElementById('coords-text').innerHTML = '<strong style="color:#2c5aa0;">' + coords + '</strong>';
            document.title = 'COORDS:' + coords;  // Para que Python pueda leerlo
        }}
        
        // Click en el mapa
        map.on('click', function(e) {{
            setMarker(e.latlng.lat, e.latlng.lng);
        }});
        
        // Funciones de botones
        function copiarCoordenadas() {{
            if (selectedLat && selectedLon) {{
                var coords = selectedLat.toFixed(6) + ',' + selectedLon.toFixed(6);
                navigator.clipboard.writeText(coords).then(function() {{
                    var status = document.getElementById('status');
                    status.innerText = '✅ Coordenadas copiadas al portapapeles';
                    status.style.color = '#4CAF50';
                    setTimeout(function() {{
                        status.innerText = 'Haz click en el mapa o arrastra el marcador';
                        status.style.color = '#666';
                    }}, 2000);
                }});
            }} else {{
                alert('Primero selecciona un punto en el mapa');
            }}
        }}
        
        async function usarCoordenadas() {{
            if (selectedLat && selectedLon) {{
                const coords = selectedLat.toFixed(6) + ',' + selectedLon.toFixed(6);
                try {{
                    const res = await fetch('http://localhost:{server_port}/coords', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ coords }})
                    }});
                    if (res.ok) {{
                        document.getElementById('status').innerText = '✅ Coordenadas enviadas a la aplicación';
                        setTimeout(() => window.close(), 1200);
                    }} else {{
                        alert('No se pudieron enviar las coordenadas. Código ' + res.status);
                    }}
                }} catch (e) {{
                    alert('No se pudo contactar con la aplicación. ¿Está abierta?');
                }}
            }} else {{
                alert('Primero selecciona un punto en el mapa');
            }}
        }}
        
        // Si hay marcador inicial, colocarlo
        {'setMarker(' + str(lat) + ',' + str(lon) + ');' if tiene_marcador else ''}
    </script>
</body>
</html>
"""
    return html

class _CoordServer:
    """Servidor HTTP que recibe un POST con las coordenadas."""
    def __init__(self, port=8765):
        self.port = port
        self.result = None
        self._event = threading.Event()

        parent = self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != '/coords':
                    self.send_response(404); self.end_headers(); return
                try:
                    length = int(self.headers.get('Content-Length') or '0')
                    data = self.rfile.read(length).decode('utf-8')
                    payload = json.loads(data)
                    coords = str(payload.get('coords') or '')
                    parent.result = coords
                    parent._event.set()
                    self.send_response(200); self.end_headers()
                except Exception:
                    self.send_response(400); self.end_headers()

            def log_message(self, format, *args):
                # Silenciar logs
                return

        self.httpd = ThreadingHTTPServer(('localhost', self.port), Handler)

    def start(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def wait(self, timeout=120):
        self._event.wait(timeout)
        try:
            self.httpd.shutdown()
        except Exception:
            pass
        return self.result

def abrir_mapa_navegador(lat=40.4168, lon=-3.7038, tiene_marcador=False, puerto=8765, timeout=120):
    """
    Abre el mapa en el navegador y espera las coordenadas confirmadas.
    Retorna 'lat,lon' o None si expira el timeout.
    """
    # Iniciar servidor de callback
    srv = _CoordServer(port=puerto)
    srv.start()

    # Crear HTML temporal apuntando al puerto
    html_content = crear_mapa_html(lat, lon, tiene_marcador, server_port=puerto)
    temp_file = Path("temp_mapa_interactivo.html")
    temp_file.write_text(html_content, encoding='utf-8')

    # Abrir navegador
    webbrowser.open(f"file:///{temp_file.absolute()}")

    # Esperar resultado
    coords = srv.wait(timeout=timeout)

    # Limpiar temporal
    try:
        temp_file.unlink()
    except Exception:
        pass

    return coords


if __name__ == "__main__":
    print("="*60)
    print("TEST: Mapa en Navegador")
    print("="*60)
    
    abrir_mapa_navegador(40.4168, -3.7038, tiene_marcador=True)
    
    print("\n✅ Test completado")
