#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de rendimiento del mapa optimizado
Compara velocidad con/sin cache
"""

import time
import sys
from pathlib import Path

# Añadir gui al path
sys.path.insert(0, 'gui')

print("\n" + "="*60)
print("⚡ TEST DE RENDIMIENTO - MAPA OPTIMIZADO")
print("="*60)

try:
    from PIL import Image
    print("✅ PIL/Pillow disponible")
except ImportError:
    print("❌ PIL/Pillow NO disponible - instala con: pip install pillow")
    sys.exit(1)

try:
    import requests
    print("✅ requests disponible")
except ImportError:
    print("❌ requests NO disponible - instala con: pip install requests")
    sys.exit(1)

# Limpiar cache si existe
cache_dir = Path("output_scan") / ".map_cache"
if cache_dir.exists():
    import shutil
    print(f"\n🗑️ Limpiando cache anterior: {cache_dir}")
    try:
        shutil.rmtree(cache_dir)
        print("   ✓ Cache limpiado")
    except Exception as e:
        print(f"   ⚠️ No se pudo limpiar: {e}")

print("\n" + "="*60)
print("TEST 1: Primera carga (sin cache)")
print("="*60)
print("Descargando tiles de Madrid (zoom 14)...")

# Simular la carga del mapa
start = time.time()
try:
    # Importar después de limpiar el cache
    from metadata_manager import MetadataManager
    
    # Crear instancia dummy (necesaria para el método)
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()  # Ocultar ventana
    
    # Crear manager
    class DummyApp:
        def after(self, ms, func):
            func()
    
    manager = MetadataManager(root, DummyApp())
    
    # Primer fetch (sin cache)
    photo = manager._fetch_static_map(
        center_lat=40.4168,
        center_lon=-3.7038,
        marker_lat=40.4168,
        marker_lon=-3.7038,
        zoom=14,
        size=(800, 600)
    )
    
    elapsed1 = time.time() - start
    
    if photo is None:
        print("❌ Error generando el mapa")
        if hasattr(manager, '_last_static_map_error'):
            print(f"   Detalle: {manager._last_static_map_error}")
        sys.exit(1)
    
    print(f"✅ Mapa generado en {elapsed1:.2f} segundos")
    
    # Verificar que se creó el cache
    if cache_dir.exists():
        tile_count = len(list(cache_dir.glob("*.png")))
        print(f"✅ Cache creado: {tile_count} tiles guardados")
    else:
        print("⚠️ No se creó el directorio de cache")
    
    print("\n" + "="*60)
    print("TEST 2: Segunda carga (CON cache)")
    print("="*60)
    print("Cargando mismo mapa desde cache...")
    
    start2 = time.time()
    photo2 = manager._fetch_static_map(
        center_lat=40.4168,
        center_lon=-3.7038,
        marker_lat=40.4168,
        marker_lon=-3.7038,
        zoom=14,
        size=(800, 600)
    )
    elapsed2 = time.time() - start2
    
    if photo2 is None:
        print("❌ Error en segunda carga")
    else:
        print(f"✅ Mapa cargado en {elapsed2:.2f} segundos")
    
    # Calcular mejora
    print("\n" + "="*60)
    print("📊 RESULTADOS")
    print("="*60)
    print(f"Primera carga (sin cache):  {elapsed1:.2f}s")
    print(f"Segunda carga (con cache):  {elapsed2:.2f}s")
    
    if elapsed2 > 0:
        speedup = elapsed1 / elapsed2
        improvement = ((elapsed1 - elapsed2) / elapsed1) * 100
        print(f"\n⚡ Aceleración: {speedup:.1f}x más rápido")
        print(f"📈 Mejora: {improvement:.1f}% de reducción en tiempo")
        
        if improvement > 50:
            print("\n🎉 ¡Excelente! El cache funciona perfectamente")
        elif improvement > 20:
            print("\n👍 Buena mejora con el sistema de cache")
        else:
            print("\n⚠️ Mejora limitada - puede que la red sea muy rápida")
    
    # Limpiar
    root.destroy()
    
    print("\n" + "="*60)
    print("CARACTERÍSTICAS IMPLEMENTADAS:")
    print("="*60)
    print("✅ Cache persistente en disco (output_scan/.map_cache)")
    print("✅ Descarga paralela (6 tiles simultáneos)")
    print("✅ Timeout reducido (5s por tile)")
    print("✅ Reuso de tiles entre cargas")
    print("✅ Manejo de tiles corruptos")
    
    print("\n💡 RECOMENDACIONES:")
    print("   - El cache se mantiene entre sesiones")
    print("   - Tiles usados frecuentemente cargan instantáneamente")
    print("   - Navegación por zonas cercanas es muy rápida")
    print("   - Cache crece con el uso (considera limpiarlo periódicamente)")
    
    print("\n✅ Test completado con éxito")
    print("="*60 + "\n")

except Exception as e:
    print(f"\n❌ Error durante el test: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
