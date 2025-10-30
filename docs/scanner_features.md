# Scanner Module - Advanced Features

## Overview
The scanner module (`gui/scanner_module.py`) now includes three advanced features for professional document digitization:

### 1. Area Calibration
**Purpose**: Define a specific capture area to crop images automatically.

**Usage**:
- Click the "⚙️ Calibrar área" button in the scanner toolbar
- A dialog opens showing the current camera view
- Click and drag to draw a rectangle over the desired capture area
- Click "Guardar" to save the calibration
- All subsequent captures will be cropped to this area

**Technical Details**:
- Coordinates are stored normalized (0-1 range) for resolution independence
- Applied before page detection and perspective transform
- Calibration persists during the session

### 2. Automatic Page Detection
**Purpose**: Automatically detect document edges and apply perspective correction.

**Usage**:
- Enable "Detectar página" checkbox in the toolbar
- Green contour overlay shows detected page boundaries on preview
- Captured images are automatically straightened using perspective transform

**Technical Details**:
- Uses Canny edge detection + contour finding
- Selects largest quadrilateral contour as page boundary
- Applies 4-point perspective transform to straighten
- Handles arbitrary angles and perspectives

### 3. Book Mode (Split Double-Page)
**Purpose**: Automatically split book spreads into separate left and right pages.

**Usage**:
- Enable "Modo libro" checkbox in the toolbar
- Capture an open book spread
- Two separate images are saved with `_L` and `_R` suffixes

**Technical Details**:
- Splits image at horizontal midpoint
- Saves as `scan_XXXX_L.jpg` and `scan_XXXX_R.jpg`
- Counter increments once per spread, not per page
- Compatible with calibration and page detection

## Processing Pipeline

1. **Camera Capture** → Raw frame from camera
2. **Adjustments** → Brightness/contrast enhancements
3. **Calibration Crop** (if enabled) → Crop to calibrated area
4. **Page Detection** → Detect contour (shown as green overlay)
5. **Perspective Transform** (if page detected) → Straighten document
6. **Book Split** (if book mode enabled) → Split into L/R pages
7. **Save** → Save to output directory as JPEG

## Keyboard Shortcuts

- **Capture**: Click "📷 Capturar" button
- **Calibration**: Click "⚙️ Calibrar área" button

## Dependencies

- **OpenCV (cv2)**: Edge detection, contours, perspective transforms
- **NumPy (np)**: Array operations for image processing
- **PIL/Pillow**: Image I/O, adjustments, drawing overlays
- **ImageDraw**: Drawing contours and calibration rectangles

## Integration

The scanner module is invoked from:
- `main.py`: "Escaneado" button launches `ScannerWindow`
- `gui/scan_view.py`: "Abrir escáner existente" opens scanner with project directory

All captures are saved to:
- Project mode: `{project_dir}/paginas/`
- Standalone mode: `output_tk/`

## Configuration

No configuration files required. All settings are UI-based:
- Camera selection dropdown (auto-detects available cameras)
- Brightness/contrast sliders
- Feature checkboxes (detect page, book mode)
- Calibration dialog

## Error Handling

- Graceful degradation if OpenCV/NumPy unavailable
- Fallback to simple capture if detection fails
- User feedback via toast messages and confirmation dialogs
- No crashes on missing dependencies

## Future Enhancements

Potential improvements:
- Multi-page contour detection (detect both pages separately)
- Configurable book split position (not just center)
- Save calibration profiles (A4, A3, Letter, etc.)
- Auto-rotate based on detected orientation
- Batch processing mode
