"""Window: The zygrader window manager and input handling"""
import curses
import typing

from zygrader.config import preferences

from . import events
from .events import Event
from .layers import ComponentLayer
from .utils import add_str, resize_window


class WinContext:
    """A wrapper for the current window context when components execute a callback"""
    def __init__(self, window, event: Event, component, custom_data):
        self.window = window
        self.event = event
        self.component = component
        self.data = custom_data


class Window:
    INSTANCE = None

    @staticmethod
    def get_window() -> "Window":
        if Window.INSTANCE:
            return Window.INSTANCE
        return None

    def update_preferences(self):
        self.dark_mode = preferences.get("dark_mode")
        self.christmas_mode = preferences.get("christmas_mode")
        self.clear_filter = preferences.get("clear_filter")

        self.update_window()

    def __init__(self, callback, window_name):
        """Initialize screen and run callback function"""
        Window.INSTANCE = self
        self.name = window_name

        self.layers: typing.List[ComponentLayer] = []
        self.active_layer: ComponentLayer = None

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
        self.__header_title = ""
        self.header_offset = 0

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

        for layer in self.layers:
            layer.resize_component(self.rows, self.cols)

    def get_header_colors(self):
        if self.dark_mode:
            return curses.color_pair(5), curses.color_pair(6)
        return curses.color_pair(3), curses.color_pair(4)

    def __get_email_text(self):
        email = preferences.get("email")
        if not email:
            email = "Logged Out"
        return email

    def draw_header(self):
        """Set the header text"""
        self.header.erase()
        resize_window(self.header, 1, self.cols)

        # Store the cursor location
        loc = curses.getsyx()

        display_text = f"{self.name} | {self.__header_title} | {self.__get_email_text()}"

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

    def __update_header_title(self):
        """Set the text to be drawn centered in the header"""
        if self.active_layer and self.active_layer.title:
            self.__header_title = self.active_layer.title
            return
        elif self.active_layer:
            # Find a lower layer with a title
            for layer in reversed(self.layers):
                if layer.title:
                    self.__header_title = layer.title
                    return

        # Use default text
        self.__header_title = "Main Menu"

    def register_layer(self, layer: ComponentLayer, header_title=""):
        """Register a layer in the event loop."""
        self.layers.append(layer)
        self.active_layer = layer
        layer.title = header_title

        self.__update_header_title()

        # Run any finalizing actions this layer needs
        layer.build()

    def unregister_layer(self):
        """Remove the top layer from the stack."""
        layer = self.layers.pop()
        self.active_layer = self.layers[-1] if self.layers else None

        layer.destroy()

        self.__update_header_title()

    def run_layer(self, layer: ComponentLayer, title=""):
        self.register_layer(layer, title)

        while layer in self.layers:
            self.build()
            layer.update(self.event_manager)
            self.handle_events()
            self.draw()

    def loop(self):
        """Handle events in a loop until the program is exited."""
        # When there are no more layers, exit the main loop
        while self.layers:
            self.build()
            self.handle_events()
            # Recalculate windows and redraw
            self.draw()

    def build(self):
        for layer in self.layers:
            if layer.rebuild:
                layer.build()

    def handle_events(self):
        # Get the event on the front of the queue
        event = self.event_manager.get_event()

        # Events are either handled directly by the window manager or
        # are passed to the active component layer.
        if event.type == Event.HEADER_UPDATE:
            # self.update_header()
            pass
        elif event.type == Event.LAYER_CLOSE:
            self.unregister_layer()
        elif event.type == Event.RESIZE:
            self.__resize_terminal()
        else:
            self.active_layer.event_handler(event, self.event_manager)

    def __tag_visible_layers(self):
        """If any layer needs drawing then tag all visible layers below it for redraw."""
        for layer in reversed(self.layers):
            layer.redraw = True
            if layer.blocking:
                break

    def draw(self):
        """Draw each component in the stack"""
        if not any(layer.redraw for layer in self.layers):
            return

        self.update_window()
        self.stdscr.erase()
        self.stdscr.noutrefresh()

        self.draw_header()

        self.__tag_visible_layers()
        for layer in self.layers:
            if layer.redraw:
                layer.draw()

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
