from services.capture_service import CaptureService
import numpy as np

def test_preprocess_shapes():
    svc = CaptureService()
    img = np.zeros((80,100,3), dtype=np.uint8)
    g, stacked = svc.preprocess(img)
    assert g.shape == (80,100)
    assert stacked.shape == (80,100,3)

def test_start_and_stop(monkeypatch):
    class FakeCap:
        def __init__(self, idx):
            self.opened = True
        def isOpened(self): return True
        def read(self):
            return True, np.zeros((10,10,3), dtype=np.uint8)
        def release(self): self.opened = False
    monkeypatch.setattr('cv2.VideoCapture', FakeCap)
    svc = CaptureService()
    assert svc.start() is True
    frame = svc.read_frame()
    assert frame is not None and frame.shape == (10,10,3)
    svc.stop()
    assert svc.cap is None

def test_start_failure(monkeypatch):
    class BadCap:
        def __init__(self, idx): pass
        def isOpened(self): return False
        def release(self): pass
    monkeypatch.setattr('cv2.VideoCapture', BadCap)
    svc = CaptureService()
    assert svc.start() is False
    assert svc.cap is None

def test_capture_and_save_success(monkeypatch, tmp_path):
    # Patch cv2.imwrite to succeed
    monkeypatch.setattr('cv2.imwrite', lambda path, frame: True)
    svc = CaptureService()
    frame = np.zeros((5,5,3), dtype=np.uint8)
    out = tmp_path/'ok.png'
    assert svc.capture_and_save(frame, out) is True
    # ensure file created logically (we don't rely on real write in stub)

def test_capture_and_save_failure(monkeypatch, tmp_path):
    def fake_imwrite(path, frame):
        raise RuntimeError('disk error')
    monkeypatch.setattr('cv2.imwrite', fake_imwrite)
    svc = CaptureService()
    frame = np.zeros((5,5,3), dtype=np.uint8)
    out = tmp_path/'fail.png'
    assert svc.capture_and_save(frame, out) is False
