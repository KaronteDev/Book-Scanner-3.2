
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, math
import numpy as np
import cv2
from PIL import Image

try:
    import pytesseract
    TESS_AVAILABLE = True
except Exception:
    TESS_AVAILABLE = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


def imread_auto(path):
    import numpy as np
    data = np.fromfile(path, dtype=np.uint8)
    if data is None or data.size == 0:
        return None
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return img

def imwrite_auto(path, bgr, quality=95):
    ext = os.path.splitext(path)[1].lower()
    if ext not in [".jpg",".jpeg",".png",".tif",".tiff",".bmp"]:
        ext = ".jpg"
    params = []
    if ext in [".jpg",".jpeg"]:
        params = [cv2.IMWRITE_JPEG_QUALITY, int(quality)]
    elif ext == ".png":
        params = [cv2.IMWRITE_PNG_COMPRESSION, 3]
    ok, buf = cv2.imencode(ext, bgr, params)
    if not ok:
        raise RuntimeError("No se pudo codificar la imagen")
    with open(path, "wb") as f:
        f.write(buf.tobytes())

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts):
    rect = order_points(np.array(pts, dtype="float32"))
    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))
    dst = np.array([[0,0],[maxWidth-1,0],[maxWidth-1,maxHeight-1],[0,maxHeight-1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight), flags=cv2.INTER_CUBIC)
    return warped

def preprocess_for_edges(bgr, blur=5):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (blur, blur), 0)
    v = np.median(gray)
    lower = int(max(0, (1.0 - 0.33) * v))
    upper = int(min(255, (1.0 + 0.33) * v))
    edges = cv2.Canny(gray, lower, upper)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    edges = cv2.dilate(edges, kernel, iterations=2)
    return edges

def largest_page_contour(edged, min_area=0.15):
    h, w = edged.shape[:2]
    area_img = w * h
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_poly, best_area = None, 0
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area * area_img: continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and area > best_area:
            best_poly, best_area = approx.reshape(-1,2), area
    if best_poly is None and len(contours) > 0:
        c = max(contours, key=cv2.contourArea)
        hull = cv2.convexHull(c)
        rect = cv2.minAreaRect(hull.astype(np.float32))
        box = cv2.boxPoints(rect)
        best_poly = box.astype(np.float32)
    return best_poly

