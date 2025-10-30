
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
glossary_io.py — Importación/Exportación de glosarios:
- Import: CSV, JSON, XML (simple) con mapeo de campos configurable
- Export: CSV, JSON y TEI-XML (muy simple) para repositorios académicos
"""
from pathlib import Path
import json, csv

def import_csv(path: str, field_map: dict):
    """
    field_map: {'abbr':'col1', 'expansion':'col2', 'lang':'col3'(opt)}
    return dict(terms)
    """
    terms = {}
    with open(path, encoding='utf-8') as f:
        r = csv.DictReader(f)
        ab = field_map.get('abbr'); ex = field_map.get('expansion')
        for row in r:
            a = (row.get(ab) or '').strip()
            e = (row.get(ex) or '').strip()
            if a: terms[a] = e or ''
    return terms

def import_json(path: str, field_map: dict=None):
    """
    Soporta dos formatos:
    - dict {'abbr':'expansion', ...}
    - lista de objetos [{'abbr':'..','expansion':'..'}, ...] con mapeo de campos
    """
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    terms = {}
    if isinstance(data, dict):
        for k,v in data.items(): terms[str(k)] = str(v or '')
    elif isinstance(data, list):
        ab = (field_map or {}).get('abbr','abbr'); ex = (field_map or {}).get('expansion','expansion')
        for it in data:
            a = str(it.get(ab,'')).strip(); e = str(it.get(ex,'')).strip()
            if a: terms[a]=e
    return terms

def import_xml(path: str, field_map: dict):
    """
    XML simple. field_map {'item':'itemTag','abbr':'abbrTag','expansion':'expTag'}
    """
    from lxml import etree
    terms = {}
    root = etree.parse(path).getroot()
    item_tag = field_map.get('item','item')
    ab_tag = field_map.get('abbr','abbr')
    ex_tag = field_map.get('expansion','expansion')
    for item in root.findall('.//'+item_tag):
        a = ''.join(item.findtext(ab_tag) or '').strip()
        e = ''.join(item.findtext(ex_tag) or '').strip()
        if a: terms[a]=e
    return terms

def export_csv(terms: dict, out_path: str):
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['Abreviatura','Expansión'])
        for k,v in terms.items(): w.writerow([k,v])
    return out_path

def export_json(terms: dict, out_path: str):
    Path(out_path).write_text(json.dumps(terms, ensure_ascii=False, indent=2), encoding='utf-8')
    return out_path

def export_tei(terms: dict, out_path: str):
    """
    TEI muy básico: <list><item><abbr>..</abbr><expan>..</expan></item>...</list>
    """
    from lxml import etree
    root = etree.Element('list')
    for k,v in terms.items():
        it = etree.SubElement(root, 'item')
        ab = etree.SubElement(it, 'abbr'); ab.text = k
        ex = etree.SubElement(it, 'expan'); ex.text = v
    xml = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)
    Path(out_path).write_bytes(xml); return out_path


def import_tei(path: str):
    """TEI dictionaries: supports <list>/<item><abbr/><expan/> and <entry><form><abbr/></form><def>...</def>"""
    from lxml import etree
    terms = {}
    root = etree.parse(path).getroot()
    # list/item
    for it in root.findall('.//{*}list/{*}item'):
        ab = ''.join((it.findtext('.//{*}abbr') or '')).strip()
        ex = ''.join((it.findtext('.//{*}expan') or '')).strip()
        if ab: terms[ab]=ex
    # entry/form/abbr + def
    for en in root.findall('.//{*}entry'):
        ab = ''.join((en.findtext('.//{*}form/{*}abbr') or '')).strip()
        ex = ''.join((en.findtext('.//{*}def') or '')).strip()
        if ab and (ab not in terms or not terms[ab]): terms[ab]=ex
    return terms
