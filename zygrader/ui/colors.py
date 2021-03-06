import curses

COLOR_PAIR_DEFAULT = 1
COLOR_PAIR_LOCKED = 2
COLOR_PAIR_FLAGGED = 3
COLOR_PAIR_HEADER = 4
COLOR_PAIR_HEADER_ALT = 5


def init_colors():
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
    try_sequence = [new_color, -1]
    if fallback is not None:
        try_sequence.insert(1, fallback)
    for color in try_sequence:
        try:
            curses.init_pair(pair_id, color, -1)
            return
        except Exception:
            pass
