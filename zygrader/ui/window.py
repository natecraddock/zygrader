"""Window: The zygrader window manager and input handling"""
import curses
import os
import queue
import threading

from zygrader.config.preferences import is_preference_set
from . import components
from .utils import add_str, resize_window

from zygrader.logger import log

from . import UI_GO_BACK

UI_LEFT = 0
UI_RIGHT = 1
UI_CENTERED = 2

class Event:
    # Event types
    NONE = -1
    BACKSPACE = 0
    ENTER = 1
    UP = 2
    DOWN = 3
    LEFT = 4
    RIGHT = 5
    CHAR_INPUT = 6
    ESC = 7
    DELETE = 8
    REFRESH = 9
    HOME = 10
    END = 11
    TAB = 12
    BTAB = 13
    SLEFT = 14
    SRIGHT = 15
    SUP = 16
    SDOWN = 17
    SHOME = 18
    SEND = 19
    # Only button 1 is ever used, so no need to distinguish buttons
    MOUSE_CLICK = 20
    MOUSE_PRESS = 21
    MOUSE_RELEASE = 22

    # Modifier Keys
    MOD_ALT = 0

    def __init__(self, event_type, value, modifier=None):
        self.type = event_type
        self.value = value
        self.modifier = modifier

class WinContext:
    """A wrapper for the current window context when components execute a callback"""
    def __init__(self, window, event: Event, component, custom_data):
        self.window = window
        self.event = event
        self.component = component
        self.data = custom_data

