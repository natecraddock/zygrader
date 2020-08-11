import calendar
import curses
import datetime
from collections import Iterable

from .utils import add_str, add_ch, resize_window
from zygrader.ui import UI_GO_BACK
from .displaystring import DisplayStr

from zygrader.logger import log

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

    def __init__(self, height, width, title, message, align, can_click):
        # Popups only obscure the screen partially
        self.blocking = False

        self.available_rows = height
        self.available_cols = width

        self.title = title
        self.message = message
        self.align = align
        self.can_click = can_click

        self.__calculate_size()

        self.window = curses.newwin(self.rows, self.cols, self.y, self.x)
        self.window.bkgd(" ", curses.color_pair(1))

        curses.curs_set(0)

    def __calculate_size(self):
        self.rows = min(Popup.ROWS_MAX, self.available_rows - (Popup.PADDING * 2))
        self.cols = min(Popup.COLS_MAX, self.available_cols - (Popup.PADDING * 2))
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

    def __message_as_list(self):
        if isinstance(self.message, Iterable):
            message = list(self.message)
        else:
            message = self.message()
        return message

    def __message_display_lines(self):
        return [disp_line
                    for msg_line in self.__message_as_list()
                        for disp_line in self.__calculate_wrapping(msg_line)]

    def __draw_message(self):
        display_lines = self.__message_display_lines()
        longest_line = max((displayline for displayline in display_lines),
                            key=len)

        left_align_x = self._centered_start_x(longest_line)
        message_y = self._centered_start_y(display_lines)
        message_row = 0
        for line in display_lines:
            add_str(self.window,
                    message_y + message_row,
                    left_align_x if self.align == Popup.ALIGN_LEFT
                                    else self._centered_start_x(line),
                    line)
            message_row += 1

    def draw_title_bar(self):
        title_x = self._centered_start_x(self.title)
        add_str(self.window, 0, title_x, self.title)

        if self.can_click:
            add_ch(self.window, 0, self.cols - 3, curses.ACS_TTEE)
            add_ch(self.window, 1, self.cols - 3, curses.ACS_VLINE)
            add_ch(self.window, 1, self.cols - 2, 'X')
            add_ch(self.window, 2, self.cols - 3, curses.ACS_LLCORNER)
            add_ch(self.window, 2, self.cols - 2, curses.ACS_HLINE)
            add_ch(self.window, 2, self.cols - 1, curses.ACS_RTEE)

    def draw_text(self):
        self.window.erase()
        self.window.border()
        self.__draw_message()
        self.draw_title_bar()

    _ENTER_STRING = "Press Enter"

    def draw(self):
        self.draw_text()

        # Draw prompt to exit popup
        y = self._text_bottom_y()
        x = self._text_right_x() - len(Popup._ENTER_STRING)
        add_str(self.window, y, x, Popup._ENTER_STRING)

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

    def _to_relative_coords(self, y, x):
        return y - self.y, x - self.x

    def clicked(self, y, x):
        return UI_GO_BACK if self.__is_on_close(y, x) else None

    def __is_on_close(self, y, x):
        y, x = self._to_relative_coords(y, x)
        y_top = 0
        y_bottom = 2
        x_right = self.cols - 1
        x_left = x_right - 2
        return y >= y_top and y <= y_bottom and x >= x_left and x <= x_right

    def _msg_pos_clicked(self, y, x):
        """Returns the position of the msg at (y, x)
         as a tuple (index in self.message, char index in that line)
         or None if the (y, x) is not in the message"""
        y, x = self._to_relative_coords(y, x)

        # First see if click is in bounds of drawn message
        display_lines = self.__message_display_lines()
        #  First in the y direction
        message_y = self._centered_start_y(display_lines)
        y -= message_y
        if y < 0 or y >= len(display_lines):
            return None
        #  And then in the x direction
        longest_line = max((displayline for displayline in display_lines),
                            key=len)
        leftest_x = self._centered_start_x(longest_line)
        rightest_x = leftest_x + len(longest_line)
        if x < leftest_x or x >= rightest_x:
            return None

        # If in bounds of the message, then find the exact position
        message = self.__message_as_list()

        # Find the line from message that y is on
        msg_idx = -1
        msg_display_y_bottom = -1
        while True:
            msg_idx += 1
            wrapped_lines = self.__calculate_wrapping(message[msg_idx])
            msg_display_y_top = msg_display_y_bottom + 1
            msg_display_y_bottom += len(wrapped_lines)
            #log(f"msg_display_y_bottom:{msg_display_y_bottom}, y:{y}")
            if msg_display_y_bottom >= y:
                break

        # Find the wrapped display line that y is on
        wrapped_idx = 0
        msg_display_y = msg_display_y_top
        orig_message_x = 0
        while msg_display_y < y:
            orig_message_x += len(wrapped_lines[wrapped_idx])
            msg_display_y += 1
            wrapped_idx += 1
        wrapped_line = wrapped_lines[wrapped_idx]

        # Find the index in message[msg_idx] that x is on
        display_start_x = self._centered_start_x(wrapped_line)
        x -= display_start_x
        if x < 0 or x >= len(wrapped_line):
            return None
        char_index = orig_message_x + x

        return (msg_idx, char_index)

    def _text_bottom_y(self):
        return self.rows - 2

    def _text_right_x(self):
        return self.cols - 1 - Popup.PADDING

    def _centered_start_x(self, line):
        return self.cols // 2 - len(line) // 2

    def _centered_start_y(self, line_list):
        return self.rows // 2 - len(line_list) // 2

