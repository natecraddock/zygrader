import curses
from zygrader.ui.displaystring import DisplayStr


def add_str(window, y, x, text, attrs=0):
    """Wrapper around addstr to catch errors"""
    try:
        if isinstance(text, DisplayStr):
            xslide = x
            for segment in text.segments:
                text, extra_attrs = segment
                window.addstr(y, xslide, text, extra_attrs | attrs)
                xslide += len(text)
        else:
            window.addstr(y, x, text, attrs)
    except curses.error:
        pass


def resize_window(window, rows, cols):
    """Wrapper around resize to catch errors"""
    try:
        window.resize(rows, cols)
    except curses.error:
        pass
