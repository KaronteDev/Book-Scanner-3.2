from typing import Optional

class TTSService:
    """Servicio TTS.

    Objetivos:
    - Proporcionar interfaz uniforme para pyttsx3 (offline) y gTTS (online).
    - Permitir selección de voz, velocidad y volumen.
    - Generar archivo de audio temporal y reproducir (simpleaudio/playsound).
    - Cache opcional de fragmentos ya sintetizados.
    """

    def __init__(self, engine_preference: str = 'pyttsx3'):
        self.engine_preference = engine_preference
        self._engine = None
        self._init_engine()

    def _init_engine(self):
        if self.engine_preference == 'pyttsx3':
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
            except Exception:
                self._engine = None

    def speak(self, text: str) -> Optional[str]:
        """Sintetiza el texto. Devuelve ruta del audio si se genera.

        Implementación actual stub: si hay pyttsx3 disponible, reproduce directamente.
        Futuro: retornar WAV/MP3 y registro en DB.
        """
        if not text:
            return None
        if self._engine:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                return None
            except Exception:
                return None
        # Fallback gTTS ejemplo (comentado para evitar dependencia inmediata):
        # from gtts import gTTS
        # tts = gTTS(text=text, lang='es')
        # out = 'tts_output.mp3'
        # tts.save(out)
        # return out
        return None
