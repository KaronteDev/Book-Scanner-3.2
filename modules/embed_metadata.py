
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
embed_metadata.py — Embed DPI and technical tags into images (JPEG/TIFF) using Pillow.
"""
from pathlib import Path
def embed_dpi(path: str, dpi_x: float, dpi_y: float, desc: str = "GeoDocs Scanner v30.5"):
    try:
        from PIL import Image, TiffImagePlugin
    except Exception:
        return False, "Pillow no disponible"
    p = Path(path)
    try:
        im = Image.open(str(p))
        dpi = (float(dpi_x or 300.0), float(dpi_y or 300.0))
        if p.suffix.lower() in [".tif", ".tiff"]:
            info = TiffImagePlugin.ImageFileDirectory_v2()
            info[270] = desc
            info[271] = "GeoDocs Research Suite"
            info[272] = "Scanner OCR pipeline calibrated"
            info[305] = "GeoDocs v30.5"
            im.save(str(p), tiffinfo=info, dpi=dpi)
        else:
            im.save(str(p), dpi=dpi)
        return True, "DPI incrustado"
    except Exception as ex:
        return False, str(ex)
