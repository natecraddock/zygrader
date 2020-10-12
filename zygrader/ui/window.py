"""Window: The zygrader window manager and input handling"""
import curses
import typing

from zygrader.config import preferences
from . import components, events
from .events import Event, GO_BACK
from .utils import add_str, resize_window
from .layers import ComponentLayer, FunctionLayer, WaitPopup


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

    instance = None

    @staticmethod
    def get_window() -> "Window":
        if Window.instance:
            return Window.instance
        return None

    def update_preferences(self):
        self.dark_mode = preferences.get("dark_mode")
        self.christmas_mode = preferences.get("christmas_mode")
        self.clear_filter = preferences.get("clear_filter")

        self.update_window()

    def __init__(self, callback, window_name):
        Window.instance = self
        """Initialize screen and run callback function"""
        self.name = window_name

        self.layers: typing.List[typing.Union(ComponentLayer,
                                              FunctionLayer)] = []
        self.active_layer: typing.Union(ComponentLayer, FunctionLayer) = None

        curses.wrapper(self.__init_curses, callback)

        # Cleanup when finished accepting input
        self.stdscr.clear()
        self.stdscr.refresh()
        curses.endwin()

    def __init_curses(self, stdscr, callback):
        """Configure basic curses settings"""
        self.stdscr = stdscr

        # We use halfdelay with a delay of 1/10 of a second to prevent
        # using the 100% of a CPU core while checking for input.
        # Previously we used nodelay(True) which caused excessive CPU cycles.
        # We must use at least halfdelay to prevent input from blocking.
        curses.halfdelay(1)

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

        # All user input handling is done inside the EventManager class.
        self.event_manager = events.EventManager()

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

        if self.event_manager.insert_mode:
            display_text += " | INSERT"
        elif self.event_manager.mark_mode:
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

    def register_layer(self, layer: ComponentLayer):
        """Register a layer in the event loop."""
        self.layers.append(layer)
        self.active_layer = layer

    def run_layer(self, layer: ComponentLayer):
        self.register_layer(layer)

        while layer in self.layers:
            self.handle_events()
            self.draw()

        return layer.text

    def run_layer_for_result(self, layer: ComponentLayer):
        """Run a layer outside of the normal event loop and return a result.

        This is used for code that needs to get some user input and then continue
        a functions execution.
        """
        self.register_layer(layer)

        self.handle_events()
        self.draw()
        result = self.active_layer.update()
        self.layers.pop()
        if self.layers:
            self.active_layer = self.layers[-1]
        return result

    def register_layer_for_result(self, layer: ComponentLayer):
        layer.returns_result = True
        self.register_layer(layer)

    def loop(self):
        """Handle events in a loop until the program is exited"""
        while True:
            # When there are no more layers, exit the main loop
            if not self.layers:
                break

            self.handle_events()

            # Recalculate windows and redraw
            self.draw()

    def handle_events(self):
        # Get the event on the front of the queue
        event = self.event_manager.get_event()

        # Events are either handled directly by the window manager or
        # are passed to the active component layer.
        if event.type == Event.HEADER_UPDATE:
            # self.update_header()
            pass
        elif event.type == Event.LAYER_CLOSE:
            self.layers.pop()
            if self.layers:
                self.active_layer = self.layers[-1]
        else:
            self.active_layer.event_handler(event, self.event_manager)

    def draw(self):
        """Draw each component in the stack"""
        self.update_window()
        self.stdscr.erase()
        self.stdscr.noutrefresh()

        self.draw_header()

        for layer in self.layers:
            try:
                layer.draw()
            except:
                pass

        # All windows have been tagged for redraw with noutrefresh,
        # now do a single draw pass with doupdate.
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
        self.event_manager.disable_modes()

        self.components.append(component)
        if self.__header_title_load:
            self.header_titles.append(self.__header_title_load)
            self.__header_title_load = ""
        else:
            self.header_titles.append(self.header_titles[-1])

        self.draw()

    def component_deinit(self):
        self.event_manager.disable_modes()

        self.components.pop()
        self.header_titles.pop()
        self.draw()

    def create_popup(self, title, message, align=components.Popup.ALIGN_CENTER):
        """Create a popup with title and message that returns after enter"""
        popup = components.Popup(self.rows, self.cols, title, message, align)
        self.component_init(popup)

        while True:
            event = self.event_manager.get_event()

            if event.type == Event.ENTER:
                break

            self.draw()

        self.component_deinit()

    def create_waiting_popup(self,
                             title,
                             message,
                             align=components.Popup.ALIGN_CENTER):
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
                    self.window.event_manager.clear_event_queue()
                self.has_exited = True

        popup = components.OptionsPopup(self.rows, self.cols, title, message,
                                        [], False, align)
        self.component_init(popup)

        return WaitingPopupControl(self)

    def create_bool_popup(self,
                          title,
                          message,
                          align=components.Popup.ALIGN_CENTER):
        """Create a popup with title and message that returns true/false"""
        options = ["Yes", "No"]
        popup = components.OptionsPopup(self.rows, self.cols, title, message,
                                        options, False, align)
        self.component_init(popup)

        while True:
            event = self.event_manager.get_event()

            if event.type in {Event.LEFT, Event.UP, Event.BTAB}:
                popup.previous()
            elif event.type in {Event.RIGHT, Event.DOWN, Event.TAB}:
                popup.next()
            elif event.type == Event.ENTER:
                break

            self.draw()

        self.component_deinit()

        return popup.selected() == options[0]

    def create_options_popup(self,
                             title,
                             message,
                             options,
                             align=components.Popup.ALIGN_CENTER):
        """Create a popup with multiple options that can be selected with the keyboard.
        options is either a dictionary of string to callback function pairs or a list of strings
        """
        use_dict = bool(isinstance(options, dict))

        popup = components.OptionsPopup(self.rows, self.cols, title, message,
                                        options, use_dict, align)
        self.component_init(popup)

        while True:
            event = self.event_manager.get_event()

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
                    if not callback_fn:
                        break
                    ret = callback_fn(WinContext(self, event, popup, None))
                    if ret:
                        break
                else:
                    break

            self.draw()

        self.component_deinit()

        if not use_dict:
            return popup.selected()

    def create_datetime_spinner(self,
                                title,
                                time=None,
                                quickpicks=None,
                                optional=False,
                                include_date=True):
        """Create a popup with a datetime spinner to select a datetime.
        time is the initial time to present
        quickpicks is an optional list of (minute, second) pairs.
         If provided, spinning the minute field will spin through the quickpicks
        """

        popup = components.DatetimeSpinner(self.rows, self.cols, title, time,
                                           quickpicks, optional, include_date)

        self.component_init(popup)

        retval = None
        while True:
            event = self.event_manager.get_event()

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
                retval = GO_BACK
                break
            elif event.type == Event.ENTER and popup.is_confirmed():
                break

            self.draw()

        self.component_deinit()

        return retval if retval else popup.get_time()

    def create_list_popup(self,
                          title,
                          input_data=None,
                          callback=None,
                          list_fill=None):
        """Create a popup with a list of options that can be scrolled and selected

        If input_data (list) is supplied, the list will be drawn from the string representations
        of that data. If list_fill (function) is supplied, then list_fill will be called to generate
        a list to be drawn.
        """
        popup = components.ListPopup(self.rows, self.cols, title, input_data,
                                     list_fill)
        self.component_init(popup)

        retval = None
        while True:
            event = self.event_manager.get_event()

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
                retval = GO_BACK
                break
            elif (event.type == Event.ENTER) or (event.type == Event.RIGHT
                                                 and self.left_right_menu_nav):
                if popup.selected() is GO_BACK:
                    break
                elif callback:
                    callback(WinContext(self, event, popup, popup.selected()))
                else:
                    break

            self.draw()

        self.component_deinit()

        return retval if retval else popup.selected()

    def create_text_input(self,
                          title,
                          prompt,
                          text="",
                          mask=components.TextInput.TEXT_NORMAL):
        """Get text input from the user"""
        text_input = components.TextInput(self.rows, self.cols, title, prompt,
                                          text, mask)
        self.component_init(text_input)

        if self.event_manager.vim_mode:
            self.event_manager.insert_mode = True
            self.draw()

        while True:
            event = self.event_manager.get_event()

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
            elif event.type == Event.ESC:  # Always allow exiting from text input with ESC
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

    def create_filtered_list(
        self,
        prompt,
        input_data=None,
        callback=None,
        list_fill=None,
        filter_function=None,
        create_fn=None,
    ):
        """
        If input_data (list) is supplied, the list will be drawn from the string representations
        of that data. If list_fill (function) is supplied, then list_fill will be called to generate
        a list to be drawn.

        create_fn: A function to run when the list is created, with the filtered list as an argument
        """
        filtered_list = components.FilteredList(
            1,
            0,
            self.rows - 1,
            self.cols,
            input_data,
            list_fill,
            prompt,
            filter_function,
        )
        self.component_init(filtered_list)

        if create_fn:
            create_fn(filtered_list)

        while True:
            event = self.event_manager.get_event()

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
            elif (event.type == Event.ENTER) or (event.type == Event.RIGHT
                                                 and self.left_right_menu_nav):
                if callback and filtered_list.selected() != GO_BACK:
                    filtered_list.dirty = True
                    callback(
                        WinContext(self, event, filtered_list,
                                   filtered_list.selected()))

                    if self.clear_filter:
                        filtered_list.clear_filter()
                    filtered_list.refresh()
                else:
                    break

            self.draw()

        filtered_list.clear()
        self.component_deinit()

        if event.type == Event.LEFT and self.left_right_menu_nav:
            return GO_BACK

        return filtered_list.selected()

    def new_logger(self):
        logger = components.Logger(1, 0, self.rows - 1, self.cols)
        self.component_init(logger)

        return logger

    def remove_logger(self):
        self.component_deinit()