class OptionsPopup(Popup):
    def __init__(self, height, width, title, message, options,
                 use_dict, align, can_click):
        super().__init__(height, width, title, message, align, can_click)
        self.options = options
        self.use_dict = use_dict

        # Always add close as an option to dicts
        if self.use_dict:
            self.options["Close"] = UI_GO_BACK

        self.index = len(options) - 1
        options_strs_len = sum([len(o) for o in options])
        space_between_len = 2 * (len(options) - 1)
        self.options_length = options_strs_len + space_between_len

    def __options_start_x(self):
        return self._text_right_x() - self.options_length

    def draw(self):
        super().draw_text()

        y = self._text_bottom_y()

        previous_length = 0
        index = 0
        for option in self.options:
            x = self.__options_start_x() + previous_length
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
        return self.__item_at(self.index)

    def __item_at(self, idx):
        if self.use_dict:
            key = list(self.options)[idx]
            return self.options[key]
        return self.options[idx]

    def clicked(self, y, x):
        super_res = super().clicked(y, x)
        if super_res:
            return super_res
        y, x = self._to_relative_coords(y, x)
        if y != self._text_bottom_y():
            return None
        x = x - self.__options_start_x()
        if x < 0 or x > self.options_length:
            return None

        option_strs = list(self.options)

        options_idx = 0
        options_slide = len(option_strs[0])
        while options_slide < x:
            options_idx += 1
            options_slide += len(option_strs[options_idx]) + 2

        return self.__item_at(options_idx)

