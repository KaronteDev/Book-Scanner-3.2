import json
from pathlib import Path
from typing import Any


def export_geojson_annotations(book: Any, path: str) -> str:
    """GeoJSON de anotaciones.

    - Si la anotación incluye meta['lat'] y meta['lon'] => geometry Point.
    - En caso contrario genera Polygon derivado del bbox (x,y,w,h) en sistema de
      coordenadas de píxeles (no geográfico), marcado como pixel:true en properties.
    """
    features = []
    for ann in getattr(book, 'annotations', []):
        geom = None
        lat = ann.meta.get('lat') if hasattr(ann, 'meta') else None
        lon = ann.meta.get('lon') if hasattr(ann, 'meta') else None
        if lat is not None and lon is not None:
            try:
                lat_f = float(lat); lon_f = float(lon)
                geom = {"type": "Point", "coordinates": [lon_f, lat_f]}
            except ValueError:
                geom = None
        if geom is None:
            # bbox -> Polygon
            x, y, w, h = ann.bbox
            polygon = [
                [x, y], [x+w, y], [x+w, y+h], [x, y+h], [x, y]
            ]
            geom = {"type": "Polygon", "coordinates": [polygon]}
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "id": ann.id,
                "page": ann.page,
                "text": ann.text,
                "bbox": ann.bbox,
                "has_geo": lat is not None and lon is not None
            }
        })
    geo = {"type": "FeatureCollection", "features": features}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(geo, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(p)
