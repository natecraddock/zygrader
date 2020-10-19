"""Layers: The components and handlers that make up the user interface."""

import queue
import threading
from typing import List

from .events import Event, EventManager
from . import window, components


class WorkerThread:
    """Execute a function in a separate thread and send data back to the owner ComponentLayer.

    The data queue is for sending data from the worker thread function to the component.
    The worker_fn should accept a single argument which is the queue.
    """
    def __init__(self, thread_fn, name="Worker Thread"):
        self.data_queue = queue.Queue()
        self.thread_fn = thread_fn
        self.__result = None

        self.__thread = threading.Thread(target=self.thread_wrap,
                                         name=name,
                                         daemon=True)

    def thread_wrap(self):
        self.__result = self.thread_fn(self.data_queue)

    def start(self):
        self.__thread.start()

    def is_finished(self):
        return not self.__thread.is_alive()

    def get_result(self):
        if not self.is_finished():
            raise AssertionError("The thread isn't finished yet!")
        return self.__result


class ComponentLayer:
    def __init__(self):
        self.title: str = ""
        self.component = None

        self.blocking = False
        self.has_fn = False
        self.returns_result = False
        self._canceled = False

        # Flags to control rebuilding and redrawing in the event loop.
        # Always build on first creation.
        self.rebuild = True
        self.redraw = False

    def build(self):
        """An optional function to finalize construction of a Layer upon registration."""
        self.rebuild = False
        self.redraw = True

    def draw(self):
        self.redraw = False
        self.component.draw()

    def event_handler(self, event: Event, event_manager: EventManager):
        pass

    def update(self, event_manager: EventManager):
        pass

    def was_canceled(self) -> bool:
        return self._canceled


class Popup(ComponentLayer):
    """A popup that shows a message until the user presses Enter."""
    def __init__(self, title):
        super().__init__()

        win = window.Window.get_window()
        self.component = components.Popup(win.rows, win.cols, title, [],
                                          components.Popup.ALIGN_LEFT)

    def event_handler(self, event: Event, event_manager: EventManager):
        if event.type == Event.ENTER:
            event_manager.push_layer_close_event()

    def set_message(self, message):
        self.component.set_message(message)


class BoolPopup(ComponentLayer):
    """A popup that asks for a Yes/No response."""
    __OPTIONS = ["Yes", "No"]

    def __init__(self, title):
        super().__init__()

        win = window.Window.get_window()
        self.component = components.OptionsPopup(win.rows, win.cols, title, [],
                                                 BoolPopup.__OPTIONS, False,
                                                 components.Popup.ALIGN_LEFT)

    def event_handler(self, event: Event, event_manager: EventManager):
        if event.type in {Event.LEFT, Event.UP, Event.BTAB}:
            self.component.previous()
        elif event.type in {Event.RIGHT, Event.DOWN, Event.TAB}:
            self.component.next()
        elif event.type == Event.ENTER:
            event_manager.push_layer_close_event()

    def get_result(self) -> bool:
        return self.component.selected() == BoolPopup.__OPTIONS[0]

    def set_message(self, message):
        self.component.set_message(message)


class WaitPopup(ComponentLayer):
    """A popup that stays visibile until a process completes."""
    def __init__(self, title):
        super().__init__()
        self.__result = None

        win = window.Window.get_window()
        # TODO: Cleanup constructor
        self.component = components.OptionsPopup(win.rows, win.cols, title,
                                                 ["hey"], ["Cancel"], False,
                                                 components.Popup.ALIGN_LEFT)
        self.wait_fn = None
        self.worker_thread = None

    def event_handler(self, event: Event, event_manager: EventManager):
        if event.type in {Event.ENTER, Event.ESC}:
            # Cancel was selected
            event_manager.push_layer_close_event()
            self._canceled = True

    def set_message(self, message):
        self.component.set_message(message)

    def set_wait_fn(self, wait_fn):
        self.has_fn = True
        self.wait_fn = wait_fn
        self.worker_thread = WorkerThread(wait_fn, "Wait Popup")
        self.worker_thread.start()

    def update(self, event_manager: EventManager):
        if self.worker_thread.is_finished():
            self.__result = self.worker_thread.get_result()
            event_manager.push_layer_close_event()

    def get_result(self) -> any:
        return self.__result


