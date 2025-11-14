from typing import Optional
import os

class OCRService:
    """Servicio OCR.

    Responsabilidades previstas:
    - Cargar configuración desde `ocr_config.json` (idioma, PSM, OEM).
    - Delegar a pytesseract (o motor alternativo) y preprocesar imagen (binarización, deskew, etc.).
    - Retornar texto y/o estructura (para futuro hOCR/ALTO).
    - Registrar métricas (tiempo procesamiento, longitud texto, calidad estimada).
    """

    def __init__(self, config_path: str = 'ocr_config.json'):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if os.path.exists(self.config_path):
            import json
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def recognize_page(self, image_path: str) -> str:
        """Realiza OCR sobre la imagen indicada.

        Fallback actual: devuelve cadena vacía (stub). Cuando se integre pytesseract:
        ```python
        import pytesseract, cv2
        img = cv2.imread(image_path)
        text = pytesseract.image_to_string(img, lang=self.config.get('lang','spa'))
        return text
        ```
        """
        return ""
