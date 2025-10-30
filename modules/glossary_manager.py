
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
glossary_manager.py — CRUD de glosarios y diccionarios (proyecto/tema/global),
incluye abreviaturas académicas y utilidades para integrarse con revisión/expansión.
"""
import json, sqlite3, datetime
from pathlib import Path

def db(db_path): 
    con = sqlite3.connect(db_path); con.row_factory = sqlite3.Row
    return con

def list_glossaries(db_path, scope=None):
    con = db(db_path)
    q = "SELECT * FROM glossary" + ("" if not scope else " WHERE scope=?")
    rows = con.execute(q, (scope,) if scope else ()).fetchall(); con.close()
    return [dict(r) for r in rows]

def create_glossary(db_path, scope, name, language, terms: dict):
    con = db(db_path)
    con.execute("INSERT INTO glossary(scope,name,language,terms_json,updated_at) VALUES (?,?,?,?,datetime('now'))",
                (scope, name, language, json.dumps(terms, ensure_ascii=False)))
    con.commit(); con.close(); return True

def update_glossary(db_path, gid, terms: dict=None, name: str=None):
    con = db(db_path)
    row = con.execute("SELECT * FROM glossary WHERE id=?", (gid,)).fetchone()
    if not row: con.close(); return False
    new_terms = json.dumps(terms, ensure_ascii=False) if terms is not None else row["terms_json"]
    new_name = name or row["name"]
    con.execute("UPDATE glossary SET name=?, terms_json=?, updated_at=datetime('now') WHERE id=?", (new_name, new_terms, gid))
    con.commit(); con.close(); return True

def delete_glossary(db_path, gid):
    con = db(db_path); con.execute("DELETE FROM glossary WHERE id=?", (gid,)); con.commit(); con.close(); return True

def get_terms(db_path, language='es'):
    con = db(db_path)
    rows = con.execute("SELECT terms_json FROM glossary WHERE language=? ORDER BY scope DESC, updated_at DESC", (language,)).fetchall()
    con.close()
    terms = {}
    for r in rows:
        try:
            d = json.loads(r["terms_json"] or "{}"); terms.update(d)
        except Exception: pass
    return terms

def apply_abbreviation_hints(text: str, terms: dict):
    """Devuelve lista de sugerencias (offset, length, abbr, expansion). No altera el texto."""
    import re
    hints = []
    for abbr, expansion in terms.items():
        try:
            for m in re.finditer(r'\b'+re.escape(abbr)+r'\b', text):
                hints.append({"offset": m.start(), "length": len(abbr), "abbr": abbr, "expansion": expansion})
        except Exception:
            continue
    return hints