class Window:
    EVENT_REFRESH_LIST = "flags_and_locks"
    CANCEL = -1

    MODE_NORMAL = 0
    MODE_INSERT = 1
    MODE_MARK = 2

    instance = None

    @staticmethod
    def get_window() -> "Window":
        if Window.instance:
            return Window.instance
        return None

    def update_preferences(self):
        self.dark_mode = is_preference_set("dark_mode")
        self.christmas_mode = is_preference_set("christmas_mode")
        self.vim_mode = is_preference_set("vim_mode")
        self.left_right_menu_nav = is_preference_set("left_right_arrow_nav")
        self.clear_filter = is_preference_set("clear_filter")
        self.use_esc_back = is_preference_set("use_esc_back")

    def set_mode(self, mode: int):
        """Set the vim edit mode"""
        if mode == Window.MODE_NORMAL:
            self.insert_mode = False
            self.mark_mode = False
        elif mode == Window.MODE_INSERT:
            self.insert_mode = True
            self.mark_mode = False
        elif mode == Window.MODE_MARK:
            self.insert_mode = False
            self.mark_mode = True

        self.draw_header()
        curses.doupdate()

        return Event.NONE

    def get_input(self, input_win) -> Event:
        """Get input and handle resize events"""
        event = Event.NONE
        event_value = Event.NONE
        event_mod = None

        # Nodelay causes exception when no input is given
        input_code = input_win.getch()
        if input_code == -1:
            return Event(event, event_value)

        # Check for ALT pressed
        elif input_code == 27:
            # Check for next character
            input_code = input_win.getch()
            if input_code == -1:
                # Interpret as a single ESC char
                if self.insert_mode:
                    event = self.set_mode(Window.MODE_NORMAL)
                elif self.mark_mode:
                    event = self.set_mode(Window.MODE_NORMAL)
                else:
                    event = Event.ESC
                return Event(event, event_value)
            # Character accepted, check next symbol
            event_mod = Event.MOD_ALT

        # Cases for each type of input
        if input_code == curses.KEY_RESIZE:
            self.__resize_terminal()
            curses.flushinp()
        elif input_code == curses.KEY_MOUSE:
            mouse = curses.getmouse()
            bstate = mouse[4]
            # The bstate checks are ordered to minimize strange effects
            if bstate & curses.BUTTON1_CLICKED:
                event = Event.MOUSE_CLICK
            elif bstate & curses.BUTTON1_RELEASED:
                event = Event.MOUSE_RELEASE
            elif bstate & curses.BUTTON1_PRESSED:
                event = Event.MOUSE_PRESS
            event_value = (mouse[2], mouse[1]) # y, x of mouse event
        elif input_code in {curses.KEY_ENTER, ord('\n'), ord('\r')}:
            event = Event.ENTER
        elif input_code == curses.KEY_HOME:
            event = Event.HOME
        elif input_code == curses.KEY_END:
            event = Event.END
        elif input_code == curses.KEY_UP:
            event = Event.UP
        elif input_code == curses.KEY_DOWN:
            event = Event.DOWN
        elif input_code == curses.KEY_LEFT:
            event = Event.LEFT
        elif input_code == curses.KEY_RIGHT:
            event = Event.RIGHT
        elif input_code == curses.KEY_SLEFT:
            event = Event.SLEFT
        elif input_code == curses.KEY_SRIGHT:
            event = Event.SRIGHT
        elif input_code == curses.KEY_SHOME:
            event = Event.SHOME
        elif input_code == curses.KEY_SEND:
            event = Event.SEND
        elif input_code == curses.KEY_SR:
            event = Event.SUP
        elif input_code == curses.KEY_SF:
            event = Event.SDOWN
        elif input_code == ord('\t'):
            event = Event.TAB
        elif input_code == curses.KEY_BTAB:
            event = Event.BTAB
        elif self.vim_mode:
            event, event_value = self.get_input_vim(input_code)
        elif input_code == 27: #curses does not have a pre-defined constant for ESC
            event = Event.ESC
        elif input_code == curses.KEY_BACKSPACE:
            event = Event.BACKSPACE
        elif input_code == curses.KEY_DC:
            event = Event.DELETE
        elif input_code:
            event = Event.CHAR_INPUT
            event_value = chr(input_code)

        self.header_offset += 1
        return Event(event, event_value, event_mod)

    def get_input_vim(self, input_code):
        event = Event.NONE
        event_value = Event.NONE

        if input_code == curses.KEY_BACKSPACE and self.insert_mode:
            event = Event.BACKSPACE
        elif input_code == curses.KEY_DC and self.insert_mode:
            event = Event.DELETE
        elif input_code == 27:
            if self.insert_mode:
                event = self.set_mode(Window.MODE_NORMAL)
            elif self.mark_mode:
                event = self.set_mode(Window.MODE_NORMAL)
            else:
                event = Event.ESC
        elif not self.mark_mode and not self.insert_mode and chr(input_code) == "i":
            event = self.set_mode(Window.MODE_INSERT)
        elif not self.insert_mode and not self.mark_mode and chr(input_code) == "v":
            event = self.set_mode(Window.MODE_MARK)
        elif not self.insert_mode:
            if chr(input_code) == "h":
                event = Event.SLEFT if self.mark_mode else Event.LEFT
            elif chr(input_code) == "j":
                event = Event.SDOWN if self.mark_mode else Event.DOWN
            elif chr(input_code) == "k":
                event = Event.SUP if self.mark_mode else Event.UP
            elif chr(input_code) == "l":
                event = Event.SRIGHT if self.mark_mode else Event.RIGHT
            else:
                event = Event.NONE
        elif self.insert_mode:
            event = Event.CHAR_INPUT
            event_value = chr(input_code)

        return event, event_value

    def input_thread_fn(self):
        # Create window for input
        input_win = curses.newwin(0, 0, 1, 1)
        input_win.keypad(True)
        input_win.nodelay(True)

        while True:
            self.take_input.wait()
            event = self.get_input(input_win)
            if not self.take_input.is_set():
                continue
            if event.type != Event.NONE:
                self.event_queue.put_nowait(event)

            # Kill thread at end
            if self.stop_input:
                break

    def clear_event_queue(self):
        """Clear all events from the queue"""
        while not self.event_queue.empty():
            self.event_queue.get_nowait()

    def consume_event(self) -> Event:
        """Consume one event from the event queue. Blocks when no events are found"""
        return self.event_queue.get()

    def push_refresh_event(self):
        """Force the ui to refresh even when it is in an input loop"""
        event = Event(Event.REFRESH, None)
        self.event_queue.put_nowait(event)

    def __init__(self, callback, window_name):
        Window.instance = self

        """Initialize screen and run callback function"""
        self.name = window_name
        self.insert_mode = False
        self.mark_mode = False

        self.event_queue = queue.Queue()

        # Create a thread to handle input separately
        # The main thread handles drawing
        self.input_thread = threading.Thread(target=self.input_thread_fn, name="Input", daemon=True)
        self.stop_input = False

        # Add an event to toggle input thread
        self.take_input = threading.Event()
        self.take_input.set()

        # Set user preference variables
        self.update_preferences()

        curses.wrapper(self.__init_curses, callback)

        # Cleanup when finished accepting input
        self.stop_input = True
        self.stdscr.clear()
        self.stdscr.refresh()
        curses.endwin()

    def __init_curses(self, stdscr, callback):
        """Configure basic curses settings"""
        self.stdscr = stdscr

        self.__get_window_dimensions()

        # Hide cursor
        curses.curs_set(0)

        # Enable reporting mouse event
        mask = (curses.BUTTON1_CLICKED |
                curses.BUTTON1_PRESSED |
                curses.BUTTON1_RELEASED)
        avail, _ = curses.mousemask(mask)
        self.can_click = avail & curses.BUTTON1_CLICKED

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
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_WHITE)

        # Holiday DARK variant
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_RED, curses.COLOR_BLACK)

        # Flagged lines
        curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLACK)

    def __resize_terminal(self):
        """Function to run after resize events in the terminal"""
        self.__get_window_dimensions()
        curses.resize_term(self.rows, self.cols)

        for component in self.components:
            component.resize(self.rows, self.cols)

        self.draw()

    def get_header_colors(self):
        if self.dark_mode:
            return curses.color_pair(5), curses.color_pair(6)
        return curses.color_pair(3), curses.color_pair(4)

    def set_email(self, email):
        self.__email_text = email

    def set_header(self, text):
        """Load a string to be used for the next component"""
        self.__header_title_load = text

    def draw_header(self):
        """Set the header text"""
        self.header.erase()
        resize_window(self.header, 1, self.cols)

        # Store the cursor location
        loc = curses.getsyx()

        if self.header_titles[-1]:
            self.__header_title = self.header_titles[-1]

        if self.__header_title:
            if callable(self.__header_title):
                display_text = f"{self.name} | {self.__header_title()}"
            else:
                display_text = f"{self.name} | {self.__header_title}"
        else:
            display_text = self.name

        if self.__email_text:
            display_text += f" | {self.__email_text}"

        if self.insert_mode:
            display_text += " | INSERT"
        elif self.mark_mode:
            display_text += " | VISUAL"

        # Centered header
        row = self.cols // 2 - len(display_text) // 2
        add_str(self.header, 0, row, display_text)

        # Christmas theme
        if self.christmas_mode:
            red, green = self.get_header_colors()

            for row in range(self.cols):
                if ((row // 2) + self.header_offset) % 2 is 0:
                    self.header.chgat(0, row, red | curses.A_BOLD)
                else:
                    self.header.chgat(0, row, green | curses.A_BOLD)

        self.header.noutrefresh()

        curses.setsyx(*loc)

    def draw(self):
        """Draw each component in the stack"""
        self.update_window()
        self.stdscr.erase()
        self.stdscr.noutrefresh()

        self.draw_header()

        # Find last blocking component
        block_index = 0
        for index in reversed(range(len(self.components))):
            if self.components[index].blocking:
                block_index = index
                break

        for component in self.components[block_index:]:
            component.draw()

        # All windows have been tagged for redraw with noutrefresh
        # Now do a single draw pass with doupdate
        curses.doupdate()

    def update_window(self):
        if self.dark_mode:
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        else:
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_WHITE)
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_WHITE)
        self.stdscr.bkgd(" ", curses.color_pair(1))

    def component_init(self, component):
        # Disable insertion mode on component change
        self.insert_mode = False
        self.mark_mode = False

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
        self.mark_mode = False

        self.components.pop()
        self.header_titles.pop()
        self.draw()

    def create_popup(self, title, message, align=components.Popup.ALIGN_CENTER):
        """Create a popup with title and message that returns after enter"""
        popup = components.Popup(self.rows, self.cols, title,
                                 message, align, self.can_click)
        self.component_init(popup)

        while True:
            event = self.consume_event()

            if (event.type == Event.ENTER
                  or (event.type == Event.MOUSE_CLICK
                      and popup.clicked(*event.value) == UI_GO_BACK)):
                break

        self.component_deinit()

    def create_waiting_popup(self, title, message, align=components.Popup.ALIGN_CENTER):
        """Create a popup that the user cannot exit out of.

        Exiting the popup must be done by calling close() on the returned control object.
        The creator of the popup should block until it calls close() to avoid input issues.
        """

        class WaitingPopupControl:
            def __init__(self, window):
                self.window = window
                self.has_exited = False

            def update(self):
                self.window.draw()

            def close(self):
                if not self.has_exited:
                    self.window.component_deinit()
                    self.window.clear_event_queue()
                self.has_exited = True

        popup = components.OptionsPopup(self.rows, self.cols, title, message,
                                        [], False, align, can_click=False)
        self.component_init(popup)

        return WaitingPopupControl(self)

    def create_bool_popup(self, title, message, align=components.Popup.ALIGN_CENTER):
        """Create a popup with title and message that returns true/false"""
        options = ["Yes", "No"]
        selected = self.create_options_popup(title, message, options, align)
        return selected == options[0]

    def create_options_popup(self, title, message, options, align=components.Popup.ALIGN_CENTER):
        """Create a popup with multiple options that can be selected with the keyboard.
        options is either a dictionary of string to callback function pairs or a list of strings
        """
        use_dict = bool(isinstance(options, dict))

        popup = components.OptionsPopup(self.rows, self.cols, title,
                                        message, options, use_dict,
                                        align, self.can_click)
        self.component_init(popup)

        retval = None
        while True:
            event = self.consume_event()

            if event.type in {Event.LEFT, Event.UP, Event.BTAB}:
                popup.previous()
            elif event.type in {Event.RIGHT, Event.DOWN, Event.TAB}:
                popup.next()
            elif event.type == Event.HOME:
                popup.first()
            elif event.type == Event.END:
                popup.last()
            elif event.type == Event.ESC and self.use_esc_back:
                break
            elif event.type == Event.ENTER:
                if use_dict:
                    callback_fn = popup.selected()
                    if callback_fn == UI_GO_BACK:
                        retval = UI_GO_BACK
                        break
                    retval = callback_fn(WinContext(self, event, popup, None))
                    if retval:
                        break
                else:
                    retval = popup.selected()
                    break
            elif event.type == Event.MOUSE_CLICK:
                clicked = popup.clicked(*event.value)
                if clicked == UI_GO_BACK:
                    retval = UI_GO_BACK
                    break
                elif clicked is not None:
                    if use_dict:
                        retval = clicked(WinContext(self, event, popup, None))
                        if retval:
                            break

            self.draw()

        self.component_deinit()

        return retval

    def create_datetime_spinner(self, title, time=None,
                                quickpicks=None, optional=False,
                                include_date=True, time_format=None):
        """Create a popup with a datetime spinner to select a datetime.
        time is the initial time to present
        quickpicks is an optional list of (minute, second) pairs.
         If provided, spinning the minute field will spin through the quickpicks
        """

        popup = components.DatetimeSpinner(self.rows, self.cols, title, time,
                                           quickpicks, optional, include_date,
                                           time_format, self.can_click)

        self.component_init(popup)

        retval = None
        while True:
            event = self.consume_event()

            if event.type in {Event.LEFT, Event.BTAB}:
                popup.previous_field()
            elif event.type in {Event.RIGHT, Event.TAB}:
                popup.next_field()
            elif event.type == Event.HOME:
                popup.first_field()
            elif event.type == Event.END:
                popup.last_field()
            elif event.type == Event.UP:
                popup.increment_field()
            elif event.type == Event.DOWN:
                popup.decrement_field()
            elif event.type == Event.SUP:
                popup.alt_increment_field()
            elif event.type == Event.SDOWN:
                popup.alt_decrement_field()
            elif event.type == Event.CHAR_INPUT:
                popup.addchar(event.value)
            elif event.type == Event.ESC and self.use_esc_back:
                retval = UI_GO_BACK
                break
            elif event.type == Event.ENTER and popup.is_confirmed():
                break
            elif event.type == Event.MOUSE_CLICK:
                clicked = popup.clicked(*event.value)
                if clicked == UI_GO_BACK:
                    retval = UI_GO_BACK
                    break
                elif clicked and popup.is_confirmed():
                    break

            self.draw()

        self.component_deinit()

        return retval if retval else popup.get_time()


    def create_list_popup(self, title, input_data=None, callback=None, list_fill=None):
        """Create a popup with a list of options that can be scrolled and selected

        If input_data (list) is supplied, the list will be drawn from the string representations
        of that data. If list_fill (function) is supplied, then list_fill will be called to generate
        a list to be drawn.
        """
        popup = components.ListPopup(self.rows, self.cols, title,
                                     input_data, list_fill, self.can_click)
        self.component_init(popup)

        retval = None
        while True:
            event = self.consume_event()

            if event.type == Event.DOWN:
                popup.down()
            elif event.type == Event.UP:
                popup.up()
            elif event.type == Event.HOME:
                popup.to_top()
            elif event.type == Event.END:
                popup.to_bottom()
            elif event.type == Event.LEFT and self.left_right_menu_nav:
                break
            elif event.type == Event.ESC and self.use_esc_back:
                retval = UI_GO_BACK
                break
            elif ((event.type == Event.ENTER) or
                  (event.type == Event.RIGHT and self.left_right_menu_nav)):
                if popup.selected() is UI_GO_BACK:
                    break
                elif callback:
                    callback(WinContext(self, event, popup, popup.selected()))
                else:
                    break

            self.draw()

        self.component_deinit()

        return retval if retval else popup.selected()

    def create_text_input(self, title, prompt, text="", mask=components.TextInput.TEXT_NORMAL):
        """Get text input from the user"""
        text_input = components.TextInput(self.rows, self.cols, title, prompt,
                                          text, mask, self.can_click)
        self.component_init(text_input)

        if self.vim_mode:
            self.insert_mode = True
            self.draw()

        while True:
            event = self.consume_event()

            if event.type == Event.ENTER:
                break
            elif event.type == Event.BACKSPACE:
                text_input.delchar()
            elif event.type == Event.DELETE:
                text_input.delcharforward()
            elif event.type == Event.CHAR_INPUT:
                text_input.addchar(event.value)
            elif event.type == Event.LEFT:
                text_input.left()
            elif event.type == Event.RIGHT:
                text_input.right()
            elif event.type == Event.SLEFT:
                text_input.left(shift_pressed=True)
            elif event.type == Event.SRIGHT:
                text_input.right(shift_pressed=True)
            elif event.type == Event.ESC: # Always allow exiting from text input with ESC
                break
            elif event.type == Event.HOME:
                text_input.cursor_to_beginning()
            elif event.type == Event.END:
                text_input.cursor_to_end()
            elif event.type == Event.SHOME:
                text_input.cursor_to_beginning(shift_pressed=True)
            elif event.type == Event.SEND:
                text_input.cursor_to_end(shift_pressed=True)

            self.draw()

        self.component_deinit()
        text_input.close()

        if event.type == Event.ESC:
            return Window.CANCEL
        return text_input.text

    def create_filtered_list(self, prompt, input_data=None, callback=None,
                             list_fill=None, filter_function=None, create_fn=None):
        """
        If input_data (list) is supplied, the list will be drawn from the string representations
        of that data. If list_fill (function) is supplied, then list_fill will be called to generate
        a list to be drawn.

        create_fn: A function to run when the list is created, with the filtered list as an argument
        """
        filtered_list = components.FilteredList(1, 0, self.rows - 1, self.cols,
                                             input_data, list_fill, prompt, filter_function)
        self.component_init(filtered_list)

        if create_fn:
            create_fn(filtered_list)

        while True:
            event = self.consume_event()

            if event.type == Event.DOWN:
                filtered_list.down()
            elif event.type == Event.UP:
                filtered_list.up()
            elif event.type == Event.HOME:
                filtered_list.to_top()
            elif event.type == Event.END:
                filtered_list.to_bottom()
            elif event.type == Event.LEFT and self.left_right_menu_nav:
                break
            elif event.type == Event.BACKSPACE:
                filtered_list.delchar()
            elif event.type == Event.ESC and self.use_esc_back:
                break
            elif event.type == Event.CHAR_INPUT:
                filtered_list.addchar(event.value)
            elif ((event.type == Event.ENTER) or
                  (event.type == Event.RIGHT and self.left_right_menu_nav)):
                if callback and filtered_list.selected() != UI_GO_BACK:
                    filtered_list.dirty = True
                    callback(WinContext(self, event, filtered_list, filtered_list.selected()))

                    if self.clear_filter:
                        filtered_list.clear_filter()
                    filtered_list.refresh()
                else:
                    break

            self.draw()

        filtered_list.clear()
        self.component_deinit()

        if event.type == Event.LEFT and self.left_right_menu_nav:
            return UI_GO_BACK

        return filtered_list.selected()

    def new_logger(self):
        logger = components.Logger(1, 0, self.rows - 1, self.cols)
        self.component_init(logger)

        return logger

    def remove_logger(self):
        self.component_deinit()
