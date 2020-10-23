"""Grader: Menus and popups for grading and pair programming"""
import curses
import getpass
from zygrader.data import model

from zygrader.config import preferences
from zygrader.config.shared import SharedData
from zygrader import data
from zygrader import ui
from zygrader import utils

from zygrader.zybooks import Zybooks


def color_student_lines(lab, student):
    """Color the student names in the grader based on locked, flagged, or normal status"""
    if data.lock.is_locked(student, lab) and not isinstance(student, str):
        return curses.color_pair(2)
    if data.flags.is_submission_flagged(student,
                                        lab) and not isinstance(student, str):
        return curses.color_pair(7)
    return curses.color_pair(1)


def fill_student_list(lab, students):
    """Given a list of students, fill the list sorting locked and
    flagged students to the top; also color the lines"""
    lines = []
    num_locked = 0
    for i, student in enumerate(students):
        line = ui.components.FilteredList.ListLine(i + 1, student)
        line.color = color_student_lines(lab, student)

        if line.color == curses.color_pair(2):
            lines.insert(0, line)
            num_locked += 1
        elif line.color == curses.color_pair(7):
            lines.insert(num_locked, line)
        else:
            lines.append(line)

    return lines


def update_student_list(window: ui.Window,
                        student_list: ui.components.FilteredList):
    """Update the student list when the locks or flags change"""
    student_list.refresh()
    events = ui.get_events()
    events.push_refresh_event()


def get_submission(lab, student, use_locks=True):
    """Get a submission from zyBooks given the lab and student"""
    window = ui.get_window()
    zy_api = Zybooks()

    # Lock student
    if use_locks:
        data.lock.lock(student, lab)

    submission_response = zy_api.download_assignment(student, lab)
    submission = data.model.Submission(student, lab, submission_response)

    # Report missing files
    if submission.flag & data.model.SubmissionFlag.BAD_ZIP_URL:
        msg = [
            f"One or more URLs for {student.full_name}'s code submission are bad.",
            "Some files could not be downloaded. Please",
            "View the most recent submission on zyBooks.",
        ]
        popup = ui.layers("Warning", msg)
        window.run_layer(popup)

    # A student may have submissions beyond the due date, and an exception
    # In case that happens, always allow a normal grade, but show a message
    if submission.flag == data.model.SubmissionFlag.NO_SUBMISSION:
        pass

    return submission


def pick_submission(lab: data.model.Lab, student: data.model.Student,
                    submission: data.model.Submission):
    """Allow the user to pick a submission to view"""
    window = ui.get_window()
    zy_api = Zybooks()

    # If the lab has multiple parts, prompt to pick a part
    part_index = 0
    if len(lab.parts) > 1:
        part_index = window.create_list_popup(
            "Select Part", input_data=[name["name"] for name in lab.parts])
        if part_index is ui.GO_BACK:
            return

    # Get list of all submissions for that part
    part = lab.parts[part_index]
    all_submissions = zy_api.get_submissions_list(part["id"], student.id)
    if not all_submissions:
        popup = ui.layers.Popup("No Submissions",
                                ["The student did not submit this part"])
        window.run_layer(popup)
        return

    # Reverse to display most recent submission first
    all_submissions.reverse()

    submission_index = window.create_list_popup("Select Submission",
                                                all_submissions)
    if submission_index is ui.GO_BACK:
        return

    # Modify submission index to un-reverse the index
    submission_index = abs(submission_index - (len(all_submissions) - 1))

    # Fetch that submission
    part_response = zy_api.download_assignment_part(lab, student.id, part,
                                                    submission_index)
    submission.update_part(part_response, part_index)


