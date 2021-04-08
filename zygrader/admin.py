"""Admin: Functions for more "administrator" users of zygrader to manage
the class, scan through student submissions, and access to other menus"""
from zygrader.ui.templates import filename_input
from zygrader.ui import window
from zygrader.config import preferences

import csv
import os
import requests
import re
import time

from zygrader import bobs_shake, class_manager, data, grade_puller, ui, utils
from zygrader.zybooks import Zybooks


def check_student_submissions(zy_api, student_id, lab, search_pattern):
    """Search for a substring in all of a student's submissions for a given lab.
    Supports regular expressions.
    """
    response = {"code": Zybooks.NO_SUBMISSION}

    all_submissions = zy_api.get_all_submissions(lab["id"], student_id)
    if not all_submissions:
        return response

    for submission in all_submissions:
        # Get file from zip url
        try:
            zip_file = zy_api.get_submission_zip(submission["zip_location"])
        except requests.exceptions.ConnectionError:
            # Bad connection, wait a few seconds and try again
            return {"code": Zybooks.DOWNLOAD_TIMEOUT}

        # If there was an error
        if zip_file == Zybooks.ERROR:
            response["error"] = (f"Error fetching submission"
                                 f" {zy_api.get_time_string(submission)}")
            continue

        extracted_zip_files = utils.extract_zip(zip_file)

        # Check each file for the matched string
        for source_file in extracted_zip_files.keys():
            if search_pattern.search(extracted_zip_files[source_file]):

                # Get the date and time of the submission and return it
                response["time"] = zy_api.get_time_string(submission)
                response["code"] = Zybooks.NO_ERROR

                return response

    return response


def submission_search_fn(logger, lab, search_string, output_path, use_regex):
    students = data.get_students()
    zy_api = Zybooks()

    regex_str = search_string if use_regex else re.escape(search_string)
    search_pattern = re.compile(regex_str)

    with open(output_path, "w", newline="") as log_file:
        csv_log = csv.DictWriter(log_file,
                                 fieldnames=[
                                     "Name", "Submission",
                                     (f"(Searching for {search_string})"
                                      f"{' as a regex' if use_regex else ''}")
                                 ])
        csv_log.writeheader()
        student_num = 1

        for student in students:
            while True:
                counter = f"[{student_num}/{len(students)}]"
                logger.log(f"{counter:12} Checking {student.full_name}")

                match_result = check_student_submissions(
                    zy_api, str(student.id), lab, search_pattern)

                if match_result["code"] == Zybooks.DOWNLOAD_TIMEOUT:
                    logger.log(
                        "Download timed out... trying again after a few seconds"
                    )
                    time.sleep(5)
                else:
                    break

            if match_result["code"] == Zybooks.NO_ERROR:
                csv_log.writerow({
                    "Name": student.full_name,
                    "Submission": match_result['time']
                })

                logger.append(f" found {search_string}")

            # Check for and log errors
            if "error" in match_result:
                csv_log.writerow({
                    "Name": student.full_name,
                    "Submission": f"ERROR: {match_result['error']}"
                })

            student_num += 1


