"""Color management for displaying colored text with curses

Curses uses "pair" numbers to identify a foreground/background color pair.
The definition of the pair can be changed during runtime, so this module
provides constant semantic identifiers to use throughout the code and
`set_color` to dynamically change the definition.
"""

import curses

COLOR_PAIR_DEFAULT = 1
COLOR_PAIR_LOCKED = 2
COLOR_PAIR_FLAGGED = 3
COLOR_PAIR_HEADER = 4
COLOR_PAIR_HEADER_ALT = 5


def init_colors():
    """Initialize the color definition for all pair identifiers"""
    # This allows the use of `-1` in `init_pair()` for accessing the
    # default foreground and background terminal colors. It also enables
    # transparency.
    curses.use_default_colors()

    # Default colors from terminal preferences
    set_color(COLOR_PAIR_DEFAULT, -1)

    # Locked data. Red on default background
    set_color(COLOR_PAIR_LOCKED, curses.COLOR_RED)

    # Flagged data
    set_color(COLOR_PAIR_FLAGGED, curses.COLOR_CYAN)

    # Until a theme is set up, just use defaults from the shell
    # for the header colors
    set_color(COLOR_PAIR_HEADER, -1)
    set_color(COLOR_PAIR_HEADER_ALT, -1)


def set_color(pair_id: int, new_color, fallback=None) -> None:
    """Initialize a color pair to be the provided color

    in case of errors, the fallback is used (if provided),
    and as a last resort use the default colors of the terminal
    """
    try_sequence = [new_color, -1]
    if fallback is not None:
        try_sequence.insert(1, fallback)
    for color in try_sequence:
        try:
            curses.init_pair(pair_id, color, -1)
            return
        except Exception:
            pass
