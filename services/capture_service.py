import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional

class CaptureService:
    """Encapsula lógica de cámara y preprocesamiento para separación MVC."""
    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False

    def start(self) -> bool:
        if self.running:
            return True
        self.cap = cv2.VideoCapture(self.device_index)
        if not self.cap.isOpened():
            self.cap = None
            self.running = False
            return False
        self.running = True
        return True

    def stop(self) -> None:
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def read_frame(self) -> Optional[np.ndarray]:
        if not self.running or not self.cap:
            return None
        ok, frame = self.cap.read()
        if not ok:
            return None
        return frame

    def preprocess(self, bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        g = cv2.GaussianBlur(g, (5,5), 0)
        e = cv2.Canny(g, 50, 150)
        e = cv2.dilate(e, np.ones((3,3), np.uint8), iterations=1)
        stacked = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        stacked[e>0] = (0,255,0)
        return g, stacked

    def capture_and_save(self, frame: np.ndarray, out_path: Path) -> bool:
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out_path), frame)
            return True
        except Exception:
            return False