def submission_search_init():
    """Get lab part and string from the user for searching"""
    window = ui.get_window()
    labs = data.get_labs()

    menu = ui.layers.ListLayer()
    menu.set_searchable("Assignment")
    for lab in labs:
        menu.add_row_text(str(lab))
    window.run_layer(menu, "Submissions Search")
    if menu.canceled:
        return

    assignment = labs[menu.selected_index()]

    # Select the lab part if needed
    if len(assignment.parts) > 1:
        popup = ui.layers.ListLayer("Select Part", popup=True)
        for part in assignment.parts:
            popup.add_row_text(part["name"])
        window.run_layer(popup, "Submissions Search")
        if popup.canceled:
            return

        part = assignment.parts[popup.selected_index()]
    else:
        part = assignment.parts[0]

    regex_input = ui.layers.BoolPopup("Use Regex")
    regex_input.set_message(["Would you like to use regex?"])
    window.run_layer(regex_input)
    if regex_input.canceled:
        return
    use_regex = regex_input.get_result()

    text_input = ui.layers.TextInputLayer("Search String")
    text_input.set_prompt(["Enter a search string"])
    window.run_layer(text_input, "Submissions Search")
    if text_input.canceled:
        return

    search_string = text_input.get_text()

    # Get a valid output path
    filename_input = ui.layers.PathInputLayer("Output File")
    filename_input.set_prompt(["Enter the filename to save the search results"])
    filename_input.set_text(preferences.get("output_dir"))
    window.run_layer(filename_input, "Submissions Search")
    if filename_input.canceled:
        return

    logger = ui.layers.LoggerLayer()
    logger.set_log_fn(lambda: submission_search_fn(
        logger, part, search_string, filename_input.get_path(), use_regex))
    window.run_layer(logger, "Submission Search")


class LockToggle(ui.layers.Toggle):
    def __init__(self, name, list):
        super().__init__()
        self.__name = name
        self.__list = list
        self.get()

    def toggle(self):
        self.__list[self.__name] = not self.__list[self.__name]
        self.get()

    def get(self):
        self._toggled = self.__list[self.__name]


def remove_locks():
    window = ui.get_window()
    all_locks = {lock: False for lock in data.lock.get_lock_files()}

    popup = ui.layers.ListLayer("Select Locks to Remove", popup=True)
    popup.set_exit_text("Confirm")
    for lock in all_locks:
        popup.add_row_toggle(lock, LockToggle(lock, all_locks))
    window.run_layer(popup)

    selected_locks = [lock for lock in all_locks if all_locks[lock]]
    if not selected_locks:
        return

    # Confirm
    popup = ui.layers.BoolPopup("Confirm Removal")
    popup.set_message(
        [f"Are you sure you want to remove {len(selected_locks)} lock(s)?"])
    window.run_layer(popup)
    if not popup.get_result() or popup.canceled:
        return

    # Remove selected locked content
    for lock in selected_locks:
        if lock:
            data.lock.remove_lock_file(lock)


def _confirm_gradebook_ready():
    window = ui.get_window()

    confirmation = ui.layers.BoolPopup("Using canvas_master", [
        "This operation requires an up-to date canvas_master.",
        ("Please confirm that you have downloaded the gradebook"
         " and put it in the right place."), "Have you done so?"
    ])
    window.run_layer(confirmation)
    return (not confirmation.canceled) and confirmation.get_result()


def report_gaps():
    """Report any cells in the gradebook that do not have a score"""
    window = ui.get_window()

    if not _confirm_gradebook_ready():
        return

    # Use the Canvas parsing from the gradepuller to get the gradebook in
    puller = grade_puller.GradePuller()
    try:
        puller.read_canvas_csv()
    except grade_puller.GradePuller.StoppingException:
        return

    real_assignment_pattern = re.compile(r".*\([0-9]+\)")

    # Create mapping from assignment names to lists of students
    # with no grade for that assignment
    all_gaps = dict()
    for assignment in puller.canvas_header:
        if real_assignment_pattern.match(assignment):
            gaps = []
            for student in puller.canvas_students.values():
                if not student[assignment]:
                    gaps.append(student['Student'])
            if gaps:
                all_gaps[assignment] = gaps

    # Abort if no gaps present
    if not all_gaps:
        popup = ui.layers.Popup("Full Gradebook",
                                ["There are no gaps in the gradebook"])
        window.run_layer(popup)
        return

    # Transpose the data for easier reading
    rows = [list(all_gaps.keys())]
    added = True
    while added:
        added = False
        new_list = []
        for assignment in rows[0]:
            if all_gaps[assignment]:
                new_list.append(all_gaps[assignment].pop(0))
                added = True
            else:
                new_list.append("")
        rows.append(new_list)

    # select the output file and write to it
    out_path = filename_input(purpose="the gap report",
                              text=os.path.join(preferences.get("output_dir"),
                                                "gradebook_gaps.csv"))
    if out_path is None:
        return
    with open(out_path, "w", newline="") as out_file:
        writer = csv.writer(out_file)
        writer.writerows(rows)


