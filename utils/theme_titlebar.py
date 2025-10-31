#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils.theme_titlebar — Helper to apply Windows title bar color matching ttkbootstrap theme
Works on Windows 10/11 with pywinstyles; no-ops elsewhere or when unavailable.
"""
from __future__ import annotations

from typing import Optional

try:
    import pywinstyles  # type: ignore
except Exception:  # pragma: no cover
    pywinstyles = None  # type: ignore

# Optional: ttkbootstrap for theme colors
try:
    import ttkbootstrap as ttkb  # type: ignore
except Exception:
    ttkb = None  # type: ignore


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _relative_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    # sRGB to linear
    def srgb_to_linear(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    R = srgb_to_linear(r)
    G = srgb_to_linear(g)
    B = srgb_to_linear(b)
    return 0.2126 * R + 0.7152 * G + 0.0722 * B


def _get_ttkb_colors() -> Optional[object]:
    if ttkb is None:
        return None
    try:
        style = ttkb.Style()
        # Access color palette object
        return getattr(style, 'colors', None)
    except Exception:
        return None


def _pick_header_color() -> tuple[str, str]:
    """
    Returns a tuple: (header_hex_color, style_mode) where style_mode is 'dark' or 'light'.
    Tries to use ttkbootstrap style colors; falls back to a sensible default.
    """
    colors = _get_ttkb_colors()
    if colors:
        # Prefer background for window surfaces; fallback to primary if missing
        header = getattr(colors, 'bg', None) or colors.get('bg', None) if hasattr(colors, 'get') else None
        if not header:
            header = getattr(colors, 'primary', None) or colors.get('primary', '#2b3e50')
        try:
            lum = _relative_luminance(header)
        except Exception:
            header, lum = '#2b3e50', 0.1
        mode = 'dark' if lum < 0.5 else 'light'
        return header, mode
    # Default aligned with ttkbootstrap 'superhero' background
    return '#2b3e50', 'dark'


def apply_titlebar_theme(win) -> None:
    """Apply Windows 10/11 title bar styling to the given Tk/Toplevel window.
    Safe no-op when pywinstyles isn't available or on unsupported platforms.
    """
    if pywinstyles is None or win is None:
        return
    try:
        header, mode = _pick_header_color()
        pywinstyles.apply_style(win, mode)
        pywinstyles.change_header_color(win, header)
    except Exception:
        # Silently ignore if not supported in current environment
        pass
