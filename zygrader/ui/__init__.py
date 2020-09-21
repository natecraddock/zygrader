from .window import Window, WinContext, Event, GO_BACK
from . import components
from . import window

def get_window() -> Window:
    """Utility function to make getting the Window simpler in code"""
    return Window.get_window()
