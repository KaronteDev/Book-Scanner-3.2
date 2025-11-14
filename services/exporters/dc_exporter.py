import json
from pathlib import Path
from typing import Any


def export_dublin_core(book: Any, path: str) -> str:
    """Genera JSON-LD Dublin Core mínimo."""
    data = {
        "@context": {
            "dc": "http://purl.org/dc/elements/1.1/",
            "title": "dc:title",
            "creator": "dc:creator",
            "description": "dc:description"
        },
        "title": getattr(book, 'title', 'Untitled'),
        "creator": getattr(book, 'author', 'Desconocido'),
        "description": f"Documento con {len(getattr(book,'pages',[]))} páginas."
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(p)
