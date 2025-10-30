
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context_rules.py — Aplica reglas por zona a políticas de estilo.
Zonas esperadas en HTML: data-zone="footnote|quote|caption|bibliography"
"""
import re
from bs4 import BeautifulSoup

def extract_zones(html: str):
    soup = BeautifulSoup(html or '', 'lxml')
    zones = []
    for el in soup.find_all(attrs={"data-zone": True}):
        zones.append({"zone": el.get("data-zone"), "text": el.get_text(" ", strip=True)})
    return zones

def apply_context(style_rules: dict, html: str):
    """Devuelve reglas derivadas por zona (no altera html): lista de {zone, overrides}"""
    soup = BeautifulSoup(html or '', 'lxml')
    overrides = []
    crules = style_rules.get('context_rules') or []
    for el in soup.find_all(attrs={"data-zone": True}):
        zone = el.get("data-zone")
        ov = {}
        for r in crules:
            cond = (r.get('if') or {})
            then = (r.get('then') or {})
            if cond.get('zone') == zone:
                for k,v in then.items():
                    ov[k] = v
        if ov: overrides.append({"zone": zone, "overrides": ov})
    return overrides
