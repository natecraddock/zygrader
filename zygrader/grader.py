"""Grader: Menus and popups for grading and pair programming"""
import curses
import getpass

from . import config
from . import data
from . import utils

from .ui import components, UI_GO_BACK
from .ui.window import Event, Window
from .zybooks import Zybooks

def color_student_lines(lab, student):
    """Color the student names in the grader based on locked, flagged, or normal status"""
    if data.lock.is_lab_locked(student, lab) and not isinstance(student, str):
        return curses.color_pair(2)
    if data.flags.is_submission_flagged(student, lab) and not isinstance(student, str):
        return curses.color_pair(7)
    return curses.color_pair(0)

def fill_student_list(lab, students):
    """Given a list of students, fill the list sorting locked and
    flagged students to the top; also color the lines"""
    lines = []
    num_locked = 0
    for i, student in enumerate(students):
        line = components.FilteredList.ListLine(i + 1, student)
        line.color = color_student_lines(lab, student)

        if line.color == curses.color_pair(2):
            lines.insert(0, line)
            num_locked += 1
        elif line.color == curses.color_pair(7):
            lines.insert(num_locked, line)
        else:
            lines.append(line)

    return lines

def update_student_list(window: Window, student_list: components.FilteredList):
    """Update the student list when the locks or flags change"""
    student_list.refresh()
    window.push_refresh_event()

def get_submission(lab, student, use_locks=True):
    """Get a submission from zyBooks given the lab and student"""
    window = Window.get_window()
    zy_api = Zybooks()

    # Lock student
    if use_locks:
        data.lock.lock_lab(student, lab)

    submission_response = zy_api.download_assignment(student, lab)
    submission = data.model.Submission(student, lab, submission_response)

    # Report missing files
    if submission.flag & data.model.SubmissionFlag.BAD_ZIP_URL:
        msg = [f"One or more URLs for {student.full_name}'s code submission are bad.",
               "Some files could not be downloaded. Please",
               "View the most recent submission on zyBooks."]
        window.create_popup("Warning", msg)

    return submission

def pick_submission(lab: data.model.Lab, student: data.model.Student,
                    submission: data.model.Submission):
    """Allow the user to pick a submission to view"""
    window = Window.get_window()
    zy_api = Zybooks()

    # If the lab has multiple parts, prompt to pick a part
    part_index = 0
    if len(lab.parts) > 1:
        part_index = window.create_list_popup("Select Part",
                                              input_data=[name["name"] for name in lab.parts])
        if part_index is UI_GO_BACK:
            return

    # Get list of all submissions for that part
    part = lab.parts[part_index]
    all_submissions = zy_api.get_submissions_list(part["id"], student.id)
    if not all_submissions:
        window.create_popup("No Submissions", ["The student did not submit this part"])
        return

    # Reverse to display most recent submission first
    all_submissions.reverse()

    submission_index = window.create_list_popup("Select Submission", all_submissions)
    if submission_index is UI_GO_BACK:
        return

    # Modify submission index to un-reverse the index
    submission_index = abs(submission_index - (len(all_submissions) - 1))

    # Fetch that submission
    part_response = zy_api.download_assignment_part(lab, student.id, part, submission_index)
    submission.update_part(part_response, part_index)

def view_diff(first, second):
    """View a diff of the two submissions"""
    use_browser = config.user.is_preference_set("browser_diff")

    paths_a = utils.get_source_file_paths(first.files_directory)
    paths_b = utils.get_source_file_paths(second.files_directory)

    paths_a.sort()
    paths_b.sort()

    diff = utils.make_diff_string(paths_a, paths_b, first.student.full_name,
                                  second.student.full_name, use_browser)
    utils.view_string(diff, "submissions.diff", use_browser)

def run_code_fn(window, event: Event, submission):
    """Callback to compile and run a submission's code"""
    use_gdb = event.modifier == Event.MOD_ALT

    if not submission.compile_and_run_code(use_gdb):
        window.create_popup("Error", ["Could not compile and run code"])

def pair_programming_submission_callback(submission):
    """Show both pair programming students for viewing a diff"""
    window = Window.get_window()

    options = {
        "Run": lambda event: run_code_fn(window, event, submission),
        "View": lambda _: submission.show_files()
    }

    window.create_options_popup("Pair Programming Submission",
                                submission.msg, options, components.Popup.ALIGN_LEFT)
    config.g_data.running_process = None

