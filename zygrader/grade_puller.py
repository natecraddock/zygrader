import csv
import datetime

from .ui.window import Window
from .ui import UI_GO_BACK
from .config import g_data
from .zybooks import Zybooks

class GradePuller:
    NUM_CANVAS_ID_COLUMNS = 5
    NUM_ZYBOOKS_ID_COLUMNS = 5

    def __init__(self):
        self.window = Window.get_window()
        self.zy_api = Zybooks()

    def pull(self):
        if not self.try_pull():
            self.window.create_popup("Grade Puller", ["Grade Puller stopped"])

    def try_pull(self):
        if not self.read_canvas_csv():
            return False
        if not self.select_canvas_assignment():
            return False
        if not self.fetch_zybooks_toc():
            return False
        if not self.select_zybook_sections():
            return False
        if not self.select_class_sections():
            return False
        if not self.select_due_times():
            return False
        if not self.fetch_completion_reports():
            return False
        self.tidy_canvas_students()
        self.create_canvas_to_zybook_mapping()
        self.report_unmatched_students()
        self.calculate_grades()
        self.write_upload_file()

        return True

    def read_canvas_csv(self):
        path = g_data.get_canvas_master()
        try:
            self.canvas_students = dict()
            with open(path, 'r', newline='') as canvas_master_file:
                canvas_reader = csv.DictReader(canvas_master_file)
                self.canvas_header = canvas_reader.fieldnames
                self.canvas_points_out_of = canvas_reader.__next__()
                for row in canvas_reader:
                    id_str = row['SIS User ID']
                    row['id_number'] = int(id_str) if id_str else -1
                    self.canvas_students[row['id_number']] = row
        except FileNotFoundError:
            self.window.create_popup("Error in Reading Master CSV", [f"Could not find {path}", "Please download the gradebook from Canvas and put it in the place noted above"])
            return False
        except PermissionError:
            self.window.create_popup("Error in Reading Master CSV", [f"Could not open {path} for reading", "Please have the owner of the file grant read permissions"])
            return False
        return True

    def select_canvas_assignment(self):
        real_assignments = self.canvas_header[GradePuller.NUM_CANVAS_ID_COLUMNS:]
        index = self.window.create_filtered_list("Assignment", input_data=real_assignments)
        if index is UI_GO_BACK:
            return False
        self.selected_canvas_assignment = real_assignments[index]
        return True

    def select_class_sections(self):
        num_sections = len(self.canvas_students[-1]['Section'].split('and')) #Test Student has id -1, and is in every section
        selected_sections = set()
        draw_sections = lambda: [f"[{'X' if el in selected_sections else ' '}] {el}" for el in range(1,num_sections+1)]
        section_callback = lambda selected_index: selected_sections.remove(selected_index+1) if selected_index+1 in selected_sections else selected_sections.add(selected_index+1)
        self.window.create_list_popup("Select Class Sections (use Back to finish)", callback=section_callback, list_fill=draw_sections)
        if not selected_sections:
            return False
        self.selected_class_sections = [el for el in selected_sections]
        return True

    def fetch_zybooks_toc(self):
        wait_controller = self.window.create_waiting_popup("TOC", ["Fetching TOC from zyBooks"])
        toc = self.zy_api.get_table_of_contents()
        wait_controller.close()
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
        if not self.selected_zybook_sections:
            return False
        return True

    def select_due_times_callback(self, selected_index):
        section = self.selected_class_sections[selected_index]
        old_time_str = self.due_times[section].strftime("%m.%d.%Y:%H.%M.%S")
        new_time_str = self.window.create_text_input("Enter due date [MM.DD.YYYY:HH.MM.SS]", text=old_time_str)
        if new_time_str == Window.CANCEL:
            return

        try:
            new_time = datetime.datetime.strptime(new_time_str, "%m.%d.%Y:%H.%M.%S").astimezone(tz=None)
        except ValueError:
            self.window.create_popup("Bad Time", [f"{new_time_str} is not a properly formatted and valid time"])
            return
        self.due_times[section] = new_time

        if selected_index == 0 and len(self.selected_class_sections) > 1: #For convenience, allow the day to carried across all sections so that only the time has to be changed for the rest
            do_set_all_sections = self.window.create_bool_popup("Set Due Time", ["Set all sections to this due time?"])
            if do_set_all_sections:
                for section in self.due_times:
                    self.due_times[section] = new_time

    def select_due_times(self):
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=1)
        midnight = datetime.time(hour=23, minute=59, second=59)
        last_night = datetime.datetime.combine(yesterday, midnight)
        self.due_times = {section: last_night for section in self.selected_class_sections}
        draw = lambda: [f"Section {section}: {time.strftime('%m.%d.%Y:%H.%M.%S')}" for section, time in self.due_times.items()]
        self.window.create_list_popup("Set Due Times (use Back to finish)", callback=self.select_due_times_callback, list_fill=draw)
        return True

    def fetch_completion_reports(self):
        wait_msg = ["Fetching completion reports from zyBooks", f"Completed 0/{len(self.selected_class_sections)}"]
        wait_controller = self.window.create_waiting_popup("Fetch Reports", wait_msg)
        num_completed = 0

        self.zybooks_students = dict()
        for class_section in self.selected_class_sections:
            csv_string = self.zy_api.get_completion_report(self.due_times[class_section], self.selected_zybook_sections)
            if not csv_string:
                return False

            csv_rows = csv_string.split("\r\n")

            csv_reader = csv.DictReader(csv_rows)
            self.zybooks_header = csv_reader.fieldnames

            total_field_name = ""
            for field_name in self.zybooks_header:
                if "Total" in field_name:
                    total_field_name = field_name
                    break

            for row in csv_reader:
                if int(row['Class section']) == class_section:
                    row['id_number'] = int(''.join([c for c in row['Student ID'] if c.isdigit()]))
                    row['grade'] = float(row[total_field_name])
                    self.zybooks_students[row['id_number']] = row

            num_completed += 1
            wait_msg[-1] = f"Completed {num_completed}/{len(self.selected_class_sections)}"
            wait_controller.update()

        wait_controller.close()
        return True

    def tidy_canvas_students(self):
        filtered = dict()
        for student_id, student in self.canvas_students.items():
            section_str = student['Section']
            section_num = int(section_str.split('-')[1].split(':')[0])
            if section_num in self.selected_class_sections and student_id != -1:
                grade_str = student[self.selected_canvas_assignment]
                student['grade'] = float(grade_str) if grade_str and grade_str != "N/A" else None
                filtered[student_id] = student
        self.canvas_students = filtered

    def create_canvas_to_zybook_mapping(self):
        """Creates the mapped students dictionary and populates unmatched students lists

        All zybook students begin unmatched and are removed when paired with a canvas student.
        The canvas unmatched list populates as canvas students don't find pairs
        """
        self.mapped_students = dict()
        self.unmatched_canvas_students = dict()
        self.unmatched_zybook_students = self.zybooks_students.copy()

        for student_id, canvas_student in self.canvas_students.items():
            zystudent = None
            if student_id in self.zybooks_students:
                zystudent = self.zybooks_students[student_id]
            self.mapped_students[student_id] = (canvas_student, zystudent)
            if zystudent is None:
                self.unmatched_canvas_students[student_id] = canvas_student
            else:
                del self.unmatched_zybook_students[student_id]

    def report_unmatched_canvas_students(self):
        path = self.window.create_filename_input(purpose="the unmatched Canvas students")
        if path is None:
            return False

        with open(path, 'w', newline='') as out_file:
            fieldnames = self.canvas_header[:GradePuller.NUM_CANVAS_ID_COLUMNS]
            writer = csv.DictWriter(out_file, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.unmatched_canvas_students.values())

    def report_unmatched_zybook_students(self):
        path = self.window.create_filename_input(purpose="the unmatched zyBook students")
        if path is None:
            return False

        with open(path, 'w', newline='') as out_file:
            fieldnames = self.zybooks_header[:GradePuller.NUM_ZYBOOKS_ID_COLUMNS]
            writer = csv.DictWriter(out_file, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.unmatched_zybook_students.values())

    def report_unmatched_students(self):
        if self.window.create_bool_popup("Unmatched Reports", ["Write a file of unmatched Canvas students?"]):
            self.report_unmatched_canvas_students()
        if self.window.create_bool_popup("Unmatched Reports", ["Write a file of unmatched zyBooks students?"]):
            self.report_unmatched_zybook_students()

    def calc_grade_for(self, student_id, ignore_canvas_grade):
        student_tuple = self.mapped_students[student_id]
        canvas_student = student_tuple[0]
        zybook_student = student_tuple[1]
        if ignore_canvas_grade:
            if zybook_student is not None:
                return zybook_student['grade']
            else:
                return 0.0
        else:
            if zybook_student is not None and canvas_student['grade'] is not None:
                return max(canvas_student['grade'], zybook_student['grade'])
            elif zybook_student is not None and canvas_student['grade'] is None:
                return zybook_student['grade']
            elif zybook_student is None and canvas_student['grade'] is not None:
                return canvas_student['grade']
            else:
                return 0.0


    def calculate_grades(self):
        ignore_canvas_grade = self.window.create_bool_popup("Grading Policy", ["Ignore any grades already in the Canvas csv?"])
        for student_id in self.canvas_students:
            grade = self.calc_grade_for(student_id, ignore_canvas_grade)
            self.canvas_students[student_id][self.selected_canvas_assignment] = str(grade)

    def write_upload_file(self):
        path = self.window.create_filename_input(purpose="the upload file")
        if path is None:
            return False

        with open(path, 'w', newline='') as out_file:
            fieldnames = self.canvas_header[:GradePuller.NUM_CANVAS_ID_COLUMNS] + [self.selected_canvas_assignment]
            writer = csv.DictWriter(out_file, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerow(self.canvas_points_out_of)
            writer.writerows(self.canvas_students.values())

def start():
    puller = GradePuller()
    puller.pull()
