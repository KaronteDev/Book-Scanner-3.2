#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test simple de cache de tiles - Verificación de optimización
"""

import time
from pathlib import Path
import io

print("\n" + "="*60)
print("⚡ TEST DE CACHE DE TILES OPTIMIZADO")
print("="*60)

try:
    from PIL import Image
    print("✅ PIL/Pillow disponible")
except ImportError:
    print("❌ PIL/Pillow NO disponible")
    exit(1)

try:
    import requests
    print("✅ requests disponible")
except ImportError:
    print("❌ requests NO disponible")
    exit(1)

from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuración
cache_dir = Path("output_scan") / ".map_cache"
cache_dir.mkdir(parents=True, exist_ok=True)

print(f"\n📂 Directorio de cache: {cache_dir.absolute()}")

# Limpiar cache de test
test_tiles = list(cache_dir.glob("tile_z14_x8199_*.png"))
for f in test_tiles:
    try:
        f.unlink()
    except:
        pass

print("🗑️ Cache de test limpiado\n")

# Tiles de ejemplo (Madrid, zoom 14)
test_tiles_coords = [
    (14, 8199, 6171),
    (14, 8199, 6172),
    (14, 8200, 6171),
    (14, 8200, 6172),
    (14, 8201, 6171),
    (14, 8201, 6172),
]

headers = {'User-Agent': 'GeoDocsScanner/32.3 (test)'}

def fetch_tile_old(z, x, y):
    """Método antiguo: descarga directa sin cache"""
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return Image.open(io.BytesIO(resp.content))
    except Exception:
        pass
    return None

def fetch_tile_new(z, x, y):
    """Método nuevo: con cache"""
    cache_file = cache_dir / f"tile_z{z}_x{x}_y{y}.png"
    
    # Si existe en cache
    if cache_file.exists():
        try:
            return Image.open(cache_file)
        except:
            cache_file.unlink()
    
    # Descargar
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            img = Image.open(io.BytesIO(resp.content))
            # Guardar en cache
            img.save(cache_file, 'PNG', optimize=True)
            return img
    except Exception:
        pass
    return None

# TEST 1: Método antiguo (sin cache, secuencial)
print("="*60)
print("TEST 1: Método ANTIGUO (secuencial, sin cache)")
print("="*60)

start = time.time()
count = 0
for z, x, y in test_tiles_coords:
    img = fetch_tile_old(z, x, y)
    if img:
        count += 1
elapsed_old = time.time() - start

print(f"✅ {count}/{len(test_tiles_coords)} tiles descargados")
print(f"⏱️ Tiempo: {elapsed_old:.2f} segundos\n")

# TEST 2: Método nuevo (con cache, primera vez)
print("="*60)
print("TEST 2: Método NUEVO - Primera carga (paralelo + cache)")
print("="*60)

start = time.time()
count = 0
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = [executor.submit(fetch_tile_new, z, x, y) for z, x, y in test_tiles_coords]
    for future in as_completed(futures):
        if future.result():
            count += 1
elapsed_new_first = time.time() - start

print(f"✅ {count}/{len(test_tiles_coords)} tiles descargados")
print(f"⏱️ Tiempo: {elapsed_new_first:.2f} segundos\n")

# TEST 3: Método nuevo (segunda carga, desde cache)
print("="*60)
print("TEST 3: Método NUEVO - Segunda carga (SOLO cache)")
print("="*60)

start = time.time()
count = 0
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = [executor.submit(fetch_tile_new, z, x, y) for z, x, y in test_tiles_coords]
    for future in as_completed(futures):
        if future.result():
            count += 1
elapsed_new_cached = time.time() - start

print(f"✅ {count}/{len(test_tiles_coords)} tiles cargados desde cache")
print(f"⏱️ Tiempo: {elapsed_new_cached:.2f} segundos\n")

# RESULTADOS
print("="*60)
print("📊 COMPARACIÓN DE RENDIMIENTO")
print("="*60)
print(f"Método antiguo (secuencial):     {elapsed_old:.3f}s")
print(f"Método nuevo 1ra vez (paralelo): {elapsed_new_first:.3f}s")
print(f"Método nuevo con cache:          {elapsed_new_cached:.3f}s")

print("\n🎯 MEJORAS:")
if elapsed_old > 0 and elapsed_new_first > 0:
    speedup_first = elapsed_old / elapsed_new_first
    print(f"   • Paralelización: {speedup_first:.1f}x más rápido")

if elapsed_old > 0 and elapsed_new_cached > 0:
    speedup_cached = elapsed_old / elapsed_new_cached
    improvement = ((elapsed_old - elapsed_new_cached) / elapsed_old) * 100
    print(f"   • Con cache: {speedup_cached:.1f}x más rápido ({improvement:.0f}% mejora)")

if elapsed_new_first > 0 and elapsed_new_cached > 0:
    cache_speedup = elapsed_new_first / elapsed_new_cached
    print(f"   • Cache vs descarga: {cache_speedup:.1f}x más rápido")

print("\n✨ CARACTERÍSTICAS:")
print("   ✅ Descarga paralela (6 conexiones)")
print("   ✅ Cache persistente en disco")
print("   ✅ Timeout reducido (5s)")
print("   ✅ Reuso entre sesiones")

# Mostrar tamaño del cache
cache_files = list(cache_dir.glob("*.png"))
if cache_files:
    total_size = sum(f.stat().st_size for f in cache_files)
    print(f"\n📦 Cache actual: {len(cache_files)} tiles, {total_size/1024:.1f} KB")

print("\n✅ Test completado")
print("="*60 + "\n")
