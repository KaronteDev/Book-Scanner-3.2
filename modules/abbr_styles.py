
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
abbr_styles.py — Políticas de estilo para abreviaturas.
Devuelve reglas simples: expand_always, keep_as_is, expand_first_occurrence
"""
def get_style(name: str):
    name = (name or '').lower()
    if 'chicago' in name:
        return {'expand_first_occurrence': True, 'keep_as_is': [], 'expand_always': []}
    if 'apa' in name:
        return {'expand_first_occurrence': True, 'keep_as_is': ['etc.'], 'expand_always': []}
    if 'mla' in name:
        return {'expand_first_occurrence': True, 'keep_as_is': [], 'expand_always': []}
    if 'csic' in name or 'spanish' in name:
        return {'expand_first_occurrence': True, 'keep_as_is': ['s. f.','s. l.','s. n.'], 'expand_always': []}
    # default
    return {'expand_first_occurrence': False, 'keep_as_is': [], 'expand_always': []}


def get_style_detail(name: str, lang: str = "es"):
    name = (name or '').lower()
    # defaults per language
    keep_lang = ['etc.'] if lang.startswith('en') else ['s. f.', 's. l.', 's. n.']
    detail = {'expand_first_occurrence': True, 'keep_as_is': keep_lang, 'expand_always': []}
    if 'chicago' in name:
        detail['edition'] = '17th'
    if 'apa' in name:
        detail['edition'] = '7th'
        detail['keep_as_is'] = keep_lang + ['e.g.','i.e.']
    if 'mla' in name:
        detail['edition'] = '9th'
    if 'csic' in name:
        detail['edition'] = 'CSIC'
    return detail
