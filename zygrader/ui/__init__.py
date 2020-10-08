from .window import Window, WinContext
from .events import Event, EventManager, GO_BACK
from . import components
from . import window
from . import layers


def get_window() -> Window:
    """Utility function to make getting the Window simpler in code"""
    return Window.get_window()


def get_events() -> EventManager:
    return get_window().event_manager
