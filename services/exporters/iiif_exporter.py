import json
import os
from pathlib import Path
from typing import Any
from PIL import Image


def export_iiif_manifest(book: Any, path: str) -> str:
    """Crea un manifest IIIF v3 con:
    - Dimensiones reales por Canvas.
    - Thumbnail por Canvas (derivado de body).
    - Thumbnail global del manifest.
    - Referencias a servicio IIIF Image API mínimo (id configurable via env GEOBOOK_IIIF_BASE).
    """
    base_service = os.getenv("GEOBOOK_IIIF_BASE", "http://localhost:5000/iiif")
    canvases = []
    for idx, img_path in enumerate(getattr(book, 'pages', [])):
        width, height = 800, 1000
        identifier = Path(img_path).stem  # identificador único
        try:
            im = Image.open(img_path)
            width, height = im.width, im.height
        except Exception:
            pass
        canvas_id = f"{base_service}/canvas/{identifier}"  # Nota: representacional
        annotation_page_id = f"{base_service}/annotation/{identifier}/page"
        # Body (painting) apunta al recurso full; siguiendo Image API estilo v2 (simplificado)
        image_base = f"{base_service}/{identifier}"
        full_image = f"{image_base}/full/max/0/default.jpg"
        thumb_url = f"{image_base}/full/!200,200/0/default.jpg"
        body = {
            "id": full_image,
            "type": "Image",
            "format": "image/jpeg",
            "height": height,
            "width": width,
            "service": [
                {
                    "id": image_base,
                    "type": "ImageService2",
                    "profile": "http://iiif.io/api/image/2/level1.json"
                }
            ]
        }
        annotation = {
            "id": f"{annotation_page_id}/annotation/painting",
            "type": "Annotation",
            "motivation": "painting",
            "body": body,
            "target": canvas_id
        }
        canvas_obj = {
            "id": canvas_id,
            "type": "Canvas",
            "height": height,
            "width": width,
            "items": [
                {
                    "id": annotation_page_id,
                    "type": "AnnotationPage",
                    "items": [annotation]
                }
            ],
            "thumbnail": [
                {
                    "id": thumb_url,
                    "type": "Image",
                    "format": "image/jpeg",
                    "width": min(width, 200),
                    "height": min(height, 200)
                }
            ]
        }
        canvases.append(canvas_obj)
    manifest_thumb = None
    if canvases:
        first_thumb = canvases[0]['thumbnail'][0]
        manifest_thumb = [first_thumb]
    manifest = {
        "@context": "http://iiif.io/api/presentation/3/context.json",
        "id": f"{base_service}/manifest/book",
        "type": "Manifest",
        "label": {"en": [getattr(book, 'title', 'Untitled')]},
        "items": canvases,
        "provider": [
            {
                "id": "https://example.org/org/geodocs",
                "type": "Agent",
                "label": {"en": ["GeoDocs Scanner"]}
            }
        ]
    }
    if manifest_thumb:
        manifest['thumbnail'] = manifest_thumb
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(p)
