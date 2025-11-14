"""Minimal IIIF Image API service (simplified).

Run:
    python -m services.iiif_image_service --images <folder_with_pages>

Implements endpoints:
  /iiif/<identifier>/info.json
  /iiif/<identifier>/full/<size>/<rotation>/default.jpg
Where <identifier> maps to a file whose stem matches the identifier.
Size supports "max" or !W,H (bounded) and W, (width only) simplified.
Rotation ignored except 0.

This is a minimal educational implementation; not production-ready.
"""
from __future__ import annotations
import io, argparse, os
from pathlib import Path
from typing import Dict
from PIL import Image
from flask import Flask, jsonify, send_file, abort

app = Flask(__name__)
IMAGE_MAP: Dict[str, Path] = {}

@app.route('/iiif/<identifier>/info.json')
def info(identifier: str):
    p = IMAGE_MAP.get(identifier)
    if not p or not p.exists():
        abort(404)
    try:
        im = Image.open(p)
    except Exception:
        abort(500)
    return jsonify({
        '@context': 'http://iiif.io/api/image/2/context.json',
        'id': f"/iiif/{identifier}",
        'protocol': 'http://iiif.io/api/image',
        'profile': 'http://iiif.io/api/image/2/level1.json',
        'width': im.width,
        'height': im.height,
        'tiles': [{ 'scaleFactors': [1,2,4], 'width': 256 }]
    })

@app.route('/iiif/<identifier>/full/<size>/<rotation>/default.jpg')
def full_image(identifier: str, size: str, rotation: str):
    p = IMAGE_MAP.get(identifier)
    if not p or not p.exists():
        abort(404)
    try:
        im = Image.open(p).convert('RGB')
    except Exception:
        abort(500)
    # Size parsing
    if size == 'max':
        out = im
    elif size.startswith('!') and ',' in size:
        # Bounded box !W,H keep aspect
        box = size[1:]
        try:
            w_str, h_str = box.split(',')
            max_w, max_h = int(w_str), int(h_str)
            im.thumbnail((max_w, max_h))
            out = im
        except Exception:
            out = im
    elif size.endswith(','):
        # Width only specified
        try:
            w = int(size[:-1])
            ratio = w / im.width
            h = int(im.height * ratio)
            out = im.resize((w, h))
        except Exception:
            out = im
    else:
        out = im
    # Rotation ignored except basic check
    buf = io.BytesIO()
    out.save(buf, format='JPEG', quality=85)
    buf.seek(0)
    return send_file(buf, mimetype='image/jpeg')


def build_image_map(folder: Path):
    for p in folder.glob('page_*.png'):
        IMAGE_MAP[p.stem] = p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--images', required=True, help='Folder with page_*.png images')
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=5000)
    args = ap.parse_args()
    folder = Path(args.images)
    if not folder.exists():
        raise SystemExit('Images folder not found')
    build_image_map(folder)
    app.run(host=args.host, port=args.port)

if __name__ == '__main__':
    main()
