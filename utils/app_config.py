#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app_config.py — Utilidad para cargar y guardar la configuración de la aplicación
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _base_dir() -> Path:
    # utils/ -> repo root
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return _base_dir() / "data" / "app_config.json"


def load_config() -> Dict[str, Any]:
    cfg_path = config_path()
    if not cfg_path.exists():
        return {}
    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # En caso de error devolvemos dict vacío para no romper la app
        return {}


def save_config(cfg: Dict[str, Any]) -> bool:
    cfg_path = config_path()
    try:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with cfg_path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def get_theme(default: str = "superhero") -> str:
    cfg = load_config() or {}
    return (
        cfg.get("ui", {}).get("theme")
        or default
    )


def set_theme(theme: str) -> bool:
    cfg = load_config() or {}
    ui = cfg.setdefault("ui", {})
    ui["theme"] = theme
    return save_config(cfg)


def get_root_dir() -> Path:
    cfg = load_config() or {}
    paths = cfg.get("paths", {})
    root = paths.get("root_dir")
    if root:
        p = Path(root)
        return p
    # Por defecto, raíz en el directorio del proyecto
    return _base_dir()


def set_root_dir(path: Path | str) -> bool:
    p = Path(path)
    cfg = load_config() or {}
    paths = cfg.setdefault("paths", {})
    paths["root_dir"] = str(p)
    return save_config(cfg)


def get_config() -> Dict[str, Any]:
    """Convenience: devuelve la configuración completa (mutarla con cuidado)."""
    return load_config() or {}


# --- UI preferences helpers ---
def get_ui_prefs() -> Dict[str, Any]:
    cfg = load_config() or {}
    return cfg.get("ui", {})


def set_ui_prefs(**kwargs) -> bool:
    cfg = load_config() or {}
    ui = cfg.setdefault("ui", {})
    for k, v in kwargs.items():
        ui[k] = v
    return save_config(cfg)


def get_window_geometry(name: str) -> Optional[str]:
    cfg = load_config() or {}
    ui = cfg.get("ui", {})
    geos = ui.get("window_geometry", {})
    if isinstance(geos, dict):
        val = geos.get(name)
        if isinstance(val, str):
            return val
    return None


def set_window_geometry(name: str, geometry: str) -> bool:
    cfg = load_config() or {}
    ui = cfg.setdefault("ui", {})
    geos = ui.setdefault("window_geometry", {})
    geos[name] = geometry
    return save_config(cfg)


def resolve_path(key: str, ensure: bool = False) -> Path:
    """Return absolute path for a paths.* key joined with root_dir.
    If ensure=True, create the directory.
    """
    cfg = load_config() or {}
    root = get_root_dir()
    sub = (cfg.get("paths", {}) or {}).get(key)
    if not sub:
        # default to key name if not configured
        sub = key
    p = root / str(sub)
    if ensure:
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
    return p
