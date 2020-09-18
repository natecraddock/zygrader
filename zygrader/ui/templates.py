"""UI Templates: For reusable ui pieces built from components."""

import os

from .window import Window
from zygrader.zybooks import Zybooks
from zygrader import ui

class ZybookSectionSelector:
    def __init__(self, allow_optional_and_hidden=False):
        self.window = ui.get_window()
        self.zy_api = Zybooks()
        self.allow_optional_and_hidden = allow_optional_and_hidden

    def is_allowed(self, section):
        return (self.allow_optional_and_hidden
                or (not(section['hidden'] or section['optional'])))

    def draw_zybook_sections(self, chapters_expanded, selected_sections):
        res = []
        items = []
        chapter_pad_width = len(str(len(self.zybooks_toc)))
        section_pad_width = max([len(str(len(chapter['sections'])))
                                    for chapter in self.zybooks_toc])
        for chapter in self.zybooks_toc:
            res.append(f"{str(chapter['number']):>{chapter_pad_width}}"
                       f" - {chapter['title']}")
            items.append(chapter['number'])
            if chapters_expanded[chapter['number']]:
                for section in chapter['sections']:
                    section_string = (
                        f"{chapter['number']}"
                        f".{section['number']:<{section_pad_width}}"
                        f" - {section['title']}")
                    is_selected = selected_sections[(chapter['number'],
                                                     section['number'])]
                    if self.is_allowed(section):
                        res.append(f"  [{'X' if is_selected else ' '}]"
                                   f" {section_string}")
                    else:
                        res.append(f"  -{'X' if is_selected else '-'}-"
                                   f" {section_string} (hidden/optional)")
                    items.append((chapter['number'], section['number']))
        self.drawn_zybook_items = items
        return res

    def select_zybook_sections_callback(self, chapters_expanded, selected_sections, selected_index):
        item = self.drawn_zybook_items[selected_index]
        if isinstance(item, tuple): #is a section
            section = self.zybooks_sections[item]
            if self.is_allowed(section):
                selected_sections[item] = not selected_sections[item]
        else: #is a chapter
            chapters_expanded[item] = not chapters_expanded[item]

    def select_zybook_sections(self, return_just_numbers=False, title_extra=""):
        self.zybooks_toc = self.zy_api.get_table_of_contents()
        if not self.zybooks_toc:
            return None
        self.zybooks_sections = {(chapter['number'], section['number']): section for chapter in self.zybooks_toc for section in chapter['sections']}

        chapters_expanded = {chapter['number']: False for chapter in self.zybooks_toc}
        selected_sections = {(chapter['number'], section['number']): False for chapter in self.zybooks_toc for section in chapter['sections']}
        draw_sections = lambda: self.draw_zybook_sections(chapters_expanded, selected_sections)
        draw_sections()
        section_callback = lambda context: self.select_zybook_sections_callback(chapters_expanded, selected_sections, context.data)

        title = "Select zyBook Sections (use Back to finish)" if not title_extra else f"{title_extra} - Select Sections"
        self.window.create_list_popup(title, callback=section_callback, list_fill=draw_sections)
        res = []
        for section_numbers, selected in selected_sections.items():
            if selected:
                if return_just_numbers:
                    res.append(section_numbers)
                else:
                    res.append(self.zybooks_sections[section_numbers])
        return res

def filename_input(purpose, text=""):
    """Get a valid filename from the user"""
    window = ui.get_window()
    full_prompt = f"Enter the path and filename for {purpose} [~ is supported]"

    while True:
        path = window.create_text_input("Filepath Entry",
                                        full_prompt,
                                        text=text)
        if path == Window.CANCEL:
            return None

        path = os.path.expanduser(path)
        if os.path.exists(os.path.dirname(path)):
            return path

        msg = [f"Path {os.path.dirname(path)} does not exist!"]
        window.create_popup("Invalid Path", msg)
