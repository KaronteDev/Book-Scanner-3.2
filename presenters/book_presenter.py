from .base_presenter import BasePresenter
from models.book import Book, Annotation

class BookPresenter(BasePresenter):
    def __init__(self, view, book: Book):
        super().__init__(view)
        self.book = book

    def add_annotation(self, annotation: Annotation):
        self.book.add_annotation(annotation)
        self._view.refresh()

    def page_count(self) -> int:
        return self.book.total_pages()
