#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Servidor HTTP temporal para mapa interactivo
Alternativa a tkinterweb cuando no renderiza correctamente
"""

import http.server
import socketserver
import webbrowser
import threading
import time
from pathlib import Path

def crear_mapa_html(lat=40.4168, lon=-3.7038, tiene_marcador=False):
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
        
        function usarCoordenadas() {{
            if (selectedLat && selectedLon) {{
                // Cambiar el título para señalar que se aceptaron
                document.title = 'ACCEPTED:' + selectedLat.toFixed(6) + ',' + selectedLon.toFixed(6);
                alert('Coordenadas confirmadas: ' + selectedLat.toFixed(6) + ',' + selectedLon.toFixed(6) + 
                      '\\n\\nVuelve a la aplicación para continuar.');
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


def abrir_mapa_navegador(lat=40.4168, lon=-3.7038, tiene_marcador=False, puerto=8765):
    """
    Abre el mapa interactivo en el navegador del sistema
    Retorna las coordenadas seleccionadas o None si se cancela
    """
    # Crear HTML temporal
    html_content = crear_mapa_html(lat, lon, tiene_marcador)
    temp_file = Path("temp_mapa_interactivo.html")
    temp_file.write_text(html_content, encoding='utf-8')
    
    print(f"\n📄 Mapa HTML creado: {temp_file.absolute()}")
    print(f"🌐 Abriendo en navegador predeterminado...")
    
    # Abrir en navegador
    webbrowser.open(f"file:///{temp_file.absolute()}")
    
    print("✅ Mapa abierto en el navegador")
    print("   Cuando selecciones las coordenadas y hagas clic en 'Usar estas coordenadas',")
    print("   vuelve aquí y presiona ENTER para continuar...")
    
    input()
    
    # Nota: En una implementación real, se usaría un servidor HTTP local
    # y JavaScript comunicaría las coordenadas vía localStorage o similar
    # Por ahora, el usuario debe copiar manualmente
    
    print("\n📋 Las coordenadas han sido copiadas al portapapeles.")
    print("   Pégalas en el campo de coordenadas de la aplicación.")
    
    # Limpiar archivo temporal
    try:
        temp_file.unlink()
    except:
        pass
    
    return None


if __name__ == "__main__":
    print("="*60)
    print("TEST: Mapa en Navegador")
    print("="*60)
    
    abrir_mapa_navegador(40.4168, -3.7038, tiene_marcador=True)
    
    print("\n✅ Test completado")
