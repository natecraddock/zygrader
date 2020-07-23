import curses

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

    def __calculate_size(self):
        self.rows = min(Popup.ROWS_MAX, self.available_rows - (Popup.PADDING * 2))
        self.cols = min(Popup.COLS_MAX, self.available_cols - (Popup.PADDING * 2))
        self.y = (self.available_rows - self.rows) // 2
        self.x = (self.available_cols - self.cols) // 2

    def __draw_message_left(self, message: list):
        longest_line = max([len(l) for l in message])

        message_x = self.cols // 2 - longest_line // 2

        message_y = self.rows // 2 - len(message) // 2
        message_row = 0
        for line in message:
            line = line[:self.cols - Popup.PADDING]
            add_str(self.window, message_y + message_row, message_x, line)
            message_row += 1

    def __draw_message_center(self, message: list):
        message_y = self.rows // 2 - len(message) // 2
        message_row = 0
        for line in message:
            line = line[:self.cols - Popup.PADDING]
            message_x = self.cols // 2 - len(line) // 2
            add_str(self.window, message_y + message_row, message_x, line)
            message_row += 1

    def draw_title(self):
        title_x = self.cols // 2 - len(self.title) // 2
        add_str(self.window, 0, title_x, self.title)

    def draw_text(self):
        self.window.erase()
        self.window.border()

        if not isinstance(self.message, list):
            message = list(self.message)
        else:
            message = self.message

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

    def __fill_text(self, lines):
        line_number = 0

        draw_lines = lines[self.scroll:self.scroll+self.rows - 1]

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
        self.masked = (mask is TextInput.TEXT_MASKED)

        self.text = text
        self.text_width = self.cols - (TextInput.PADDING * 2)

        # Set cursor to the location of text
        self.cursor_index = len(self.text)

        # Create a text input
        self.text_input = curses.newwin(TextInput.TEXT_HEIGHT, self.text_width,
                                        self.y + self.rows - TextInput.TEXT_HEIGHT - 1,
                                        self.x + TextInput.PADDING)
        self.text_input.bkgd(" ", curses.color_pair(1))
        curses.curs_set(1)

    def resize(self, rows, cols):
        super().resize(rows, cols)

        self.text_width = self.cols - (TextInput.PADDING * 2)

        try:
            self.text_input.mvwin(self.rows - TextInput.TEXT_HEIGHT - 1, self.x + TextInput.PADDING)
        except:
            pass
        resize_window(self.text_input, TextInput.TEXT_HEIGHT, self.text_width)

    def draw_text_chars(self, row, col, display_text):
        for char in display_text:
            add_str(self.text_input, row, col, char)
            col += 1
            if col >= self.text_width:
                col = 0
                row += 1

    def draw(self):
        super().draw_text()
        self.text_input.erase()

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
        # Insert character at cursor location and move cursor
        self.text = self.text[:self.cursor_index] + c + self.text[self.cursor_index:]
        self.right()

    def delchar(self):
        if self.cursor_index == 0:
            return

        # Remove character at cursor location
        self.text = self.text[:self.cursor_index - 1] + self.text[self.cursor_index:]
        self.left()

    def delcharforward(self):
        if self.cursor_index == len(self.text):
            return

        # Remove character just forward of cursor location
        self.text = self.text[:self.cursor_index] + self.text[self.cursor_index + 1:]

    def right(self):
        self.cursor_index = min(len(self.text), self.cursor_index + 1)

    def left(self):
        self.cursor_index = max(0, self.cursor_index - 1)

    def cursor_to_beginning(self):
        self.cursor_index = 0

    def cursor_to_end(self):
        self.cursor_index = len(self.text)

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
        if (self.selected_index + 1) > self.scroll + self.rows - ListPopup.V_PADDING:
            self.scroll = self.selected_index + ListPopup.V_PADDING - self.rows + 1
        # Cursor set above view
        elif self.selected_index < self.scroll:
            self.scroll = self.selected_index

    def draw_list(self):
        line = 0

        for l in self.data[self.scroll:self.scroll + self.rows - ListPopup.V_PADDING]:
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

        self.draw_title()

        if self.list_fill:
            self.data = ["Back"] + self.list_fill()

        self.draw_list()

        self.window.noutrefresh()

    def resize(self, rows, cols):
        Popup.resize(self, rows, cols)

    def selected(self):
        return self.selected_index - 1
