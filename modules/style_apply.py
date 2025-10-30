
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
style_apply.py — Aplica políticas de abreviaturas a un documento completo:
- Expansión solo en la primera mención (por abreviatura)
- Respeta 'keep_as_is' y 'expand_always'
- Genera registro de cambios (CSV/JSON)
"""
import re, json, sqlite3, csv, time
from pathlib import Path

def _strip_html(html):
    return re.sub("<[^<]+?>", " ", html or "")

def load_terms(db_path: str, language='es'):
    import json as _j, sqlite3
    con = sqlite3.connect(db_path); con.row_factory=sqlite3.Row
    rows = con.execute("SELECT terms_json FROM glossary WHERE language=?", (language,)).fetchall()
    con.close()
    terms = {}
    for r in rows:
        try: terms.update(_j.loads(r["terms_json"] or "{}"))
        except: pass
    return terms

def apply_style_to_document(db_path: str, document_id: int, style_rules: dict, out_dir: str, language='es'):
    con = sqlite3.connect(db_path); con.row_factory=sqlite3.Row
    pages = con.execute("SELECT id, seq, ocr_html FROM page WHERE document_id=? ORDER BY seq", (int(document_id),)).fetchall()
    terms = load_terms(db_path, language)
    keep = set(style_rules.get('keep_as_is') or [])
    expand_always = set(style_rules.get('expand_always') or [])
    expand_first = bool(style_rules.get('expand_first_occurrence', True))

    seen = set()  # abreviaturas ya expandidas
    changes = []  # para changelog

    for p in pages:
        html = p["ocr_html"] or ""
        txt = _strip_html(html)
        new_html = html
        # Primero, expand_always
        for ab, ex in terms.items():
            if ab in expand_always and ab not in keep:
                # reemplazo simple en html visible (evitar tags)
                new_html = re.sub(r'(>[^<]*)\\b'+re.escape(ab)+r'\\b', lambda m: m.group(0).replace(ab, ex), new_html)

        # Luego, 1ª mención si procede
        if expand_first:
            for ab, ex in terms.items():
                if ab in keep or ab in expand_always: 
                    continue
                if ab not in seen:
                    # buscar primera ocurrencia en html textual
                    pat = re.compile(r'(>[^<]*)\\b'+re.escape(ab)+r'\\b')
                    m = pat.search(new_html)
                    if m:
                        before = new_html
                        new_html = pat.sub(lambda mm: mm.group(0).replace(ab, f'<span class="abbr-expanded" data-orig="{ab}">{ex}</span>'), new_html, count=1)
                        seen.add(ab)
                        changes.append({
                            "page_id": p["id"], "seq": p["seq"],
                            "abbr": ab, "expansion": ex,
                            "action": "expand_first_occurrence"
                        })

        # Guardar si cambió
        if new_html != html:
            con.execute("UPDATE page SET ocr_html=? WHERE id=?", (new_html, p["id"]))
    con.commit(); con.close()

    # Changelog
    outp = Path(out_dir); outp.mkdir(parents=True, exist_ok=True)
    csv_path = outp / f"changes_doc_{document_id}.csv"
    json_path = outp / f"changes_doc_{document_id}.json"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["page_id","seq","abbr","expansion","action"])
        w.writeheader(); w.writerows(changes)
    Path(json_path).write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"changes_csv": str(csv_path), "changes_json": str(json_path), "count": len(changes)}


from bs4 import BeautifulSoup
from .context_rules import apply_context

def _apply_in_element(el, terms, rules, seen):
    """Apply expand_always and first occurrence within a single element (BeautifulSoup Tag)."""
    html = str(el)
    # Expand always
    for ab, ex in terms.items():
        if ab in (rules.get('keep_as_is') or []): 
            continue
        if ab in (rules.get('expand_always') or []):
            html = re.sub(r'(>[^<]*)\b'+re.escape(ab)+r'\b', lambda m: m.group(0).replace(ab, ex), html)
    # First occurrence
    if rules.get('expand_first_occurrence', True):
        for ab, ex in terms.items():
            if ab in (rules.get('keep_as_is') or []) or ab in (rules.get('expand_always') or []):
                continue
            if ab not in seen:
                pat = re.compile(r'(>[^<]*)\b'+re.escape(ab)+r'\b')
                if pat.search(html):
                    html = pat.sub(lambda mm: mm.group(0).replace(ab, f'<span class="abbr-expanded" data-orig="{ab}">{ex}</span>'), html, count=1)
                    seen.add(ab)
    return BeautifulSoup(html, 'lxml')

def apply_style_with_context(db_path: str, document_id: int, style_rules: dict, out_dir: str, language='es'):
    """Like apply_style_to_document but honoring context_rules per element with data-zone."""
    con = sqlite3.connect(db_path); con.row_factory=sqlite3.Row
    pages = con.execute("SELECT id, seq, ocr_html FROM page WHERE document_id=? ORDER BY seq", (int(document_id),)).fetchall()
    terms = load_terms(db_path, language)
    base_rules = {
        "expand_first_occurrence": bool(style_rules.get('expand_first_occurrence', True)),
        "keep_as_is": list(style_rules.get('keep_as_is') or []),
        "expand_always": list(style_rules.get('expand_always') or []),
        "context_rules": style_rules.get('context_rules') or []
    }
    changes = []
    seen = set()
    for p in pages:
        html = p["ocr_html"] or ""
        soup = BeautifulSoup(html, 'lxml')
        # default apply to whole doc first-pass minimal (expand_always global)
        # then per zone overrides
        # Global expand_always (outside zones too)
        new_html = re.sub(r'(>[^<]*)', lambda m: m.group(0), html)  # no-op placeholder
        # Per-zone overrides
        for el in soup.find_all(attrs={"data-zone": True}):
            zone = el.get("data-zone")
            overrides = {}
            for r in base_rules["context_rules"]:
                cond = (r.get('if') or {})
                then = (r.get('then') or {})
                if cond.get('zone') == zone:
                    overrides.update(then)
            zrules = dict(base_rules); 
            zrules.update(overrides)
            new_el = _apply_in_element(el, terms, zrules, seen)
            el.replace_with(new_el)
        # Apply base rules to the rest (non-zoned)
        # Here we serialize and re-parse to ensure we apply to outer HTML too
        s2 = BeautifulSoup(str(soup), 'lxml')
        for el in s2.find_all(True):
            if el.has_attr('data-zone'): 
                continue
            replaced = _apply_in_element(el, terms, base_rules, seen)
            el.replace_with(replaced)
        final_html = str(s2)
        if final_html != html:
            con.execute("UPDATE page SET ocr_html=? WHERE id=?", (final_html, p["id"]))
            changes.append({"page_id": p["id"], "seq": p["seq"], "action": "context_style"})
    con.commit(); con.close()
    # write minimal changelog
    outp = Path(out_dir); outp.mkdir(parents=True, exist_ok=True)
    import csv, json as _j
    csv_path = outp / f"changes_context_doc_{document_id}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["page_id","seq","action"]); w.writeheader(); w.writerows(changes)
    (outp / f"changes_context_doc_{document_id}.json").write_text(_j.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"count": len(changes), "csv": str(csv_path)}
