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
    window.push_refresh_event()


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
        window.create_popup("Warning", msg)

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
        window.create_popup("No Submissions",
                            ["The student did not submit this part"])
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
        window.create_popup(
            "No Submission",
            [
                "Cannot diff submissions because at least one student has not submitted."
            ],
        )
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
        window.create_popup("Error", ["Could not compile and run code"])


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
            window.create_popup("Student Locked", msg)
            return False

    if data.flags.is_submission_flagged(student, lab):
        msg = [
            "This submission has been flagged",
            "",
            f"Note: {data.flags.get_flag_message(student, lab)}",
            "",
            "Would you like to unflag it?",
        ]
        remove = window.create_bool_popup("Submission Flagged", msg)

        if remove:
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

    note = window.create_text_input("Flag Note", "Enter a flag note")
    if note == ui.GO_BACK:
        return

    data.flags.flag_submission(student, lab, note)


def diff_parts_fn(window, submission):
    """Callback for text diffing parts of a submission"""
    error = submission.diff_parts()
    if error:
        window.create_popup("Error", [error])


def student_callback(context: ui.WinContext, lab, use_locks=True):
    """Show the submission for the selected lab and student"""
    window = context.window
    student_list = context.component
    student = data.get_students()[context.data]

    # Wait for student's assignment to be available
    if not can_get_through_locks(use_locks, student, lab):
        return

    try:
        # Get the student's submission
        submission = get_submission(lab, student, use_locks)

        # Exit if student has not submitted
        if submission is None:
            return

        update_student_list(window, student_list)

        options = {
            "Flag":
            lambda _: flag_submission(lab, student),
            "Pick Submission":
            lambda _: pick_submission(lab, student, submission),
            "Pair Programming":
            lambda _: grade_pair_programming(student_list, submission, use_locks
                                             ),
            "Diff Parts":
            lambda _: diff_parts_fn(window, submission),
            "Run":
            lambda context: run_code_fn(window, context, submission),
            "View":
            lambda _: submission.show_files(),
        }

        # Add option to diff parts if this lab requires it
        if not (use_locks
                and submission.flag & data.model.SubmissionFlag.DIFF_PARTS):
            del options["Diff Parts"]

        window.create_options_popup("Submission", submission, options,
                                    ui.components.Popup.ALIGN_LEFT)

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


def lab_callback(context: ui.WinContext, use_locks=True):
    """Create the list of labs to pick a student to grade"""
    window = context.window

    lab = data.get_labs()[context.data]
    window.set_header(lab.name)

    students = data.get_students()

    student_select_fn = lambda context: student_callback(
        context, lab, use_locks)

    # Get student
    window.create_filtered_list(
        "Student",
        list_fill=lambda: fill_student_list(lab, students),
        callback=student_select_fn,
        filter_function=data.Student.find,
        create_fn=lambda student_list: watch_students(window, student_list),
    )

    # Remove the file watch handler when done choosing students
    data.fs_watch.fs_watch_unregister("student_list_watch")


def grade(use_locks=True):
    """Create the list of labs to pick one to grade"""
    window = ui.get_window()
    labs = data.get_labs()

    if use_locks:
        window.set_header("Grader")
    else:
        window.set_header("Run for Fun")
    if not labs:
        window.create_popup("Error", ["No labs have been created yet"])
        return

    # Pick a lab
    lab_select_fn = lambda context: lab_callback(context, use_locks)
    window.create_filtered_list("Assignment",
                                input_data=labs,
                                callback=lab_select_fn,
                                filter_function=data.Lab.find)
