
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diff_engine.py — Diff a nivel token con estrategia tipo Patience (simplificada).
Devuelve lista de cambios: tokens con tipo ('keep'|'ins'|'del'|'sub').
"""
import re

def tokenize(text: str):
    # Palabras, signos, espacios; preserva posición aproximada
    tokens = re.findall(r'\w+|[^\w\s]|\s+', text, flags=re.UNICODE)
    return tokens

def diff_tokens(a_tokens, b_tokens):
    # Si iguales
    if a_tokens == b_tokens:
        return [('keep', t) for t in a_tokens]
    # Índices por token para coincidencias rápidas
    index = {}
    for i,t in enumerate(b_tokens):
        index.setdefault(t, []).append(i)
    used_b = set()
    result = []
    ai = 0; bi = 0
    while ai < len(a_tokens) and bi < len(b_tokens):
        if a_tokens[ai] == b_tokens[bi]:
            result.append(('keep', a_tokens[ai])); ai += 1; bi += 1; continue
        # buscar próxima coincidencia de a_tokens[ai] en b
        nxt = None
        for j in index.get(a_tokens[ai], []):
            if j >= bi and j not in used_b:
                nxt = j; break
        if nxt is None:
            # a[ai] eliminado o sustituido
            # si el siguiente b coincide con el siguiente a -> inserción en b
            if ai+1 < len(a_tokens) and bi < len(b_tokens) and a_tokens[ai+1] == b_tokens[bi]:
                result.append(('ins', b_tokens[bi])); used_b.add(bi); bi += 1
            else:
                result.append(('del', a_tokens[ai])); ai += 1
        else:
            # insertar b[bi:nxt] como ins
            while bi < nxt:
                result.append(('ins', b_tokens[bi])); used_b.add(bi); bi += 1
            # ahora coincide
            result.append(('keep', a_tokens[ai])); ai += 1; bi += 1
    # remanentes
    while ai < len(a_tokens):
        result.append(('del', a_tokens[ai])); ai += 1
    while bi < len(b_tokens):
        result.append(('ins', b_tokens[bi])); bi += 1
    # compactar sustituciones: patrón del+ins cercano -> sub
    compact = []
    i = 0
    while i < len(result):
        if i+1 < len(result) and result[i][0]=='del' and result[i+1][0]=='ins':
            compact.append(('sub', (result[i][1], result[i+1][1])))
            i += 2
        else:
            compact.append(result[i]); i += 1
    return compact

def diff_text(a: str, b: str):
    ta = tokenize(a or '')
    tb = tokenize(b or '')
    return diff_tokens(ta, tb)
