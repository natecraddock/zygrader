"""Defines all the color pairs and emojis for each theme.
To add a new theme:
    1. use 'curses.init_pair()' with the 256-colors you would like (use constants).
    This needs to be INSIDE of 'if curses.can_change_colors()'
    In most cases, -1 should be the background color to use the terminal default

    2. Then, add the theme to THEME_COLORS with the color pair you specified.

    3. add the separator you want

    4. add the bookend you want

    3. add the theme name to THEMES. This name will appear in the preferences menu,
    and is used to get the theme colors and emojis

To see what colors are assigned to a specific numeric value, run the following code:
#####
import curses

def main(stdscr):
    curses.start_color()
    curses.use_default_colors()
    for i in range(0, curses.COLORS):
        curses.init_pair(i, i, -1)
    try:
        for i in range(0, 255):
            stdscr.addstr(str(i) + " ", curses.color_pair(i))
    except curses.ERR:
        # End of screen reached
        pass
    stdscr.getch()

curses.wrapper(main)
#####
This will print each color to the screen, colored appropriately.


"""

import curses

from zygrader.ui import colors

LIGHT_GREEN = 82
CURSES_GREEN = 34
CURSES_PURPLE = 93

CURSES_BDAY_BLUE = 45
CURSES_BDAY_PINK = 207

CURSES_THANKSGIVING_BROWN = 130
CURSES_THANKSGIVING_ORANGE = 208

VALENTINES_RED = 196
VALENTINES_PINK = 204

WARM_ORANGE = 220
GOLDEN_YELLOW = 226


class Theme:
    def __init__(self,
                 separator: str,
                 bookends: str,
                 header_color_a,
                 header_color_b,
                 fallback_a=None,
                 fallback_b=None):
        self.separator = separator
        self.bookends = bookends
        self.header_color_a = header_color_a
        self.header_color_b = header_color_b
        self.fallback_a = fallback_a
        self.fallback_b = fallback_b

    def adjust_screen_colors(self):
        colors.set_color(colors.COLOR_PAIR_HEADER, self.header_color_a,
                         self.fallback_a)
        colors.set_color(colors.COLOR_PAIR_HEADER_ALT, self.header_color_b,
                         self.fallback_b)


THEMES = {
    "Default":
    Theme("|", "", -1, -1),
    "Christmas":
    Theme("❄️", "🎄", curses.COLOR_GREEN, curses.COLOR_RED),
    "Spooky":
    Theme("🎃", "👻", CURSES_GREEN, CURSES_PURPLE, curses.COLOR_GREEN,
          curses.COLOR_MAGENTA),
    "Birthday":
    Theme("🎂", "🎉", CURSES_BDAY_BLUE, CURSES_BDAY_PINK, curses.COLOR_BLUE,
          curses.COLOR_MAGENTA),
    "Thanksgiving":
    Theme("🦃", "🍗", CURSES_THANKSGIVING_BROWN, CURSES_THANKSGIVING_ORANGE,
          curses.COLOR_RED, curses.COLOR_RED),
    "Valentines":
    Theme("💕", "❤️", VALENTINES_RED, VALENTINES_PINK, curses.COLOR_RED,
          curses.COLOR_MAGENTA),
    "America":
    Theme("🎆", "🗽", curses.COLOR_RED, curses.COLOR_BLUE),
    "St Patricks":
    Theme("🍀", "🌈", CURSES_GREEN, LIGHT_GREEN, curses.COLOR_GREEN,
          curses.COLOR_GREEN),
    "Summer":
    Theme("☀️", "🌻", WARM_ORANGE, GOLDEN_YELLOW, curses.COLOR_YELLOW,
          curses.COLOR_WHITE)
}
