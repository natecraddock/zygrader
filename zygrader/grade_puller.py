import csv

from .ui.window import Window
from .ui import components, UI_GO_BACK
from .config import g_data
from .zybooks import Zybooks

class GradePuller:
    NUM_CANVAS_ID_COLUMNS = 5
    def __init__(self):
        self.window = Window.get_window()

    def pull(self):
        if not self.read_canvas_csv():
            return
        if not self.select_canvas_assignment():
            return
        if not self.fetch_zybooks_toc():
            return
        self.window.create_popup("Test", [f"The assignment is {self.canvas_assignment}"])
        self.window.create_list_popup("The students", input_data=self.canvas_students)
        self.window.create_popup("The points", [str(self.canvas_points_out_of)])
        self.select_class_sections()
        self.window.create_list_popup("The class sections", input_data=[el for el in self.selected_class_sections])

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
        self.window.create_list_popup("Select Class Sections", callback=section_callback, list_fill=draw_sections)
        self.selected_class_sections = selected_sections

    def fetch_zybooks_toc(self):
        zy_api = Zybooks()
        toc = zy_api.get_table_of_contents()
        self.window.create_list_popup("The TOC", [toc])

def start():
    puller = GradePuller()
    puller.pull()