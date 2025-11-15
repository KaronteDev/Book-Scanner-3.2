# -*- mode: python -*-

import os
from pathlib import Path

# PyInstaller spec file for GeoDocs Scanner Suite
# Run: pyinstaller geodocs_scanner.spec --clean --noconfirm

block_cipher = None

BASE_DIR = Path(SPECPATH)

assets_data = []
# Add icons folder
icons_dir = BASE_DIR / 'assets' / 'icons'
if icons_dir.exists():
    assets_data.append((str(icons_dir), 'assets/icons'))
# Add web viewer html
wv_dir = BASE_DIR / 'web_viewer'
if wv_dir.exists():
    for p in wv_dir.glob('*.html'):
        assets_data.append((str(p), 'web_viewer'))
# Add services that might have json configs
for cfg in ['ocr_config.json','rest_config.json','quality_scheduler.json','geodocs_config.json']:
    f = BASE_DIR / cfg
    if f.exists():
        assets_data.append((str(f), '.'))


a = Analysis(
    ['launcher.py'],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=assets_data,
    hiddenimports=[
        'tkinter','tkinter.ttk','tkinter.messagebox','PIL._imaging','pytesseract','pyttsx3','lxml.etree'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tests','htmlcov'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='GeoDocsScanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(icons_dir/'app.ico') if (icons_dir/'app.ico').exists() else None,
)
