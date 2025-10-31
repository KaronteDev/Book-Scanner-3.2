#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script de prueba para verificar instancia única"""
import subprocess
import time
import sys

print("Iniciando primera instancia...")
# Iniciar primera instancia en background
proc1 = subprocess.Popen([sys.executable, "main.py"], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)

# Esperar un momento para que se inicie
time.sleep(2)

print("Intentando iniciar segunda instancia...")
# Intentar iniciar segunda instancia
proc2 = subprocess.Popen([sys.executable, "main.py"], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)

# Esperar a que termine
time.sleep(2)

# Verificar el resultado
if proc2.poll() is not None:
    print(f"✓ Segunda instancia fue bloqueada correctamente (exit code: {proc2.poll()})")
else:
    print("✗ Segunda instancia se está ejecutando (no debería)")
    proc2.terminate()

# Cerrar primera instancia
print("Cerrando primera instancia...")
proc1.terminate()
proc1.wait()

print("\nPrueba completada.")