def grade_pair_programming(student_list, first_submission):
    """Pick a second student to grade pair programming with"""
    # Get second student
    window = Window.get_window()
    students = data.get_students()

    lab = first_submission.lab

    # Get student
    student_index = window.create_filtered_list("Student",
                                                list_fill=lambda: fill_student_list(lab, students),
                                                filter_function=data.Student.find)
    if student_index is UI_GO_BACK:
        return

    student = students[student_index]

    if data.lock.is_lab_locked(student, lab):
        netid = data.lock.get_locked_netid(student, lab)

        msg = [f"This student is already being graded by {netid}"]
        window.create_popup("Student Locked", msg)
        return

    try:
        second_submission = get_submission(lab, student)
        # Immediately redraw the original list
        update_student_list(window, student_list)

        if second_submission.flag == data.model.SubmissionFlag.NO_SUBMISSION:
            msg = [f"{student.full_name} has not submitted"]
            window.create_popup("No Submissions", msg)

            data.lock.unlock_lab(student, lab)
            return

        first_submission_fn = lambda _: pair_programming_submission_callback(first_submission)
        second_submission_fn = lambda _: pair_programming_submission_callback(second_submission),
        options = {
            first_submission.student.full_name: first_submission_fn,
            second_submission.student.full_name: second_submission_fn,
            "View Diff": lambda _: view_diff(first_submission, second_submission)
        }

        msg = [f"{first_submission.student.full_name} {first_submission.latest_submission}",
               f"{second_submission.student.full_name} {second_submission.latest_submission}",
               "", "Pick a student's submission to view or view the diff"]

        window.create_options_popup("Pair Programming", msg, options)

        data.lock.unlock_lab(student, lab)
    except KeyboardInterrupt:
        data.lock.unlock_lab(student, lab)
    except curses.error:
        data.lock.unlock_lab(student, lab)

def flag_submission(lab, student):
    """Flag a submission with a note"""
    window = Window.get_window()

    note = window.create_text_input("Flag Note")
    if note == UI_GO_BACK:
        return

    data.flags.flag_submission(student, lab, note)

def diff_parts_fn(window, submission):
    """Callback for text diffing parts of a submission"""
    error = submission.diff_parts()
    if error:
        window.create_popup("Error", [error])

def student_callback(student_list, lab, student_index, use_locks=True):
    """Show the submission for the selected lab and student"""
    window = Window.get_window()
    student = data.get_students()[student_index]

    # Wait for student's assignment to be available
    if use_locks and data.lock.is_lab_locked(student, lab):
        netid = data.lock.get_locked_netid(student, lab)

        # If being graded by the user who locked it, allow grading
        if netid != getpass.getuser():
            msg = [f"This student is already being graded by {netid}"]
            window.create_popup("Student Locked", msg)
            return

    if use_locks and data.flags.is_submission_flagged(student, lab):
        msg = ["This submission has been flagged", "",
               f"Note: {data.flags.get_flag_message(student, lab)}", "",
               "Would you like to unflag it?"]
        remove = window.create_bool_popup("Submission Flagged", msg)

        if remove:
            data.flags.unflag_submission(student, lab)
        else:
            return

    try:
        # Get the student's submission
        submission = get_submission(lab, student, use_locks)
        update_student_list(window, student_list)

        # Unlock if student has not submitted
        if submission.flag == data.model.SubmissionFlag.NO_SUBMISSION:
            msg = [f"{student.full_name} has not submitted"]
            window.create_popup("No Submissions", msg)
            return

        options = {
            "Flag": lambda _: flag_submission(lab, student),
            "Pick Submission": lambda _: pick_submission(lab, student, submission),
            "Pair Programming": lambda _: grade_pair_programming(student_list, submission),
            "Diff Parts": lambda _: diff_parts_fn(window, submission),
            "Run": lambda event: run_code_fn(window, event, submission),
            "View": lambda _: submission.show_files()
        }

        if not use_locks:
            del options["Pair Programming"]

        # Add option to diff parts if this lab requires it
        if not (use_locks and submission.flag & data.model.SubmissionFlag.DIFF_PARTS):
            del options["Diff Parts"]

        window.create_options_popup("Submission", submission.msg,
                                    options, components.Popup.ALIGN_LEFT)

        config.g_data.running_process = None

    finally:
        # Always unlock the lab when no longer grading
        if use_locks:
            data.lock.unlock_lab(student, lab)

def watch_students(window: Window, student_list: components.FilteredList):
    """Register paths when the filtered list is created"""
    paths = [config.g_data.get_locks_directory(), config.g_data.get_flags_directory()]

    update_list = lambda _: update_student_list(window, student_list)
    data.fs_watch.fs_watch_register(paths, "student_list_watch", update_list)

def lab_callback(lab_index, use_locks=True):
    """Create the list of labs to pick a student to grade"""
    window = Window.get_window()

    lab = data.get_labs()[lab_index]
    window.set_header(lab.name)

    students = data.get_students()

    student_select_fn = (lambda student_index, student_list:
                         student_callback(student_list, lab, student_index, use_locks))

    # Get student
    window.create_filtered_list("Student", list_fill=lambda: fill_student_list(lab, students),
                                callback=student_select_fn, filter_function=data.Student.find,
                                create_fn=lambda student_list: watch_students(window, student_list))

    # Remove the file watch handler when done choosing students
    data.fs_watch.fs_watch_unregister("student_list_watch")

def grade(use_locks=True):
    """Create the list of labs to pick one to grade"""
    window = Window.get_window()
    labs = data.get_labs()

    if use_locks:
        window.set_header("Grader")
    else:
        window.set_header("Run for Fun")
    if not labs:
        window.create_popup("Error", ["No labs have been created yet"])
        return

    # Pick a lab
    lab_select_fn = lambda lab_index, _filtered_list: lab_callback(lab_index, use_locks)
    window.create_filtered_list("Assignment", input_data=labs, callback=lab_select_fn,
                                filter_function=data.Lab.find)
