import csv
import datetime

from .ui.window import Window
from .ui import components, UI_GO_BACK
from .config import g_data
from .zybooks import Zybooks

class GradePuller:
    NUM_CANVAS_ID_COLUMNS = 5

    def __init__(self):
        self.window = Window.get_window()
        self.zy_api = Zybooks()

    def pull(self):
        if not self.try_pull():
            self.window.create_popup("Grade Puller", ["Grade Puller stopped"])

    def try_pull(self):
        if not self.read_canvas_csv():
            return False
        """
        if not self.select_canvas_assignment():
            return False
        if not self.fetch_zybooks_toc():
            return False
        if not self.select_zybook_sections():
            return False
        """
        if not self.select_class_sections():
            return False
        if not self.select_due_times():
            return False
        self.window.create_list_popup("The zysections", input_data=[str(nums) for nums in self.selected_zybook_sections])
        return True

    def read_canvas_csv(self):
        path = g_data.get_canvas_master()
        try:
            self.canvas_students = []
            with open(path, 'r', newline='') as canvas_master_file:
                canvas_reader = csv.DictReader(canvas_master_file)
                self.canvas_header = canvas_reader.fieldnames
                self.canvas_points_out_of = canvas_reader.__next__()
                for row in canvas_reader:
                    self.canvas_students.append(row)
        except FileNotFoundError:
            self.window.create_popup("Error in Reading Master CSV", [f"Could not find {path}", "Please download the gradebook from Canvas and put it in the place noted above"])
            return False
        except PermissionError:
            self.window.create_popup("Error in Reading Master CSV", [f"Could not open {path} for reading", "Please have the owner of the file grant read permissions"])
            return False
        return True

    def select_canvas_assignment(self):
        real_assignments = self.canvas_header[GradePuller.NUM_CANVAS_ID_COLUMNS:]
        index = self.window.create_filtered_list(real_assignments, "Assignment")
        if index is UI_GO_BACK:
            return False
        self.canvas_assignment = real_assignments[index]
        return True

    def select_class_sections(self):
        num_sections = len(self.canvas_students[-1]['Section'].split('and')) #The last student is always "Test Student", and is in every section
        selected_sections = set()
        draw_sections = lambda: [f"[{'X' if el in selected_sections else ' '}] {el}" for el in range(1,num_sections+1)]
        section_callback = lambda selected_index: selected_sections.remove(selected_index+1) if selected_index+1 in selected_sections else selected_sections.add(selected_index+1)
        self.window.create_list_popup("Select Class Sections (use Back to finish)", callback=section_callback, list_fill=draw_sections)
        if not selected_sections:
            return False
        self.selected_class_sections = [el for el in selected_sections]
        return True

    def fetch_zybooks_toc(self):
        toc = self.zy_api.get_table_of_contents()
        if not toc:
            return False
        self.zybooks_toc = toc
        self.zybooks_sections = {(chapter['number'], section['number']): section for chapter in toc for section in chapter['sections']}
        return True

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

    def select_zybook_sections(self):
        chapters_expanded = {chapter['number']: False for chapter in self.zybooks_toc}
        selected_sections = {(chapter['number'], section['number']): False for chapter in self.zybooks_toc for section in chapter['sections']}
        draw_sections = lambda: self.draw_zybook_sections(chapters_expanded, selected_sections)
        draw_sections()
        section_callback = lambda selected_index: self.select_zybook_sections_callback(chapters_expanded, selected_sections, selected_index)
        self.window.create_list_popup("Select zyBook Sections (use Back to finish)", callback=section_callback, list_fill=draw_sections)
        self.selected_zybook_sections = []
        for section_numbers, selected in selected_sections.items():
            if selected:
                self.selected_zybook_sections.append(self.zybooks_sections[section_numbers])
        if not self.select_zybook_sections:
            return False
        return True

    def select_due_times_callback(self, selected_index):
        section = self.selected_class_sections[selected_index]
        old_time_str = self.due_times[section].strftime("%m.%d.%Y:%H.%M.%S")
        new_time_str = self.window.create_text_input("Enter due date [MM.DD.YYYY:HH.MM.SS]", text=old_time_str)
        if new_time_str == Window.CANCEL:
            return
        
        new_time = datetime.datetime.strptime(new_time_str, "%m.%d.%Y:%H.%M.%S").astimezone(tz=None)
        self.due_times[section] = new_time

        if selected_index == 0: #For convenience, allow the day to carried across all sections so that only the time has to be changed for the rest
            do_set_all_sections = self.window.create_bool_popup("Set Due Time", ["Set all sections to this due time?"])
            if do_set_all_sections:
                for section in self.due_times:
                    self.due_times[section] = new_time

    def select_due_times(self):
        now = datetime.datetime.now()
        self.due_times = {section: now for section in self.selected_class_sections}
        draw = lambda: [f"Section {section}: {time.strftime('%m.%d.%Y:%H.%M.%S')}" for section, time in self.due_times.items()]
        callback = lambda index: self.select_due_times_callback(index)
        self.window.create_list_popup("Set Due Times (use Back to finish)", callback=callback, list_fill=draw)


def start():
    puller = GradePuller()
    puller.pull()