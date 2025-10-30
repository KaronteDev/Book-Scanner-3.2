#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scanner_module.py — Core camera scanning functionality
Extracted from gui_book_scan_tk2.py and refactored for modular integration
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import threading
import time
from typing import Optional, List, Tuple

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    from PIL import Image, ImageTk, ImageEnhance, ImageDraw
except ImportError:
    Image = None
    ImageTk = None
    ImageDraw = None


class CameraScanner:
    """Core scanner functionality with camera preview and capture"""
    
    def __init__(self, parent, output_dir: Path):
        self.parent = parent
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.cap = None
        self._preview_running = False
        self._tkimg = None
        self.current_camera_idx = None
        self.camera_map = {}
        self.camera_resolutions = {}
        self._frame_counter = 0
        
        # Calibration and detection
        self.calibration_area = None  # {tl: (x, y), br: (x, y)} normalized coords
        self.detect_page = tk.BooleanVar(value=True)
        self.book_mode = tk.BooleanVar(value=False)
        self.detected_contour = None
        
        self.setup_ui()
        self.refresh_cameras()
        
    def setup_ui(self):
        """Create the scanner UI"""
        # Main container
        main_frame = ttk.Frame(self.parent, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(toolbar, text="Cámara:").pack(side=tk.LEFT, padx=5)
        
        self.cmb_cam = ttk.Combobox(toolbar, width=35, state="readonly")
        self.cmb_cam.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar,
            text="Refrescar",
            command=self.refresh_cameras
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar,
            text="Conectar",
            command=self.open_camera
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar,
            text="Desconectar",
            command=self.close_camera
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Checkbutton(
            toolbar,
            text="Detectar página",
            variable=self.detect_page
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(
            toolbar,
            text="Modo libro",
            variable=self.book_mode
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar,
            text="⚙️ Calibrar área",
            command=self.open_calibration
        ).pack(side=tk.LEFT, padx=5)
        
        # Preview canvas
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.canvas = tk.Canvas(
            canvas_frame,
            width=960,
            height=720,
            bg="#1a1a1a",
            highlightthickness=0
        )
        self.canvas.pack()
        
        self._image_item = self.canvas.create_image(0, 0, anchor="nw", image=None)
        
        # Image adjustments
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls_frame, text="Brillo:").pack(side=tk.LEFT, padx=5)
        self.s_brightness = tk.DoubleVar(value=1.0)
        ttk.Scale(
            controls_frame,
            variable=self.s_brightness,
            from_=0.5,
            to=1.5,
            orient="horizontal",
            length=150
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(controls_frame, text="Contraste:").pack(side=tk.LEFT, padx=(20, 5))
        self.s_contrast = tk.DoubleVar(value=1.0)
        ttk.Scale(
            controls_frame,
            variable=self.s_contrast,
            from_=0.5,
            to=1.5,
            orient="horizontal",
            length=150
        ).pack(side=tk.LEFT, padx=5)
        
        # Bottom buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X)
        
        ttk.Button(
            buttons_frame,
            text="📸 Capturar (Espacio)",
            command=self.capture_image
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            buttons_frame,
            text="📂 Abrir carpeta",
            command=self.open_output_folder
        ).pack(side=tk.LEFT, padx=5)
        
        # Bind keyboard shortcuts
        self.parent.bind('<space>', lambda e: self.capture_image())
        self.parent.bind('<Escape>', lambda e: self.close_camera())
        
        # Show initial state
        self._show_camera_off_screen()
        
    def detect_cameras(self, max_index: int = 8) -> List[tuple]:
        """Detect available cameras and return list of (index, name, max_width, max_height) tuples"""
        if cv2 is None:
            return []
        
        found = []
        camera_names = {}
        
        # Try to get camera names on Windows
        if hasattr(cv2, 'CAP_DSHOW'):
            try:
                import subprocess
                result = subprocess.run(
                    ['powershell', '-Command', 
                     "Get-PnpDevice -Class Camera | Where-Object {$_.Status -eq 'OK'} | Select-Object -ExpandProperty FriendlyName"],
                    capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    names = [n.strip() for n in result.stdout.strip().split('\n') if n.strip()]
                    for idx, name in enumerate(names[:max_index]):
                        camera_names[idx] = name
            except Exception:
                pass
        
        # Test cameras
        for i in range(max_index):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if hasattr(cv2, 'CAP_DSHOW') else cv2.VideoCapture(i)
            if cap.isOpened():
                try:
                    # Test resolutions
                    max_w, max_h = 640, 480
                    test_resolutions = [
                        (1920, 1080),  # Full HD
                        (1280, 720),   # HD
                        (640, 480)     # VGA
                    ]
                    
                    for test_w, test_h in test_resolutions:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, test_w)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, test_h)
                        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        if actual_w >= test_w * 0.9 and actual_h >= test_h * 0.9:
                            max_w, max_h = actual_w, actual_h
                            break
                    
                    name = camera_names.get(i, f"Cámara {i}")
                    found.append((i, f"{name} ({max_w}x{max_h})", max_w, max_h))
                except Exception:
                    name = camera_names.get(i, f"Cámara {i}")
                    found.append((i, name, 640, 480))
            cap.release()
        
        return found
    
    def refresh_cameras(self):
        """Refresh camera list"""
        cams = self.detect_cameras()
        self.camera_map = {}
        self.camera_resolutions = {}
        
        if not cams:
            self.cmb_cam["values"] = ["(sin cámara)"]
            self.cmb_cam.current(0)
        else:
            names = [name for idx, name, w, h in cams]
            self.camera_map = {name: idx for idx, name, w, h in cams}
            self.camera_resolutions = {name: (w, h) for idx, name, w, h in cams}
            self.cmb_cam["values"] = names
            self.cmb_cam.current(0)
            
            # Auto-connect to first camera
            self.parent.after(500, self.open_camera)
    
    def open_camera(self):
        """Open and start camera preview"""
        self.close_camera()
        
        if cv2 is None:
            messagebox.showwarning("Cámara", "OpenCV no está instalado")
            return
        
        sel = self.cmb_cam.get()
        if sel not in self.camera_map:
            messagebox.showerror("Cámara", "Seleccione una cámara válida")
            return
        
        idx = self.camera_map[sel]
        max_w, max_h = self.camera_resolutions.get(sel, (1920, 1080))
        
        self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if hasattr(cv2, 'CAP_DSHOW') else cv2.VideoCapture(idx)
        
        if not self.cap.isOpened():
            messagebox.showerror("Cámara", f"No se pudo abrir la cámara {idx}")
            self.cap = None
            return
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, max_w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, max_h)
        
        # Clear "camera off" message
        self.canvas.delete("camera_off_message")
        
        self.current_camera_idx = idx
        self._preview_running = True
        self._start_preview()
    
    def close_camera(self):
        """Stop camera preview and release"""
        self._preview_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self._show_camera_off_screen()
    
    def _start_preview(self):
        """Start preview thread"""
        def preview_loop():
            while self._preview_running and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Apply adjustments and detect page
                    adjusted, contour = self._apply_adjustments(frame_rgb)
                    self.detected_contour = contour
                    
                    # Update canvas
                    self._update_canvas(adjusted)
                
                time.sleep(0.033)  # ~30 fps
        
        threading.Thread(target=preview_loop, daemon=True).start()
    
    def _apply_adjustments(self, img_array):
        """Apply brightness/contrast adjustments and detect page if enabled"""
        if Image is None:
            return img_array, None
        
        try:
            pil_img = Image.fromarray(img_array)
            
            # Brightness
            brightness = self.s_brightness.get()
            if abs(brightness - 1.0) > 0.01:
                enhancer = ImageEnhance.Brightness(pil_img)
                pil_img = enhancer.enhance(brightness)
            
            # Contrast
            contrast = self.s_contrast.get()
            if abs(contrast - 1.0) > 0.01:
                enhancer = ImageEnhance.Contrast(pil_img)
                pil_img = enhancer.enhance(contrast)
            
            adjusted = np.array(pil_img) if np else img_array
            
            # Detect page contour if enabled
            contour = None
            if self.detect_page.get() and cv2 is not None and np is not None:
                contour = self._detect_page_contour(adjusted)
            
            return adjusted, contour
        except Exception:
            return img_array, None
    
    def _detect_page_contour(self, img):
        """Detect page contour using edge detection"""
        if cv2 is None or np is None:
            return None
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            
            # Apply bilateral filter to reduce noise while keeping edges sharp
            filtered = cv2.bilateralFilter(gray, 9, 75, 75)
            
            # Edge detection
            edges = cv2.Canny(filtered, 50, 150)
            
            # Dilate edges to close gaps
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Filter contours by area (must be at least 10% of image)
            img_area = img.shape[0] * img.shape[1]
            min_area = img_area * 0.1
            
            valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
            
            if not valid_contours:
                return None
            
            # Find largest valid contour
            largest = max(valid_contours, key=cv2.contourArea)
            
            # Approximate to polygon
            peri = cv2.arcLength(largest, True)
            approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
            
            # We want a quadrilateral (4 corners)
            if len(approx) == 4:
                return approx.reshape(4, 2)
            
            # If not exactly 4, try with different epsilon
            for epsilon_mult in [0.01, 0.03, 0.04, 0.05]:
                approx = cv2.approxPolyDP(largest, epsilon_mult * peri, True)
                if len(approx) == 4:
                    return approx.reshape(4, 2)
            
            return None
        except Exception as e:
            print(f"Error detecting page: {e}")
            return None
    
    def _draw_contour_on_frame(self, img, contour):
        """Draw detected contour on frame"""
        if cv2 is None or np is None:
            return
        
        try:
            # Use cv2 to draw directly on the image
            # Convert points to proper format for cv2.polylines
            points = contour.reshape((-1, 1, 2)).astype(np.int32)
            # Draw green polygon
            cv2.polylines(img, [points], isClosed=True, color=(0, 255, 0), thickness=3)
            # Draw corner circles for better visibility
            for point in contour:
                x, y = int(point[0]), int(point[1])
                cv2.circle(img, (x, y), 8, (0, 255, 0), -1)
        except Exception as e:
            print(f"Error drawing contour: {e}")
    
    def _draw_calibration_on_frame(self, img):
        """Draw calibration area on frame"""
        if cv2 is None or np is None:
            return
        
        try:
            h, w = img.shape[:2]
            tl = self.calibration_area['tl']
            br = self.calibration_area['br']
            
            # Convert normalized coords to pixel coords
            x1 = int(tl[0] * w)
            y1 = int(tl[1] * h)
            x2 = int(br[0] * w)
            y2 = int(br[1] * h)
            
            # Draw red rectangle using cv2
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
            # Draw corner markers
            marker_size = 10
            # Top-left
            cv2.line(img, (x1, y1), (x1 + marker_size, y1), (255, 0, 0), 3)
            cv2.line(img, (x1, y1), (x1, y1 + marker_size), (255, 0, 0), 3)
            # Top-right
            cv2.line(img, (x2, y1), (x2 - marker_size, y1), (255, 0, 0), 3)
            cv2.line(img, (x2, y1), (x2, y1 + marker_size), (255, 0, 0), 3)
            # Bottom-right
            cv2.line(img, (x2, y2), (x2 - marker_size, y2), (255, 0, 0), 3)
            cv2.line(img, (x2, y2), (x2, y2 - marker_size), (255, 0, 0), 3)
            # Bottom-left
            cv2.line(img, (x1, y2), (x1 + marker_size, y2), (255, 0, 0), 3)
            cv2.line(img, (x1, y2), (x1, y2 - marker_size), (255, 0, 0), 3)
        except Exception as e:
            print(f"Error drawing calibration: {e}")
    
    def _update_canvas(self, img_array):
        """Update canvas with frame"""
        if Image is None or ImageTk is None:
            return
        
        try:
            # Clear any "camera off" message
            self.canvas.delete("camera_off_message")
            
            # Draw overlays on frame if needed
            display_img = img_array.copy() if np else img_array
            
            # Draw detected page contour
            if self.detected_contour is not None:
                self._draw_contour_on_frame(display_img, self.detected_contour)
            
            # Draw calibration area
            if self.calibration_area:
                self._draw_calibration_on_frame(display_img)
            
            # Convert to PIL and resize to fit canvas
            pil_img = Image.fromarray(display_img)
            cw = self.canvas.winfo_width() or 960
            ch = self.canvas.winfo_height() or 720
            
            # Calculate scaling to fit
            img_w, img_h = pil_img.size
            scale = min(cw / img_w, ch / img_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Create PhotoImage
            self._tkimg = ImageTk.PhotoImage(pil_img)
            
            # Center on canvas
            x = (cw - new_w) // 2
            y = (ch - new_h) // 2
            
            # Update or create image item
            if self._image_item is None or not self.canvas.coords(self._image_item):
                # Create new image item
                self._image_item = self.canvas.create_image(x, y, anchor="nw", image=self._tkimg)
            else:
                # Update existing image item
                self.canvas.coords(self._image_item, x, y)
                self.canvas.itemconfig(self._image_item, image=self._tkimg)
        except Exception:
            pass
    
    def _show_camera_off_screen(self):
        """Show 'CAMERA OFF' message"""
        self.canvas.delete("all")
        self._image_item = None
        cw = self.canvas.winfo_width() or 960
        ch = self.canvas.winfo_height() or 720
        self.canvas.create_text(
            cw // 2,
            ch // 2,
            text="CÁMARA DESCONECTADA",
            fill="#666666",
            font=("Open Sans", 20, "bold"),
            tags="camera_off_message"
        )
    
    def capture_image(self):
        """Capture current frame and save to output directory"""
        if self.cap is None or cv2 is None:
            messagebox.showwarning("Captura", "Cámara no disponible")
            return
        
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Captura", "No se pudo capturar imagen")
            return
        
        # Convert to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Apply adjustments and get contour
        adjusted, contour = self._apply_adjustments(frame_rgb)
        
        # Apply calibration crop if set
        if self.calibration_area and np is not None:
            h, w = adjusted.shape[:2]
            tl = self.calibration_area['tl']
            br = self.calibration_area['br']
            x1, y1 = int(tl[0] * w), int(tl[1] * h)
            x2, y2 = int(br[0] * w), int(br[1] * h)
            adjusted = adjusted[y1:y2, x1:x2]
        
        # Apply perspective transform if page detected
        if self.detect_page.get() and contour is not None and cv2 is not None and np is not None:
            adjusted = self._apply_perspective_transform(adjusted, contour)
        
        # Split in book mode
        if self.book_mode.get() and np is not None:
            self._save_book_pages(adjusted)
        else:
            self._save_single_page(adjusted)
    
    def _apply_perspective_transform(self, img, contour):
        """Apply perspective transform to straighten page"""
        if cv2 is None or np is None:
            return img
        
        try:
            # Order points: top-left, top-right, bottom-right, bottom-left
            rect = np.zeros((4, 2), dtype="float32")
            s = contour.sum(axis=1)
            rect[0] = contour[np.argmin(s)]
            rect[2] = contour[np.argmax(s)]
            diff = np.diff(contour, axis=1)
            rect[1] = contour[np.argmin(diff)]
            rect[3] = contour[np.argmax(diff)]
            
            # Compute width and height of new image
            (tl, tr, br, bl) = rect
            widthA = np.linalg.norm(br - bl)
            widthB = np.linalg.norm(tr - tl)
            maxWidth = max(int(widthA), int(widthB))
            
            heightA = np.linalg.norm(tr - br)
            heightB = np.linalg.norm(tl - bl)
            maxHeight = max(int(heightA), int(heightB))
            
            # Destination points
            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")
            
            # Compute perspective transform
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))
            
            return warped
        except Exception:
            return img
    
    def _save_single_page(self, img):
        """Save single page image"""
        if Image is None:
            return
        
        try:
            self._frame_counter += 1
            filename = f"scan_{self._frame_counter:04d}.jpg"
            output_path = self.output_dir / filename
            
            pil_img = Image.fromarray(img)
            pil_img.save(output_path, "JPEG", quality=95)
            
            # Show confirmation
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                30,
                text=f"✓ Guardado: {filename}",
                fill="#00ff00",
                font=("Open Sans", 14, "bold"),
                tags="toast"
            )
            self.parent.after(2000, lambda: self.canvas.delete("toast"))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")
    
    def _save_book_pages(self, img):
        """Split and save left/right pages from book"""
        if Image is None or np is None:
            return
        
        try:
            h, w = img.shape[:2]
            mid = w // 2
            
            # Split into left and right
            left_page = img[:, :mid]
            right_page = img[:, mid:]
            
            self._frame_counter += 1
            
            # Save left page
            left_filename = f"scan_{self._frame_counter:04d}_L.jpg"
            left_path = self.output_dir / left_filename
            Image.fromarray(left_page).save(left_path, "JPEG", quality=95)
            
            # Save right page
            right_filename = f"scan_{self._frame_counter:04d}_R.jpg"
            right_path = self.output_dir / right_filename
            Image.fromarray(right_page).save(right_path, "JPEG", quality=95)
            
            # Show confirmation
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                30,
                text=f"✓ Guardado: {left_filename}, {right_filename}",
                fill="#00ff00",
                font=("Open Sans", 14, "bold"),
                tags="toast"
            )
            self.parent.after(2000, lambda: self.canvas.delete("toast"))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")
    
    def open_calibration(self):
        """Open calibration dialog to set capture area"""
        if self.cap is None or cv2 is None:
            messagebox.showwarning("Calibración", "Cámara no disponible")
            return
        
        # Capture current frame
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Calibración", "No se pudo capturar imagen")
            return
        
        # Create modal dialog
        dialog = tk.Toplevel(self.parent)
        dialog.title("Calibrar Área de Captura")
        dialog.geometry("800x650")
        dialog.transient(self.parent)  # Make it a child window
        dialog.grab_set()  # Make it modal
        
        # Convert frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        adjusted, _ = self._apply_adjustments(frame_rgb)
        
        # Instructions at top
        instr_label = tk.Label(
            dialog,
            text="Arrastra el mouse para dibujar el área de captura",
            font=("Open Sans", 10),
            pady=10
        )
        instr_label.pack()
        
        # Canvas for drawing
        canvas = tk.Canvas(dialog, bg="#000000")
        canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Display image
        pil_img = Image.fromarray(adjusted)
        canvas_w = 780
        canvas_h = 500
        pil_img.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(pil_img)
        img_w, img_h = pil_img.size
        
        # Center image
        x_offset = (canvas_w - img_w) // 2
        y_offset = (canvas_h - img_h) // 2
        canvas.create_image(x_offset, y_offset, anchor="nw", image=photo)
        
        # Store reference
        canvas.photo = photo
        canvas.img_size = (img_w, img_h)
        canvas.offset = (x_offset, y_offset)
        canvas.orig_size = adjusted.shape[:2][::-1]  # (w, h)
        
        # Drawing state
        rect_start = [None, None]
        rect_id = [None]
        
        def on_mouse_down(event):
            rect_start[0] = event.x
            rect_start[1] = event.y
        
        def on_mouse_move(event):
            if rect_start[0] is not None:
                if rect_id[0]:
                    canvas.delete(rect_id[0])
                rect_id[0] = canvas.create_rectangle(
                    rect_start[0], rect_start[1],
                    event.x, event.y,
                    outline="#ff0000", width=2
                )
        
        def on_mouse_up(event):
            rect_start[0] = None
            rect_start[1] = None
        
        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_move)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        
        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def save_calibration():
            if rect_id[0]:
                coords = canvas.coords(rect_id[0])
                x1, y1, x2, y2 = coords
                
                # Convert to image coordinates
                x1 -= canvas.offset[0]
                y1 -= canvas.offset[1]
                x2 -= canvas.offset[0]
                y2 -= canvas.offset[1]
                
                # Normalize to original image size
                orig_w, orig_h = canvas.orig_size
                img_w, img_h = canvas.img_size
                
                x1_norm = (x1 / img_w)
                y1_norm = (y1 / img_h)
                x2_norm = (x2 / img_w)
                y2_norm = (y2 / img_h)
                
                # Clamp to [0, 1]
                x1_norm = max(0, min(1, x1_norm))
                y1_norm = max(0, min(1, y1_norm))
                x2_norm = max(0, min(1, x2_norm))
                y2_norm = max(0, min(1, y2_norm))
                
                self.calibration_area = {
                    'tl': (x1_norm, y1_norm),
                    'br': (x2_norm, y2_norm)
                }
                
                messagebox.showinfo("Calibración", "Área de captura guardada")
                dialog.grab_release()
                dialog.destroy()
            else:
                messagebox.showwarning("Calibración", "Dibuja un rectángulo primero")
        
        def cancel():
            dialog.grab_release()
            dialog.destroy()
        
        tk.Button(btn_frame, text="Guardar", command=save_calibration, width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancelar", command=cancel, width=12).pack(side="left", padx=5)
        
        # Center dialog on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def open_output_folder(self):
        """Open output directory in file explorer"""
        import subprocess
        import sys
        
        try:
            if sys.platform == "win32":
                subprocess.Popen(f'explorer "{self.output_dir}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.output_dir)])
            else:
                subprocess.Popen(["xdg-open", str(self.output_dir)])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir carpeta: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        self.close_camera()


class ScannerWindow(tk.Toplevel):
    """Standalone scanner window"""
    
    def __init__(self, master, project_dir: Optional[Path] = None):
        super().__init__(master)
        self.title("GeoDocs Scanner - Módulo de Captura")
        self.geometry("1000x850")
        
        # Set output directory
        if project_dir:
            self.output_dir = project_dir / "paginas"
        else:
            self.output_dir = Path.cwd() / "output_scan"
        
        # Create scanner
        self.scanner = CameraScanner(self, self.output_dir)
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_close(self):
        """Clean up before closing"""
        self.scanner.cleanup()
        self.destroy()


if __name__ == "__main__":
    # Test standalone
    root = tk.Tk()
    root.withdraw()
    win = ScannerWindow(root)
    root.mainloop()
