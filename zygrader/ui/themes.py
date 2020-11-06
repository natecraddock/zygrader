"""Defines all the color pairs and emojis for each theme.
To add a new theme, use 'curses.init_pair()' with the 256-colors you would like (use constants).

"""

import curses
from zygrader.config.preferences import THEMES


class Theme:
    def __init__(self):
        self.__init_colors()

        self.THEME_COLORS = {
            "default_dark": [curses.color_pair(1),
                             curses.color_pair(1)],
            "default_light": [curses.color_pair(2),
                              curses.color_pair(2)],
            "christmas_dark": [curses.color_pair(3),
                               curses.color_pair(4)],
            "christmas_light": [curses.color_pair(5),
                                curses.color_pair(6)],
            "spooky_dark": [curses.color_pair(8),
                            curses.color_pair(9)],
            "spooky_light": [curses.color_pair(10),
                             curses.color_pair(11)],
            "birthday_dark": [curses.color_pair(12),
                              curses.color_pair(13)],
            "birthday_light": [curses.color_pair(14),
                               curses.color_pair(15)]
        }

        self.THEME_SEPARATORS = {
            "default": "|",
            "spooky": "🎃",
            "christmas": "❄️",
            "birthday": "🎂"
        }
        self.THEME_BOOKENDS = {
            "default": "",
            "spooky": "👻",
            "christmas": "🎄",
            "birthday": "🎉"
        }

    def __init_colors(self):
        CURSES_ORANGE = 202
        CURSES_GREY = 240
        CURSES_GREEN = 34
        CURSES_PURPLE = 93
        CURSES_BDAY_BLUE = 4
        CURSES_BDAY_PINK = 200

        #this line can't change
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        #this line can't change
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)

        # Holiday DARK variant
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)

        # Holiday LIGHT variant
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_WHITE)
        curses.init_pair(6, curses.COLOR_RED, curses.COLOR_WHITE)

        # Flagged lines
        #this line can't change
        curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLACK)

        if curses.can_change_color():
            # Spooky variant DARK
            curses.init_pair(8, CURSES_ORANGE, curses.COLOR_BLACK)
            curses.init_pair(9, CURSES_GREY, curses.COLOR_BLACK)

            # Spooky variant LIGHT
            curses.init_pair(10, CURSES_GREEN, curses.COLOR_WHITE)
            curses.init_pair(11, CURSES_PURPLE, curses.COLOR_WHITE)

            # Birthday DARK
            curses.init_pair(12, CURSES_BDAY_BLUE, curses.COLOR_BLACK)
            curses.init_pair(13, CURSES_BDAY_PINK, curses.COLOR_BLACK)

            # Birthday LIGHT
            curses.init_pair(14, CURSES_BDAY_BLUE, curses.COLOR_WHITE)
            curses.init_pair(15, CURSES_BDAY_PINK, curses.COLOR_WHITE)

    def get_colors(self, key: str):
        if key not in self.THEME_COLORS:
            raise KeyError("Invalid Colors Key")

        # curses can change the colors for Christmas theme, even if the terminal doesn't support the other ones.
        # hence all this logic...
        if not curses.can_change_color():
            index = key.find("_")
            theme = key[:index]
            if theme is not "christmas":
                key = key.replace(theme, "default")
        return self.THEME_COLORS[key]

    def get_separator(self, key: str):
        if key not in self.THEME_SEPARATORS:
            raise KeyError("Invalid Separator Key")
        return self.THEME_SEPARATORS[key]

    def get_bookends(self, key: str):
        if key not in self.THEME_BOOKENDS:
            raise KeyError("Invalid Bookend Key")
        return self.THEME_BOOKENDS[key]