class TextInputLayer(ComponentLayer):
    """A popup that prompts the user for a string."""
    def __init__(self, title, mask=components.TextInput.TEXT_NORMAL):
        super().__init__()

        win = window.Window.get_window()
        self.component = components.TextInput(win.rows, win.cols, title, "", "",
                                              mask)
        if win.event_manager.vim_mode:
            win.event_manager.insert_mode = True

    def event_handler(self, event: Event, event_manager: EventManager):
        if event.type == Event.ENTER:
            event_manager.push_layer_close_event()
        elif event.type == Event.BACKSPACE:
            self.component.delchar()
        elif event.type == Event.DELETE:
            self.component.delcharforward()
        elif event.type == Event.CHAR_INPUT:
            self.component.addchar(event.value)
        elif event.type == Event.LEFT:
            self.component.left()
        elif event.type == Event.RIGHT:
            self.component.right()
        elif event.type == Event.SLEFT:
            self.component.left(shift_pressed=True)
        elif event.type == Event.SRIGHT:
            self.component.right(shift_pressed=True)
        elif event.type == Event.ESC:  # Always allow exiting from text input with ESC
            event_manager.push_layer_close_event()
            self._canceled = True
        elif event.type == Event.HOME:
            self.component.cursor_to_beginning()
        elif event.type == Event.END:
            self.component.cursor_to_end()
        elif event.type == Event.SHOME:
            self.component.cursor_to_beginning(shift_pressed=True)
        elif event.type == Event.SEND:
            self.component.cursor_to_end(shift_pressed=True)

    def set_prompt(self, prompt: str):
        self.component.set_message([prompt])

    def set_text(self, text: str):
        self.component.text = text
        self.component.cursor_index = len(text)

    def get_text(self):
        return self.component.text


class Radio:
    def __init__(self, name, get_fn, set_fn):
        self.__values = []
        self.__name = name
        self.__get_fn = get_fn
        self.__set_fn = set_fn

    def add_value(self, value):
        self.__values.append(value)

    def is_toggled(self, value):
        return self.__get_fn(self.__name) == value

    def set(self, value):
        self.__set_fn(self.__name, value)


class Toggle:
    def __init__(self, name, get_fn=None, set_fn=None, extra_fn=None):
        self._toggled = False
        self._name = name
        self.__get_fn = get_fn
        self.__set_fn = set_fn
        self.__extra_fn = extra_fn

        if self.__get_fn:
            self.get()

    def get(self):
        self._toggled = self.__get_fn(self._name)

    def toggle(self):
        self.__set_fn(self._name, not self._toggled)
        self.get()

        if self.__extra_fn:
            self.__extra_fn()

    def is_toggled(self):
        return self._toggled


class Row:
    # Row types
    HOLDER = 0
    TEXT = 1
    PARENT = 2
    TOGGLE = 3
    RADIO = 4

    def __init__(self, text: str = "", _type=HOLDER):
        self.__type = _type
        self.__text = text

        self.__subrows: List[self.__class__] = []
        self.__callback_fn = None

        self.__expanded = False

        self.__toggle: Toggle = None
        self.__radio: Radio = None

    def __str__(self):
        """Render a textual representation of this row."""
        if self.__type == Row.TEXT:
            return self.__text
        if self.__type == Row.PARENT:
            return f" {'v' if self.__expanded else '>'} " + self.__text
        elif self.__type == Row.TOGGLE:
            return f"[{'x' if self.__toggle.is_toggled() else ' '}] " + self.__text
        elif self.__type == Row.RADIO:
            return f"({'x' if self.__radio.is_toggled(self.__text) else ' '}) " + self.__text

    def build_string_lines(self, lines, start, depth=0):
        OFFSET = " " * (4 * depth)
        for row in start.get_subrows():
            lines.append(OFFSET + str(row))
            if row.get_type() == Row.PARENT and row.is_expanded():
                self.build_string_lines(lines, row, depth + 1)

    def __add_row(self, text: str, _type=TEXT):
        row = Row(text, _type)
        self.__subrows.append(row)
        return row

    def add_row_text(self, text: str, callback_fn=None):
        row = self.__add_row(text)
        row.set_callback_fn(callback_fn)

    def add_row_parent(self, text: str):
        return self.__add_row(text, Row.PARENT)

    def add_row_toggle(self, text: str, toggle: Toggle):
        row = self.__add_row(text, Row.TOGGLE)
        row.set_toggle_ob(toggle)

    def add_row_radio(self, text: str, radio: Radio):
        row = self.__add_row(text, Row.RADIO)
        row.set_radio_ob(radio)

    def get_type(self):
        return self.__type

    def get_subrows(self):
        return self.__subrows

    def is_expanded(self):
        return self.__expanded

    def set_callback_fn(self, callback_fn):
        self.__callback_fn = callback_fn

    def set_toggle_ob(self, toggle: Toggle):
        self.__toggle = toggle

    def set_radio_ob(self, radio: Radio):
        self.__radio = radio

    def do_action(self):
        if self.__type == Row.TEXT and self.__callback_fn:
            self.__callback_fn()
        if self.__type == Row.PARENT:
            if self.__subrows:
                self.__expanded = not self.__expanded
        elif self.__type == Row.TOGGLE:
            self.__toggle.toggle()
        elif self.__type == Row.RADIO:
            self.__radio.set(self.__text)

    def __row_iter(self, rows):
        for row in rows:
            yield row
            if row.is_expanded():
                yield from self.__row_iter(row.get_subrows())

    def __row_from_index(self, index):
        # This will become more complex as nesting is introduced
        for i, row in enumerate(self.__row_iter(self.__subrows)):
            if i == index:
                return row

    def select_row(self, index):
        row = self.__row_from_index(index)
        row.do_action()


