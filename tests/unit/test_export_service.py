from services.export_service import ExportService
from models.book import Book, Annotation


def test_export_book_creates_file(tmp_path):
    book = Book(title='Prueba', pages=['p1.png','p2.png'])
    book.add_annotation(Annotation(id='a1', page=0, bbox=(0,0,10,10), text='Nota de prueba'))
    dest = tmp_path / 'export_stub.txt'
    svc = ExportService()
    svc.export_book(book, str(dest))
    assert dest.exists(), 'El archivo exportado no se creó'
    content = dest.read_text(encoding='utf-8')
    assert 'Prueba' in content
    assert 'Pages: 2' in content
    assert 'a1' in content
