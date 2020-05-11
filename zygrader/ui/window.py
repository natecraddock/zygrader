import curses
import os
import threading

from . import components
from .utils import add_str, resize_window
from .. import logger
from .. import config

from . import UI_GO_BACK

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
    KEY_ESC = 7
    KEY_NONE = -1

    CANCEL = -1

    instance = None

    @staticmethod
    def get_window() -> "Window":
        if Window.instance:
            return Window.instance
        return None

    def update_preferences(self):
        self.dark_mode = config.user.is_preference_set("dark_mode")
        self.christmas_mode = config.user.is_preference_set("christmas_mode")
        self.vim_mode = config.user.is_preference_set("vim_mode")
        self.left_right_menu_nav = config.user.is_preference_set("left_right_arrow_nav")
        self.clear_filter = config.user.is_preference_set("clear_filter")

    def input_thread_fn(self):
        while not self.kill_threads:
            self.get_input()
            self.dirty.release()
            logger.log("GOT SOME INPUT", self.event)

        # Cleanup when finished accepting input
        self.stdscr.clear()
        self.stdscr.refresh()
        curses.endwin()

    def __init__(self, callback, window_name):
        Window.instance = self

        """Initialize screen and run callback function"""
        self.name = window_name
        self.insert_mode = False
        self.event = Window.KEY_NONE
        self.event_value = None

        # A semaphore to control the draw thread
        self.dirty = threading.Semaphore(0)

        # Create a thread to handle input separately
        # The main thread handles drawing
        self.kill_threads = False
        self.input_thread = threading.Thread(target=self.input_thread_fn, name="Input", daemon=True)

        # Set user preference variables
        self.update_preferences()

        curses.wrapper(self.__init_curses, callback)

        # Allow the draw thread time to exit
        self.kill_threads = True
        self.draw()

        # Window is closing, join thread
        self.input_thread.join()

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

        # Stacks for Components and header titles
        self.components = []
        self.header_titles = [""]

        # Used for animated themes
        self.header_offset = 0
        self.__header_title = ""
        self.__header_title_load = ""
        self.__email_text = ""

        # Create window for input
        self.input_win = curses.newwin(0, 0, 1, 1)
        self.input_win.keypad(True)

        # Hack to fix getkey
        self.input_win.nodelay(True)
        self.input_win.getch()
        curses.flushinp()
        self.input_win.nodelay(False)

        # Input is now ready to start
        self.input_thread.start()

        # Execute callback with a reference to the window object
        callback(self)
    
    def __get_window_dimensions(self):
        self.rows, self.cols = self.stdscr.getmaxyx()

    def __init_colors(self):
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)

        # Holiday LIGHT variant
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_GREEN)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_RED)

        # Holiday DARK variant
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_RED, curses.COLOR_BLACK)

        curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLACK)

    def __resize_terminal(self):
        """Function to run after resize events in the terminal"""
        self.__get_window_dimensions()
        curses.resizeterm(self.rows, self.cols)

        for component in self.components:
            component.resize(self.rows, self.cols)

        self.draw(True)

    def get_header_colors(self):
        if self.dark_mode:
            return curses.color_pair(5), curses.color_pair(6)
        return curses.color_pair(3), curses.color_pair(4)

    def set_email(self, email):
        self.__email_text = email

    def set_header(self, text):
        """Load a string to be used for the next component"""
        self.__header_title_load = text

    def draw_header(self, text=""):
        """Set the header text"""        
        self.header.erase()
        resize_window(self.header, 1, self.cols)

        if self.header_titles[-1]:
            self.__header_title = self.header_titles[-1]

        if self.__header_title:
            display_text = f"{self.name} | {self.__header_title}"
        else:
            display_text = self.name

        if self.__email_text:
            display_text += f" | {self.__email_text}"

        if self.insert_mode:
            display_text += " | INSERT"

        # Centered header
        x = self.cols // 2 - len(display_text) // 2
        add_str(self.header, 0, x, display_text)

        # Christmas theme
        if self.christmas_mode:
            red, green = self.get_header_colors()

            for x in range(self.cols):
                if ((x // 2) + self.header_offset) % 2 is 0:
                    self.header.chgat(0, x, red | curses.A_BOLD)
                else:
                    self.header.chgat(0, x, green | curses.A_BOLD)

        self.header.refresh()

    def draw(self, flush=False):
        """Draw each component in the stack"""
        self.update_window()
        self.stdscr.erase()
        self.stdscr.refresh()
        
        self.draw_header()
        
        # Find last blocking component
        block_index = 0
        for index in reversed(range(len(self.components))):
            if self.components[index].blocking:
                block_index = index
                break

        for component in self.components[block_index:]:
            component.draw()
        
        if flush:
            curses.flushinp()

    def update_window(self):
        if self.dark_mode:
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        else:
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        self.draw_header()

    def get_input(self):
        """Get input and handle resize events"""
        input_code = "KEY_RESIZE"

        while input_code == "KEY_RESIZE":
            self.event = Window.KEY_NONE

            # getkey is blocking
            try:
                input_code = self.input_win.getkey()
            except curses.error:
                pass

            # Cases for each type of input
            if input_code == "KEY_RESIZE":
                self.__resize_terminal()
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
            elif self.vim_mode:
                self.get_input_vim(input_code)
                break
            elif input_code == "\x1b":
                self.input_win.nodelay(True)
                self.event = Window.KEY_ESC
                self.input_win.nodelay(False)
                break
            elif input_code == "KEY_BACKSPACE":
                self.event = Window.KEY_BACKSPACE
                break
            else:
                self.event = Window.KEY_INPUT
                self.event_value = input_code[0]
                break

        self.header_offset += 1
        # Draw after receiving input
        # self.draw()

    def get_input_vim(self, input_code):
        if input_code == "KEY_BACKSPACE" and self.insert_mode:
            self.event = Window.KEY_BACKSPACE
        elif input_code == "\x1b":
            self.input_win.nodelay(True)
            if self.insert_mode:
                self.insert_mode = False
            else:
                self.event = Window.KEY_ESC
            self.input_win.nodelay(False)
        else:
            if not self.insert_mode and input_code[0] == "i":
                self.insert_mode = True
                self.event = Window.KEY_NONE
            elif not self.insert_mode:
                if input_code[0] == "h":
                    self.event = Window.KEY_LEFT
                elif input_code[0] == "j":
                    self.event = Window.KEY_DOWN
                elif input_code[0] == "k":
                    self.event = Window.KEY_UP
                elif input_code[0] == "l":
                    self.event = Window.KEY_RIGHT
                else:
                    self.event = Window.KEY_NONE
            elif self.insert_mode:
                self.event = Window.KEY_INPUT
                self.event_value = input_code[0]

    def component_init(self, component):
        # Disable insertion mode on component change
        self.insert_mode = False

        self.components.append(component)
        if self.__header_title_load:
            self.header_titles.append(self.__header_title_load)
            self.__header_title_load = ""
        else:
            self.header_titles.append(self.header_titles[-1])

        self.draw()

    def component_deinit(self):
        # Disable insertion mode on component change
        self.insert_mode = False

        self.components.pop()
        self.header_titles.pop()
        self.draw()

    def create_popup(self, title, message, align=components.Popup.ALIGN_CENTER):
        """Create a popup with title and message that returns after enter"""
        pop = components.Popup(self.rows, self.cols, title, message, align)
        self.component_init(pop)
        
        while True:
            self.dirty.acquire()

            if self.event == Window.KEY_ENTER:
                break

        self.component_deinit()
    
    def create_bool_popup(self, title, message, align=components.Popup.ALIGN_CENTER):
        """Create a popup with title and message that returns true/false"""
        options = ["YES", "NO"]
        popup = components.OptionsPopup(self.rows, self.cols, title, message, options, align)
        self.component_init(popup)
        
        while True:
            self.dirty.acquire()

            if self.event in {Window.KEY_LEFT, Window.KEY_UP}:
                popup.previous()
            elif self.event in {Window.KEY_RIGHT, Window.KEY_DOWN}:
                popup.next()
            elif self.event == Window.KEY_ENTER:
                break

            self.draw()

        self.component_deinit()

        return popup.selected() == options[0]

    def create_options_popup(self, title, message, options, align=components.Popup.ALIGN_CENTER):
        """Create a popup with multiple options that can be selected with the keyboard"""
        popup = components.OptionsPopup(self.rows, self.cols, title, message, options, align)
        self.component_init(popup)

        while True:
            self.dirty.acquire()

            if self.event in {Window.KEY_LEFT, Window.KEY_UP}:
                popup.previous()
            elif self.event in {Window.KEY_RIGHT, Window.KEY_DOWN}:
                popup.next()
            elif self.event == Window.KEY_ENTER:
                break

            self.draw()

        self.component_deinit()

        return popup.selected()

    def create_list_popup(self, title, input_data=None, callback=None, list_fill=None):
        """Create a popup with a list of options that can be scrolled and selected

        If input_data (list) is supplied, the list will be drawn from the string representations
        of that data. If list_fill (function) is supplied, then list_fill will be called to generate
        a list to be drawn.
        """
        popup = components.ListPopup(self.rows, self.cols, title, input_data, list_fill)
        self.component_init(popup)

        while True:
            self.dirty.acquire()

            if self.event == Window.KEY_DOWN:
                popup.down()
            elif self.event == Window.KEY_UP:
                popup.up()
            elif self.event == Window.KEY_LEFT and self.left_right_menu_nav:
                break
            elif (self.event == Window.KEY_ENTER) or (self.event == Window.KEY_RIGHT and self.left_right_menu_nav):
                if popup.selected() is UI_GO_BACK:
                    break
                elif callback:
                    callback(popup.selected())
                else:
                    break

            self.draw()

        self.component_deinit()

        return popup.selected()

    def create_filename_input(self, purpose):
        """Get a valid filename from the user"""
        full_prompt = f"Enter the path and filename for {purpose} [~ is supported]"

        while True:
            path = self.create_text_input(full_prompt)
            if path == Window.CANCEL:
                return None

            path = os.path.expanduser(path)
            if os.path.exists(os.path.dirname(path)):
                return path

            msg = [f"Path {os.path.dirname(path)} does not exist!"]
            self.create_popup("Invalid Path", msg)
    
    def create_text_input(self, prompt, text="", mask=components.TextInput.TEXT_NORMAL):
        """Get text input from the user"""
        text = components.TextInput(1, 0, self.rows, self.cols, prompt, text, mask)
        self.component_init(text)

        if self.vim_mode:
            self.insert_mode = True
            self.draw()

        while True:
            self.dirty.acquire()

            if self.event == Window.KEY_ENTER:
                break
            elif self.event == Window.KEY_BACKSPACE:
                text.delchar()
            elif self.event == Window.KEY_INPUT:
                text.addchar(self.event_value)
            elif self.event == Window.KEY_LEFT:
                text.left()
            elif self.event == Window.KEY_RIGHT:
                text.right()
            elif self.event == Window.KEY_ESC:
                break

            self.draw()

        self.component_deinit()

        text.close()
        
        if self.event == Window.KEY_ESC:
            return Window.CANCEL
        return text.text

    def create_filtered_list(self, prompt, input_data=None, callback=None, list_fill=None, filter_function=None, draw_function=None):
        """
        If input_data (list) is supplied, the list will be drawn from the string representations
        of that data. If list_fill (function) is supplied, then list_fill will be called to generate
        a list to be drawn.
        """
        list_input = components.FilteredList(1, 0, self.rows - 1, self.cols, input_data, prompt, filter_function, draw_function)
        self.component_init(list_input)

        while True:
            self.dirty.acquire()

            if self.event == Window.KEY_DOWN:
                list_input.down()
            elif self.event == Window.KEY_UP:
                list_input.up()
            elif self.event == Window.KEY_LEFT and self.left_right_menu_nav:
                break
            elif self.event == Window.KEY_BACKSPACE:
                list_input.delchar()
            elif self.event == Window.KEY_INPUT:
                list_input.addchar(self.event_value)
            elif (self.event == Window.KEY_ENTER) or (self.event == Window.KEY_RIGHT and self.left_right_menu_nav):
                if callback and list_input.selected() != UI_GO_BACK:
                    list_input.dirty = True
                    callback(list_input.selected())

                    if self.clear_filter:
                        list_input.clear_filter()
                    list_input.flag_dirty()

                else:
                    break
            
            list_input.draw()

        list_input.clear()
        self.component_deinit()

        if self.event == Window.KEY_LEFT and self.left_right_menu_nav:
            return UI_GO_BACK

        return list_input.selected()

    def new_logger(self):
        logger = components.Logger(1, 0, self.rows - 1, self.cols)
        self.component_init(logger)

        return logger

    def remove_logger(self, logger):
        self.component_deinit()
