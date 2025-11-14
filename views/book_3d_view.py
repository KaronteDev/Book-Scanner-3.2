import os
from pathlib import Path

# Depending on chosen embedding (tkinterweb, cefpython). This stub exposes an HTML asset path.

class Book3DView:
    def __init__(self):
        self.html_path = Path(__file__).parent.parent / "web_viewer" / "book_3d.html"

    def refresh(self):
        # In a real view this would trigger a redraw or JS bridge update
        pass

    def get_html_file(self) -> str:
        return str(self.html_path)
