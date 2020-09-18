# Negative 1 because "Back" is 0th in the index of lists
# And lists return their (index - 1) to handle that offset
UI_GO_BACK = -1

# from .window import Window, WinContext
from . import components
from . import window

def get_window() -> window.Window:
    """Utility function to make getting the Window simpler in code"""
    return window.Window.get_window()
