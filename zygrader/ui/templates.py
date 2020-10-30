"""UI Templates: For reusable ui pieces built from components."""

from zygrader import ui
from zygrader.zybooks import Zybooks


class ZybookSectionSelector:
    def __init__(self, allow_optional_and_hidden=False):
        self.window = ui.get_window()
        self.zy_api = Zybooks()
        self.allow_optional_and_hidden = allow_optional_and_hidden

    def is_allowed(self, section):
        return self.allow_optional_and_hidden or (not (section["hidden"]
                                                       or section["optional"]))

    class _SectionToggle(ui.layers.Toggle):
        def __init__(self, index, data):
            super().__init__()
            self.__index = index
            self.__data = data
            self.get()

        def get(self):
            self._toggled = self.__data[self.__index]

        def toggle(self):
            self.__data[self.__index] = not self.__data[self.__index]
            self.get()

    def select_zybook_sections(self, return_just_numbers=False, title_extra=""):
        self.zybooks_toc = self.zy_api.get_table_of_contents()
        if not self.zybooks_toc:
            return None
        self.zybooks_sections = {(chapter["number"], section["number"]): section
                                 for chapter in self.zybooks_toc
                                 for section in chapter["sections"]}

        selected_sections = {(chapter["number"], section["number"]): False
                             for chapter in self.zybooks_toc
                             for section in chapter["sections"]}

        title = ("Select zyBooks Sections"
                 if not title_extra else f"{title_extra} - Select Sections")
        chapter_pad_width = len(str(len(self.zybooks_toc)))
        section_pad_width = max([
            len(str(len(chapter["sections"]))) for chapter in self.zybooks_toc
        ])
        popup = ui.layers.ListLayer(title, popup=True)
        popup.set_exit_text("Done")
        for i, chapter in enumerate(self.zybooks_toc, 1):
            row = popup.add_row_parent(
                f"{str(chapter['number']):>{chapter_pad_width}} - {chapter['title']}"
            )
            for j, section in enumerate(chapter["sections"], 1):
                section_string = (f"{chapter['number']}"
                                  f".{section['number']:<{section_pad_width}}"
                                  f" - {section['title']}")
                row.add_row_toggle(
                    section_string,
                    ZybookSectionSelector._SectionToggle((i, j),
                                                         selected_sections))
        self.window.run_layer(popup)

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

    path_input = ui.layers.PathInputLayer("Filepath Entry")
    path_input.set_prompt(
        [f"Enter the path and filename for {purpose} [~ is supported]"])
    path_input.set_text(text)
    window.run_layer(path_input)
    if path_input.was_canceled():
        return None

    return path_input.get_path()
