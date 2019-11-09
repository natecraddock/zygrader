import curses

from . import components

UI_LEFT = 0
UI_RIGHT = 1
UI_CENTERED = 2

class Window:
    KEY_BACKSPACE = 0
    KEY_ENTER = 1
    KEY_UP = 2
    KEY_DOWN = 3
    KEY_LEFT = 4
    KEY_RIGHT = 5
    KEY_INPUT = 6

    def __init__(self, callback, window_name):
        """Initialize screen and run callback function"""

        self.name = window_name

        curses.wrapper(self.__init_curses, callback)

    def __init_curses(self, stdscr, callback):
        """Configure basic curses settings"""
        self.stdscr = stdscr

        self.__get_window_dimensions()

        # Hide cursor
        curses.curs_set(0)

        self.__init_colors()

        # Create header
        self.header = curses.newwin(1, self.cols, 0, 0)
        self.header.bkgd(" ", curses.color_pair(1))
        self.set_header()

        # Create window for input
        self.input_win = curses.newwin(0, 0, 1, 1)
        self.input_win.keypad(True)

        # Hack to fix getkey
        self.input_win.nodelay(True)
        self.input_win.getch()
        curses.flushinp()
        self.input_win.nodelay(False)

        # Stack for operators
        self.operators = []

        # Execute callback with a reference to the window object
        callback(self)

        # Cleanup when finished
        self.stdscr.clear()
        self.stdscr.refresh()
    
    def __get_window_dimensions(self):
        self.rows, self.cols = self.stdscr.getmaxyx()

    def __init_colors(self):
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

    def __resize_terminal(self):
        """Function to run after resize events in the terminal"""
        self.__get_window_dimensions()
        curses.resizeterm(self.rows, self.cols)

        for operator in self.operators:
            operator.resize(self.rows, self.cols)

        self.draw(True)

    def set_header(self, text="", align=UI_CENTERED):
        """Set the header text"""        
        self.header.erase()
        self.header.resize(1, self.cols)
        self.__header_text = text

        if text:
            display_text = f"{self.name} | {self.__header_text}"
        else:
            display_text = self.name

        if align is UI_LEFT:
            x = 0
        elif align is UI_CENTERED:
            x = self.cols // 2 - len(display_text) // 2
        elif align is UI_RIGHT:
            x = self.cols - len(display_text) - 1
        
        self.header.addstr(0, x, display_text)
        self.header.refresh()

    def draw(self, flush=False):
        """Draw each operator in the stack"""
        self.stdscr.erase()
        self.stdscr.refresh()
        
        self.set_header(self.__header_text)
        
        for operator in self.operators:
            operator.draw()
        
        if flush:
            curses.flushinp()

    def get_input(self):
        """Get input and handle resize events"""

        input_code = "KEY_RESIZE"

        while input_code == "KEY_RESIZE":
            # getkey is blocking
            input_code = self.input_win.getkey()

            if input_code == "KEY_RESIZE":
                self.__resize_terminal()
            elif input_code == "KEY_BACKSPACE":
                self.event = Window.KEY_BACKSPACE
                break
            elif input_code in {"KEY_ENTER", "\n", "\r"}:
                self.event = Window.KEY_ENTER
                break
            elif input_code == "KEY_UP":
                self.event = Window.KEY_UP
                break
            elif input_code == "KEY_DOWN":
                self.event = Window.KEY_DOWN
                break
            elif input_code == "KEY_LEFT":
                self.event = Window.KEY_LEFT
                break
            elif input_code == "KEY_RIGHT":
                self.event = Window.KEY_RIGHT
                break
            else:
                self.event = Window.KEY_INPUT
                self.event_value = input_code[0]
                break
                
        # Draw after receiving input
        self.draw()

    def create_popup(self, title, message):
        """Create a popup with title and message that returns after enter"""
        pop = components.Popup(self.rows, self.cols, title, message)
        self.operators.append(pop)
        pop.draw()
        
        while True:
            self.get_input()

            if self.event == Window.KEY_ENTER:
                break

        self.operators.pop()
        self.draw()
    
    def create_bool_popup(self, title, message):
        """Create a popup with title and message that returns true/false"""
        popup = components.BoolPopup(self.rows, self.cols, title, message)
        self.operators.append(popup)
        popup.draw()
        
        while True:
            self.get_input()

            if self.event == Window.KEY_INPUT:
                if self.event_value.lower() == "y":
                    retval = True
                    break
                elif self.event_value.lower() == "n":
                    retval = False
                    break

        self.operators.pop()
        self.draw()

        return retval
    
    def text_input(self, prompt, callback=None, mask=components.TextInput.TEXT_NORMAL):
        """Get text input from the user"""
        text = components.TextInput(1, 0, self.rows, self.cols, prompt, mask)
        self.operators.append(text)
        text.draw()

        while True:
            self.get_input()

            if self.event == Window.KEY_ENTER:
                if callback:
                    return callback(self, text.text)
                break
            elif self.event == Window.KEY_BACKSPACE:
                text.text = text.text[:-1]
                text.draw()
            elif self.event == Window.KEY_INPUT:
                text.text += self.event_value
                text.draw()

        self.operators.pop()
        self.draw()

        text.close()
        
        if callback:
            return callback(self, text.text)
        else:
            return text.text

    def filtered_list(self, input_data, prompt, filter_function=None):
        list_input = components.FilteredList(1, 0, self.rows - 1, self.cols, input_data, prompt, filter_function)
        self.operators.append(list_input)
        list_input.draw()

        while True:
            self.get_input()

            if self.event == Window.KEY_DOWN:
                list_input.down()
            elif self.event == Window.KEY_UP:
                list_input.up()
            elif self.event == Window.KEY_BACKSPACE:
                list_input.delchar()
            elif self.event == Window.KEY_INPUT:
                list_input.addchar(self.event_value)
            elif self.event == Window.KEY_ENTER:
                break
            
            list_input.draw()

        list_input.clear()
        self.operators.pop()
        self.draw()

        return list_input.selected()

    def menu_input(self, options):
        menu_input = components.Menu(1, 0, self.rows, self.cols, options)
        self.operators.append(menu_input)
        menu_input.draw()

        while True:
            self.get_input()

            if self.event == Window.KEY_INPUT:
                if menu_input.valid_option(self.event_value):
                    break
        
        self.operators.pop()
        self.draw()

        return menu_input.get_option(self.event_value)

    def new_logger(self):
        logger = components.Logger(1, 0, self.rows - 1, self.cols)
        self.operators.append(logger)
        logger.draw()

        return logger

    def remove_logger(self, logger):
        self.operators.remove(logger)
        self.draw()