def midterm_mercy():
    """Replace the lower of the two midterm scores with the final exam score"""
    window = ui.get_window()

    if not _confirm_gradebook_ready():
        return

    # Use the Canvas parsing from the gradepuller to get the gradebook in
    # also use the selection of canvas assignments from the gradepuller
    puller = grade_puller.GradePuller()
    try:
        puller.read_canvas_csv()

        popup = ui.layers.Popup("Selection")
        popup.set_message(["First Select the Midterm 1 Assignment"])
        window.run_layer(popup)
        midterm_1_assignment = puller.select_canvas_assignment()

        midterm_2_assignment = None
        double_midterm_popup = ui.layers.BoolPopup("2 Midterms")
        double_midterm_popup.set_message([
            "Is there a second midterm this semester?",
            "If so, select that assignment next."
        ])
        window.run_layer(double_midterm_popup)
        if double_midterm_popup.canceled:
            return
        if double_midterm_popup.get_result():
            midterm_2_assignment = puller.select_canvas_assignment()

        popup.set_message(["Next Select the Final Exam Assignment"])
        window.run_layer(popup)
        final_exam_assignment = puller.select_canvas_assignment()

    except grade_puller.GradePuller.StoppingException:
        return

    # Do the replacement for each student
    for student in puller.canvas_students.values():
        midterm_1_score = float(student[midterm_1_assignment])
        midterm_2_score = (float(student[midterm_2_assignment])
                           if midterm_2_assignment else None)
        final_exam_score = float(student[final_exam_assignment])

        if midterm_2_assignment:
            # Figure out lower midterm, then if it should be replaced do so
            if midterm_2_score < midterm_1_score:
                if final_exam_score > midterm_2_score:
                    student[midterm_2_assignment] = final_exam_score
            else:
                if final_exam_score > midterm_1_score:
                    student[midterm_1_assignment] = final_exam_score
        else:
            # With only one midterm, just replace it if lower than final
            if final_exam_score > midterm_1_score:
                student[midterm_1_assignment] = final_exam_score

    out_path = filename_input(purpose="the updated midterm scores",
                              text=os.path.join(preferences.get("output_dir"),
                                                "midterm_mercy.csv"))
    if out_path is None:
        return

    # Again use the gradepuller functionality
    # We just need to programmatically set the selected assignments
    puller.selected_assignments = [midterm_1_assignment]
    if midterm_2_assignment:
        puller.selected_assignments.append(midterm_2_assignment)
    puller.write_upload_file(out_path)

    popup = ui.layers.Popup("Reminder")
    popup.set_message([
        "Don't forget to manually correct as necessary"
        " (for any students who should not have a score replaced)."
    ])
    window.run_layer(popup)


