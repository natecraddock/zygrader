import curses

class Component:
    def __init__(self):
        raise NotImplementedError
        
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

    def __init__(self, height, width, title, message):
        self.available_rows = height
        self.available_cols = width

        self.title = title
        self.message = message

        self.__calculate_size()

        self.window = curses.newwin(self.rows, self.cols, self.y, self.x)
        self.window.bkgd(" ", curses.color_pair(1))
        
    def __calculate_size(self):
        self.rows = min(Popup.ROWS_MAX, self.available_rows - (Popup.PADDING * 2))
        self.cols = min(Popup.COLS_MAX, self.available_cols - (Popup.PADDING * 2))
        self.y = (self.available_rows - self.rows) // 2
        self.x = (self.available_cols - self.cols) // 2

    def draw_text(self):
        self.window.erase()
        #self.window.box(0, 0)

        # Draw lines of message
        message_y = self.rows // 2 - len(self.message) // 2
        message_row = 0
        for line in self.message:
            line = line[:self.cols - Popup.PADDING]
            message_x = self.cols // 2 - len(line) // 2
            self.window.addstr(message_y + message_row, message_x, line)
            message_row += 1
        
        # Draw title
        title_x = self.cols // 2 - len(self.title) // 2
        self.window.addstr(0, title_x, self.title)


    def draw(self):        
        self.draw_text()

        # Draw prompt to exit popup
        enter_string = "Press Enter"
        len(enter_string)
        
        y = self.rows - 2
        x = self.cols - 1 - Popup.PADDING - len(enter_string)
        self.window.addstr(y, x, enter_string)

        self.window.refresh()

    def resize(self, rows, cols):
        self.available_rows = rows
        self.available_cols = cols

        self.__calculate_size()

        try:
            self.window.mvwin(self.y, self.x)
        except:
            pass

        self.window.resize(self.rows, self.cols)


class BoolPopup(Popup):
    def draw(self):
        super().draw_text()
        
        # Draw prompt to exit popup
        y = self.rows - 3
        x = self.cols - 1 - Popup.PADDING - len("[Y]es")
        self.window.addstr(y, x, "[Y]es")
        self.window.addstr(y + 1, x, "[N]o")

        self.window.refresh()

class FilteredList(Component):
    def __filter_data(self, input_data, filter_function, filter_text):
        # Don't filter if the string is empty
        if filter_text == "":
            data = input_data[:]
            data.insert(0, "Back")
            return data

        # Apply filter (via function)
        data = ["Back"]
        if filter_function is None:
            for x in input_data:
                if x.find(filter_text) is not -1:
                    data.append(x)
        else:
            for x in input_data:
                if filter_function(x, filter_text):
                    data.append(x)

        return data

    def __fill_text(self, lines, selected_index):
        self.pad.erase()
        line = 0
        for l in lines:
            if line is selected_index:
                display_text = "> " + str(l)
            else:
                display_text = "  " + str(l)
            self.pad.addstr(line, 0, display_text)
            line += 1

    def __init__(self, y, x, rows, cols, options, prompt, filter_function):
        self.y = y
        self.x = x

        self.available_rows = rows - 1
        self.available_cols = cols - 1

        self.height = len(options) + 1
        self.width = 1000
        self.options = options[:]
        self.filter_function = filter_function

        self.scroll = 0
        self.selected_index = 1
        self.filter_text = ""

        self.prompt = prompt

        # List box
        self.pad = curses.newpad(self.height, self.width)

        # Text input
        self.window = curses.newwin(1, cols, rows - 1, 0)
        self.window.bkgd(" ", curses.color_pair(1))

        curses.curs_set(1)

    def resize(self, height, width):
        self.available_rows = height - 1
        self.available_cols = width - 1

        try:
            self.window.mvwin(height - 1, 0)
        except:
            pass
        self.window.resize(1, width)

    def draw(self):
        self.pad.erase()
        self.window.erase()

        self.data = self.__filter_data(self.options, self.filter_function, self.filter_text)

        # If no matches, set selected index to 0
        if len(self.data) is 1:
            self.selected_index = 0

        self.__fill_text(self.data, self.selected_index)

        self.pad.refresh(self.scroll, 0, self.y, self.x, self.available_rows - 1, self.available_cols)

        self.window.addstr(0, 0, f"{self.prompt}: {self.filter_text}")
        self.window.refresh()

    def clear(self):
        curses.curs_set(0)

    def down(self):
        if self.selected_index < len(self.data) - 1:
            self.selected_index += 1
        if self.selected_index > self.available_rows - 2:
            self.scroll += 1

    def up(self):
        if self.selected_index > 0:
            self.selected_index -= 1
        if self.selected_index < self.scroll:
            self.scroll -= 1

    def delchar(self):
        self.filter_text = self.filter_text[:-1]

    def addchar(self, c):
        self.filter_text += c

        self.selected_index = 1
    
    def selected(self):
        if self.selected_index is 0:
            return 0
        else:
            return self.data[self.selected_index]

class Menu(Component):
    def __init__(self, y, x, height, width, options):
        self.height = height
        self.width = width

        self.valid_options = {}
        for line in options:
            letter = line[0].lower()
            self.valid_options[letter] = line

        self.window = curses.newwin(height, width, y, x)
        
    def resize(self, rows, cols):
        self.height = rows
        self.width = cols

        self.window.resize(self.height, self.width)

    def draw(self):
        self.window.erase()

        line_num = 0
        for key in self.valid_options.keys():
            line = self.valid_options[key]
            
            display_str = f"[{key}] - {line}"
            self.window.addstr(line_num, 0, display_str)
            line_num += 1
    
        self.window.refresh()

    def valid_option(self, key):
        return key in self.valid_options.keys()
    
    def get_option(self, key):
        return self.valid_options[key]

class TextInput(Component):
    TEXT_NORMAL = 0
    TEXT_MASKED = 1

    def __init__(self, y, x, height, width, prompt, mask=TEXT_NORMAL):
        self.y = y
        self.x = x
        self.height = height
        self.width = width
        self.prompt = prompt
        self.masked = (mask is TextInput.TEXT_MASKED)

        self.text = ""

        # Always position text input at the bottom of the screen
        self.window = curses.newwin(1, self.width, self.height - 1, 0)
        self.window.bkgd(" ", curses.color_pair(1))

        curses.curs_set(1)
    
    def resize(self, height, width):
        self.height = height
        self.width = width

        try:
            self.window.mvwin(self.height - 1, 0)
        except:
            pass
        self.window.resize(1, self.width)
    
    def draw(self):
        self.window.erase()

        if self.masked:
            display_text = "*" * len(self.text)
        else:
            display_text = self.text
        
        self.window.addstr(0, 0, f"{self.prompt}: {display_text}")
        self.window.refresh()

    def close(self):
        curses.curs_set(0)
