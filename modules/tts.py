
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tts.py — Texto a voz para OCR original y corregido.
- pyttsx3 (offline) -> WAV/AIFF
- gTTS (opcional, si disponible y con internet) -> MP3
- In-app playback via simpleaudio/playsound
"""
from pathlib import Path

def synth_to_file(text: str, out_path: str, voice_lang: str = "es"):
    # Try pyttsx3 first (offline)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        # select spanish voice if available
        try:
            for v in engine.getProperty("voices"):
                if voice_lang in (v.id or "") or voice_lang in (v.name or "").lower():
                    engine.setProperty("voice", v.id); break
        except Exception:
            pass
        engine.save_to_file(text or "", out_path)
        engine.runAndWait()
        return True, out_path
    except Exception:
        pass
    # Fallback: gTTS (needs internet)
    try:
        from gtts import gTTS
        tts = gTTS(text=text or "", lang=voice_lang[:2] if voice_lang else "es")
        mp3_path = str(Path(out_path).with_suffix(".mp3"))
        tts.save(mp3_path)
        return True, mp3_path
    except Exception:
        # ultimate fallback: save txt
        txt_path = str(Path(out_path).with_suffix(".txt"))
        Path(txt_path).write_text(text or "", encoding="utf-8")
        return False, txt_path

def play_audio(path: str):
    """Attempts to play audio in-app. Returns (ok, backend)."""
    try:
        import simpleaudio as sa
        if path.lower().endswith(".wav"):
            wave_obj = sa.WaveObject.from_wave_file(path)
            play_obj = wave_obj.play()
            return True, "simpleaudio"
    except Exception:
        pass
    try:
        from playsound import playsound
        playsound(path, block=False)
        return True, "playsound"
    except Exception:
        return False, "none"


def list_voices(lang_filter: str = None):
    """Return available voices (id,name,lang) if pyttsx3 is available."""
    out = []
    try:
        import pyttsx3
        engine = pyttsx3.init()
        for v in engine.getProperty("voices"):
            out.append({"id": getattr(v, "id", ""), "name": getattr(v, "name", ""), "lang": getattr(v, "languages", "")})
    except Exception:
        pass
    # gTTS langs minimal list (not exhaustive)
    out.append({"id":"gtts:es","name":"gTTS Español","lang":"es"})
    out.append({"id":"gtts:en","name":"gTTS English","lang":"en"})
    return out

def synth_to_file_opts(text: str, out_path: str, voice_id: str = None, rate: int = None, volume: float = None, voice_lang: str = "es"):
    # Try pyttsx3 with options
    try:
        import pyttsx3
        engine = pyttsx3.init()
        if voice_id:
            try: engine.setProperty("voice", voice_id)
            except Exception: pass
        else:
            # pick by lang
            try:
                for v in engine.getProperty("voices"):
                    if voice_lang in (v.id or "") or voice_lang in (v.name or "").lower():
                        engine.setProperty("voice", v.id); break
            except Exception: pass
        if rate is not None:
            try: engine.setProperty("rate", int(rate))
            except Exception: pass
        if volume is not None:
            try: engine.setProperty("volume", float(volume))
            except Exception: pass
        engine.save_to_file(text or "", out_path)
        engine.runAndWait()
        return True, out_path
    except Exception:
        pass
    # gTTS fallback (no rate/volume control)
    try:
        from gtts import gTTS
        lang = voice_lang[:2] if voice_lang else "es"
        if voice_id and voice_id.startswith("gtts:"):
            lang = voice_id.split(":")[1]
        tts = gTTS(text=text or "", lang=lang)
        mp3_path = str(Path(out_path).with_suffix(".mp3"))
        tts.save(mp3_path)
        return True, mp3_path
    except Exception:
        txt_path = str(Path(out_path).with_suffix(".txt"))
        Path(txt_path).write_text(text or "", encoding="utf-8")
        return False, txt_path

def concat_wav(files, out_path):
    """Concatenate WAV files with same params."""
    if not files: return False, "No files"
    import wave
    params = None
    frames = []
    for f in files:
        if not str(f).lower().endswith(".wav"):
            return False, "Solo WAV para concatenación"
        with wave.open(f, 'rb') as w:
            if params is None:
                params = w.getparams()
            elif w.getparams()[:3] != params[:3]:
                return False, "Parámetros WAV incompatibles"
            frames.append(w.readframes(w.getnframes()))
    with wave.open(out_path, 'wb') as out:
        out.setparams(params)
        for fr in frames:
            out.writeframes(fr)
    return True, out_path

def synth_audiobook(pages_text, out_dir: str, base_name: str = "audiobook", voice_id: str = None, rate: int = None, volume: float = None, voice_lang: str = "es"):
    """Generate per-page audio and playlist; try to concatenate WAV if possible."""
    outd = Path(out_dir); outd.mkdir(parents=True, exist_ok=True)
    tracks = []
    for i, txt in enumerate(pages_text, start=1):
        tgt = outd / f"{base_name}_p{i:04d}.wav"
        ok, path = synth_to_file_opts(txt, str(tgt), voice_id=voice_id, rate=rate, volume=volume, voice_lang=voice_lang)
        tracks.append(path)
    # playlist M3U
    m3u = outd / f"{base_name}.m3u"
    m3u.write_text("\n".join([str(Path(t).name) for t in tracks]), encoding="utf-8")
    # try concat WAV
    if all(str(t).lower().endswith(".wav") for t in tracks):
        concat = outd / f"{base_name}.wav"
        ok, merged = concat_wav(tracks, str(concat))
        merged_path = str(concat) if ok else None
    else:
        merged_path = None
    # CUE (simple)
    cue = outd / f"{base_name}.cue"
    cue_lines = ["FILE "{}" WAVE".format(Path(tracks[0]).name if tracks else base_name+".wav")]
    mm, ss, ff = 0, 0, 0
    for i, t in enumerate(tracks, start=1):
        cue_lines.append(f"  TRACK {i:02d} AUDIO")
        cue_lines.append(f"    INDEX 01 {mm:02d}:{ss:02d}:{ff:02d}")
        # naive time advance unknown without reading durations; leave 00:00
    cue.write_text("\n".join(cue_lines), encoding="utf-8")
    return {"tracks": tracks, "playlist": str(m3u), "merged": merged_path, "cue": str(cue)}
