"""UI Templates: For reusable ui components"""

from .window import Window
from zygrader.zybooks import Zybooks

class ZybookSectionSelector:
    def __init__(self):
        self.window = Window.get_window()
        self.zy_api = Zybooks()

    def draw_zybook_sections(self, chapters_expanded, selected_sections):
        res = []
        items = []
        for chapter in self.zybooks_toc:
            res.append(f"{chapter['number']} - {chapter['title']}")
            items.append(chapter['number'])
            if chapters_expanded[chapter['number']]:
                for section in chapter['sections']:
                    section_string = f"{chapter['number']}.{section['number']} - {section['title']}"
                    is_selected = selected_sections[(chapter['number'], section['number'])]
                    if not section['hidden'] and not section['optional']:
                        res.append(f"  [{'X' if is_selected else ' '}] {section_string}")
                    else:
                        res.append(f"  -{'X' if is_selected else '-'}- {section_string} (hidden/optional)")
                    items.append((chapter['number'], section['number']))
        self.drawn_zybook_items = items
        return res

    def select_zybook_sections_callback(self, chapters_expanded, selected_sections, selected_index):
        item = self.drawn_zybook_items[selected_index]
        if isinstance(item, tuple): #is a section
            section = self.zybooks_sections[item]
            if not section['hidden'] and not section['optional']:
                selected_sections[item] = not selected_sections[item]
        else: #is a chapter
            chapters_expanded[item] = not chapters_expanded[item]

    def select_zybook_sections(self, return_just_numbers=False):
        self.zybooks_toc = self.zy_api.get_table_of_contents()
        if not self.zybooks_toc:
            return None
        self.zybooks_sections = {(chapter['number'], section['number']): section for chapter in self.zybooks_toc for section in chapter['sections']}

        chapters_expanded = {chapter['number']: False for chapter in self.zybooks_toc}
        selected_sections = {(chapter['number'], section['number']): False for chapter in self.zybooks_toc for section in chapter['sections']}
        draw_sections = lambda: self.draw_zybook_sections(chapters_expanded, selected_sections)
        draw_sections()
        section_callback = lambda context: self.select_zybook_sections_callback(chapters_expanded, selected_sections, context.data)
        self.window.create_list_popup("Select zyBook Sections (use Back to finish)", callback=section_callback, list_fill=draw_sections)
        res = []
        for section_numbers, selected in selected_sections.items():
            if selected:
                if return_just_numbers:
                    res.append(section_numbers)
                else:
                    res.append(self.zybooks_sections[section_numbers])
        return res