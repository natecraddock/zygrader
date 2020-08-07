import curses
from zygrader.ui.displaystring import DisplayStr

def text_adder(func):
    """Wrappers around addstr/addch to catch errors"""
    def wrapped(window, y, x, text, attrs=curses.A_NORMAL):
        try:
            if isinstance(text, DisplayStr):
                xslide = x
                for segment in text.segments:
                    text, extra_attrs = segment
                    func(window, y, xslide, text, extra_attrs | attrs)
                    xslide += len(text)
            else:
                func(window, y, x, text, attrs)
        except curses.error:
            pass
    return wrapped

@text_adder
def add_str(window, y, x, text, attrs=curses.A_NORMAL):
    window.addstr(y, x, text, attrs)

@text_adder
def add_ch(window, y, x, text, attrs=curses.A_NORMAL):
    window.addch(y, x, text, attrs)

def resize_window(window, rows, cols):
    """Wrapper around resize to catch errors"""
    try:
        window.resize(rows, cols)
    except curses.error:
        pass