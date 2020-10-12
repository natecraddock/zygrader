"""Layers: The components and handlers that make up the user interface."""

import typing

from .events import Event, EventManager
from . import window, components


class FunctionLayer:
    def __init__(self, fn: typing.Coroutine, *args, **kwargs):
        self.fn = fn(*args, **kwargs)


class ComponentLayer:
    def __init__(self):
        self.title: str = ""
        self.component = None

        self.blocking = False
        self.has_fn = False
        self.returns_result = False

    def draw(self):
        self.component.draw()

    def event_handler(self, event: Event, event_manager: EventManager):
        pass


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


class WaitPopup(ComponentLayer):
    """A popup that stays visibile until a process completes."""
    def __init__(self, title):
        super().__init__()

        win = window.Window.get_window()
        self.component = components.OptionsPopup(win.rows, win.cols, title,
                                                 ["hey"], ["Cancel"], False,
                                                 components.Popup.ALIGN_LEFT)
        self.wait_fn = None

    def event_handler(self, event: Event, event_manager: EventManager):
        if event.type == Event.ENTER:
            # Cancel was selected
            event_manager.push_layer_close_event()

    def set_message(self, message):
        self.component.set_message(message)

    def set_wait_fn(self, wait_fn):
        self.has_fn = True
        self.wait_fn = wait_fn

    def update(self):
        return self.wait_fn()


class TextInputLayer(ComponentLayer):
    """A popup that prompts the user for a string."""
    def __init__(self, title, mask=components.TextInput.TEXT_NORMAL):
        super().__init__()

        self.text = ""

        win = window.Window.get_window()
        self.component = components.TextInput(win.rows, win.cols, title, "", "",
                                              mask)
        if win.event_manager.vim_mode:
            win.event_manager.insert_mode = True

    def event_handler(self, event: Event, event_manager: EventManager):
        if event.type == Event.ENTER:
            self.text = self.component.text
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


class MenuLayer(ComponentLayer):
    """A reusable menu that supports searching the options."""
    def __init__(self):
        super().__init__()
        self.entries = {}

        win = window.Window.get_window()
        self.component = components.FilteredList(1, 0, win.rows - 1, win.cols,
                                                 [], None, "hey", None)

    def __update_lines(self):
        """Update the lines in the FilteredList"""
        lines = [
            components.FilteredList.ListLine(i, option)
            for i, option in enumerate(self.entries)
        ]
        self.component.create_lines(self.entries.keys())

    def register_entry(self, name: str, fn: typing.Callable):
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
            # TODO: Handle this event
            pass
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
            pass
            # TODO: Handle this event
            # if callback and self.component.selected() != GO_BACK:
            #     self.component.dirty = True
            #     callback(WinContext(self, event, self.component, self.component.selected()))
            #     if self.clear_filter:
            #         self.component.clear_filter()
            #     self.component.refresh()
            # else:
            #     break
