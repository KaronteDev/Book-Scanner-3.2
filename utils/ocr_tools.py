#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_tools.py — OCR processing with Tesseract
"""
import os
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    
from PIL import Image


def configure_tesseract():
    """Configure Tesseract path if needed"""
    if not TESSERACT_AVAILABLE:
        return False
    
    # Common paths on Windows
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\%USERNAME%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    ]
    
    # Check environment variable
    env_path = os.environ.get('TESSERACT_CMD')
    if env_path:
        possible_paths.insert(0, env_path)
    
    for path in possible_paths:
        expanded = os.path.expandvars(path)
        if os.path.exists(expanded):
            pytesseract.pytesseract.tesseract_cmd = expanded
            return True
    
    return False


def preprocess_for_ocr(img_path: str, output_path: Optional[str] = None) -> str:
    """
    Preprocess image for better OCR results:
    - Convert to grayscale
    - Remove noise
    - Increase contrast
    - Binarize
    """
    if not CV2_AVAILABLE:
        return img_path
    
    # Read image
    img = cv2.imread(img_path)
    if img is None:
        return img_path
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # Increase contrast (CLAHE - Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(denoised)
    
    # Binarize (Otsu's method)
    _, binary = cv2.threshold(contrasted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Save preprocessed image
    if output_path is None:
        output_path = str(Path(img_path).parent / f"{Path(img_path).stem}_ocr_prep.jpg")
    
    cv2.imwrite(output_path, binary)
    
    return output_path


def detect_text_rotation(img_path: str) -> float:
    """Detect text rotation angle using Tesseract OSD"""
    if not TESSERACT_AVAILABLE:
        return 0.0
    
    configure_tesseract()
    
    try:
        osd = pytesseract.image_to_osd(img_path)
        
        # Parse rotation
        for line in osd.split('\n'):
            if 'Rotate:' in line:
                angle = float(line.split(':')[1].strip())
                return angle
    except Exception:
        pass
    
    return 0.0


def correct_rotation(img_path: str, angle: float = None) -> str:
    """Auto-correct image rotation"""
    if angle is None:
        angle = detect_text_rotation(img_path)
    
    if angle == 0:
        return img_path
    
    if not CV2_AVAILABLE:
        return img_path
    
    img = cv2.imread(img_path)
    if img is None:
        return img_path
    
    # Rotate
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # Save
    output_path = str(Path(img_path).parent / f"{Path(img_path).stem}_rotated.jpg")
    cv2.imwrite(output_path, rotated)
    
    return output_path


def perform_ocr(
    img_path: str,
    lang: str = 'spa',
    config: str = '--psm 3'
) -> Dict[str, Any]:
    """
    Perform OCR on image
    
    Args:
        img_path: Path to image file
        lang: Tesseract language code (spa, eng, lat, etc.)
        config: Tesseract config string
    
    Returns:
        Dictionary with text, confidence, and metadata
    """
    if not TESSERACT_AVAILABLE:
        return {
            'success': False,
            'error': 'Tesseract not available',
            'text': '',
            'confidence': 0.0
        }
    
    configure_tesseract()
    
    try:
        # Get text
        text = pytesseract.image_to_string(img_path, lang=lang, config=config)
        
        # Get detailed data
        data = pytesseract.image_to_data(img_path, lang=lang, config=config, output_type=pytesseract.Output.DICT)
        
        # Calculate average confidence (excluding -1 values)
        confidences = [conf for conf in data['conf'] if conf != -1]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            'success': True,
            'text': text,
            'confidence': avg_confidence,
            'word_count': len([w for w in data['text'] if w.strip()]),
            'language': lang,
            'data': data
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'text': '',
            'confidence': 0.0
        }


def perform_ocr_hocr(
    img_path: str,
    lang: str = 'spa',
    config: str = '--psm 3'
) -> str:
    """Perform OCR and return hOCR format"""
    if not TESSERACT_AVAILABLE:
        return ''
    
    configure_tesseract()
    
    try:
        hocr = pytesseract.image_to_pdf_or_hocr(img_path, lang=lang, config=config, extension='hocr')
        return hocr.decode('utf-8')
    except Exception:
        return ''


def ocr_batch(
    img_paths: List[str],
    lang: str = 'spa',
    config: str = '--psm 3',
    preprocess: bool = True,
    progress_callback=None
) -> List[Dict[str, Any]]:
    """
    Perform OCR on multiple images
    
    Args:
        img_paths: List of image paths
        lang: Language code
        config: Tesseract config
        preprocess: Whether to preprocess images
        progress_callback: Function to call with progress (current, total)
    
    Returns:
        List of OCR results
    """
    results = []
    total = len(img_paths)
    
    for i, img_path in enumerate(img_paths):
        if progress_callback:
            progress_callback(i + 1, total)
        
        # Preprocess if requested
        if preprocess:
            processed_path = preprocess_for_ocr(img_path)
        else:
            processed_path = img_path
        
        # Perform OCR
        result = perform_ocr(processed_path, lang, config)
        result['original_path'] = img_path
        result['processed_path'] = processed_path
        
        results.append(result)
    
    return results


def get_available_languages() -> List[str]:
    """Get list of available Tesseract languages"""
    if not TESSERACT_AVAILABLE:
        return []
    
    configure_tesseract()
    
    try:
        langs = pytesseract.get_languages()
        return langs
    except Exception:
        return ['spa', 'eng', 'lat']  # Default fallback


def extract_text_regions(img_path: str, lang: str = 'spa') -> List[Dict[str, Any]]:
    """
    Extract text regions with bounding boxes
    
    Returns list of dicts with: text, x, y, width, height, confidence
    """
    if not TESSERACT_AVAILABLE:
        return []
    
    configure_tesseract()
    
    try:
        data = pytesseract.image_to_data(
            img_path,
            lang=lang,
            output_type=pytesseract.Output.DICT
        )
        
        regions = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            if int(data['conf'][i]) > 0:
                text = data['text'][i].strip()
                if text:
                    regions.append({
                        'text': text,
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                        'confidence': data['conf'][i],
                        'block': data['block_num'][i],
                        'par': data['par_num'][i],
                        'line': data['line_num'][i],
                        'word': data['word_num'][i]
                    })
        
        return regions
    
    except Exception:
        return []
