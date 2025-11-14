from services.export_service import ExportService
from models.book import Book, Annotation
import json
from lxml import etree


def test_export_bundle(tmp_path):
    book = Book(title='BundleTest', pages=['p1.png','p2.png'])
    book.add_annotation(Annotation(id='ann1', page=0, bbox=(0,0,10,10), text='Hola'))
    svc = ExportService()
    outputs = svc.export_bundle(book, str(tmp_path))
    # PDF exists
    assert 'pdf' in outputs and outputs['pdf']
    # IIIF manifest structure
    manifest = json.loads((tmp_path/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['type'] == 'Manifest'
    assert len(manifest['items']) == 2
    # TEI basic parse
    tree = etree.parse(str(tmp_path/'book.xml'))
    assert tree.getroot().tag.endswith('TEI')
    # Dublin Core
    dc = json.loads((tmp_path/'dublin_core.json').read_text(encoding='utf-8'))
    assert dc['title'] == 'BundleTest'
    # GeoJSON annotations
    geo = json.loads((tmp_path/'annotations.geojson').read_text(encoding='utf-8'))
    assert geo['type'] == 'FeatureCollection'
    assert len(geo['features']) == 1
