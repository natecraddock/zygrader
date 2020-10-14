import calendar
import curses
import datetime
from collections import Iterable

from .utils import add_str, resize_window


class Component:
    def __init__(self):
        # This determines if a component blocks layers beneath it completely
        self.blocking = True

    def resize(self, rows, cols):
        raise NotImplementedError

    def draw(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class Popup(Component):
    # Semi-arbitrary max/min restrictions for popups
    ROWS_MAX = 20
    COLS_MAX = 100
    PADDING = 3

    ALIGN_LEFT = 0
    ALIGN_CENTER = 1

    def __init__(self, height, width, title, message, align):
        # Popups only obscure the screen partially
        self.blocking = False

        self.available_rows = height
        self.available_cols = width

        self.title = title
        self.message = message
        self.align = align

        self.__calculate_size()

        self.window = curses.newwin(self.rows, self.cols, self.y, self.x)
        self.window.bkgd(" ", curses.color_pair(1))

        curses.curs_set(0)

    def __calculate_size(self):
        self.rows = min(Popup.ROWS_MAX,
                        self.available_rows - (Popup.PADDING * 2))
        self.cols = min(Popup.COLS_MAX,
                        self.available_cols - (Popup.PADDING * 2))
        self.y = (self.available_rows - self.rows) // 2
        self.x = (self.available_cols - self.cols) // 2

    def __find_wrap_index(self, line: str, max_line_len: int) -> int:
        WRAP_CHARS = {" ", "/"}

        max_line_len = self.cols - 2 * Popup.PADDING
        max_cutoff = min(len(line), max_line_len)

        cutoff = max_cutoff
        while cutoff > 0 and str(line[cutoff]) not in WRAP_CHARS:
            cutoff -= 1

        return max_cutoff if cutoff == 0 else cutoff

    def __calculate_wrapping(self, line: str) -> list:
        wrapped_lines = []
        if line == "":
            return [line]

        max_line_len = self.cols - 2 * Popup.PADDING

        while line:
            if len(line) > max_line_len:
                wrap_index = self.__find_wrap_index(line, max_line_len)
                wrapped_lines.append(line[:wrap_index])

                # If it's too long, wrap again
                line = line[wrap_index:]
            else:
                wrapped_lines.append(line)
                break
        return wrapped_lines

    def __draw_message_left(self, message: list):
        longest_line = max([len(l) for l in message])

        message_x = self.cols // 2 - longest_line // 2

        message_y = self.rows // 2 - len(message) // 2
        message_row = 0
        for line in message:
            wrapped_lines = self.__calculate_wrapping(line)
            for wrapped in wrapped_lines:
                add_str(self.window, message_y + message_row, message_x,
                        wrapped)
                message_row += 1

    def __draw_message_center(self, message: list):
        message_y = self.rows // 2 - len(message) // 2
        message_row = 0
        for line in message:
            wrapped_lines = self.__calculate_wrapping(line)
            for wrapped in wrapped_lines:
                message_x = self.cols // 2 - len(wrapped) // 2
                add_str(self.window, message_y + message_row, message_x,
                        wrapped)
                message_row += 1

    def draw_title(self):
        title_x = self.cols // 2 - len(self.title) // 2
        add_str(self.window, 0, title_x, self.title)

    def draw_text(self):
        self.window.erase()
        self.window.border()

        if isinstance(self.message, Iterable):
            message = list(self.message)
        else:
            message = self.message()

        # Draw lines of message
        if self.align == Popup.ALIGN_CENTER:
            self.__draw_message_center(message)
        elif self.align == Popup.ALIGN_LEFT:
            self.__draw_message_left(message)

        self.draw_title()

    def draw(self):
        self.draw_text()

        # Draw prompt to exit popup
        enter_string = "Press Enter"
        len(enter_string)

        y = self.rows - 2
        x = self.cols - 1 - Popup.PADDING - len(enter_string)
        add_str(self.window, y, x, enter_string)

        self.window.noutrefresh()

    def resize(self, rows, cols):
        self.available_rows = rows
        self.available_cols = cols

        self.__calculate_size()

        try:
            self.window.mvwin(self.y, self.x)
        except:
            pass

        resize_window(self.window, self.rows, self.cols)

    def set_message(self, message):
        self.message = message


class OptionsPopup(Popup):
    def __init__(self, height, width, title, message, options, use_dict, align):
        super().__init__(height, width, title, message, align)
        self.options = options
        self.use_dict = use_dict

        # Always add close as an option to dicts
        if self.use_dict:
            self.options["Close"] = None

        self.index = len(options) - 1
        self.options_length = sum([len(o) for o in options]) + len(options) + 2

    def draw(self):
        super().draw_text()

        y = self.rows - 2

        previous_length = 0
        index = 0
        for option in self.options:
            x = self.cols - 1 - Popup.PADDING - self.options_length + previous_length
            if index == self.index:
                add_str(self.window, y, x, option, curses.A_STANDOUT)
            else:
                add_str(self.window, y, x, option)

            previous_length += len(option) + 2
            index += 1

        self.window.noutrefresh()

    def next(self):
        self.index = (self.index + 1) % len(self.options)

    def previous(self):
        self.index = (self.index - 1) % len(self.options)

    def first(self):
        self.index = 0

    def last(self):
        self.index = len(self.options) - 1

    def selected(self):
        if self.use_dict:
            key = list(self.options)[self.index]
            return self.options[key]
        return self.options[self.index]


class DatetimeSpinner(Popup):
    NO_DATE = "datetime_no_date"

    def __init__(self, height, width, title, time, quickpicks, optional,
                 include_date):
        super().__init__(height, width, title, [], Popup.ALIGN_CENTER)

        if time is None:
            time = datetime.datetime.now()
        self.time = time

        if quickpicks:
            quickpicks = sorted(quickpicks)
        self.quickpicks = quickpicks

        self.optional = optional
        self.include_date = include_date

        self.__init_fields()
        self.__init_format_str()
        self.__init_input_str()

        curses.curs_set(0)

    def __resolve_date(self, date, year, month, day) -> datetime.datetime:
        """Find the closest valid date to an invalid date"""

        # Handle leap year
        if month == 2 and day > 28 and not calendar.isleap(year):
            day = 28

        # Handle out-of-range days in a month month:
        if month in {2, 4, 6, 9, 11} and day == 31:
            day = 30

        if month == 2 and day > 28:
            day = 28

        return date.replace(year, month, day)

    def __replace_date(self,
                       date: datetime.date,
                       year=None,
                       month=None,
                       day=None) -> datetime.datetime:
        """A wrapper around datetime.datetime.replace that checks for out-of range dates
        like a Feb 29 on a non-leap year"""

        if not year:
            year = date.year
        if not month:
            month = date.month
        if not day:
            day = date.day

        try:
            date = date.replace(year, month, day)
        except ValueError:
            date = self.__resolve_date(date, year, month, day)

        return date

    def __init_fields(self):
        self.field_index = 3

        date_x_fill = 16 if self.include_date else 0

        self.fields = []
        if self.include_date:
            self.fields = [
                {
                    "name": "month",
                    "x_offset": 0,
                    "unit": None,
                    "formatter": "%b"
                },
                {
                    "name": "day",
                    "x_offset": 4,
                    "unit": datetime.timedelta(days=1),
                    "formatter": "%d",
                },
                {
                    "name": "year",
                    "x_offset": 10,
                    "unit": None,
                    "formatter": "%y"
                },
            ]
        self.fields = self.fields + [
            {
                "name": "hour",
                "x_offset": 0 + date_x_fill,
                "unit": datetime.timedelta(hours=1),
                "formatter": "%I",
            },
            {
                "name": "minute",
                "x_offset": 3 + date_x_fill,
                "unit": datetime.timedelta(minutes=1),
                "formatter": "%M",
            },
            {
                "name": "second",
                "x_offset": 6 + date_x_fill,
                "unit": datetime.timedelta(seconds=1),
                "formatter": "%S",
            },
            {
                "name": "period",
                "x_offset": 8 + date_x_fill,
                "unit": datetime.timedelta(hours=12),
                "formatter": "%p",
            },
            {
                "name": "confirm",
                "x_offset": 13 + date_x_fill,
                "unit": None,
                "formatter": None,
                "display_name": "Confirm",
            },
        ]

        # If the date is optional (show 'No Date')
        if self.optional:
            self.fields.append({
                "name": "no_date",
                "x_offset": 23 + date_x_fill,
                "unit": None,
                "formatter": None,
                "display_name": "No Date",
            })

    def __init_format_str(self):
        self.format_str = ""
        if self.include_date:
            self.format_str = "%b %d, %Y at "
        self.format_str = self.format_str + "%I:%M:%S%p"

    def __init_input_str(self):
        self.input_str = ""
        self.input_str_last_field_index = None
        self._reset_month_str_position()

    def draw(self):
        date_str = (f"{self.time.strftime(self.format_str)} "
                    f"| Confirm{' | No Date' if self.optional else ''}")
        self.message = [date_str]
        super().draw_text()

        time_y = self.rows // 2
        time_x = self.cols // 2 - len(date_str) // 2

        field = self.fields[self.field_index]
        field_x = time_x + field["x_offset"]

        # Special Cases for confirm/no date
        if "display_name" in field:
            field_str = field["display_name"]
        else:
            field_str = self.time.strftime(field["formatter"])

        add_str(self.window, time_y, field_x, field_str, curses.A_STANDOUT)

        self.window.noutrefresh()

    def is_confirmed(self) -> str:
        return self.fields[self.field_index]["name"] in {"confirm", "no_date"}

    def get_time(self):
        if self.fields[self.field_index]["name"] == "no_date":
            return DatetimeSpinner.NO_DATE
        return self.time if self.include_date else self.time.time()

    def next_field(self):
        self.field_index = (self.field_index + 1) % len(self.fields)

    def previous_field(self):
        self.field_index = (self.field_index - 1) % len(self.fields)

    def first_field(self):
        self.field_index = 0

    def last_field(self):
        self.field_index = len(self.fields) - 1

    def increment_field(self):
        field = self.fields[self.field_index]
        if field["name"] == "minute" and self.quickpicks:
            self._increment_quickpick()
        else:
            self._increment_field()

    def decrement_field(self):
        field = self.fields[self.field_index]
        if field["name"] == "minute" and self.quickpicks:
            self._decrement_quickpick()
        else:
            self._decrement_field()

    def alt_increment_field(self):
        self._increment_field()

    def alt_decrement_field(self):
        self._decrement_field()

    def _increment_field(self):
        field = self.fields[self.field_index]
        if field["unit"]:
            self.time = self.time + field["unit"]
        else:
            if field["name"] == "month":
                # month is in 1..12, this incs 12->1
                new_month = (self.time.month % 12) + 1
                self.time = self.__replace_date(self.time, month=new_month)
            elif field["name"] == "year":
                new_year = min(max(self.time.year + 1, datetime.MINYEAR),
                               datetime.MAXYEAR)
                self.time = self.__replace_date(self.time, year=new_year)

    def _decrement_field(self):
        field = self.fields[self.field_index]
        if field["unit"]:
            self.time = self.time - field["unit"]
        else:
            if field["name"] == "month":
                new_month = self.time.month - 1
                if new_month == 0:
                    new_month = 12
                self.time = self.__replace_date(self.time, month=new_month)
            elif field["name"] == "year":
                new_year = min(max(self.time.year - 1, datetime.MINYEAR),
                               datetime.MAXYEAR)
                self.time = self.__replace_date(self.time, year=new_year)

    def _increment_quickpick(self):
        new_minute, new_second = self.quickpicks[0]
        for minute, second in self.quickpicks:
            if minute > self.time.minute:
                new_minute, new_second = minute, second
                break

        self.time = self.time.replace(minute=new_minute, second=new_second)

    def _decrement_quickpick(self):
        new_minute, new_second = self.quickpicks[-1]
        for minute, second in self.quickpicks[::-1]:
            if minute < self.time.minute:
                new_minute, new_second = minute, second
                break

        self.time = self.time.replace(minute=new_minute, second=new_second)

    def addchar(self, c):
        if self.input_str_last_field_index != self.field_index:
            self.input_str = ""
        self.input_str_last_field_index = self.field_index

        if c.isdigit():
            self.input_str += c

            if self._set_field_numerically():
                self.input_str = ""
                self.next_field()
        else:
            if self.fields[self.field_index]["name"] == "month":
                if self._set_month_from_chars(c):
                    self._reset_month_str_position()
                    self.next_field()
            if self.fields[self.field_index]["name"] == "period":
                c = c.lower()
                if c in "ap":
                    current_period = self.time.strftime("%p")[0].lower()
                    delta = datetime.timedelta()
                    if c == "p" and current_period == "a":
                        delta = datetime.timedelta(hours=12)
                    elif c == "a" and current_period == "p":
                        delta = datetime.timedelta(hours=-12)
                    self.time = self.time + delta
                    self.next_field()

    def _set_field_numerically(self):
        """Attempts to set the current field to
        the current input_str interpreted as a number
        Returns true if the input_str completely fills the current field"""
        try:
            new_val = int(self.input_str)
            field_name = self.fields[self.field_index]["name"]
            str_len = len(self.input_str)

            if field_name == "month":
                self.time = self.__replace_date(self.time, month=new_val)
                # 1 could be Jan or Oct-Dec,
                # but other single digits are complete
                return new_val > 1 or str_len >= 2
            elif field_name == "day":
                self.time = self.__replace_date(self.time, day=new_val)
                # 1-3 could have a second digit,
                # but other single digits are complete
                return new_val > 3 or str_len >= 2
            elif field_name == "year":
                century = self.time.year - (self.time.year % 100)
                new_year = century + new_val
                self.time = self.__replace_date(self.time, year=new_year)
                # user only enters last two digits
                return len(self.input_str) >= 2
            elif field_name == "hour":
                self.time = self.time.replace(hour=new_val)
                # 1 could have a second digit,
                # but other single digits are complete
                return new_val > 1 or str_len >= 2
            elif field_name == "minute":
                self.time = self.time.replace(minute=new_val)
                # 1-5 could have a second digit,
                # but other single digits are complete
                return new_val > 5 or str_len >= 2
            elif field_name == "second":
                self.time = self.time.replace(second=new_val)
                # 1-5 could have a second digit,
                # but other single digits are complete
                return new_val > 5 or str_len >= 2

        except ValueError:
            return False

    MONTH_STR_PATH = {
        "j": (
            1,
            False,
            {
                "a": (1, True, {
                    "n": (1, True, "uary")
                }),
                "u": (6, False, {
                    "n": (6, True, "e"),
                    "l": (7, True, "y")
                }),
            },
        ),
        "f": (2, True, {
            "e": (2, True, {
                "b": (2, True, "ruary")
            })
        }),
        "m": (3, False, {
            "a": (3, False, {
                "r": (3, True, "ch"),
                "y": (5, True, "")
            })
        }),
        "a": (
            4,
            False,
            {
                "p": (4, True, {
                    "r": (4, True, "il")
                }),
                "u": (8, True, {
                    "g": (8, True, "ust")
                })
            },
        ),
        "s": (9, True, {
            "e": (9, True, {
                "p": (9, True, "tember")
            })
        }),
        "o": (10, True, {
            "c": (10, True, {
                "t": (10, True, "ober")
            })
        }),
        "n": (11, True, {
            "o": (11, True, {
                "v": (11, True, "ember")
            })
        }),
        "d": (12, True, {
            "e": (12, True, {
                "c": (12, True, "ember")
            })
        }),
    }

    def _reset_month_str_position(self):
        self.month_str_position = DatetimeSpinner.MONTH_STR_PATH
        self.month_str_len = 0

    def _set_month_from_chars(self, newchar, recursed=False):
        """Attempts to set the month based on inputted chars
        Returns true once the input chars completely fill the month field"""
        newchar = newchar.lower()
        if newchar in self.month_str_position:
            guess, _, position = self.month_str_position[newchar]
            self.month_str_len += 1
            self.month_str_position = position

            self.time = self.time.replace(month=guess)

            return self.month_str_len >= 3
        elif not recursed:
            self._reset_month_str_position()
            return self._set_month_from_chars(newchar, recursed=True)


class FilteredList(Component):
    class ListLine:
        """Represents a single line of the list"""
        def __init__(self, index, data):
            self.index = index
            self.data = data
            self.text = str(data)
            self.color = curses.color_pair(1)

    def filter_string(self, line, filter):
        return line.text.lower().find(filter.lower()) is not -1

    def __filter_data(self, input_data, filter_function, filter_text):
        # Apply filter (via function)
        data = input_data[:1]

        for line in input_data[1:]:
            if filter_text == "" or filter_function(line, filter_text):
                data.append(line)

        self.dirty = False
        return data

    def __fill_text(self, lines):
        line_number = 0

        draw_lines = lines[self.scroll:self.scroll + self.rows - 1]

        for line in draw_lines:
            if (line_number + self.scroll) == self.selected_index:
                display_text = f"> {line.text}"
                add_str(self.window, line_number, 0, display_text,
                        curses.A_BOLD | line.color)
            else:
                display_text = f"  {line.text}"
                add_str(self.window, line_number, 0, display_text,
                        curses.A_DIM | line.color)

            line_number += 1

    def create_lines(self, options):
        lines = [FilteredList.ListLine(0, "Back")]

        if self.list_fill:
            lines += self.list_fill()
        else:
            for i, option in enumerate(options):
                lines.append(FilteredList.ListLine(i + 1, option))
        self.options = lines
        self.dirty = True

    def __init__(self, y, x, rows, cols, options, list_fill, prompt,
                 filter_function):
        self.blocking = True

        # Flag to determine if the list needs to be updated.
        # Only scrolling the list does not require an update of the list items,
        # but after filtering the list should be regenerated.
        self.dirty = True

        self.y = y
        self.x = x

        self.rows = rows
        self.cols = cols

        self.list_fill = list_fill
        self.create_lines(options)

        if filter_function:
            self.filter_function = filter_function
        else:
            self.filter_function = self.filter_string

        self.scroll = 0
        self.selected_index = 1
        self.selected_index = self.selected_index
        self.filter_text = ""

        self.prompt = prompt

        # List box
        self.window = curses.newwin(self.rows - 1, self.cols, y, x)
        self.window.bkgd(" ", curses.color_pair(1))

        # Text input
        self.text_input = curses.newwin(1, cols, self.rows, 0)
        self.text_input.bkgd(" ", curses.color_pair(1))

        curses.curs_set(1)

    def resize(self, rows, width):
        self.rows = rows - 1
        self.cols = width

        try:
            self.window.mvwin(self.y, self.x)
            self.text_input.mvwin(self.rows, 0)
        except:
            pass

        resize_window(self.window, self.rows - 1, self.cols)
        resize_window(self.text_input, 1, self.cols)

    def refresh(self):
        if self.list_fill:
            self.create_lines(None)
        self.flag_dirty()

    def draw(self):
        self.window.erase()
        self.text_input.erase()

        if self.dirty:
            self.data = self.__filter_data(self.options, self.filter_function,
                                           self.filter_text)

        # If no matches, set selected index to 0
        if len(self.data) is 1:
            self.selected_index = 0

        self.__fill_text(self.data)
        self.window.noutrefresh()

        add_str(self.text_input, 0, 0, f"{self.prompt}: {self.filter_text}")
        self.text_input.noutrefresh()

    def clear(self):
        curses.curs_set(0)

    def set_scroll(self):
        # Cursor set below view
        if (self.selected_index + 1) > self.scroll + self.rows - 1:
            self.scroll = self.selected_index + 2 - self.rows

        # Cursor set above view
        elif self.selected_index < self.scroll:
            self.scroll = self.selected_index

    def down(self):
        self.selected_index = (self.selected_index + 1) % len(self.data)
        self.set_scroll()

    def up(self):
        self.selected_index = (self.selected_index - 1) % len(self.data)
        self.set_scroll()

    def to_top(self):
        self.selected_index = 0
        self.set_scroll()

    def to_bottom(self):
        self.selected_index = len(self.data) - 1
        self.set_scroll()

    def delchar(self):
        self.filter_text = self.filter_text[:-1]

        self.selected_index = 0
        self.set_scroll()
        self.selected_index = 1

        self.dirty = True

    def addchar(self, c):
        self.filter_text += c
        self.selected_index = 0

        self.set_scroll()
        self.selected_index = 1

        self.dirty = True

    def selected(self):
        if self.selected_index < 0 or self.selected_index > len(self.data) - 1:
            self.selected_index = len(self.data) - 1

        return self.data[self.selected_index].index - 1

    def clear_filter(self):
        self.filter_text = ""
        self.selected_index = 0
        self.set_scroll()
        self.selected_index = 1

    def flag_dirty(self):
        self.dirty = True


class TextInput(Popup):
    TEXT_NORMAL = 0
    TEXT_MASKED = 1

    PADDING = 2
    # 1 Row for prompt, 4 for text
    TEXT_HEIGHT = 5

    def __init__(self, height, width, title, prompt, text, mask=TEXT_NORMAL):
        super().__init__(height, width, title, [prompt], Popup.ALIGN_CENTER)

        self.prompt = prompt
        self.masked = mask is TextInput.TEXT_MASKED

        self.text = text
        self.text_width = self.cols - (TextInput.PADDING * 2)

        # Set cursor to the location of text
        self.cursor_index = len(self.text)

        # Set selection marks
        self.reset_marks()

        # Create a text input
        self.text_input = curses.newwin(
            TextInput.TEXT_HEIGHT,
            self.text_width,
            self.y + self.rows - TextInput.TEXT_HEIGHT - 1,
            self.x + TextInput.PADDING,
        )
        self.text_input.bkgd(" ", curses.color_pair(1))
        curses.curs_set(1)

    def resize(self, rows, cols):
        super().resize(rows, cols)

        self.text_width = self.cols - (TextInput.PADDING * 2)

        try:
            self.text_input.mvwin(self.rows - TextInput.TEXT_HEIGHT - 1,
                                  self.x + TextInput.PADDING)
        except:
            pass
        resize_window(self.text_input, TextInput.TEXT_HEIGHT, self.text_width)

    def draw_text_chars(self, row, col, display_text):
        attrs = 0

        start_select = len(display_text)
        end_select = start_select
        if self.marks:
            start_select = min(self.marks)
            end_select = max(self.marks)

        index = 0
        for char in display_text:
            if index == start_select:
                attrs = curses.A_STANDOUT

            add_str(self.text_input, row, col, char, attrs)
            col += 1
            if col >= self.text_width:
                col = 0
                row += 1

            if index == end_select:
                attrs = 0
            index += 1

    def draw(self):
        super().draw_text()
        self.text_input.erase()

        curses.curs_set(0 if self.marks else 1)

        # Draw input prompt
        add_str(self.text_input, 0, 0, f"Input:")

        # Draw text and wrap on end of line
        if self.masked:
            display_text = "*" * len(self.text)
        else:
            display_text = self.text
        self.draw_text_chars(1, 0, display_text)

        # Set cursor index
        cursor_x = self.cursor_index % self.text_width
        cursor_y = (self.cursor_index // self.text_width) + 1
        self.text_input.move(cursor_y, cursor_x)

        self.window.noutrefresh()
        self.text_input.noutrefresh()

    def close(self):
        curses.curs_set(0)

    def addchar(self, c):
        before_index = self.cursor_index
        after_index = self.cursor_index

        # If text selected, use marks
        if self.marks:
            before_index = min(self.marks)
            after_index = max(self.marks) + 1
            self.reset_marks()

        # Insert character at cursor location
        #  and set cursor one past insert
        self.text = self.text[:before_index] + c + self.text[after_index:]
        self.cursor_index = before_index
        self.right()

    def delselection(self):
        left = self.text[:min(self.marks)]
        right = self.text[max(self.marks) + 1:]
        self.text = left + right
        self.cursor_index = min(self.marks)
        self.reset_marks()

    def delchar(self):
        if self.marks:
            self.delselection()
            return

        if self.cursor_index == 0:
            return

        # Remove character at cursor location
        self.text = self.text[:self.cursor_index -
                              1] + self.text[self.cursor_index:]
        self.left()

    def delcharforward(self):
        if self.marks:
            self.delselection()
            return

        if self.cursor_index == len(self.text):
            return

        # Remove character just forward of cursor location
        self.text = self.text[:self.
                              cursor_index] + self.text[self.cursor_index + 1:]

    def _cursor_mover(move_func):
        """Wrap a cursor-moving function without moving marks"""
        def wrapped(self, shift_pressed=False):
            if shift_pressed:
                if not self.marks:
                    self.marks = [self.cursor_index] * 2
                move_func(self)
                self.marks[1] = self.cursor_index
            else:
                move_func(self)
                self.reset_marks()

        return wrapped

    @_cursor_mover
    def right(self):
        self.cursor_index = min(len(self.text), self.cursor_index + 1)

    @_cursor_mover
    def left(self):
        self.cursor_index = max(0, self.cursor_index - 1)

    @_cursor_mover
    def cursor_to_beginning(self):
        self.cursor_index = 0

    @_cursor_mover
    def cursor_to_end(self):
        self.cursor_index = len(self.text)

    def reset_marks(self):
        self.marks = []


class Logger(Component):
    PADDING = 2

    def __init__(self, y, x, height, width):
        self.blocking = True

        self.height = height
        self.width = width

        self.window = curses.newwin(height, width, y, x)

        # Maintain a log (list) of data to display
        self.__log = []

    def resize(self, rows, cols):
        self.height = rows
        self.width = cols

        resize_window(self.window, self.height, self.width)

    def draw(self):
        self.window.erase()

        # Draw the last n elements of the log, with n being the available height
        # minus PADDING to give a border on the top and bottom

        NUM_LINES = self.height - Logger.PADDING

        liney = Logger.PADDING // 2
        for line in self.__log[-NUM_LINES:]:
            add_str(self.window, liney, 0, line)
            liney += 1

        # Loggers take control of event loop, refresh always
        self.window.refresh()

    def log(self, entry):
        self.__log.append(entry)

        self.draw()

    def append(self, entry):
        self.__log[-1] += entry

        self.draw()


class ListPopup(FilteredList, Popup):
    """A list in a popup view"""

    V_PADDING = Popup.PADDING * 2

    def __init__(self, rows, cols, title, input_data, list_fill):
        self.blocking = False
        Popup.__init__(self, rows, cols, title, None, None)

        if input_data:
            self.data = ["Back"] + input_data[:]
        else:
            self.data = []
        self.list_fill = list_fill

        self.scroll = 0
        self.selected_index = 1

    def set_scroll(self):
        if (self.selected_index +
                1) > self.scroll + self.rows - ListPopup.V_PADDING:
            self.scroll = self.selected_index + ListPopup.V_PADDING - self.rows + 1
        # Cursor set above view
        elif self.selected_index < self.scroll:
            self.scroll = self.selected_index

    def draw_list(self):
        line = 0

        for l in self.data[self.scroll:self.scroll + self.rows -
                           ListPopup.V_PADDING]:
            if (line + self.scroll) == self.selected_index:
                display_text = f"> {str(l)}"
                add_str(self.window, Popup.PADDING + line, Popup.PADDING,
                        display_text, curses.A_DIM)
            else:
                display_text = f"  {str(l)}"
                add_str(self.window, Popup.PADDING + line, Popup.PADDING,
                        display_text, curses.A_BOLD)
            line += 1

    def draw(self):
        self.window.erase()
        self.window.border()

        self.draw_title()

        if self.list_fill:
            self.data = ["Back"] + self.list_fill()

        self.draw_list()

        self.window.noutrefresh()

    def resize(self, rows, cols):
        Popup.resize(self, rows, cols)

    def selected(self):
        return self.selected_index - 1
