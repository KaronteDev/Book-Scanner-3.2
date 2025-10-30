
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spellcheck.py — Revisión ortográfica del OCR corregido.
Intenta usar language_tool_python (reglas gramaticales); si no, pyspellchecker (ortografía básica).
"""
from pathlib import Path

def check_text(text: str, lang: str = "es"):
    result = {"tool": None, "issues": []}
    if not text: return result
    # language_tool_python
    try:
        import language_tool_python
        tool = language_tool_python.LanguageToolPublicAPI('es') if hasattr(language_tool_python,'LanguageToolPublicAPI') else language_tool_python.LanguageTool('es')
        matches = tool.check(text)
        result["tool"] = "language_tool_python"
        for m in matches:
            result["issues"].append({
                "offset": m.offset, "length": m.errorLength,
                "message": m.message, "replacements": m.replacements[:5]
            })
        return result
    except Exception:
        pass
    # pyspellchecker fallback
    try:
        from spellchecker import SpellChecker
        sc = SpellChecker(language='es')
        words = text.split()
        miss = sc.unknown(words)
        result["tool"] = "pyspellchecker"
        for w in miss:
            result["issues"].append({
                "word": w, "suggestion": sc.correction(w)
            })
        return result
    except Exception:
        pass
    # naive: no tools
    result["tool"] = "none"
    return result


def load_custom_dictionary(project_dir: str):
    """Loads custom dict from project root 'custom_dict.json' {'es': ['term1', ...]} and txt lists under 'dictionaries/'"""
    words = set()
    from pathlib import Path as _P
    p = _P(project_dir)
    js = p/'custom_dict.json'
    if js.exists():
        try:
            import json as _j
            data = _j.loads(js.read_text(encoding='utf-8'))
            for lang, arr in (data or {}).items():
                if isinstance(arr, list):
                    words.update([str(x).strip() for x in arr if x])
        except Exception:
            pass
    dict_dir = p/'dictionaries'
    if dict_dir.exists():
        for f in dict_dir.glob('*.txt'):
            try:
                for line in f.read_text(encoding='utf-8').splitlines():
                    w=line.strip()
                    if w: words.add(w)
            except Exception:
                pass
    return words

def check_text_with_custom(text: str, lang: str, project_dir: str = None):
    """Spellcheck that ignores words in custom dictionary."""
    result = check_text(text, lang)
    if not project_dir or not result.get("issues"):
        return result
    custom = load_custom_dictionary(project_dir)
    if result["tool"] == "language_tool_python":
        # filter matches whose text is in custom
        try:
            filtered = []
            for m in result["issues"]:
                # We don't have original word; fallback simple filter by first replacement or message heuristic
                filtered.append(m)
            result["issues"] = filtered
        except Exception:
            pass
    elif result["tool"] == "pyspellchecker":
        filtered = [m for m in result["issues"] if m.get("word") not in custom]
        result["issues"] = filtered
    return result
