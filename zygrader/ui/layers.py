"""Layers: The components and handlers that make up the user interface."""

import queue
import threading
import typing
from typing import Callable

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

    def draw(self):
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

    def get_text(self):
        return self.component.text


class ListLayer(ComponentLayer):
    """A reusable list that supports searching the options."""
    def __init__(self):
        super().__init__()
        self.entries = {}

        win = window.Window.get_window()
        self.component = components.NewFilteredList(1, 0, win.rows - 1,
                                                    win.cols)

    def __update_lines(self):
        """Update the lines in the FilteredList"""
        self.component.set_lines(list(self.entries.keys()))

    def __string_search_fn(text: str, search_str: str):
        return text.lower().find(search_str.lower()) != -1

    def set_searchable(self, prompt: str, search_fn=__string_search_fn):
        self.component.set_searchable(prompt, search_fn)

    def add_row(self, name: str, fn: typing.Callable):
        self.entries[name] = fn
        self.__update_lines()

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
        elif event.type == Event.ESC and event_manager.use_esc_back:
            # TODO: Handle this event by the window manager?
            event_manager.push_layer_close_event()
        elif event.type == Event.CHAR_INPUT:
            self.component.addchar(event.value)
        elif (
            (event.type == Event.ENTER) or
            (event.type == Event.RIGHT and event_manager.left_right_menu_nav)):
            key = list(self.entries.keys())[self.component.selected()]
            self.entries[key]()

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


class ListPopup(ComponentLayer):
    def __init__(self, title, input_data, list_fill):
        super().__init__()

        win = window.Window.get_window()
        self.component = components.ListPopup(win.rows, win.cols, title, None,
                                              list_fill)

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
            pass
            # if self.component.selected() is GO_BACK:
            #     break
            # elif callback:
            #     callback(
            #         WinContext(self, event, self.component,
            #                    self.component.selected()))
            # else:
            #     break