def detect_gutter_x(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    mag = cv2.convertScaleAbs(np.abs(gx))
    inv = 255 - mag
    proj = inv.mean(axis=0)
    w = bgr.shape[1]
    center = w // 2
    bias = np.linspace(1.3, 1.0, center)
    bias = np.concatenate([bias, bias[::-1]])[:w]
    score = proj * bias
    x = int(np.argmin(score))
    win = max(10, w//40)
    lo = max(0, x - win)
    hi = min(w-1, x + win)
    x_local = lo + int(np.argmin(score[lo:hi+1]))
    return x_local

def cylindrical_dewarp(bgr, strength=0.22, center_x=None):
    h, w = bgr.shape[:2]
    if center_x is None:
        center_x = detect_gutter_x(bgr)
    R = max(1.0, w / (2 * math.pi) / max(1e-3, strength))
    xs = np.linspace(0, w - 1, w, dtype=np.float32)
    ys = np.linspace(0, h - 1, h, dtype=np.float32)
    x_grid, y_grid = np.meshgrid(xs, ys)
    x_rel = x_grid - center_x
    src_x = center_x + R * np.tan((x_rel) / R)
    src_y = y_grid
    src_x = np.clip(src_x, 0, w - 1).astype(np.float32)
    src_y = np.clip(src_y, 0, h - 1).astype(np.float32)
    return cv2.remap(bgr, src_x, src_y, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def _tps_kernel(r2):
    with np.errstate(divide='ignore', invalid='ignore'):
        k = r2 * np.where(r2==0, 0, np.log(r2))
    return k

def tps_warp(bgr, src_pts, dst_pts):
    h, w = bgr.shape[:2]
    src_pts = np.asarray(src_pts, dtype=np.float32)
    dst_pts = np.asarray(dst_pts, dtype=np.float32)
    n = src_pts.shape[0]
    if n < 3:
        return bgr.copy()
    P = np.hstack([np.ones((n,1), dtype=np.float32), src_pts])
    diff = src_pts[:,None,:] - src_pts[None,:,:]
    r2 = (diff**2).sum(axis=2) + 1e-20
    K = _tps_kernel(r2).astype(np.float32)
    zeros = np.zeros((3,3), dtype=np.float32)
    L = np.vstack([np.hstack([K, P]), np.hstack([P.T, zeros])])
    Vx = np.vstack([dst_pts[:,0:1], np.zeros((3,1), dtype=np.float32)])
    Vy = np.vstack([dst_pts[:,1:2], np.zeros((3,1), dtype=np.float32)])
    try:
        coeffs_x = np.linalg.solve(L, Vx)
        coeffs_y = np.linalg.solve(L, Vy)
    except np.linalg.LinAlgError:
        L[:n,:n] += np.eye(n, dtype=np.float32)*1e-6
        coeffs_x = np.linalg.solve(L, Vx)
        coeffs_y = np.linalg.solve(L, Vy)
    w_x, a_x = coeffs_x[:n], coeffs_x[n:]
    w_y, a_y = coeffs_y[:n], coeffs_y[n:]
    xs = np.arange(0, w, 1, dtype=np.float32)
    ys = np.arange(0, h, 1, dtype=np.float32)
    X, Y = np.meshgrid(xs, ys)
    XY = np.stack([X, Y], axis=-1).reshape(-1,2)
    diff_all = XY[:,None,:] - src_pts[None,:,:]
    r2_all = (diff_all**2).sum(axis=2) + 1e-20
    U = _tps_kernel(r2_all)
    fx = (a_x[0] + a_x[1]*XY[:,0:1] + a_x[2]*XY[:,1:2] + (U @ w_x)).reshape(h, w).astype(np.float32)
    fy = (a_y[0] + a_y[1]*XY[:,0:1] + a_y[2]*XY[:,1:2] + (U @ w_y)).reshape(h, w).astype(np.float32)
    map_x = np.clip(fx, 0, w-1)
    map_y = np.clip(fy, 0, h-1)
    out = cv2.remap(bgr, map_x, map_y, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return out

def detect_text_baselines(gray, min_gap=12, angle_thresh_deg=5, min_len_frac=0.3):
    h, w = gray.shape[:2]
    blur = cv2.GaussianBlur(gray, (3,3), 0)
    thr = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 35, 15)
    kx = max(15, w//60)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kx, 3))
    dil = cv2.dilate(thr, kernel, iterations=1)
    edges = cv2.Canny(dil, 50, 150)
    min_len = int(w * min_len_frac)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=120,
                            minLineLength=min_len, maxLineGap=20)
    if lines is None:
        return []
    segs = []
    for l in lines[:,0,:]:
        x1,y1,x2,y2 = l
        if x2==x1: continue
        angle = abs(np.degrees(np.arctan2(y2-y1, x2-x1)))
        if angle <= angle_thresh_deg:
            segs.append((x1,y1,x2,y2))
    if not segs:
        return []
    segs.sort(key=lambda s: (s[1]+s[3])/2.0)
    groups = []
    for s in segs:
        ym = (s[1]+s[3])/2.0
        if not groups or abs(ym - groups[-1][0]) > min_gap:
            groups.append([ym, [s]])
        else:
            groups[-1][1].append(s)
            groups[-1][0] = np.mean([(ss[1]+ss[3])/2.0 for ss in groups[-1][1]])
    baselines = []
    for _, seglist in groups:
        pts = []
        for (x1,y1,x2,y2) in seglist:
            xs = np.linspace(min(x1,x2), max(x1,x2), num=20, dtype=np.float32)
            ys = np.linspace(y1, y2, num=20, dtype=np.float32)
            pts.extend(list(zip(xs, ys)))
        if len(pts) < 12:
            continue
        pts = np.array(pts, dtype=np.float32)
        try:
            coeffs = np.polyfit(pts[:,0], pts[:,1], deg=2)
            baselines.append((coeffs, (0, w-1)))
        except Exception:
            continue
    return baselines

def generate_mesh_from_baselines(gray, cols=8, max_lines=12, gutter_x=None, gutter_density=2.0):
    h, w = gray.shape[:2]
    baselines = detect_text_baselines(gray)
    if not baselines:
        return None, None
    baselines = baselines[:max_lines]
    if gutter_x is None:
        gutter_x = w // 2
    n = cols
    left = np.linspace(0, gutter_x, max(2, n//2), endpoint=False, dtype=np.float32)
    right = np.linspace(gutter_x, w-1, max(2, n - len(left)), endpoint=True, dtype=np.float32)
    band = int(0.05*w)
    extra_left = np.linspace(max(0,gutter_x-band), gutter_x, int((gutter_density-1)*2), endpoint=False, dtype=np.float32) if gutter_density>1 else np.array([],dtype=np.float32)
    extra_right = np.linspace(gutter_x, min(w-1,gutter_x+band), int((gutter_density-1)*2), endpoint=False, dtype=np.float32) if gutter_density>1 else np.array([],dtype=np.float32)
    x_samples = np.unique(np.concatenate([left, extra_left, [gutter_x], extra_right, right])).astype(np.float32)

    src_pts = []
    dst_pts = []
    for i, (coeffs, xr) in enumerate(baselines):
        a,b,c = coeffs
        for x in x_samples:
            y_src = a*x*x + b*x + c
            y_src = np.clip(y_src, 0, h-1)
            src_pts.append([x, y_src])
            y_dst = (i+1) * (h / (len(baselines)+1))
            dst_pts.append([x, y_dst])
    return np.array(src_pts, dtype=np.float32), np.array(dst_pts, dtype=np.float32)

def split_two_pages(bgr, gutter_x=None, margin=8):
    h, w = bgr.shape[:2]
    if gutter_x is None:
        gutter_x = detect_gutter_x(bgr)
    x1 = max(0, gutter_x - margin)
    x2 = min(w, gutter_x + margin)
    left = bgr[:, :x1 if x1>0 else gutter_x].copy()
    right = bgr[:, x2 if x2<w else gutter_x:].copy()
    if left.size == 0 or right.size == 0:
        mid = w//2
        left = bgr[:, :mid].copy()
        right = bgr[:, mid:].copy()
    return left, right

def local_contrast_and_clean(gray, mode="clahe"):
    if mode == "clahe":
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        out = clahe.apply(gray)
    else:
        out = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 35, 15)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2,2))
    out = cv2.morphologyEx(out, cv2.MORPH_OPEN, kernel, iterations=1)
    return out

def run_ocr_rgb(rgb, lang="spa+eng"):
    if not TESS_AVAILABLE:
        return None, None
    try:
        txt = pytesseract.image_to_string(rgb, lang=lang)
        pdf_bytes = pytesseract.image_to_pdf_or_hocr(rgb, lang=lang, extension='pdf')
        return txt, pdf_bytes
    except Exception:
        return None, None

def assemble_pdf_from_images(image_paths, out_pdf_path, dpi=300, meta=None, pdfa=False):
    if not REPORTLAB_AVAILABLE:
        imgs = [Image.open(p).convert("RGB") for p in image_paths]
        base, tail = imgs[0], imgs[1:]
        base.save(out_pdf_path, save_all=True, append_images=tail)
        return
    c = canvas.Canvas(out_pdf_path)
    if meta:
        c.setAuthor(meta.get("author",""))
        c.setTitle(meta.get("title",""))
        c.setSubject(meta.get("subject",""))
        c.setKeywords(meta.get("keywords",""))
        c.setCreator(meta.get("creator","BookScannerTK"))
    if pdfa:
        xmp = _build_basic_xmp(meta or {})
        try:
            c._doc.XMPMetadata = xmp.encode("utf-8")
        except Exception:
            pass
    for p in image_paths:
        img = Image.open(p).convert("RGB")
        iw, ih = img.size
        pw = iw / dpi * 72.0
        ph = ih / dpi * 72.0
        c.setPageSize((pw, ph))
        c.drawImage(ImageReader(img), 0, 0, width=pw, height=ph)
        c.showPage()
    c.save()

def _build_basic_xmp(meta):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = meta.get("title","")
    author = meta.get("author","")
    subject = meta.get("subject","")
    xmp = (
        '<?xpacket begin=" " id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:xmp="http://ns.adobe.com/xap/1.0/" '
        'xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">\n'
        '  <rdf:Description rdf:about="" '
        'xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/" '
        'pdfaid:part="1" pdfaid:conformance="B">\n'
        f'    <dc:title><rdf:Alt><rdf:li xml:lang="x-default">{title}</rdf:li></rdf:Alt></dc:title>\n'
        f'    <dc:creator><rdf:Seq><rdf:li>{author}</rdf:li></rdf:Seq></dc:creator>\n'
        f'    <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{subject}</rdf:li></rdf:Alt></dc:description>\n'
        f'    <xmp:CreateDate>{now}</xmp:CreateDate>\n'
        f'    <xmp:ModifyDate>{now}</xmp:ModifyDate>\n'
        f'    <xmp:MetadataDate>{now}</xmp:MetadataDate>\n'
        '  </rdf:Description>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
        '<?xpacket end="w"?>'
    )
    return xmp

def process_one_image(bgr, do_dewarp=None, dewarp_strength=0.22, contrast_mode="clahe",
                      final_scale=1.0, manual_quad=None, mesh=False, mesh_cols=8, mesh_rows=10,
                      asymmetric=False, split_spread=False, ocr_lang=None):
    edges = preprocess_for_edges(bgr)
    if manual_quad is not None and len(manual_quad)==4:
        quad = np.array(manual_quad, dtype=np.float32)
    else:
        quad = largest_page_contour(edges, min_area=0.12)
        if quad is None:
            edges2 = preprocess_for_edges(bgr, blur=7)
            quad = largest_page_contour(edges2, min_area=0.08)
        if quad is None:
            h, w = bgr.shape[:2]
            quad = np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]], dtype=np.float32)
    warped = four_point_transform(bgr, quad)
    results = []
    targets = [warped]
    if split_spread:
        left, right = split_two_pages(warped, gutter_x=None, margin=8)
        targets = [left, right]
    for img in targets:
        base = img
        if do_dewarp == "cylindrical":
            base = cylindrical_dewarp(base, strength=dewarp_strength, center_x=None)
        elif do_dewarp == "mesh":
            gray_tmp = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
            gutter_x = detect_gutter_x(base) if asymmetric else None
            if asymmetric:
                src_pts, dst_pts = generate_mesh_from_baselines(gray_tmp, cols=mesh_cols, max_lines=12, gutter_x=gutter_x, gutter_density=2.5)
            else:
                src_pts, dst_pts = generate_mesh_from_baselines(gray_tmp, cols=mesh_cols, max_lines=12, gutter_x=None, gutter_density=1.0)
            if src_pts is None or len(src_pts) < 3:
                src_pts, dst_pts = heuristic_mesh_points(base, cols=mesh_cols, rows=mesh_rows)
            base = tps_warp(base, src_pts, dst_pts)
        gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
        post = local_contrast_and_clean(gray, mode=contrast_mode)
        if final_scale != 1.0 and final_scale > 0:
            new_w = int(base.shape[1] * final_scale)
            new_h = int(base.shape[0] * final_scale)
            base = cv2.resize(base, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            post = cv2.resize(post, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        ocr_txt = None; ocr_pdf = None
        if ocr_lang:
            rgb_mono = cv2.cvtColor(post, cv2.COLOR_GRAY2RGB)
            ocr_txt, ocr_pdf = run_ocr_rgb(rgb_mono, lang=ocr_lang)
        results.append({"warped": img, "dewarped": base, "post_gray": post, "ocr_txt": ocr_txt, "ocr_pdf": ocr_pdf})
    return results if split_spread else results[0]

def heuristic_mesh_points(bgr, cols=6, rows=10):
    h, w = bgr.shape[:2]
    gx = np.linspace(0, w-1, cols, dtype=np.float32)
    gy = np.linspace(0, h-1, rows, dtype=np.float32)
    gX, gY = np.meshgrid(gx, gy)
    dst_pts = np.stack([gX.flatten(), gY.flatten()], axis=1)
    cx = w/2.0
    k = 0.0003
    src_pts = dst_pts.copy()
    dx = (src_pts[:,0] - cx)
    src_pts[:,0] = src_pts[:,0] + k * dx * (src_pts[:,1] - h/2.0)
    return src_pts.astype(np.float32), dst_pts.astype(np.float32)
