#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

# Constants
APP_NAME = "GeoDocs Scanner v12"
BASE_DIR = Path(__file__).resolve().parent.parent.parent
GLOBAL_DB = BASE_DIR / "geodocs_scanner.db"
CONFIG_PATH = BASE_DIR / "geodocs_config.json"
API_MAP_PATH = BASE_DIR / "geodocs_api_map.json"
IMG_EXTS = (".jpg",".jpeg",".png",".tif",".tiff",".bmp")