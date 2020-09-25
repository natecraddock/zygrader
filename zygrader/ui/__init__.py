from .window import Window, WinContext
from .input import Event, GO_BACK, Input
from . import components
from . import window
from . import layers


def get_window() -> Window:
    """Utility function to make getting the Window simpler in code"""
    return Window.get_window()

def get_input() -> Input:
    return get_window().input
