#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils.window_utils — Window geometry helpers
"""
import tkinter as tk


def center_to_parent(win: tk.Misc, parent: tk.Misc | None, dx: int = 0, dy: int = 0) -> None:
    """Center window 'win' over 'parent'. Safe no-op if sizes unknown yet."""
    try:
        if win is None:
            return
        win.update_idletasks()
        # Window size
        w = win.winfo_width()
        h = win.winfo_height()
        # Fallback minimal size if not yet calculated
        if w <= 1 or h <= 1:
            try:
                w = int(win.winfo_reqwidth())
                h = int(win.winfo_reqheight())
            except Exception:
                pass
        if parent is None:
            # Center on screen
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            x = (sw - w) // 2 + dx
            y = (sh - h) // 2 + dy
        else:
            parent.update_idletasks()
            px = parent.winfo_x()
            py = parent.winfo_y()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            if pw <= 1 or ph <= 1:
                try:
                    pw = int(parent.winfo_reqwidth())
                    ph = int(parent.winfo_reqheight())
                except Exception:
                    pass
            x = px + (pw - w) // 2 + dx
            y = py + (ph - h) // 2 + dy
        x = max(0, int(x))
        y = max(0, int(y))
        try:
            win.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            # If size controlled elsewhere, just move
            try:
                win.geometry(f"+{x}+{y}")
            except Exception:
                pass
    except Exception:
        pass
