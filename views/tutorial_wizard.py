import tkinter as tk
from tkinter import ttk

STEPS = [
    {"title": "Bienvenida", "text": "Este asistente te guiará en la captura y anotación."},
    {"title": "Captura", "text": "Inicia la cámara y captura páginas. Usa iluminación uniforme."},
    {"title": "OCR", "text": "Procesa la cola OCR desde el menú Archivo. Revisa resultados."},
    {"title": "Anotaciones", "text": "Abre el anotador para resaltar palabras y crear hotspots."},
    {"title": "Visor 3D", "text": "Explora el libro en 3D y realiza zoom sobre palabras."},
    {"title": "Finalizar", "text": "Exporta PDF/EPUB y comparte documentación generada."}
]

class TutorialWizard(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Tutorial Interactivo GeoDocs")
        self.geometry("480x300")
        self.step_index = 0
        self.header = ttk.Label(self, text="", font=("Arial", 16, "bold"))
        self.header.pack(pady=10)
        self.body = ttk.Label(self, text="", wraplength=440, justify="left")
        self.body.pack(pady=10, padx=10, fill="x")
        nav = ttk.Frame(self); nav.pack(side="bottom", fill="x", pady=8)
        self.btn_prev = ttk.Button(nav, text="⟵ Anterior", command=self.prev)
        self.btn_prev.pack(side="left", padx=6)
        self.btn_next = ttk.Button(nav, text="Siguiente ⟶", command=self.next)
        self.btn_next.pack(side="right", padx=6)
        self.update_step()

    def update_step(self):
        data = STEPS[self.step_index]
        self.header.config(text=data["title"])
        self.body.config(text=data["text"])
        self.btn_prev.config(state="normal" if self.step_index>0 else "disabled")
        if self.step_index == len(STEPS)-1:
            self.btn_next.config(text="Cerrar")
        else:
            self.btn_next.config(text="Siguiente ⟶")

    def next(self):
        if self.step_index == len(STEPS)-1:
            self.destroy(); return
        self.step_index += 1
        self.update_step()

    def prev(self):
        if self.step_index == 0: return
        self.step_index -= 1
        self.update_step()


def open_tutorial(root):
    TutorialWizard(root)
