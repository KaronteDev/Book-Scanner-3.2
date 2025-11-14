from models.book import Book, Annotation

def test_add_page_and_count():
    b = Book(title="Demo")
    b.add_page("page1.png")
    b.add_page("page2.png")
    assert b.total_pages() == 2

def test_add_annotation_and_query():
    b = Book(title="Demo")
    b.add_page("page1.png")
    ann = Annotation(id="a1", page=0, bbox=(10,10,100,50), text="Nota")
    b.add_annotation(ann)
    result = b.find_annotations_on_page(0)
    assert len(result) == 1 and result[0].id == "a1"
