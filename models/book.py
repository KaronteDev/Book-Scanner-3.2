from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class Annotation:
    id: str
    page: int
    bbox: tuple  # (x, y, w, h) relative to page image
    text: str = ""
    meta: Dict[str, str] = field(default_factory=dict)

@dataclass
class Book:
    title: str
    author: Optional[str] = None
    pages: List[str] = field(default_factory=list)  # paths or IDs to page images/text
    annotations: List[Annotation] = field(default_factory=list)

    def add_page(self, page_ref: str) -> None:
        self.pages.append(page_ref)

    def add_annotation(self, annotation: Annotation) -> None:
        self.annotations.append(annotation)

    def find_annotations_on_page(self, page: int) -> List[Annotation]:
        return [a for a in self.annotations if a.page == page]

    def total_pages(self) -> int:
        return len(self.pages)
