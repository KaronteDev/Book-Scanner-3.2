import json
from pathlib import Path
from services.export_service import ExportService
from models.book import Book, Annotation
from lxml import etree


def make_dummy_images(tmp_path: Path, count: int):
    from PIL import Image
    paths = []
    for i in range(count):
        im = Image.new('RGB', (320 + i*10, 240 + i*5), color=(200, 100, 50))
        p = tmp_path / f"page_{i+1:02d}.png"
        im.save(p)
        paths.append(str(p))
    return paths


def test_validation_report_and_iiif_enrichment(tmp_path):
    pages = make_dummy_images(tmp_path, 3)
    book = Book(title='ValReport', pages=pages)
    book.add_annotation(Annotation(id='a1', page=0, bbox=(0,0,50,40), text='Primera', meta={'lat': '40.1', 'lon': '-3.6'}))
    svc = ExportService()
    outputs = svc.export_bundle(book, str(tmp_path/'out'))

    # Validation report keys
    report = svc.validation_report
    for key in ['pdf','iiif','tei','dc','geojson']:
        assert key in report, f"Missing report for {key}"
        r = report[key]
        assert r.get('exists') is True
        assert r.get('size', 0) > 0
        assert isinstance(r.get('sha256'), str) and len(r['sha256']) == 64
        if key in ('iiif','dc','geojson'):
            assert r.get('json_valid') is True
        if key == 'tei':
            assert r.get('xml_wellformed') is True

    # IIIF enrichment: provider + thumbnail present
    manifest = json.loads((Path(outputs['iiif']).read_text(encoding='utf-8')))
    assert 'provider' in manifest and isinstance(manifest['provider'], list)
    assert 'thumbnail' in manifest and isinstance(manifest['thumbnail'], list)
    # Canvas dimensions reflect dummy image sizes
    first_canvas = manifest['items'][0]
    assert first_canvas['width'] == 320 and first_canvas['height'] == 240

    # GeoJSON point geometry for annotation with lat/lon
    geo = json.loads(Path(outputs['geojson']).read_text(encoding='utf-8'))
    feature = geo['features'][0]
    assert feature['geometry']['type'] == 'Point'
    assert feature['properties']['has_geo'] is True

    # TEI well-formed and contains pages count
    tree = etree.parse(str(Path(outputs['tei'])))
    divs = tree.xpath('//*[local-name()="div"]')
    assert len(divs) == 3
