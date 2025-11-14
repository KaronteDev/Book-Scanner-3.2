from presenters.book_presenter import BookPresenter
from presenters.base_presenter import BasePresenter
from models.book import Book, Annotation

class DummyView:
    def __init__(self):
        self.refresh_count = 0
    def refresh(self):
        self.refresh_count += 1

def test_book_presenter_page_count():
    book = Book(title='Demo')
    book.add_page('p1')
    book.add_page('p2')
    view = DummyView()
    presenter = BookPresenter(view, book)
    assert presenter.page_count() == 2

def test_base_presenter_attach_detach_noop():
    view = DummyView()
    bp = BasePresenter(view)
    bp.attach()
    bp.detach()
