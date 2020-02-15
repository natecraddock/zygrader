import curses

def add_str(window, y, x, text, attrs=0):
    """Wrapper around addstr to catch errors"""
    try:
        window.addstr(y, x, text, attrs)
    except curses.error:
        pass

def resize_window(window, rows, cols):
    """Wrapper around resize to catch errors"""
    try:
        window.resize(rows, cols)
    except curses.error:
        pass