from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pathlib import Path
from typing import Any


def export_pdf(book: Any, path: str) -> str:
    """Genera PDF mínimo con título y listado de páginas.
    No incrusta imágenes (optimización futura).
    """
    p = Path(path)
    c = canvas.Canvas(str(p), pagesize=A4)
    c.setTitle(getattr(book, 'title', 'Libro'))
    c.drawString(50, 800, f"Titulo: {getattr(book, 'title', 'Libro')}")
    c.drawString(50, 785, f"Total páginas: {len(getattr(book, 'pages', []))}")
    y = 760
    for idx, ref in enumerate(getattr(book, 'pages', [])):
        c.drawString(50, y, f"Pagina {idx+1}: {ref}")
        y -= 15
        if y < 50:
            c.showPage(); y = 800
    c.showPage()
    c.save()
    return str(p)
