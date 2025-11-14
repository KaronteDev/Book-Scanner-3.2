from presenters.book_presenter import BookPresenter
from models.book import Book, Annotation

class DummyView:
    def __init__(self):
        self.refresh_count = 0
    def refresh(self):
        self.refresh_count += 1


def test_add_annotation_triggers_refresh():
    book = Book(title='Demo')
    view = DummyView()
    presenter = BookPresenter(view, book)
    ann = Annotation(id='a2', page=0, bbox=(0,0,10,10), text='x')
    presenter.add_annotation(ann)
    assert view.refresh_count == 1
    assert len(book.annotations) == 1
