"""Input: For the user input thread and input events"""

import curses
import queue
import threading

# Negative 1 because "Back" is 0th in the index of lists
# And lists return their (index - 1) to handle that offset
GO_BACK = -1

UI_LEFT = 0
UI_RIGHT = 1
UI_CENTERED = 2

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

    def __init__(self, event_type, value, modifier=None):
        self.type = event_type
        self.value = value
        self.modifier = modifier

class Input:
    def __init__(self):
        self.event_queue = queue.Queue()

        # Vim mode settings
        self.vim_mode = False
        self.input_mode = False
        self.mark_mode = False

        # An event to toggle input thread
        self.take_input = threading.Event()
        self.take_input.set()

        # Create a thread to handle input separately
        # The main thread handles drawing
        self.input_thread = threading.Thread(target=self.input_thread_fn,
                                             name="Input", daemon=True)

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

        # TODO: Handle header update event
        # self.window.draw_header()
        # curses.doupdate()
        return Event.HEADER_UPDATE

    def disable_modes(self):
        """Disable non-normal modes"""
        self.insert_mode = False
        self.mark_mode = False

    def get_input(self, input_win) -> Event:
        """Get input and handle resize events"""
        event = Event.NONE
        event_value = Event.NONE
        event_mod = None

        input_code = input_win.getch()
        if input_code == -1:
            return Event(event, event_value)

        # Cases for each type of input
        if input_code == curses.KEY_RESIZE:
            #TODO: Send resize event
            # self.__resize_terminal()
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

        # TODO: Move back to window
        # self.header_offset += 1
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
                event = self.set_mode(MODE_NORMAL)
            elif self.mark_mode:
                event = self.set_mode(MODE_NORMAL)
            else:
                event = Event.ESC
        elif not self.mark_mode and not self.insert_mode and chr(input_code) == "i":
            event = self.set_mode(MODE_INSERT)
        elif not self.insert_mode and not self.mark_mode and chr(input_code) == "v":
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

    def input_thread_fn(self):
        # Create window for input
        input_win = curses.newwin(0, 0, 1, 1)
        input_win.keypad(True)
        # Makes getch blocking to reduce CPU usage
        input_win.nodelay(False)

        while True:
            self.take_input.wait()
            event = self.get_input(input_win)
            if not self.take_input.is_set():
                continue
            if event.type != Event.NONE:
                self.event_queue.put_nowait(event)
