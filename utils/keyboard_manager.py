#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
keyboard_manager.py — Global keyboard shortcuts for Book Scanner 3.2
Manages application-wide keyboard bindings for common actions
"""
import tkinter as tk
from typing import Callable, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class KeyBinding:
    """Keyboard shortcut binding"""
    key: str  # Tkinter key sequence (e.g., "<F5>", "<Control-e>")
    description: str
    callback: Optional[Callable] = None
    enabled: bool = True


class KeyboardManager:
    """
    Manages global keyboard shortcuts for the application.
    
    Usage:
        km = KeyboardManager(root_window)
        km.register("capture", "<F5>", "Capturar imagen", lambda: scanner.capture())
        km.bind_all()
    """
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.bindings: Dict[str, KeyBinding] = {}
        self._bound_keys = set()
        
    def register(self, name: str, key: str, description: str, callback: Callable = None):
        """
        Register a keyboard shortcut.
        
        Args:
            name: Unique identifier for this binding
            key: Tkinter key sequence (e.g., "<F5>", "<Control-e>", "<Control-Shift-s>")
            description: Human-readable description
            callback: Function to call when key is pressed
        """
        self.bindings[name] = KeyBinding(
            key=key,
            description=description,
            callback=callback,
            enabled=True
        )
        
    def set_callback(self, name: str, callback: Callable):
        """Set or update callback for an existing binding"""
        if name in self.bindings:
            self.bindings[name].callback = callback
        else:
            raise KeyError(f"Binding '{name}' not registered")
            
    def enable(self, name: str):
        """Enable a binding"""
        if name in self.bindings:
            self.bindings[name].enabled = True
            
    def disable(self, name: str):
        """Disable a binding (keeps it registered but doesn't execute)"""
        if name in self.bindings:
            self.bindings[name].enabled = False
            
    def bind_all(self):
        """Bind all registered shortcuts to the root window"""
        for name, binding in self.bindings.items():
            if binding.key not in self._bound_keys:
                self.root.bind(binding.key, lambda e, n=name: self._execute(n))
                self._bound_keys.add(binding.key)
                
    def unbind_all(self):
        """Unbind all shortcuts"""
        for key in self._bound_keys:
            self.root.unbind(key)
        self._bound_keys.clear()
        
    def _execute(self, name: str):
        """Execute callback if binding is enabled"""
        binding = self.bindings.get(name)
        if binding and binding.enabled and binding.callback:
            try:
                binding.callback()
            except Exception as e:
                print(f"Error executing shortcut '{name}': {e}")
                
    def get_shortcuts_list(self) -> list[Tuple[str, str, bool]]:
        """
        Get list of all shortcuts for display.
        
        Returns:
            List of tuples (key, description, enabled)
        """
        result = []
        for binding in self.bindings.values():
            # Format key for display
            display_key = binding.key.replace("<", "").replace(">", "")
            display_key = display_key.replace("Control", "Ctrl")
            display_key = display_key.replace("-", "+")
            result.append((display_key, binding.description, binding.enabled))
        return sorted(result, key=lambda x: x[0])


def setup_default_shortcuts(km: KeyboardManager, app_context: dict):
    """
    Setup default keyboard shortcuts for Book Scanner.
    
    Args:
        km: KeyboardManager instance
        app_context: Dictionary with references to app components
            Expected keys: 'scanner', 'export_func', 'gallery_func', 'quality_func'
    """
    
    # F5 - Capture image
    km.register(
        "capture",
        "<F5>",
        "Capturar imagen",
        lambda: app_context.get('scanner').capture_image() if app_context.get('scanner') else None
    )
    
    # Ctrl+E - Export
    km.register(
        "export",
        "<Control-e>",
        "Exportar proyecto",
        lambda: app_context.get('export_func')() if app_context.get('export_func') else None
    )
    
    # Ctrl+G - Gallery view
    km.register(
        "gallery",
        "<Control-g>",
        "Enfocar galería",
        lambda: app_context.get('gallery_func')() if app_context.get('gallery_func') else None
    )
    
    # Ctrl+1 - Quality filter: All
    km.register(
        "quality_all",
        "<Control-Key-1>",
        "Mostrar todas las calidades",
        lambda: app_context.get('quality_func')('all') if app_context.get('quality_func') else None
    )
    
    # Ctrl+2 - Quality filter: Good
    km.register(
        "quality_good",
        "<Control-Key-2>",
        "Mostrar solo calidad buena",
        lambda: app_context.get('quality_func')('good') if app_context.get('quality_func') else None
    )
    
    # Ctrl+3 - Quality filter: Bad
    km.register(
        "quality_bad",
        "<Control-Key-3>",
        "Mostrar solo calidad mala",
        lambda: app_context.get('quality_func')('bad') if app_context.get('quality_func') else None
    )
    
    # Ctrl+N - New project
    km.register(
        "new_project",
        "<Control-n>",
        "Nuevo proyecto",
        lambda: app_context.get('new_project_func')() if app_context.get('new_project_func') else None
    )
    
    # Ctrl+O - Open project
    km.register(
        "open_project",
        "<Control-o>",
        "Abrir proyecto",
        lambda: app_context.get('open_project_func')() if app_context.get('open_project_func') else None
    )
    
    # Ctrl+S - Save/Quick save
    km.register(
        "save",
        "<Control-s>",
        "Guardar cambios",
        lambda: app_context.get('save_func')() if app_context.get('save_func') else None
    )
    
    # Ctrl+R - Rotate selected image
    km.register(
        "rotate",
        "<Control-r>",
        "Rotar imagen seleccionada 90°",
        lambda: app_context.get('rotate_func')(90) if app_context.get('rotate_func') else None
    )
    
    # Ctrl+Shift+R - Rotate selected image -90°
    km.register(
        "rotate_ccw",
        "<Control-Shift-R>",
        "Rotar imagen seleccionada -90°",
        lambda: app_context.get('rotate_func')(-90) if app_context.get('rotate_func') else None
    )
    
    # Delete - Delete selected image
    km.register(
        "delete",
        "<Delete>",
        "Eliminar imagen seleccionada",
        lambda: app_context.get('delete_func')() if app_context.get('delete_func') else None
    )
    
    # Ctrl+F - Find/Search
    km.register(
        "search",
        "<Control-f>",
        "Buscar en proyecto",
        lambda: app_context.get('search_func')() if app_context.get('search_func') else None
    )
    
    # F1 - Help/Shortcuts
    km.register(
        "help",
        "<F1>",
        "Mostrar ayuda y atajos",
        lambda: show_shortcuts_help(km, app_context.get('root'))
    )
    
    # Ctrl+Plus/Minus - Zoom
    km.register(
        "zoom_in",
        "<Control-plus>",
        "Aumentar zoom",
        lambda: app_context.get('zoom_func')(1.2) if app_context.get('zoom_func') else None
    )
    
    km.register(
        "zoom_out",
        "<Control-minus>",
        "Reducir zoom",
        lambda: app_context.get('zoom_func')(0.8) if app_context.get('zoom_func') else None
    )
    
    km.register(
        "zoom_reset",
        "<Control-Key-0>",
        "Restablecer zoom",
        lambda: app_context.get('zoom_func')(1.0) if app_context.get('zoom_func') else None
    )


def show_shortcuts_help(km: KeyboardManager, parent=None):
    """Show a window with all available keyboard shortcuts"""
    from tkinter import messagebox
    try:
        import ttkbootstrap as ttk
        from ttkbootstrap.dialogs import Messagebox
        USE_BOOTSTRAP = True
    except ImportError:
        from tkinter import ttk
        Messagebox = None
        USE_BOOTSTRAP = False
    
    # Create help window
    help_win = tk.Toplevel(parent)
    help_win.title("📌 Atajos de Teclado")
    help_win.geometry("600x500")
    
    if parent:
        from utils.window_utils import center_to_parent
        center_to_parent(help_win, parent)
    
    # Title
    title_frame = ttk.Frame(help_win, padding=15)
    title_frame.pack(fill='x')
    ttk.Label(
        title_frame,
        text="⌨️ Atajos de Teclado Disponibles",
        font=("Segoe UI", 14, "bold")
    ).pack()
    
    # Shortcuts list in frame with scrollbar
    list_frame = ttk.Frame(help_win, padding=10)
    list_frame.pack(fill='both', expand=True)
    
    # Create Treeview
    columns = ("key", "description", "status")
    tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
    tree.heading("key", text="Atajo")
    tree.heading("description", text="Descripción")
    tree.heading("status", text="Estado")
    
    tree.column("key", width=120, anchor='w')
    tree.column("description", width=350, anchor='w')
    tree.column("status", width=80, anchor='center')
    
    # Add scrollbar
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    tree.pack(side='left', fill='both', expand=True)
    scrollbar.pack(side='right', fill='y')
    
    # Populate shortcuts
    shortcuts = km.get_shortcuts_list()
    for key, desc, enabled in shortcuts:
        status = "✓ Activo" if enabled else "✗ Desactivado"
        tree.insert("", "end", values=(key, desc, status))
    
    # Close button
    btn_frame = ttk.Frame(help_win, padding=10)
    btn_frame.pack(fill='x')
    ttk.Button(
        btn_frame,
        text="Cerrar",
        command=help_win.destroy,
        bootstyle="secondary" if USE_BOOTSTRAP else None
    ).pack()
    
    help_win.transient(parent)
    help_win.grab_set()


# Example usage:
if __name__ == "__main__":
    from tkinter import ttk
    
    root = tk.Tk()
    root.title("Keyboard Manager Demo")
    root.geometry("400x300")
    
    km = KeyboardManager(root)
    
    def test_action(name):
        print(f"Action triggered: {name}")
    
    km.register("test_f5", "<F5>", "Test F5", lambda: test_action("F5"))
    km.register("test_ctrl_e", "<Control-e>", "Test Ctrl+E", lambda: test_action("Ctrl+E"))
    km.bind_all()
    
    ttk.Label(root, text="Press F5 or Ctrl+E to test", font=("Arial", 12)).pack(pady=50)
    ttk.Button(root, text="Show Shortcuts", command=lambda: show_shortcuts_help(km, root)).pack()
    
    root.mainloop()
