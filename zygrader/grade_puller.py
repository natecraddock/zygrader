import csv
import datetime

from zygrader import data
from zygrader.ui.window import WinContext, Window
from zygrader.ui.templates import ZybookSectionSelector, filename_input
from zygrader.ui import UI_GO_BACK
from zygrader.config.shared import SharedData
from zygrader.zybooks import Zybooks
from zygrader.utils import fetch_zybooks_toc

def create_last_night():
    now = datetime.datetime.now()
    yesterday = now - datetime.timedelta(days=1)
    midnight = datetime.time(hour=23, minute=59, second=59)
    last_night = datetime.datetime.combine(yesterday, midnight)
    return last_night

class GradePuller:
    NUM_CANVAS_ID_COLUMNS = 5
    NUM_ZYBOOKS_ID_COLUMNS = 5

    class StoppingException(Exception):
        pass

    def __init__(self):
        self.window = Window.get_window()
        self.zy_api = Zybooks()

    def pull(self):
        try:
            self.read_canvas_csv()
            self.selected_assignments = []

            more_assignments = True
            while more_assignments:
                canvas_assignment = self.select_canvas_assignment()
                zybook_sections = self.select_zybook_sections()
                class_sections = self.select_class_sections()
                due_times = self.select_due_times(class_sections)

                self.add_assignment_to_report(canvas_assignment, zybook_sections, class_sections, due_times)

                msg = ["Add another assignment to the report?"]
                more_assignments = self.window.create_bool_popup("More Assignments", msg)

            self.write_upload_file(canvas_assignment)
        except GradePuller.StoppingException:
            self.window.create_popup("Grade Puller", ["Grade Puller stopped"])

    def read_canvas_csv(self):
        path = SharedData.get_canvas_master()
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
            raise GradePuller.StoppingException()
        except PermissionError:
            self.window.create_popup("Error in Reading Master CSV", [f"Could not open {path} for reading", "Please have the owner of the file grant read permissions"])
            raise GradePuller.StoppingException()

    def select_canvas_assignment(self):
        real_assignments = self.canvas_header[GradePuller.NUM_CANVAS_ID_COLUMNS:]
        index = self.window.create_filtered_list("Assignment", input_data=real_assignments)
        if index is UI_GO_BACK:
            raise GradePuller.StoppingException()
        return real_assignments[index]

    def select_zybook_sections(self):
        selector = ZybookSectionSelector()
        res = selector.select_zybook_sections()
        if not res:
            raise GradePuller.StoppingException()
        return res

    def select_class_sections(self):
        sections_list = [section.section_number
                             for section in data.get_class_sections()]

        selected = [False] * len(sections_list)
        def toggle_selected(index):
            selected[index] = not selected[index]

        draw_sections = lambda: [
            f"[{'X' if selected else ' '}] {el}"
                for el, selected in zip(sections_list, selected)]
        section_callback = lambda context: toggle_selected(context.data)

        self.window.create_list_popup(
            "Select Class Sections (use Back to finish)",
            callback=section_callback, list_fill=draw_sections)

        if not any(selected):
            raise GradePuller.StoppingException()
        return [el for el, selected in zip(sections_list, selected)
                       if selected]

    def select_due_times(self, class_sections):
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=1)
        stored_class_sections = data.get_class_sections_in_ordered_list()

        default_due_times = []
        for section in stored_class_sections:
            if section:
                default_due_times.append(
                    datetime.datetime.combine(yesterday,
                                              section.default_due_time))
            else:
                default_due_times.append(None)

        due_times = {section: default_due_times[section]
                         for section in class_sections}
        draw = lambda: [f"Section {section}: {time.strftime('%b %d, %Y at %I:%M:%S%p')}" for section, time in due_times.items()]

        def select_due_times_callback(context: WinContext):
            selected_index = context.data

            section = class_sections[selected_index]

            new_time = self.window.create_datetime_spinner("Due Date", due_times[section], [(50, 0), (59, 59), (0,0)])
            due_times[section] = new_time

            if selected_index == 0 and len(class_sections) > 1: #For convenience, allow the day to carried across all sections so that only the time has to be changed for the rest
                do_set_all_sections = self.window.create_bool_popup("Set Due Time", ["Set all sections to this due time?"])
                if do_set_all_sections:
                    for section in due_times:
                        due_times[section] = new_time

        self.window.create_list_popup("Set Due Times (use Back to finish)", callback=select_due_times_callback, list_fill=draw)

        return due_times

    def add_assignment_to_report(self, canvas_assignment, zybook_sections, class_sections, due_times):
        self.fetch_completion_reports(zybook_sections, class_sections, due_times)

        for student_id, student in self.canvas_students.items():
            class_section = self.parse_section_from_canvas_student(student)
            if class_section in class_sections:
                grade = 0.0
                if student_id in self.zybooks_students:
                    grade = self.zybooks_students[student_id]['grade']
                student[canvas_assignment] = grade
            # else leave canvas grade as it was

        self.selected_assignments.append(canvas_assignment)

    def parse_section_from_canvas_student(self, student):
        section_str = student['Section']
        section_num = int(section_str.split('-')[1].split(':')[0])
        return section_num

    def parse_grade_from_canvas_student(self, student, assignment):
        grade_str = student[assignment]
        grade_num = float(grade_str) if grade_str and grade_str != "N/A" else None
        return grade_num

    def parse_completion_report(self, csv_string):
        csv_rows = csv_string.split("\r\n")

        csv_reader = csv.DictReader(csv_rows)
        header = csv_reader.fieldnames

        total_field_name = ""
        for field_name in header:
            if "Total" in field_name:
                total_field_name = field_name
                break

        report = dict()
        for row in csv_reader:
            try:
                row['id_number'] = int(''.join([c for c in row['Student ID'] if c.isdigit()]))
            except ValueError:
                row['id_number'] = 0
            row['grade'] = float(row[total_field_name])
            report[row['id_number']] = row

        return report, header

    def fetch_completion_report(self, due_time, zybook_sections):
        csv_string = self.zy_api.get_completion_report(due_time, zybook_sections)
        if not csv_string:
            raise GradePuller.StoppingException()

        return self.parse_completion_report(csv_string)

    def fetch_completion_reports(self, zybook_sections, class_sections, due_times):
        wait_msg = ["Fetching completion reports from zyBooks", f"Completed 0/{len(class_sections)}"]
        wait_controller = self.window.create_waiting_popup("Fetch Reports", wait_msg)
        num_completed = 0

        self.zybooks_students = dict()
        for class_section in class_sections:
            report, _ = self.fetch_completion_report(due_times[class_section], zybook_sections)

            for id, row in report.items():
                if (int(row['Class section'])) == class_section:
                    self.zybooks_students[id] = row

            num_completed += 1
            wait_msg[-1] = f"Completed {num_completed}/{len(class_sections)}"
            wait_controller.update()

        wait_controller.close()

    def write_upload_file(self, selected_canvas_assignment):
        path = filename_input(purpose="the upload file")
        if path is None:
            raise GradePuller.StoppingException()

        with open(path, 'w', newline='') as out_file:
            fieldnames = self.canvas_header[:GradePuller.NUM_CANVAS_ID_COLUMNS] + self.selected_assignments
            writer = csv.DictWriter(out_file, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerow(self.canvas_points_out_of)
            writer.writerows(self.canvas_students.values())

    def find_unmatched_students(self):
        try:
            self.read_canvas_csv()
            zybooks_toc = fetch_zybooks_toc()

            zybook_section_1_1 = zybooks_toc[0]['sections'][0]
            wait_msg = ["Fetching a completion report from zyBooks"]
            wait_controller = self.window.create_waiting_popup("Fetch Reports", wait_msg)
            zybooks_students, zybooks_header = self.fetch_completion_report(create_last_night(), [zybook_section_1_1])
            wait_controller.close()

            zybooks_student_ids = zybooks_students.keys()
            canvas_student_ids = self.canvas_students.keys()

            unmatched_canvas_ids = canvas_student_ids - zybooks_student_ids
            unmatched_zybooks_ids = zybooks_student_ids - canvas_student_ids

            unmatched_canvas_students = [self.canvas_students[id] for id in unmatched_canvas_ids]
            unmatched_zybook_students = [zybooks_students[id] for id in unmatched_zybooks_ids]

            canvas_report_headers = self.canvas_header[:GradePuller.NUM_CANVAS_ID_COLUMNS]
            self.report_list(unmatched_canvas_students, canvas_report_headers, "unmatched canvas students")

            zybooks_report_headers = zybooks_header[:GradePuller.NUM_ZYBOOKS_ID_COLUMNS]
            self.report_list(unmatched_zybook_students, zybooks_report_headers, "unmatched zybooks students")

        except GradePuller.StoppingException:
            self.window.create_popup("Grade Puller", ["Finding Bad Zybooks Student ID#s stopped"])

    def report_list(self, data, headers, name):
        if not data:
            self.window.create_popup("No Data", [f"There are no {name}"])
            return

        path = filename_input(purpose=f"the {name}")
        if path is None:
            raise GradePuller.StoppingException()

        with open(path, 'w', newline='') as out_file:
            writer = csv.DictWriter(out_file, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)
