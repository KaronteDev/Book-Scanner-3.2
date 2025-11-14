import os
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import webbrowser

DOCS_SRC = Path(__file__).resolve().parent.parent / 'docs_src'
DOCS_BUILD = Path(__file__).resolve().parent.parent / 'docs_html'


def build_docs():
    if not DOCS_SRC.exists():
        raise RuntimeError('Directorio docs_src no existe.')
    try:
        import sphinx
        from sphinx.application import Sphinx
        conf_dir = str(DOCS_SRC)
        app = Sphinx(
            srcdir=conf_dir,
            confdir=conf_dir,
            outdir=str(DOCS_BUILD),
            doctreedir=str(DOCS_BUILD/'_doctrees'),
            buildername='html'
        )
        app.build(force_all=False)
    except ImportError:
        raise RuntimeError('Sphinx no instalado.')


YOUTUBE_TOUR_URL = 'https://www.youtube.com/embed/dQw4w9WgXcQ'  # Placeholder demo video

def open_help_window(root):
    # Build docs if missing index.html
    index_html = DOCS_BUILD / 'index.html'
    if not index_html.exists():
        try:
            build_docs()
        except Exception as e:
            messagebox.showwarning('Ayuda', f'No se pudieron generar las docs: {e}\nSe abrirá README en navegador.')
            fallback = Path(__file__).resolve().parent.parent / 'README.md'
            if fallback.exists():
                webbrowser.open_new_tab(fallback.as_uri())
            return
    # Try to embed with tkinterweb if available; else open browser
    try:
        from tkinterweb import HtmlFrame  # type: ignore
        win = tk.Toplevel(root)
        win.title('Documentación GeoDocs')
        frm = HtmlFrame(win)
        frm.pack(fill='both', expand=True)
        frm.load_website(index_html.as_uri())
        bar = ttk.Frame(win); bar.pack(fill='x')
        ttk.Button(bar, text='Abrir en navegador', command=lambda: webbrowser.open_new_tab(index_html.as_uri())).pack(side='right', padx=6, pady=4)
        ttk.Button(bar, text='🎬 Video Tour', command=lambda: open_video_tour(root)).pack(side='left', padx=6, pady=4)
    except Exception:
        webbrowser.open_new_tab(index_html.as_uri())
        messagebox.showinfo('Ayuda', 'Documentación abierta en el navegador.')
        open_video_tour(root)

def open_video_tour(root):
    # Minimal embed: open a toplevel with iframe if tkinterweb else browser
    try:
        from tkinterweb import HtmlFrame  # type: ignore
        win = tk.Toplevel(root)
        win.title('Video Tour GeoDocs')
        html = f"""
        <html><body style='margin:0'>
        <iframe width='640' height='360' src='{YOUTUBE_TOUR_URL}' title='Video Tour GeoDocs' frameborder='0' allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture' allowfullscreen></iframe>
        </body></html>
        """
        frm = HtmlFrame(win)
        frm.pack(fill='both', expand=True)
        frm.set_html(html)
    except Exception:
        webbrowser.open_new_tab(YOUTUBE_TOUR_URL)
