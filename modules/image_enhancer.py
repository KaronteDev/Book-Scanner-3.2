
# (same as previous cell content omitted for brevity in retry)
from pathlib import Path
import json, math, time
try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None
DEFAULTS={"clahe_clip":3.0,"clahe_grid":8,"sharpen_amount":1.5,"sharpen_blur":3,"light_sigma":25,"use_white_balance":True}
def _apply_clahe(img, clip, grid):
    lab=cv2.cvtColor(img, cv2.COLOR_BGR2LAB); l,a,b=cv2.split(lab)
    clahe=cv2.createCLAHE(clipLimit=float(clip), tileGridSize=(int(grid),int(grid)))
    cl=clahe.apply(l); merged=cv2.merge((cl,a,b)); return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
def _light_compensation(img, sigma=25):
    gray=cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); blur=cv2.GaussianBlur(gray,(0,0),sigmaX=float(sigma))
    div=cv2.divide(gray, blur, scale=255); return cv2.cvtColor(div, cv2.COLOR_GRAY2BGR)
def _white_balance(img):
    if not hasattr(cv2,"xphoto"): return img
    try:
        wb=cv2.xphoto.createSimpleWB(); return wb.balanceWhite(img)
    except Exception: return img
def _sharpen(img, amount=1.5, k=3):
    blur=cv2.GaussianBlur(img,(int(k),int(k)),0); return cv2.addWeighted(img,float(amount),blur,-float(amount-1.0),0)
def _grid_for_dpi(dpi_x, dpi_y):
    if not dpi_x or not dpi_y: return DEFAULTS["clahe_grid"]
    px_per_10mm=(dpi_x/25.4)*10.0; grid=max(4, min(16, int(px_per_10mm//16) or 8)); return grid
def enhance_image(input_path, output_path, dpi_x=None, dpi_y=None, params=None):
    if cv2 is None: raise RuntimeError("OpenCV no disponible para image_enhancer")
    p=params.copy() if isinstance(params,dict) else DEFAULTS.copy()
    img=cv2.imread(str(input_path))
    if img is None: raise RuntimeError("No se pudo leer la imagen: "+str(input_path))
    grid=_grid_for_dpi(dpi_x,dpi_y)
    img=_apply_clahe(img,p.get("clahe_clip",3.0),grid)
    img=_light_compensation(img,p.get("light_sigma",25))
    if p.get("use_white_balance",True): img=_white_balance(img)
    img=_sharpen(img,p.get("sharpen_amount",1.5),p.get("sharpen_blur",3))
    out=Path(output_path); out.parent.mkdir(parents=True, exist_ok=True); import cv2 as _cv; _cv.imwrite(str(out), img)
    return str(out), {"method": f"CLAHE(grid={grid})+LightComp+WB+Sharpen"}
