"""Defines all the color pairs and emojis for each theme.
To add a new theme:
    1. use 'curses.init_pair()' with the 256-colors you would like (use constants).
    This needs to be INSIDE of 'if curses.can_change_colors()'
    Make sure to define four color pairs: two for light and two for dark

    2. Then, add the theme with "{theme_name}_[light|dark]" convention to theme_colors,
    along with the color pair you specified.

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
This will print each color to the screen, colored appreopriately.


"""

import curses
THEMES = [
    "Default", "Christmas", "Spooky", "Birthday", "Thanksgiving", "Valentines"
]


class Theme:
    def __init__(self):
        self.__init_colors()
        # cannot declare this outside the function, since it requires curses to be initialized
        self.theme_colors = {
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
                               curses.color_pair(15)],
            "thanksgiving_dark": [curses.color_pair(16),
                                  curses.color_pair(17)],
            "thanksgiving_light":
            [curses.color_pair(18),
             curses.color_pair(19)],
            "valentines_dark": [curses.color_pair(20),
                                curses.color_pair(21)],
            "valentines_light": [curses.color_pair(22),
                                 curses.color_pair(23)],
        }

    THEME_SEPARATORS = {
        "default": "|",
        "spooky": "🎃",
        "christmas": "❄️",
        "birthday": "🎂",
        "thanksgiving": "🦃",
        "valentines": "💕",
    }
    THEME_BOOKENDS = {
        "default": "",
        "spooky": "👻",
        "christmas": "🎄",
        "birthday": "🎉",
        "thanksgiving": "🍗",
        "valentines": "❤️ ",
    }

    def __init_colors(self):
        CURSES_ORANGE = 202
        CURSES_GREY = 240
        CURSES_GREEN = 34
        CURSES_PURPLE = 93

        CURSES_BDAY_BLUE = 45
        CURSES_BDAY_PINK = 207

        CURSES_THXGVNG_BROWN = 130
        CURSES_THXGVNG_ORANGE = 208

        VALENTINES_RED = 196
        VALENTINES_PINK = 204

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

            # Thanksgiving DARK
            curses.init_pair(16, CURSES_THXGVNG_BROWN, curses.COLOR_BLACK)
            curses.init_pair(17, CURSES_THXGVNG_ORANGE, curses.COLOR_BLACK)

            # THanksgiving LIGHT
            curses.init_pair(18, CURSES_THXGVNG_BROWN, curses.COLOR_WHITE)
            curses.init_pair(19, CURSES_THXGVNG_ORANGE, curses.COLOR_WHITE)

            # Valentines DARK
            curses.init_pair(20, VALENTINES_RED, curses.COLOR_BLACK)
            curses.init_pair(21, VALENTINES_PINK, curses.COLOR_BLACK)

            # Valentines LIGHT
            curses.init_pair(22, VALENTINES_RED, curses.COLOR_WHITE)
            curses.init_pair(23, VALENTINES_PINK, curses.COLOR_WHITE)

    def get_colors(self, key: str):
        if key not in self.theme_colors:
            raise KeyError("Invalid Colors Key")

        # curses can change the colors for Christmas theme, even if the terminal doesn't support the other ones.
        # hence all this logic...
        if not curses.can_change_color():
            if "christmas" not in key:
                index = key.find("_")
                theme = key[:index]
                key = key.replace(theme, "default")
        return self.theme_colors[key]

    def get_separator(self, key: str):
        if key not in self.THEME_SEPARATORS:
            raise KeyError("Invalid Separator Key")
        return self.THEME_SEPARATORS[key]

    def get_bookends(self, key: str):
        if key not in self.THEME_BOOKENDS:
            raise KeyError("Invalid Bookend Key")
        return self.THEME_BOOKENDS[key]
