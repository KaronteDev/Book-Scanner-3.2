from typing import Protocol

class View(Protocol):
    def refresh(self) -> None: ...

class BasePresenter:
    """Base presenter connecting model(s) with a view.
    Subclasses should implement binding logic and event handlers.
    """
    def __init__(self, view: View):
        self._view = view

    def attach(self):
        """Hook for attaching signals / events."""
        pass

    def detach(self):
        """Cleanup any bindings."""
        pass
