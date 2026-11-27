"""
The interface every scope layer implements.
"""

from views.scope_layers.scope_canvas import ScopeCanvas
from views.scope_layers.scope_frame import ScopeFrame


class ScopeLayer:
    """
    Something drawn on a top-down scope: weather, breadcrumbs,
    airports, traffic, ...

    A layer is created once per scope with that scope's canvas,
    then asked to render every frame.
    """

    def __init__(self, canvas: ScopeCanvas) -> None:
        self.canvas = canvas

    def render(self, frame: ScopeFrame) -> None:
        raise NotImplementedError
