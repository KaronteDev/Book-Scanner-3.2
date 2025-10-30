#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

# Add src to Python path
src_dir = Path(__file__).resolve().parent / "src"
sys.path.append(str(src_dir))

# Constants
APP_NAME = "GeoDocs Scanner v12"
BASE_DIR = Path(__file__).resolve().parent
GLOBAL_DB = BASE_DIR / "geodocs_scanner.db"
CONFIG_PATH = BASE_DIR / "geodocs_config.json"
API_MAP_PATH = BASE_DIR / "geodocs_api_map.json"
IMG_EXTS = (".jpg",".jpeg",".png",".tif",".tiff",".bmp")

def main():
    # Importar dependencias locales
    from database.db import Database
    from api.geodocs import GeoDocsAPI
    
    # Asegurar que existe la base de datos
    db = Database(GLOBAL_DB)
    db.ensure_schema()
    
    # Inicializar API
    api = GeoDocsAPI(CONFIG_PATH, API_MAP_PATH)
    
    # Iniciar GUI
    import tkinter as tk
    from ui.main_window import MainWindow
    
    root = tk.Tk()
    app = MainWindow(root, db, api)
    root.mainloop()

if __name__ == '__main__':
    main()