def view_diff(first: model.Submission, second: model.Submission):
    """View a diff of the two submissions"""
    if (first.flag & model.SubmissionFlag.NO_SUBMISSION
            or second.flag & model.SubmissionFlag.NO_SUBMISSION):
        window = ui.get_window()
        popup = ui.layers.Popup("No Submissions", [
            "Cannot diff submissions because at least one student has not submitted."
        ])
        window.run_layer(popup)
        return

    use_browser = preferences.get("browser_diff")

    paths_a = utils.get_source_file_paths(first.files_directory)
    paths_b = utils.get_source_file_paths(second.files_directory)

    paths_a.sort()
    paths_b.sort()

    diff = utils.make_diff_string(paths_a, paths_b, first.student.full_name,
                                  second.student.full_name, use_browser)
    utils.view_string(diff, "submissions.diff", use_browser)


def run_code_fn(window, context: ui.WinContext, submission):
    """Callback to compile and run a submission's code"""
    use_gdb = False

    if not submission.compile_and_run_code(use_gdb):
        popup = ui.layers.Popup("Error", ["Could not compile and run code"])
        window.run_layer(popup)


def pair_programming_submission_callback(lab, submission):
    """Show both pair programming students for viewing a diff"""
    window = ui.get_window()

    options = {
        "Pick Submission":
        lambda _: pick_submission(lab, submission.student, submission),
        "Run":
        lambda context: run_code_fn(window, context, submission),
        "View":
        lambda _: submission.show_files(),
    }

    window.create_options_popup("Pair Programming Submission", submission,
                                options, ui.components.Popup.ALIGN_LEFT)
    SharedData.running_process = None


def can_get_through_locks(use_locks, student, lab):
    if not use_locks:
        return True

    window = ui.get_window()

    if data.lock.is_locked(student, lab):
        netid = data.lock.get_locked_netid(student, lab)

        # If being graded by the user who locked it, allow grading
        if netid != getpass.getuser():
            msg = [f"This student is already being graded by {netid}"]
            popup = ui.layers.Popup("Student Locked", msg)
            window.run_layer(popup)
            return False

    if data.flags.is_submission_flagged(student, lab):
        msg = [
            "This submission has been flagged",
            "",
            f"Note: {data.flags.get_flag_message(student, lab)}",
            "",
            "Would you like to unflag it?",
        ]
        popup = ui.layers.BoolPopup("Submission Flagged", msg)
        window.run_layer(popup)

        if popup.get_result():
            data.flags.unflag_submission(student, lab)
        else:
            return False

    return True


def pair_programming_message(first, second) -> list:
    """To support dynamic updates on the pair programming popup"""
    return [
        f"{first.student.full_name} {first.latest_submission}",
        f"{second.student.full_name} {second.latest_submission}",
        "",
        "Pick a student's submission to view or view the diff",
    ]


def grade_pair_programming(student_list, first_submission, use_locks):
    """Pick a second student to grade pair programming with"""
    # Get second student
    window = ui.get_window()
    students = data.get_students()

    lab = first_submission.lab

    # Get student
    student_index = window.create_filtered_list(
        "Student",
        list_fill=lambda: fill_student_list(lab, students),
        filter_function=data.Student.find,
    )
    if student_index is ui.GO_BACK:
        return

    student = students[student_index]

    if not can_get_through_locks(use_locks, student, lab):
        return

    try:
        second_submission = get_submission(lab, student, use_locks)

        if second_submission is None:
            return

        # Redraw the original list
        update_student_list(window, student_list)

        first_submission_fn = lambda _: pair_programming_submission_callback(
            lab, first_submission)
        second_submission_fn = lambda _: pair_programming_submission_callback(
            lab, second_submission)
        options = {
            first_submission.student.full_name: first_submission_fn,
            second_submission.student.full_name: second_submission_fn,
            "View Diff":
            lambda _: view_diff(first_submission, second_submission),
        }

        msg = lambda: pair_programming_message(first_submission,
                                               second_submission)
        window.create_options_popup("Pair Programming", msg, options)

    finally:
        if use_locks:
            data.lock.unlock(student, lab)


