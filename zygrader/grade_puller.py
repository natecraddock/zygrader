import csv
import datetime

from zygrader import data
from zygrader import ui
from zygrader.ui.templates import ZybookSectionSelector, filename_input
from zygrader.ui.displaystring import DisplayStr
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
        self.window = ui.get_window()
        self.zy_api = Zybooks()

    def pull(self):
        try:
            self.read_canvas_csv()
            self.selected_assignments = []

            more_assignments = True
            while more_assignments:
                try:
                    canvas_assignment = self.select_canvas_assignment()
                except GradePuller.StoppingException:
                    # Canceling the operation, but not the grade-pulling operation
                    break
                zybook_sections = self.select_zybook_sections(canvas_assignment)
                class_sections = self.select_class_sections()
                due_times = self.select_due_times(class_sections)

                self.add_assignment_to_report(canvas_assignment,
                                              zybook_sections, class_sections,
                                              due_times)

                msg = ["Add another assignment to the report?"]
                popup = ui.layers.BoolPopup("More Assignments")
                popup.set_message(msg)
                self.window.run_layer(popup)
                more_assignments = popup.get_result()

            self.write_upload_file()
        except GradePuller.StoppingException:
            popup = ui.layers.Popup("Grade Puller")
            popup.set_message(["Grade Puller stopped"])
            self.window.run_layer(popup)

    def read_canvas_csv(self):
        path = SharedData.get_canvas_master()
        popup = ui.layers.Popup("Error in Reading Master CSV")
        try:
            self.canvas_students = dict()
            bad_id_count = 0
            with open(path, "r", newline="") as canvas_master_file:
                canvas_reader = csv.DictReader(canvas_master_file)
                self.canvas_header = canvas_reader.fieldnames
                self.canvas_points_out_of = canvas_reader.__next__()
                for row in canvas_reader:
                    id_str = row["SIS User ID"]
                    if id_str:
                        row["id_number"] = int(id_str)
                    else:
                        bad_id_count += 1
                        row["id_number"] = f"bad_canvas_id_{bad_id_count}"
                    self.canvas_students[row["id_number"]] = row
        except FileNotFoundError:
            msg = [
                f"Could not find {path}",
                "Please download the gradebook from Canvas and put it in the place noted above",
            ]
            popup.set_message(msg)
            self.window.run_layer(popup)
            raise GradePuller.StoppingException()
        except PermissionError:
            msg = [
                f"Could not open {path} for reading",
                "Please have the owner of the file grand read permissions",
            ]
            popup.set_message(msg)
            self.window.run_layer(popup)
            raise GradePuller.StoppingException()

    def select_canvas_assignment(self):
        num_id_columns = GradePuller.NUM_CANVAS_ID_COLUMNS
        real_assignments = self.canvas_header[num_id_columns:]
        assignment_list = ui.layers.ListLayer()
        # TODO: Cleanup setting rows from lists
        for assignment in real_assignments:
            assignment_list.add_row_text(assignment)
        self.window.run_layer(assignment_list)

        if assignment_list.was_canceled():
            raise GradePuller.StoppingException()
        return real_assignments[assignment_list.selected_index()]

    def select_zybook_sections(self, text):
        selector = ZybookSectionSelector()
        res = selector.select_zybook_sections(title_extra=text)
        if not res:
            raise GradePuller.StoppingException()
        return res

    class _SectionToggle(ui.layers.Toggle):
        def __init__(self, index, data):
            self._toggled = False
            self.index = index
            self.data = data

            self.get()

        def get(self):
            self._toggled = self.data[self.index]

        def toggle(self):
            self.data[self.index] = not self.data[self.index]
            self.get()

    def select_class_sections(self):
        sections_list = [
            section.section_number for section in data.get_class_sections()
        ]

        selected = [True] * len(sections_list)

        popup = ui.layers.ListLayer(
            "Select Class Sections (use Back to finish)", popup=True)
        for i, section in enumerate(sections_list):
            popup.add_row_toggle(str(section),
                                 GradePuller._SectionToggle(i, selected))
        self.window.run_layer(popup)

        if not any(selected):
            raise GradePuller.StoppingException()
        return [el for el, selected in zip(sections_list, selected) if selected]

    def select_due_times(self, class_sections):
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=1)
        stored_class_sections = data.get_class_sections_in_ordered_list()
        last_night = create_last_night()

        section_padding = max([len(str(section)) for section in class_sections])

        default_due_times = []
        for section in stored_class_sections:
            if section:
                default_due_times.append(
                    datetime.datetime.combine(yesterday,
                                              section.default_due_time))
            else:
                default_due_times.append(last_night)

        due_times = {
            section: default_due_times[section]
            for section in class_sections
        }

        def select_due_times_fn(selected_index,
                                due_time_popup: ui.layers.ListLayer):
            update_row_text = lambda time, index: due_time_popup.set_subrow_text(
                f"Section {section:>{section_padding}}: {time.strftime('%b %d, %Y at %I:%M:%S%p')}",
                index)

            section = class_sections[selected_index]

            date_spinner = ui.layers.DatetimeSpinner("Due Date")
            date_spinner.set_initial_time(due_times[section])
            date_spinner.set_quickpicks([(50, 0), (59, 59), (0, 0)])
            self.window.run_layer(date_spinner)
            new_datetime = date_spinner.get_time()

            due_times[section] = new_datetime

            # Reset row text for the selected row
            update_row_text(new_datetime, selected_index)

            # For convenience, allow the day or datetime to be carried across
            # all sections so that selecting due times is easier
            # but only if the first section was just edited
            if selected_index != 0 or len(class_sections) <= 1:
                return

            msg = DisplayStr("Set all sections to this due date [u:and time]?")
            popup = ui.layers.BoolPopup("Set Due Time")
            popup.set_message([msg])
            self.window.run_layer(popup)

            if popup.get_result():
                for i, section in enumerate(due_times):
                    due_times[section] = new_datetime
                    update_row_text(new_datetime, i)
                return

            popup = ui.layers.BoolPopup("Set Due Date")
            popup.set_message(
                ["Set all sections to this due date (but retain time)?"])
            self.window.run_layer(popup)

            if popup.get_result():
                for i, section in enumerate(due_times):
                    old_datetime = due_times[section]
                    due_times[section] = datetime.datetime.combine(
                        date=new_datetime, time=old_datetime.time())
                    update_row_text(due_times[section], i)

        popup = ui.layers.ListLayer("Set Due Times (use Back to finish)",
                                    popup=True)
        index = 0
        for section, time in due_times.items():
            row_text = f"Section {section:>{section_padding}}: {time.strftime('%b %d, %Y at %I:%M:%S%p')}"
            popup.add_row_text(row_text, select_due_times_fn, index, popup)
            index += 1
        self.window.run_layer(popup)

        return due_times

    class StudentMapping:
        def __init__(self, canvas_students, zybook_students):
            self.canvas_students = canvas_students
            self.zybook_students = zybook_students
            self._create_mapping()

        def _add_entry(self, canvas_id, zybook_id):
            zybook_student = self.zybook_students[zybook_id]
            self.mapping[canvas_id] = zybook_student
            self.unmatched_canvas_ids.remove(canvas_id)
            self.unmatched_zybook_ids.remove(zybook_id)

        def edit_distance(self, seq1, seq2):
            table = [[0] * (len(seq1) + 1) for _ in range(len(seq2) + 1)]
            for i in range(len(seq1) + 1):
                table[0][i] = i
            for j in range(len(seq2) + 1):
                table[j][0] = j
            for i in range(1, len(seq2) + 1):
                for j in range(1, len(seq1) + 1):
                    left_score = table[i][j - 1] + 1
                    up_score = table[i - 1][j] + 1
                    diag_score = table[i - 1][j - 1] + (0 if seq2[i - 1]
                                                        == seq1[j - 1] else 1)
                    table[i][j] = min(left_score, up_score, diag_score)
            return table[-1][-1]

        def _create_mapping(self):
            self.mapping = dict()
            self.unmatched_canvas_ids = set(self.canvas_students.keys())
            self.unmatched_zybook_ids = set(self.zybook_students.keys())
            for student_id, canvas_student in self.canvas_students.items():
                # try matching by id#
                if student_id in self.zybook_students:
                    self._add_entry(student_id, student_id)
                    continue

                # try matching by netid
                netid = canvas_student["SIS Login ID"]
                if netid in self.zybook_students:
                    self._add_entry(student_id, netid)
                    continue

            for bad_zybook_id in self.unmatched_zybook_ids.copy():
                # try to detect if student included issue# in id#
                zybook_student = self.zybook_students[bad_zybook_id]
                id_str = zybook_student["Student ID"]
                id_chrs = [c for c in id_str if c.isdigit()]
                # the issue number is usually the last two digits
                #  when students try to include it
                real_id_chrs = id_chrs[:-2]
                real_id = None
                try:
                    real_id = int("".join(real_id_chrs))
                except ValueError:
                    continue  # the student has something very wrong
                if real_id in self.unmatched_canvas_ids:
                    self._add_entry(real_id, bad_zybook_id)
                    continue

            # now try fuzzy matching id numbers
            EDIT_DISTANCE_CUTOFF = 4
            consider_pairs = dict()
            for canvas_id in self.unmatched_canvas_ids:
                for zybook_id in self.unmatched_zybook_ids:
                    canvas_student = self.canvas_students[canvas_id]
                    canvas_str_id = canvas_student["SIS User ID"]
                    zybook_student = self.zybook_students[zybook_id]
                    zybook_str_id = zybook_student["Student ID"]
                    if not [c for c in zybook_str_id if c.isalpha()]:
                        zybook_id_digits = [
                            c for c in zybook_str_id if c.isdigit()
                        ]
                        edit_distance = self.edit_distance(
                            zybook_id_digits, canvas_str_id)
                        if edit_distance < EDIT_DISTANCE_CUTOFF:
                            if canvas_id in consider_pairs:
                                consider_pairs[canvas_id].append(zybook_id)
                            else:
                                consider_pairs[canvas_id] = [zybook_id]
            for canvas_id, zybook_id_list in consider_pairs.items():
                # don't fuzzy match ids if they're too close
                #  to multiple students
                if len(zybook_id_list) == 1:
                    self._add_entry(canvas_id, zybook_id_list[0])

    def add_assignment_to_report(self, canvas_assignment, zybook_sections,
                                 class_sections, due_times):
        zybooks_students = self.fetch_completion_reports(
            zybook_sections, due_times)
        mapping = GradePuller.StudentMapping(self.canvas_students,
                                             zybooks_students)

        for canvas_student_id, zybook_student in mapping.mapping.items():
            canvas_student = self.canvas_students[canvas_student_id]
            class_section = self.parse_section_from_canvas_student(
                canvas_student)
            if class_section in class_sections:
                grade = zybook_student["grade"]
                canvas_student[canvas_assignment] = grade
            # else leave canvas grade as it was
        for canvas_student_id in mapping.unmatched_canvas_ids:
            canvas_student = self.canvas_students[canvas_student_id]
            class_section = self.parse_section_from_canvas_student(
                canvas_student)
            if class_section in class_sections:
                canvas_student[canvas_assignment] = 0.0
            # else leave canvas grade as it was

        self.selected_assignments.append(canvas_assignment)

    def parse_section_from_canvas_student(self, student):
        section_str = student["Section"]
        section_num = int(section_str.split("-")[1].split(":")[0])
        return section_num

    def parse_grade_from_canvas_student(self, student, assignment):
        grade_str = student[assignment]
        is_real_grade = grade_str and grade_str != "N/A"
        grade_num = float(grade_str) if is_real_grade else None
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

        bad_id_count = 0
        report = dict()
        for row in csv_reader:
            string_id = row["Student ID"]
            real_id = None
            num_alpha = len([c for c in string_id if c.isalpha()])
            if num_alpha > 0:
                # netids are case-insensitive
                real_id = string_id.lower()
            else:
                try:
                    real_id = int("".join([c for c in string_id
                                           if c.isdigit()]))
                except ValueError:
                    bad_id_count += 1
                    real_id = string_id if string_id else f"bad_zybooks_id_{bad_id_count}"
            while real_id in report:
                real_id = str(real_id) + "(02)"
            row["id_number"] = real_id
            row["grade"] = float(row[total_field_name])
            report[real_id] = row

        return report, header

    def fetch_completion_report(self, due_time, zybook_sections):
        csv_string = self.zy_api.get_completion_report(due_time,
                                                       zybook_sections)
        if not csv_string:
            raise GradePuller.StoppingException()

        return self.parse_completion_report(csv_string)

    def fetch_completion_reports(self, zybook_sections, due_times):
        unique_due_times = set(time for time in due_times.values())
        due_time_to_sections = {time: [] for time in unique_due_times}
        for section_num, due_time in due_times.items():
            due_time_to_sections[due_time].append(section_num)

        wait_msg = [
            "Fetching completion reports from zyBooks",
            "(one per unique due time)",
            f"Completed 0/{len(unique_due_times)}",
        ]

        popup = ui.layers.WaitPopup("Fetch Reports")
        popup.set_message(wait_msg)

        zybooks_students = dict()

        def fetch_reports_fn():
            num_completed = 0
            for due_time, class_section_list in due_time_to_sections.items():
                report, _ = self.fetch_completion_report(
                    due_time, zybook_sections)

                bad_section_count = 0
                for id, row in report.items():
                    try:
                        if (int(row["Class section"])) in class_section_list:
                            zybooks_students[id] = row
                    except ValueError:
                        bad_section_count += 1
                        key = f"bad_zy_class_section_{bad_section_count}"
                        zybooks_students[key] = row

                num_completed += 1
                wait_msg[
                    -1] = f"Completed {num_completed}/{len(unique_due_times)}"
                popup.set_message(wait_msg)

        popup.set_wait_fn(fetch_reports_fn)
        self.window.run_layer(popup)

        return zybooks_students

    def write_upload_file(self):
        default_path_str = "~/" + "&".join(self.selected_assignments) + ".csv"
        default_path_str = default_path_str.replace(" ", "")
        path = filename_input(purpose="the upload file", text=default_path_str)
        if path is None:
            raise GradePuller.StoppingException()

        with open(path, "w", newline="") as out_file:
            id_columns = self.canvas_header[:GradePuller.NUM_CANVAS_ID_COLUMNS]
            fieldnames = id_columns + self.selected_assignments
            writer = csv.DictWriter(out_file,
                                    fieldnames=fieldnames,
                                    extrasaction="ignore")
            writer.writeheader()
            writer.writerow(self.canvas_points_out_of)
            writer.writerows(self.canvas_students.values())

    def find_unmatched_students(self):
        try:
            self.read_canvas_csv()
            zybooks_toc = fetch_zybooks_toc()

            zybook_section_1_1 = zybooks_toc[0]["sections"][0]

            fetch_report_fn = lambda: self.fetch_completion_report(
                create_last_night(), [zybook_section_1_1])

            popup = ui.layers.WaitPopup("Fetch Reports")
            popup.set_message(["Fetching a completion report from zyBooks"])
            popup.set_wait_fn(fetch_report_fn)
            self.window.run_layer(popup)

            zybooks_students, zybooks_header = popup.get_result()

            mapping = GradePuller.StudentMapping(self.canvas_students,
                                                 zybooks_students)

            unmatched_canvas_students = [
                self.canvas_students[id] for id in mapping.unmatched_canvas_ids
            ]
            unmatched_zybook_students = [
                zybooks_students[id] for id in mapping.unmatched_zybook_ids
            ]

            num_id_columns = GradePuller.NUM_CANVAS_ID_COLUMNS
            canvas_report_headers = self.canvas_header[:num_id_columns]
            self.report_list(
                unmatched_canvas_students,
                canvas_report_headers,
                "unmatched canvas students",
                "~/unmatched_canvas.csv",
            )

            num_id_columns = GradePuller.NUM_ZYBOOKS_ID_COLUMNS
            zybooks_report_headers = zybooks_header[:num_id_columns]
            self.report_list(
                unmatched_zybook_students,
                zybooks_report_headers,
                "unmatched zybooks students",
                "~/unmatched_zybooks.csv",
            )

        except GradePuller.StoppingException:
            msg = ["Finding Bad Zybooks Student ID#s stopped"]
            popup = ui.layers.Popup("Grade Puller")
            popup.set_message(msg)
            self.window.run_layer(popup)

    def report_list(self, data, headers, name, default_path=""):
        if not data:
            popup = ui.layers.Popup("No Data")
            popup.set_message([f"There are no {name}"])
            self.window.run_layer(popup)
            return

        path = filename_input(purpose=f"the {name}", text=default_path)
        if path is None:
            raise GradePuller.StoppingException()

        with open(path, "w", newline="") as out_file:
            writer = csv.DictWriter(out_file,
                                    fieldnames=headers,
                                    extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)