def attendance_score():
    """Calculate the participation score from the attendance score columns"""
    window = ui.get_window()

    if not _confirm_gradebook_ready():
        return

    # Make use of many functions from gradepuller to avoid code duplication
    puller = grade_puller.GradePuller()
    try:
        puller.read_canvas_csv()

        popup = ui.layers.Popup("Selection")
        popup.set_message(["First Select the Participation Score Assignment"])
        window.run_layer(popup)
        participation_score_assignment = puller.select_canvas_assignment()

        popup.set_message(["Next Select the first Classes Missed Assignment"])
        window.run_layer(popup)
        start_classes_missed_assignment = puller.select_canvas_assignment()

        popup.set_message(["Next Select the last Classes Missed Assignment"])
        window.run_layer(popup)
        end_classes_missed_assignment = puller.select_canvas_assignment()

        class_sections = puller.select_class_sections()

    except grade_puller.GradePuller.StoppingException:
        return

    # Get all of the assignments between the start and end
    start_index = puller.canvas_header.index(start_classes_missed_assignment)
    end_index = puller.canvas_header.index(end_classes_missed_assignment)
    all_classes_missed_assignments = puller.canvas_header[
        start_index:end_index + 1]

    # Figure out the grading scheme - the mapping from classes missed to grade
    builtin_schemes = [
        ("TR", [100, 100, 98, 95, 91, 86, 80, 73, 65, 57, 49, 46]),
        ("MWF", [100, 100, 99, 97, 94, 90, 85, 80, 75, 70, 65, 60, 55, 53]),
    ]
    scheme_selector = ui.layers.ListLayer("Scheme Selector", popup=True)
    for name, scheme in builtin_schemes:
        scheme_selector.add_row_text(f"{name}: {','.join(map(str,scheme))},...")
    scheme_selector.add_row_text("Create New Scheme")

    window.run_layer(scheme_selector)
    if scheme_selector.canceled:
        return

    selected = scheme_selector.selected_index()
    if selected < len(builtin_schemes):
        points_by_classes_missed = builtin_schemes[selected][1]
    else:
        # Get the custom scheme
        scheme_inputter = ui.layers.TextInputLayer("New Scheme")
        scheme_inputter.set_prompt([
            "Enter a new scheme as a comma-separated list",
            "e.g. '100,100,95,90,85,80,78'",
            "",
            "The difference between the last two values will be repeated"
            " until a score of 0 is reached",
        ])
        window.run_layer(scheme_inputter)
        if scheme_inputter.canceled:
            return
        scheme_text = scheme_inputter.get_text()
        points_by_classes_missed = list(map(int, scheme_text.split(',')))

    # Extend the scheme until 0 is reached
    delta = points_by_classes_missed[-2] - points_by_classes_missed[-1]
    while points_by_classes_missed[-1] >= 0:
        points_by_classes_missed.append(points_by_classes_missed[-1] - delta)
    # Get rid of the negative element
    del points_by_classes_missed[-1]

    # Calculate and assign the grade for each student
    for student in puller.canvas_students.values():
        if student["section_number"] in class_sections:
            total_classes_missed = 0
            for assignment in all_classes_missed_assignments:
                try:
                    total_classes_missed += int(student[assignment])
                except ValueError:
                    total_classes_missed += int(
                        puller.canvas_points_out_of[assignment])

            try:
                grade = points_by_classes_missed[total_classes_missed]
            except IndexError:
                grade = 0
            student[participation_score_assignment] = grade

    out_path = filename_input(purpose="the partipation score",
                              text=os.path.join(preferences.get("output_dir"),
                                                "participation.csv"))
    if out_path is None:
        return

    # Again use the gradepuller functionality
    # We just need to programmatically set the selected assignments
    puller.selected_assignments = [participation_score_assignment]
    # And the involved class sections
    puller.involved_class_sections = set(class_sections)
    puller.write_upload_file(out_path, restrict_sections=True)


def end_of_semester_tools():
    """Create the menu for end of semester tools"""
    window = ui.get_window()

    menu = ui.layers.ListLayer()
    menu.add_row_text("Report Gaps", report_gaps)
    menu.add_row_text("Midterm Mercy", midterm_mercy)
    menu.add_row_text("Attendance Score", attendance_score)

    window.register_layer(menu)


def admin_menu():
    """Create the admin menu"""
    window = ui.get_window()

    menu = ui.layers.ListLayer()
    menu.add_row_text("Submissions Search", submission_search_init)
    menu.add_row_text("Grade Puller", grade_puller.GradePuller().pull)
    menu.add_row_text("Find Unmatched Students",
                      grade_puller.GradePuller().find_unmatched_students)
    menu.add_row_text("Remove Locks", remove_locks)
    menu.add_row_text("Class Management", class_manager.start)
    menu.add_row_text("Bob's Shake", bobs_shake.shake)
    menu.add_row_text("End Of Semester Tools", end_of_semester_tools)

    window.register_layer(menu, "Admin")
