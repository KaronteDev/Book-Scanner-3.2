
import os
# Suppress OpenCV logging before import - set to SILENT level
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

import subprocess, shutil
try:
    import cv2
    # Additional runtime suppression (though env vars should handle most)
    try:
        cv2.setLogLevel(0)  # 0 = SILENT
    except Exception:
        pass
except Exception:
    cv2=None
class AutoExposureController:
    def __init__(self, camera_index=0):
        self.camera_index=camera_index; self.cap=None
    def start(self):
        if cv2 is None: return False, "OpenCV no disponible"
        # Try default backend first (auto-selection), fallback to DSHOW if needed
        try:
            self.cap=cv2.VideoCapture(self.camera_index)
            if not self.cap or not self.cap.isOpened():
                # Try DSHOW explicitly if default fails
                self.cap=cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        except Exception:
            # Last resort fallback
            self.cap=cv2.VideoCapture(self.camera_index)
        if not self.cap or not self.cap.isOpened(): return False, "No se pudo abrir la cámara"
        try: self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        except Exception: pass
        return True, "Auto-exposición habilitada (si el backend lo permite)"
    def set_manual_exposure(self, value: float):
        if not self.cap: return False
        try:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
            return self.cap.set(cv2.CAP_PROP_EXPOSURE, float(value))
        except Exception: return False
    def stop(self):
        try:
            if self.cap: self.cap.release()
        except Exception: pass
    def gphoto_set(self, shutter_speed="1/60", iso="400"):
        if not shutil.which("gphoto2"): return False, "gphoto2 no encontrado"
        try:
            subprocess.check_call(["gphoto2","--set-config","/main/capturesettings/shutterspeed="+shutter_speed])
            subprocess.check_call(["gphoto2","--set-config","/main/imgsettings/iso="+iso])
            return True, "Parámetros aplicados por gphoto2"
        except Exception as ex:
            return False, str(ex)


def auto_adjust_loop(self, target_mean=0.5, max_iters=50, sleep_sec=0.05):
    """Ajuste de exposición simple basado en histograma (si el backend lo soporta).
    target_mean en [0..1] luminancia normalizada.
    """
    if not self.cap: return False, "Cámara no inicializada"
    import time
    import numpy as np
    try:
        # pasar a modo manual
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
        exp = self.cap.get(cv2.CAP_PROP_EXPOSURE)
        for _ in range(max_iters):
            ok, frame = self.cap.read()
            if not ok: break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean = gray.mean()/255.0
            err = target_mean - mean
            if abs(err) < 0.02:
                break
            # control proporcional básico; muchos drivers usan escala negativa
            step = (0.2 if exp < 0 else 20.0) * err
            exp = exp + step
            self.cap.set(cv2.CAP_PROP_EXPOSURE, exp)
            time.sleep(sleep_sec)
        return True, f"Exposición ajustada (~mean={mean:.2f})"
    except Exception as ex:
        return False, str(ex)
