#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
image_cleaner.py — Advanced image processing utilities
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List


def imread_auto(path: str) -> Optional[np.ndarray]:
    """Read image with Unicode path support"""
    data = np.fromfile(path, dtype=np.uint8)
    if data is None or data.size == 0:
        return None
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return img


def imwrite_auto(path: str, img: np.ndarray, quality: int = 95) -> bool:
    """Write image with Unicode path support"""
    ext = Path(path).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"]:
        ext = ".jpg"
    
    params = []
    if ext in [".jpg", ".jpeg"]:
        params = [cv2.IMWRITE_JPEG_QUALITY, int(quality)]
    elif ext == ".png":
        params = [cv2.IMWRITE_PNG_COMPRESSION, 3]
    
    ok, buf = cv2.imencode(ext, img, params)
    if not ok:
        return False
    
    with open(path, "wb") as f:
        f.write(buf.tobytes())
    
    return True


def order_points(pts: np.ndarray) -> np.ndarray:
    """Order points in clockwise order: top-left, top-right, bottom-right, bottom-left"""
    rect = np.zeros((4, 2), dtype="float32")
    
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    
    rect[0] = pts[np.argmin(s)]      # top-left
    rect[2] = pts[np.argmax(s)]      # bottom-right
    rect[1] = pts[np.argmin(diff)]   # top-right
    rect[3] = pts[np.argmax(diff)]   # bottom-left
    
    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Apply perspective transform to get bird's eye view"""
    rect = order_points(pts.astype("float32"))
    (tl, tr, br, bl) = rect
    
    # Calculate width
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))
    
    # Calculate height
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))
    
    # Destination points
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")
    
    # Get perspective transform matrix
    M = cv2.getPerspectiveTransform(rect, dst)
    
    # Apply transform
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight), flags=cv2.INTER_CUBIC)
    
    return warped


def detect_page_contour(
    img: np.ndarray,
    min_area: float = 0.15,
    blur: int = 5
) -> Optional[np.ndarray]:
    """
    Detect page contour in image
    
    Args:
        img: Input image (BGR)
        min_area: Minimum contour area as fraction of image area
        blur: Gaussian blur kernel size
    
    Returns:
        Array of 4 corner points or None
    """
    h, w = img.shape[:2]
    area_img = w * h
    
    # Convert to grayscale and blur
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (blur, blur), 0)
    
    # Edge detection
    v = np.median(gray)
    lower = int(max(0, (1.0 - 0.33) * v))
    upper = int(min(255, (1.0 + 0.33) * v))
    edges = cv2.Canny(gray, lower, upper)
    
    # Dilate edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    best_poly = None
    best_area = 0
    
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area * area_img:
            continue
        
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        
        if len(approx) == 4 and area > best_area:
            best_poly = approx.reshape(-1, 2)
            best_area = area
    
    # Fallback: use largest contour and get bounding box
    if best_poly is None and len(contours) > 0:
        c = max(contours, key=cv2.contourArea)
        hull = cv2.convexHull(c)
        rect = cv2.minAreaRect(hull.astype(np.float32))
        box = cv2.boxPoints(rect)
        best_poly = box.astype(np.float32)
    
    return best_poly


def detect_finger_regions(img: np.ndarray) -> Optional[np.ndarray]:
    """
    Detect finger/hand regions using skin tone detection
    
    Returns binary mask where 255 = skin detected
    """
    # Convert to YCrCb for better skin detection
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    
    # Skin color range in YCrCb
    lower_skin = np.array([0, 133, 77], dtype=np.uint8)
    upper_skin = np.array([255, 173, 127], dtype=np.uint8)
    mask_ycrcb = cv2.inRange(ycrcb, lower_skin, upper_skin)
    
    # Also try HSV for complementary detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_hsv = np.array([0, 15, 0], dtype=np.uint8)
    upper_hsv = np.array([17, 170, 255], dtype=np.uint8)
    mask_hsv = cv2.inRange(hsv, lower_hsv, upper_hsv)
    
    # Combine both masks
    mask = cv2.bitwise_or(mask_ycrcb, mask_hsv)
    
    # Morphological operations to clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Find contours and filter by area
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Create filtered mask with only significant regions
    filtered_mask = np.zeros_like(mask)
    min_area = img.shape[0] * img.shape[1] * 0.001  # 0.1% of image
    max_area = img.shape[0] * img.shape[1] * 0.15   # 15% of image
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_area < area < max_area:
            cv2.drawContours(filtered_mask, [contour], -1, 255, -1)
    
    return filtered_mask


def remove_fingers(img: np.ndarray, method: str = 'inpaint') -> np.ndarray:
    """
    Remove detected finger regions from image
    
    Args:
        img: Input image
        method: 'inpaint' or 'blur'
    
    Returns:
        Image with fingers removed
    """
    mask = detect_finger_regions(img)
    if mask is None or mask.max() == 0:
        return img.copy()
    
    if method == 'inpaint':
        # Inpainting (slower but better quality)
        result = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
    else:
        # Blur (faster)
        blurred = cv2.GaussianBlur(img, (15, 15), 0)
        result = img.copy()
        result[mask == 255] = blurred[mask == 255]
    
    return result


def split_double_page(img: np.ndarray, gutter_margin: int = 20) -> Tuple[np.ndarray, np.ndarray]:
    """
    Split double-page spread into two pages
    
    Args:
        img: Input image
        gutter_margin: Pixels to add/remove from gutter
    
    Returns:
        Tuple of (left_page, right_page)
    """
    h, w = img.shape[:2]
    mid_x = w // 2
    
    # Try to detect gutter line
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Look for darkest column in middle region
    search_width = w // 10  # Search ±10% from center
    search_start = mid_x - search_width
    search_end = mid_x + search_width
    
    col_sums = []
    for x in range(search_start, search_end):
        col = gray[:, x]
        col_sums.append((x, np.mean(col)))
    
    # Find darkest column (likely the gutter)
    if col_sums:
        gutter_x = min(col_sums, key=lambda t: t[1])[0]
    else:
        gutter_x = mid_x
    
    # Split at gutter with margin
    left_page = img[:, :gutter_x - gutter_margin]
    right_page = img[:, gutter_x + gutter_margin:]
    
    return left_page, right_page


def enhance_image(
    img: np.ndarray,
    brightness: float = 1.0,
    contrast: float = 1.0,
    sharpness: float = 1.0
) -> np.ndarray:
    """
    Enhance image with brightness, contrast, and sharpness adjustments
    
    Args:
        img: Input image
        brightness: Brightness factor (1.0 = no change)
        contrast: Contrast factor (1.0 = no change)
        sharpness: Sharpness factor (1.0 = no change)
    
    Returns:
        Enhanced image
    """
    from PIL import Image, ImageEnhance
    
    # Convert to PIL
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    # Apply enhancements
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(img_pil)
        img_pil = enhancer.enhance(brightness)
    
    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(img_pil)
        img_pil = enhancer.enhance(contrast)
    
    if sharpness != 1.0:
        enhancer = ImageEnhance.Sharpness(img_pil)
        img_pil = enhancer.enhance(sharpness)
    
    # Convert back to OpenCV
    img_enhanced = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    return img_enhanced


def create_thumbnail(img_path: str, thumb_path: str, max_size: int = 200) -> bool:
    """Create thumbnail of image"""
    try:
        img = imread_auto(img_path)
        if img is None:
            return False
        
        h, w = img.shape[:2]
        scale = max_size / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        thumb = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return imwrite_auto(thumb_path, thumb, quality=85)
    except Exception:
        return False
