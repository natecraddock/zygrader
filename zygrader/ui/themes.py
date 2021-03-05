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
THEMES = [
    "Default", "Christmas", "Spooky", "Birthday", "Thanksgiving", "Valentines",
    "America", "St Patricks", "Summer"
]


class Theme:
    THEME_SEPARATORS = {
        "default": "|",
        "spooky": "🎃",
        "christmas": "❄️",
        "birthday": "🎂",
        "thanksgiving": "🦃",
        "valentines": "💕",
        "america": "🎆",
        "stpatricks": "🍀",
        "summer": "☀️",
    }

    THEME_BOOKENDS = {
        "default": "",
        "spooky": "👻",
        "christmas": "🎄",
        "birthday": "🎉",
        "thanksgiving": "🍗",
        "valentines": "❤️",
        "america": "🗽",
        "stpatricks": "🌈",
        "summer": "🌻",
    }

    THEME_COLORS = {}

    def __init__(self):
        self.__init_colors()

        Theme.THEME_COLORS = {
            "default": [curses.color_pair(2),
                        curses.color_pair(2)],
            "christmas": [curses.color_pair(5),
                          curses.color_pair(6)],
            "spooky": [curses.color_pair(10),
                       curses.color_pair(11)],
            "birthday": [curses.color_pair(14),
                         curses.color_pair(15)],
            "thanksgiving": [curses.color_pair(18),
                             curses.color_pair(19)],
            "valentines": [curses.color_pair(22),
                           curses.color_pair(23)],
            "america": [curses.color_pair(7),
                        curses.color_pair(8)],
            "stpatricks": [curses.color_pair(12),
                           curses.color_pair(13)],
            "summer": [curses.color_pair(16),
                       curses.color_pair(17)],
        }

    def __init_colors(self):
        # This allows the use of `-1` in `init_pair()` for accessing the
        # default foreground and background terminal colors. It also enables
        # transparency.
        curses.use_default_colors()

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

        # Default colors from terminal preferences
        curses.init_pair(1, -1, -1)

        # Locked data. Red on default background
        curses.init_pair(2, curses.COLOR_RED, -1)

        # Flagged data
        curses.init_pair(7, curses.COLOR_CYAN, -1)

        # Christmas variant
        curses.init_pair(5, curses.COLOR_GREEN, -1)
        curses.init_pair(6, curses.COLOR_RED, -1)

        if curses.can_change_color():
            # Spooky variant
            curses.init_pair(10, CURSES_GREEN, -1)
            curses.init_pair(11, CURSES_PURPLE, -1)

            # Birthday
            curses.init_pair(14, CURSES_BDAY_BLUE, -1)
            curses.init_pair(15, CURSES_BDAY_PINK, -1)

            # Thanksgiving
            curses.init_pair(18, CURSES_THANKSGIVING_BROWN, -1)
            curses.init_pair(19, CURSES_THANKSGIVING_ORANGE, -1)

            # Valentines
            curses.init_pair(22, VALENTINES_RED, -1)
            curses.init_pair(23, VALENTINES_PINK, -1)

            # America
            curses.init_pair(7, curses.COLOR_RED, -1)
            curses.init_pair(8, curses.COLOR_BLUE, -1)

            # St Patricks
            curses.init_pair(12, CURSES_GREEN, -1)
            curses.init_pair(13, LIGHT_GREEN, -1)

            # Summer
            curses.init_pair(16, WARM_ORANGE, -1)
            curses.init_pair(17, GOLDEN_YELLOW, -1)
        else:
            # Use fallback colors on non-supported terminals
            curses.init_pair(10, curses.COLOR_RED, -1)
            curses.init_pair(11, curses.COLOR_RED, -1)
            curses.init_pair(14, curses.COLOR_BLUE, -1)
            curses.init_pair(15, curses.COLOR_BLUE, -1)
            curses.init_pair(18, curses.COLOR_YELLOW, -1)
            curses.init_pair(19, curses.COLOR_RED, -1)
            curses.init_pair(22, curses.COLOR_RED, -1)
            curses.init_pair(23, curses.COLOR_RED, -1)
            curses.init_pair(7, curses.COLOR_RED, -1)
            curses.init_pair(8, curses.COLOR_BLUE, -1)
            curses.init_pair(12, curses.COLOR_GREEN, -1)
            curses.init_pair(13, curses.COLOR_GREEN, -1)
            curses.init_pair(16, curses.COLOR_YELLOW, -1)
            curses.init_pair(17, curses.COLOR_WHITE, -1)

    def __format_key(self, key: str) -> str:
        return key.replace(" ", "").lower()

    def get_colors(self, key: str):
        key = self.__format_key(key)
        if key not in Theme.THEME_COLORS:
            raise KeyError("Invalid Colors Key")
        return Theme.THEME_COLORS[key]

    def get_separator(self, key: str):
        key = self.__format_key(key)
        if key not in self.THEME_SEPARATORS:
            raise KeyError(f"Invalid Separator Key {key}")
        return self.THEME_SEPARATORS[key]

    def get_bookends(self, key: str):
        key = self.__format_key(key)
        if key not in self.THEME_BOOKENDS:
            raise KeyError("Invalid Bookend Key")
        return self.THEME_BOOKENDS[key]
