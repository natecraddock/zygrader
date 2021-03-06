"""Events: For managing user input and other events"""

import curses

from zygrader.config import preferences

# Negative 1 because "Back" is 0th in the index of lists
# And lists return their (index - 1) to handle that offset
GO_BACK = -1

MODE_NORMAL = 0
MODE_INSERT = 1
MODE_MARK = 2


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
    HEADER_UPDATE = 20

    LAYER_CLOSE = 21
    RESIZE = 22
    QUIT = 23

    def __init__(self, event_type, value):
        self.type = event_type
        self.value = value


class EventManager:
    def __init__(self):
        self.input_win = curses.newwin(0, 0, 1, 1)
        self.input_win.keypad(True)

        # Use a 5 millisecond timeout before getch() stops blocking.
        # Previously used halfdelay(), but the 100ms delay was sometimes
        # visible to the user. 5ms makes the ui more responsive while
        # still not using 100% of a CPU.
        self.input_win.timeout(5)

        # A simple list used as a queue of events.
        # Events are either from keyboard input, or from zygrader itself
        # (a component informing the window to update something, etc.)
        self.event_queue = []

        # Vim mode settings
        self.insert_mode = False
        self.mark_mode = False

        self.update_preferences()

    def update_preferences(self):
        """Update the input settings from user preferences"""
        self.vim_mode = preferences.get("vim_mode")
        self.left_right_menu_nav = preferences.get("left_right_arrow_nav")
        self.use_esc_back = preferences.get("use_esc_back")

    def __queue_push(self, event: Event):
        self.event_queue.append(event)

    def __queue_pop(self) -> Event:
        """Pop the first event in the queue. If no events are in the queue
        an empty event is returned.
        """
        if len(self.event_queue) > 0:
            return self.event_queue.pop(0)
        return Event(Event.NONE, Event.NONE)

    def clear_event_queue(self):
        """Clear all events from the queue"""
        self.event_queue = []

    def push_layer_close_event(self):
        event = Event(Event.LAYER_CLOSE, None)
        self.__queue_push(event)

    def push_zygrader_quit_event(self):
        """Quit zygrader by removing all layers from the stack."""
        event = Event(Event.QUIT, None)
        self.__queue_push(event)

    def set_mode(self, mode: int):
        """Set the vim edit mode"""
        if mode == MODE_NORMAL:
            self.insert_mode = False
            self.mark_mode = False
        elif mode == MODE_INSERT:
            self.insert_mode = True
            self.mark_mode = False
        elif mode == MODE_MARK:
            self.insert_mode = False
            self.mark_mode = True

        return Event.HEADER_UPDATE

    def disable_modes(self):
        """Disable non-normal modes"""
        self.insert_mode = False
        self.mark_mode = False

    def get_keyboard_input(self) -> Event:
        """Get input and handle resize events"""
        event = Event.NONE
        event_value = Event.NONE

        input_code = self.input_win.getch()
        if input_code == -1:
            return Event(event, event_value)

        # Cases for each type of input
        if input_code == curses.KEY_RESIZE:
            event = Event.RESIZE
            curses.flushinp()
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
            event, event_value = self.get_keyboard_input_vim(input_code)
        elif input_code == 27:  #curses does not have a pre-defined constant for ESC
            event = Event.ESC
        elif input_code == curses.KEY_BACKSPACE:
            event = Event.BACKSPACE
        elif input_code == curses.KEY_DC:
            event = Event.DELETE
        elif input_code:
            event = Event.CHAR_INPUT
            event_value = chr(input_code)

        return Event(event, event_value)

    def get_keyboard_input_vim(self, input_code):
        event = Event.NONE
        event_value = Event.NONE

        if input_code == curses.KEY_BACKSPACE and self.insert_mode:
            event = Event.BACKSPACE
        elif input_code == curses.KEY_DC and self.insert_mode:
            event = Event.DELETE
        elif input_code == 27:
            if self.insert_mode:
                event = self.set_mode(MODE_NORMAL)
            elif self.mark_mode:
                event = self.set_mode(MODE_NORMAL)
            else:
                event = Event.ESC
        elif not self.mark_mode and not self.insert_mode and chr(
                input_code) == "i":
            event = self.set_mode(MODE_INSERT)
        elif not self.insert_mode and not self.mark_mode and chr(
                input_code) == "v":
            event = self.set_mode(MODE_MARK)
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

    def get_event(self) -> Event:
        """Poll for user-given keyboard input, or input from other sources.
        
        This function takes up to 1/10 of a second to execute at which point
        `getch` will return -1 and no event will be added to the queue.
        """
        event = self.get_keyboard_input()
        if event.type != Event.NONE:
            self.__queue_push(event)

        return self.__queue_pop()
