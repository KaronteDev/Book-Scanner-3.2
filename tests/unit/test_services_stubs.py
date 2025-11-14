from services.ocr_service import OCRService
from services.tts_service import TTSService
from services.export_service import ExportService
from models.book import Book


def test_ocr_service_returns_string():
    svc = OCRService()
    text = svc.recognize_page('dummy.png')
    assert isinstance(text, str)


def test_tts_service_speak_no_exception():
    svc = TTSService()
    svc.speak("Hola mundo")  # Should not raise


def test_export_service_no_exception(tmp_path):
    book = Book(title='Demo')
    out = tmp_path/'book_export.txt'
    svc = ExportService()
    # Currently stub: just ensure no exception
    svc.export_book(book, str(out))
