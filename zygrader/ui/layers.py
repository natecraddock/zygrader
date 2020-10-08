"""Layers: The components and handlers that make up the user interface."""

import typing

from .events import Event, EventManager
from . import window, components


class ComponentLayer:
    def __init__(self):
        self.title: str = ""
        self.blocking = False
        self.component = None

    def draw(self):
        pass

    def event_handler(self, event: Event, event_manager: EventManager):
        pass


class MenuLayer(ComponentLayer):
    """A reusable menu that supports searching the options."""
    def __init__(self):
        super().__init__()
        self.entries = {}

        win = window.Window.get_window()
        self.filtered_list = components.FilteredList(1, 0, win.rows - 1,
                                                     win.cols, [], None, "hey",
                                                     None)

    def __update_lines(self):
        """Update the lines in the FilteredList"""
        lines = [
            components.FilteredList.ListLine(i, option)
            for i, option in enumerate(self.entries)
        ]
        self.filtered_list.create_lines(self.entries.keys())

    def register_entry(self, name: str, fn: typing.Callable):
        self.entries[name] = fn
        self.__update_lines()

    def draw(self):
        self.filtered_list.draw()

    def event_handler(self, event: Event, event_manager: EventManager):
        if event.type == Event.DOWN:
            self.filtered_list.down()
        elif event.type == Event.UP:
            self.filtered_list.up()
        elif event.type == Event.HOME:
            self.filtered_list.to_top()
        elif event.type == Event.END:
            self.filtered_list.to_bottom()
        elif event.type == Event.LEFT and event_manager.left_right_menu_nav:
            # TODO: Handle this event
            pass
        elif event.type == Event.BACKSPACE:
            self.filtered_list.delchar()
        elif event.type == Event.ESC and event_manager.use_esc_back:
            # TODO: Handle this event
            pass
        elif event.type == Event.CHAR_INPUT:
            self.filtered_list.addchar(event.value)
        elif (
            (event.type == Event.ENTER) or
            (event.type == Event.RIGHT and event_manager.left_right_menu_nav)):
            pass
            # TODO: Handle this event
            # if callback and self.filtered_list.selected() != GO_BACK:
            #     self.filtered_list.dirty = True
            #     callback(WinContext(self, event, self.filtered_list, self.filtered_list.selected()))
            #     if self.clear_filter:
            #         self.filtered_list.clear_filter()
            #     self.filtered_list.refresh()
            # else:
            #     break