class DatetimeSpinner(Popup):
    NO_DATE = "datetime_no_date"

    __FIELDS = {
        'b': {'name': 'month',
               'unit': None,
               'formatter': lambda time: time.strftime('%b')},
        'm': {'name': 'month',
               'unit': None,
               'formatter': lambda time: time.strftime('%m')},
        'd': {'name': 'day',
               'unit': datetime.timedelta(days=1),
               'formatter': lambda time: time.strftime('%d')},
        'Y': {'name': 'year',
               'unit': None,
               # The built in Y formatter does not zero-pad
               'formatter': lambda time: f"{time.year:0>4}"},
        'I': {'name': 'hour-12',
               'unit': datetime.timedelta(hours=1),
               'formatter': lambda time: time.strftime('%I')},
        'H': {'name': 'hour-24',
               'unit': datetime.timedelta(hours=1),
               'formatter': lambda time: time.strftime('%H')},
        'M': {'name': 'minute',
               'unit': datetime.timedelta(minutes=1),
               'formatter': lambda time: time.strftime('%M')},
        'S': {'name': 'second',
               'unit': datetime.timedelta(seconds=1),
               'formatter': lambda time: time.strftime('%S')},
        'p': {'name': 'period',
               'unit': datetime.timedelta(hours=12),
               'formatter': lambda time: time.strftime('%p')},
        'confirm': {'name': 'confirm',
                    'unit': None,
                    'formatter': lambda _:'Confirm'},
        'no_date': {'name': 'no_date',
                    'unit': None,
                    'formatter': lambda _:'No Date'}
    }

    def __init__(self, height, width, title, time, quickpicks, optional,
                 include_date, time_format, can_click):
        super().__init__(height, width, title, [],
                         Popup.ALIGN_CENTER, can_click)

        if time is None:
            time = datetime.datetime.now()
        self.time = time

        if quickpicks:
            quickpicks = sorted(quickpicks)
        self.quickpicks = quickpicks

        self.optional = optional
        self.include_date = include_date

        if time_format is None:
            time_format = (f"{'%b %d, %Y at ' if self.include_date else ''}"
                           f"%I:%M:%S%p")

        self.__init_fields(time_format)
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

    def __replace_date(self, date: datetime.date, year=None, month=None, day=None) -> datetime.datetime:
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

    def __init_fields(self, time_format):
        self.fields = []
        self.field_index = 0

        format_pieces = [[]]

        prevC = None
        for c in time_format:
            if prevC == '%':
                if c in DatetimeSpinner.__FIELDS:
                    if not format_pieces[-1]:
                        format_pieces[-1] = len(self.fields)
                    else:
                        format_pieces.append(len(self.fields))
                    format_pieces.append([])
                    self.fields.append(DatetimeSpinner.__FIELDS[c])
                else:
                    format_pieces[-1].append(c)
            elif c != '%':
                format_pieces[-1].append(c)
            prevC = c
        if not format_pieces[-1]:
            del format_pieces[-1]

        self.format_pieces = [piece if isinstance(piece, int)
                                    else ''.join(piece)
                                        for piece in format_pieces]

        self.format_pieces += [" | ", len(self.fields)]
        self.fields.append(DatetimeSpinner.__FIELDS['confirm'])

        # If the date is optional (show 'No Date')
        if self.optional:
            self.format_pieces += [" | ", len(self.fields)]
            self.fields.append(DatetimeSpinner.__FIELDS['no_date'])

    def __init_input_str(self):
        self.input_str = ''
        self.input_str_last_field_index = None
        self._reset_month_str_position()

    def __display_str_from_format_piece(self, piece):
        if isinstance(piece, int):
            return self.fields[piece]['formatter'](self.time)
        else:
            return piece

    def __get_date_str(self):
        before_selected = []
        selected = None
        after_selected = []

        add_to = before_selected

        for format_piece in self.format_pieces:
            disp_str = self.__display_str_from_format_piece(format_piece)
            if (isinstance(format_piece, int)
                    and format_piece == self.field_index):
                selected = DisplayStr(f"[s:{disp_str}]")
                add_to = after_selected
            else:
                add_to.append(disp_str)

        return ''.join(before_selected) + selected + ''.join(after_selected)

    def draw(self):
        date_str = self.__get_date_str()
        self.message = [date_str]
        super().draw_text()
        self.window.noutrefresh()

    def is_confirmed(self) -> str:
        return self.fields[self.field_index]['name'] in {'confirm', 'no_date'}

    def get_time(self):
        if self.fields[self.field_index]['name'] == 'no_date':
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

    def clicked(self, y, x):
        """Return UI_GO_BACK for close, None for nothing clicked,
        otherwise the name of the field clicked"""
        super_res = super().clicked(y, x)
        if super_res:
            return super_res
        msg_pos = self._msg_pos_clicked(y, x)
        if not msg_pos or msg_pos[0] != 0:
            return None

        msg_x = msg_pos[1]
        x_slide = 0
        for format_piece in self.format_pieces:
            disp_str = self.__display_str_from_format_piece(format_piece)
            x_slide += len(disp_str)
            if x_slide > msg_x:
                if isinstance(format_piece, int):
                    self.field_index = format_piece
                    return self.fields[format_piece]['name']
                else:
                    return None

    def increment_field(self):
        field = self.fields[self.field_index]
        if field['name'] == 'minute' and self.quickpicks:
            self._increment_quickpick()
        else:
            self._increment_field()

    def decrement_field(self):
        field = self.fields[self.field_index]
        if field['name'] == 'minute' and self.quickpicks:
            self._decrement_quickpick()
        else:
            self._decrement_field()

    def alt_increment_field(self):
        self._increment_field()

    def alt_decrement_field(self):
        self._decrement_field()

    def _increment_field(self):
        field = self.fields[self.field_index]
        if field['unit']:
            self.time = self.time + field['unit']
        else:
            if field['name'] == 'month':
                #month is in 1..12, this incs 12->1
                new_month = (self.time.month % 12) + 1
                self.time = self.__replace_date(self.time, month=new_month)
            elif field['name'] == 'year':
                new_year = min(max(self.time.year + 1, datetime.MINYEAR),
                               datetime.MAXYEAR)
                self.time = self.__replace_date(self.time, year=new_year)

    def _decrement_field(self):
        field = self.fields[self.field_index]
        if field['unit']:
            self.time = self.time - field['unit']
        else:
            if field['name'] == 'month':
                new_month = self.time.month - 1
                if new_month == 0:
                    new_month = 12
                self.time = self.__replace_date(self.time, month=new_month)
            elif field['name'] == 'year':
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
            self.input_str = ''
        self.input_str_last_field_index = self.field_index

        if c.isdigit():
            self.input_str += c

            if self._set_field_numerically():
                self.input_str = ''
                self.next_field()
        else:
            if self.fields[self.field_index]['name'] == 'month':
                if self._set_month_from_chars(c):
                    self._reset_month_str_position()
                    self.next_field()
            if self.fields[self.field_index]['name'] == 'period':
                c = c.lower()
                if c in "ap":
                    current_period = self.time.strftime("%p")[0].lower()
                    delta = datetime.timedelta()
                    if c == 'p' and current_period == 'a':
                        delta = datetime.timedelta(hours=12)
                    elif c == 'a' and current_period == 'p':
                        delta = datetime.timedelta(hours=-12)
                    self.time = self.time + delta
                    self.next_field()

    def _set_field_numerically(self):
        """Attempts to set the current field to
        the current input_str interpreted as a number
        Returns true if the input_str completely fills the current field"""
        try:
            new_val = int(self.input_str)
            field_name = self.fields[self.field_index]['name']
            str_len = len(self.input_str)

            if field_name == 'month':
                self.time = self.__replace_date(self.time, month=new_val)
                #1 could be Jan or Oct-Dec,
                # but other single digits are complete
                return new_val > 1 or str_len >= 2
            elif field_name == 'day':
                self.time = self.__replace_date(self.time, day=new_val)
                #1-3 could have a second digit,
                # but other single digits are complete
                return new_val > 3 or str_len >= 2
            elif field_name == 'year':
                self.time = self.__replace_date(self.time, year=new_val)
                #user only enters 4-digit year
                return len(self.input_str) >= 4
            elif field_name in {'hour-12', 'hour-24'}:
                self.time = self.time.replace(hour=new_val)
                single_digit_cap = 1 if field_name == 'hour-12' else 2
                #1 (or 2 for 24-hour) could have a second digit,
                # but other single digits are complete
                return new_val > single_digit_cap or str_len >= 2
            elif field_name == 'minute':
                self.time = self.time.replace(minute=new_val)
                #1-5 could have a second digit,
                # but other single digits are complete
                return new_val > 5 or str_len >= 2
            elif field_name == 'second':
                self.time = self.time.replace(second=new_val)
                #1-5 could have a second digit,
                # but other single digits are complete
                return new_val > 5 or str_len >= 2

        except ValueError:
            return False

    MONTH_STR_PATH = {
        'j': (1, False, {
            'a': (1, True, {
                'n': (1, True, 'uary')
            }),
            'u': (6, False, {
                'n': (6, True, 'e'),
                'l': (7, True, 'y')
            })
        }),
        'f': (2, True, {
            'e': (2, True, {
                'b': (2, True, 'ruary')
            })
        }),
        'm': (3, False, {
            'a': (3, False, {
                'r': (3, True, 'ch'),
                'y': (5, True, '')
            })
        }),
        'a': (4, False, {
            'p': (4, True, {
                'r': (4, True, 'il')
            }),
            'u': (8, True, {
                'g': (8, True, 'ust')
            })
        }),
        's': (9, True, {
            'e': (9, True, {
                'p': (9, True, 'tember')
            })
        }),
        'o': (10, True, {
            'c': (10, True, {
                't': (10, True, 'ober')
            })
        }),
        'n': (11, True, {
            'o': (11, True, {
                'v': (11, True, 'ember')
            })
        }),
        'd': (12, True, {
            'e': (12, True, {
                'c': (12, True, 'ember')
            })
        })
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

    class ListLine():
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

    def __display_lines(self):
        return self.data[self.scroll:self.scroll+self.rows - 1]

    def __fill_text(self):
        line_number = 0

        draw_lines = self.__display_lines()

        for line in draw_lines:
            if (line_number + self.scroll) == self.selected_index:
                display_text = f"> {line.text}"
                add_str(self.window, line_number, 0, display_text, curses.A_BOLD | line.color)
            else:
                display_text = f"  {line.text}"
                add_str(self.window, line_number, 0, display_text, curses.A_DIM | line.color)

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

    def __init__(self, y, x, rows, cols, options, list_fill, prompt, filter_function):
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
            self.data = self.__filter_data(self.options, self.filter_function, self.filter_text)

        # If no matches, set selected index to 0
        if len(self.data) is 1:
            self.selected_index = 0

        self.__fill_text()
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

    def clicked(self, y, x):
        y -= self.y

        display_lines = self.__display_lines()
        if y < 0 or y >= len(display_lines):
            return None
        # The drawn lines have an indent of 2
        x -= (self.x + 2)
        if x < 0 or x >= len(display_lines[y].text):
            return None
        self.selected_index = y
        self.set_scroll()
        return self.selected()

class TextInput(Popup):
    TEXT_NORMAL = 0
    TEXT_MASKED = 1

    PADDING = 2
    # 1 Row for prompt, 4 for text
    TEXT_HEIGHT = 5

    def __init__(self, height, width, title, prompt, text, mask, can_click):
        super().__init__(height, width, title,
                         [prompt], Popup.ALIGN_CENTER, can_click)

        self.prompt = prompt
        self.masked = (mask is TextInput.TEXT_MASKED)

        self.text = text
        self.text_width = self.cols - (TextInput.PADDING * 2)

        # Set cursor to the location of text
        self.cursor_index = len(self.text)

        # Set selection marks
        self.reset_marks()

        # Create a text input
        self.text_input = curses.newwin(TextInput.TEXT_HEIGHT, self.text_width,
                                        self.__text_win_start_y(),
                                        self.__text_win_start_x())
        self.text_input.bkgd(" ", curses.color_pair(1))
        curses.curs_set(1)

    def __text_win_start_y(self):
        return self.y + self.rows - TextInput.TEXT_HEIGHT - 1

    def __text_win_start_x(self):
        return self.x + TextInput.PADDING

    def resize(self, rows, cols):
        super().resize(rows, cols)

        self.text_width = self.cols - (TextInput.PADDING * 2)

        try:
            self.text_input.mvwin(self.__text_win_start_y(),
                                  self.__text_win_start_x())
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
        self.text = self.text[:self.cursor_index - 1] + self.text[self.cursor_index:]
        self.left()

    def delcharforward(self):
        if self.marks:
            self.delselection()
            return

        if self.cursor_index == len(self.text):
            return

        # Remove character just forward of cursor location
        self.text = self.text[:self.cursor_index] + self.text[self.cursor_index + 1:]

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

    def __to_text_coords(self, y, x):
        # The input starts on the second line of the text window
        return (y - (self.__text_win_start_y() + 1),
                x - self.__text_win_start_x())

    def __text_coord_max_y(self):
        num_full_lines = len(self.text) // self.text_width
        if len(self.text) % self.text_width == 0:
            return num_full_lines - 1
        else:
            return num_full_lines

    def __text_coord_last_line_max_x(self):
        last_line_len = len(self.text) % self.text_width
        if last_line_len == 0:
            last_line_len = self.text_width
        return last_line_len - 1

    def __text_index_from_text_coords(self, y, x):
        if x < 0 or x >= self.text_width:
            return None
        max_y = self.__text_coord_max_y()
        if y < 0 or y > max_y:
            return None
        if y == max_y:
            if x > self.__text_coord_last_line_max_x():
                return None
        return y * self.text_width + x

    def __text_index_clicked(self, y, x):
        y, x = self.__to_text_coords(y, x)
        return self.__text_index_from_text_coords(y, x)

    def clicked(self, y, x):
        super_res = super().clicked(y, x)
        if super_res:
            return super_res
        idx = self.__text_index_clicked(y, x)
        self.reset_marks()
        if idx is not None:
            self.cursor_index = idx

    def mouse_pressed(self, y, x):
        idx = self.__text_index_clicked(y, x)
        if idx is None:
            self.reset_marks()
        else:
            self.marks = [idx, idx]

    def mouse_released(self, y, x):
        if not self.marks:
            return
        idx = self.__text_index_clicked(y, x)
        if idx is None:
            y, x = self.__to_text_coords(y, x)
            max_y = self.__text_coord_max_y()
            y = min(max(y, 0), max_y)
            x = min(max(x, 0), self.text_width - 1)
            if y == max_y:
                x = min(x, self.__text_coord_last_line_max_x())
            idx = self.__text_index_from_text_coords(y, x)
        self.marks[1] = idx
        self.cursor_index = idx

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

    def __init__(self, rows, cols, title, input_data, list_fill, can_click):
        self.blocking = False
        Popup.__init__(self, rows, cols, title, None, None, can_click)

        if input_data:
            self.data = ["Back"] + input_data[:]
        else:
            self.data = []
        self.list_fill = list_fill

        self.scroll = 0
        self.selected_index = 1

    def set_scroll(self):
        if (self.selected_index + 1) > self.scroll + self.rows - ListPopup.V_PADDING:
            self.scroll = self.selected_index + ListPopup.V_PADDING - self.rows + 1
        # Cursor set above view
        elif self.selected_index < self.scroll:
            self.scroll = self.selected_index

    def __display_lines(self):
        return self.data[self.scroll:self.scroll + self.rows - ListPopup.V_PADDING]

    def draw_list(self):
        line = 0

        for l in self.__display_lines():
            if (line + self.scroll) == self.selected_index:
                display_text = f"> {str(l)}"
                add_str(self.window, Popup.PADDING + line, Popup.PADDING, display_text, curses.A_DIM)
            else:
                display_text = f"  {str(l)}"
                add_str(self.window, Popup.PADDING + line, Popup.PADDING, display_text, curses.A_BOLD)
            line += 1

    def draw(self):
        self.window.erase()
        self.window.border()

        self.draw_title_bar()

        if self.list_fill:
            self.data = ["Back"] + self.list_fill()

        self.draw_list()

        self.window.noutrefresh()

    def resize(self, rows, cols):
        Popup.resize(self, rows, cols)

    def selected(self):
        return self.selected_index - 1

    def clicked(self, y, x):
        super_res = Popup.clicked(self, y, x)
        if super_res:
            return super_res
        y, x = self._to_relative_coords(y, x)
        y -= Popup.PADDING

        display_lines = self.__display_lines()
        if y < 0 or y >= len(display_lines):
            return None
        # The drawn lines have an indent of 2 beyond the padding
        x -= (Popup.PADDING + 2)
        if x < 0 or x >= len(display_lines[y]):
            return None
        self.selected_index = y
        self.set_scroll()
        return self.selected()