def flag_submission(lab, student):
    """Flag a submission with a note"""
    window = ui.get_window()

    text_input = ui.layers.TextInputLayer("Flag Note")
    text_input.set_prompt("Enter a flag note")
    window.run_layer(text_input)
    if text_input.was_canceled():
        return

    data.flags.flag_submission(student, lab, text_input.get_text())


def diff_parts_fn(window, submission):
    """Callback for text diffing parts of a submission"""
    error = submission.diff_parts()
    if error:
        popup = ui.layer.Popup("Error", [error])
        window.run_layer(popup)


def student_select_fn(selected_index, lab, use_locks):
    """Show the submission for the selected lab and student"""
    window = ui.get_window()
    student = data.get_students()[selected_index]

    # Wait for student's assignment to be available
    if not can_get_through_locks(use_locks, student, lab):
        return

    try:
        # Get the student's submission
        submission = get_submission(lab, student, use_locks)

        # Exit if student has not submitted
        if submission is None:
            return

        popup = ui.layers.OptionsPopup("Submission")
        popup.set_message(
            ["TODO: Fill in the submission text here... needs to update"])
        popup.add_option("Flag", lambda _: flag_submission(lab, student))
        popup.add_option("Pick Submission",
                         lambda _: pick_submission(lab, student, submission))
        # TODO: Pass student_list (component..) to grade_pair_programming
        popup.add_option(
            "Pair Programming",
            lambda _: grade_pair_programming(None, submission, use_locks))
        if submission.flag & data.model.SubmissionFlag.DIFF_PARTS:
            popup.add_option("Diff Parts",
                             lambda _: diff_parts_fn(window, submission))
        popup.add_option(
            "Run", lambda context: run_code_fn(window, context, submission))
        popup.add_option("View", lambda _: submission.show_files())
        window.run_layer(popup)

        SharedData.running_process = None

    finally:
        # Always unlock the lab when no longer grading
        if use_locks:
            data.lock.unlock(student, lab)


def watch_students(window: ui.Window, student_list: ui.components.FilteredList):
    """Register paths when the filtered list is created"""
    paths = [SharedData.get_locks_directory(), SharedData.get_flags_directory()]

    update_list = lambda _: update_student_list(window, student_list)
    data.fs_watch.fs_watch_register(paths, "student_list_watch", update_list)


def lab_select_fn(selected_index, use_locks):
    """Create the list of labs to pick a student to grade"""
    window = ui.get_window()
    lab = data.get_labs()[selected_index]
    students = data.get_students()

    # student_select_fn = lambda context: student_callback(
    #     context, lab, use_locks)

    # # Get student
    # window.create_filtered_list(
    #     "Student",
    #     list_fill=lambda: fill_student_list(lab, students),
    #     callback=student_select_fn,
    #     filter_function=data.Student.find,
    #     create_fn=lambda student_list: watch_students(window, student_list),
    # )

    student_list = ui.layers.ListLayer()
    student_list.set_searchable("Student")
    for index, student in enumerate(students):
        student_list.add_row_text(str(student), student_select_fn, index, lab,
                                  use_locks)
    window.register_layer(student_list, lab.name)

    # Remove the file watch handler when done choosing students
    data.fs_watch.fs_watch_unregister("student_list_watch")


def grade(use_locks=True):
    """Create the list of labs to pick one to grade"""
    window = ui.get_window()
    labs = data.get_labs()

    if not labs:
        popup = ui.layers.Popup("Error")
        popup.set_message(["No labs have been created yet"])
        window.run_layer(popup)
        return

    title = "Grader"
    if not use_locks:
        title = "Run for Fun"

    lab_list = ui.layers.ListLayer()
    lab_list.set_searchable("Lab")
    for index, lab in enumerate(labs):
        lab_list.add_row_text(str(lab), lab_select_fn, index, use_locks)
    window.register_layer(lab_list, title)
