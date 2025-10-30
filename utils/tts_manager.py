#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tts_manager.py — Text-to-Speech manager with pyttsx3
"""
import threading
from pathlib import Path
from typing import Optional, Callable, List, Dict

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


class TTSManager:
    """Thread-safe TTS manager for text-to-speech functionality"""
    
    def __init__(self):
        self.engine = None
        self.is_speaking = False
        self.is_paused = False
        self.current_text = ""
        self._lock = threading.Lock()
        self._init_engine()
    
    def _init_engine(self):
        """Initialize pyttsx3 engine"""
        if not TTS_AVAILABLE:
            return
        
        try:
            self.engine = pyttsx3.init()
            
            # Default settings
            self.engine.setProperty('rate', 150)    # Speed
            self.engine.setProperty('volume', 0.9)  # Volume (0-1)
        except Exception as e:
            print(f"TTS initialization error: {e}")
            self.engine = None
    
    def get_voices(self) -> List[Dict[str, str]]:
        """Get list of available voices"""
        if not self.engine:
            return []
        
        voices = []
        try:
            for voice in self.engine.getProperty('voices'):
                voices.append({
                    'id': voice.id,
                    'name': voice.name,
                    'languages': getattr(voice, 'languages', []),
                    'gender': getattr(voice, 'gender', 'unknown')
                })
        except Exception:
            pass
        
        return voices
    
    def set_voice(self, voice_id: str) -> bool:
        """Set voice by ID"""
        if not self.engine:
            return False
        
        try:
            self.engine.setProperty('voice', voice_id)
            return True
        except Exception:
            return False
    
    def set_voice_by_language(self, lang_code: str = 'es') -> bool:
        """Set voice by language code"""
        if not self.engine:
            return False
        
        try:
            voices = self.engine.getProperty('voices')
            for voice in voices:
                voice_id = voice.id.lower()
                voice_name = voice.name.lower()
                
                # Check if language matches
                if lang_code in voice_id or lang_code in voice_name:
                    self.engine.setProperty('voice', voice.id)
                    return True
        except Exception:
            pass
        
        return False
    
    def set_rate(self, rate: int):
        """Set speech rate (words per minute)"""
        if self.engine:
            try:
                self.engine.setProperty('rate', rate)
            except Exception:
                pass
    
    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)"""
        if self.engine:
            try:
                self.engine.setProperty('volume', max(0.0, min(1.0, volume)))
            except Exception:
                pass
    
    def speak(self, text: str, wait: bool = False):
        """
        Speak text
        
        Args:
            text: Text to speak
            wait: If True, blocks until speech is complete
        """
        if not self.engine or not text:
            return
        
        with self._lock:
            if self.is_speaking:
                self.stop()
            
            self.current_text = text
            self.is_speaking = True
            self.is_paused = False
        
        if wait:
            self._speak_sync(text)
        else:
            thread = threading.Thread(target=self._speak_sync, args=(text,))
            thread.daemon = True
            thread.start()
    
    def _speak_sync(self, text: str):
        """Internal method for synchronous speech"""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")
        finally:
            with self._lock:
                self.is_speaking = False
                self.is_paused = False
    
    def pause(self):
        """Pause speech (if supported by platform)"""
        # Note: pyttsx3 doesn't support pause/resume on all platforms
        # This is a placeholder for future enhancement
        with self._lock:
            self.is_paused = True
    
    def resume(self):
        """Resume paused speech"""
        with self._lock:
            self.is_paused = False
    
    def stop(self):
        """Stop current speech"""
        if not self.engine:
            return
        
        try:
            self.engine.stop()
        except Exception:
            pass
        
        with self._lock:
            self.is_speaking = False
            self.is_paused = False
            self.current_text = ""
    
    def save_to_file(self, text: str, output_path: str) -> bool:
        """
        Save speech to audio file
        
        Args:
            text: Text to convert
            output_path: Output file path (.wav recommended)
        
        Returns:
            True if successful
        """
        if not self.engine or not text:
            return False
        
        try:
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"TTS save error: {e}")
            return False
    
    def speak_pages(
        self,
        pages: List[str],
        output_dir: str,
        base_name: str = "page",
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """
        Generate audio files for multiple pages
        
        Args:
            pages: List of text strings (one per page)
            output_dir: Directory to save audio files
            base_name: Base name for audio files
            progress_callback: Function to call with progress (current, total)
        
        Returns:
            List of generated file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        audio_files = []
        total = len(pages)
        
        for i, text in enumerate(pages, start=1):
            if progress_callback:
                progress_callback(i, total)
            
            output_file = output_path / f"{base_name}_{i:04d}.wav"
            
            if self.save_to_file(text, str(output_file)):
                audio_files.append(str(output_file))
        
        return audio_files
    
    def create_playlist(self, audio_files: List[str], output_path: str) -> bool:
        """
        Create M3U playlist from audio files
        
        Args:
            audio_files: List of audio file paths
            output_path: Path for M3U file
        
        Returns:
            True if successful
        """
        try:
            playlist_path = Path(output_path)
            
            # Get relative paths
            base_dir = playlist_path.parent
            entries = []
            
            for audio_file in audio_files:
                rel_path = Path(audio_file).relative_to(base_dir)
                entries.append(str(rel_path))
            
            # Write M3U
            content = "#EXTM3U\n" + "\n".join(entries)
            playlist_path.write_text(content, encoding='utf-8')
            
            return True
        except Exception as e:
            print(f"Playlist creation error: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if TTS is available and working"""
        return self.engine is not None


# Global instance
_tts_manager = None


def get_tts_manager() -> TTSManager:
    """Get or create global TTS manager instance"""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager()
    return _tts_manager


# Convenience functions
def speak(text: str, wait: bool = False):
    """Speak text using global TTS manager"""
    manager = get_tts_manager()
    manager.speak(text, wait)


def stop():
    """Stop current speech"""
    manager = get_tts_manager()
    manager.stop()


def is_speaking() -> bool:
    """Check if TTS is currently speaking"""
    manager = get_tts_manager()
    return manager.is_speaking


def get_voices() -> List[Dict[str, str]]:
    """Get available voices"""
    manager = get_tts_manager()
    return manager.get_voices()