class ListLayer(ComponentLayer, Row):
    """A reusable list that supports searching the options."""
    def __init__(self):
        ComponentLayer.__init__(self)
        Row.__init__(self)
        self.blocking = True

        win = window.Window.get_window()
        self.component = components.FilteredList(1, 0, win.rows - 1, win.cols)

    def build(self):
        super().build()

        text_rows = []
        self.build_string_lines(text_rows, self)
        self.component.set_lines(text_rows)

    # TODO: move somewhere else?
    def __string_search_fn(text: str, search_str: str):
        return text.lower().find(search_str.lower()) != -1

    def set_searchable(self, prompt: str, search_fn=__string_search_fn):
        self.component.set_searchable(prompt, search_fn)

    def event_handler(self, event: Event, event_manager: EventManager):
        if event.type == Event.DOWN:
            self.component.down()
        elif event.type == Event.UP:
            self.component.up()
        elif event.type == Event.HOME:
            self.component.to_top()
        elif event.type == Event.END:
            self.component.to_bottom()
        elif event.type == Event.LEFT and event_manager.left_right_menu_nav:
            event_manager.push_layer_close_event()
        elif event.type == Event.BACKSPACE:
            self.component.delchar()
            self.rebuild = True
        elif event.type == Event.ESC and event_manager.use_esc_back:
            # TODO: Handle this event by the window manager?
            event_manager.push_layer_close_event()
        elif event.type == Event.CHAR_INPUT:
            self.component.addchar(event.value)
            self.rebuild = True
        elif (
            (event.type == Event.ENTER) or
            (event.type == Event.RIGHT and event_manager.left_right_menu_nav)):
            if self.component.is_close_selected():
                event_manager.push_layer_close_event()
            else:
                self.select_row(self.component.get_selected_index())

            # if callback and self.component.selected() != GO_BACK:
            #     self.component.dirty = True
            #     callback(
            #         WinContext(self, event, self.component,
            #                    self.component.selected()))
            #     if self.clear_filter:
            #         self.component.clear_filter()
            #     self.component.refresh()
            # else:
            #     break

        self.redraw = True


class ListPopup(ComponentLayer, Row):
    def __init__(self, title):
        ComponentLayer.__init__(self)
        Row.__init__(self)

        win = window.Window.get_window()
        self.component = components.ListPopup(win.rows, win.cols, title,
                                              components.Popup.ALIGN_CENTER)

    def build(self):
        super().build()
        text_rows = []
        self.build_string_lines(text_rows, self)
        self.component.set_lines(text_rows)

    def event_handler(self, event: Event, event_manager: EventManager):
        if event.type == Event.DOWN:
            self.component.down()
        elif event.type == Event.UP:
            self.component.up()
        elif event.type == Event.HOME:
            self.component.to_top()
        elif event.type == Event.END:
            self.component.to_bottom()
        elif event.type == Event.LEFT and event_manager.left_right_menu_nav:
            event_manager.push_layer_close_event()
        elif event.type == Event.ESC and event_manager.use_esc_back:
            # TODO: Use the wm for this?
            event_manager.push_layer_close_event()
            # retval = GO_BACK
        elif (event.type
              == Event.ENTER) or (event.type == Event.RIGHT
                                  and event_manager.left_right_menu_nav):
            if self.component.is_close_selected():
                event_manager.push_layer_close_event()
            else:
                self.select_row(self.component.get_selected_index())
            self.rebuild = True
            # if self.component.selected() is GO_BACK:
            #     break
            # elif callback:
            #     callback(
            #         WinContext(self, event, self.component,
            #                    self.component.selected()))
            # else:
            #     break

        self.redraw = True