import curses
import difflib
import getpass
import io
import os
import subprocess
from subprocess import PIPE
import tempfile

from . import config
from . import data
from . import logger
from . import utils

from .ui import components, UI_GO_BACK
from .ui.window import Window
from .zybooks import Zybooks

def get_submission(lab, student, use_locks=True):
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

def pick_submission(lab: data.model.Lab, student: data.model.Student, submission: data.model.Submission):
    """Allow the user to pick a submission to view"""
    window = Window.get_window()
    zy_api = Zybooks()

    # If the lab has multiple parts, prompt to pick a part
    part_index = 0
    if len(lab.parts) > 1:
        part_index = window.create_list_popup("Select Part", input_data=[name["name"] for name in lab.parts])
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

    diff = utils.make_diff_string(paths_a, paths_b, first.student.full_name, second.student.full_name, use_browser)
    utils.view_string(diff, "submissions.diff", use_browser)

def pair_programming_submission_callback(submission):
    window = Window.get_window()

    options = ["Run", "View", "Done"]
    while True:
        option = window.create_options_popup("Pair Programming Submission", submission.msg, options, components.Popup.ALIGN_LEFT)

        if option == "View":
            submission.show_files()
        elif option == "Run":
            if not submission.compile_and_run_code():
                window.create_popup("Error", ["Could not compile and run code"])
        else:
            break

    config.g_data.running_process = None

def grade_pair_programming(first_submission):
    # Get second student
    window = Window.get_window()
    students = data.get_students()

    lab = first_submission.lab

    # Get student
    window.set_header("Pair Programming")
    line_lock = lambda student : data.lock.is_lab_locked(student, lab) if type(student) is not str else False
    student_index = window.create_filtered_list(students, "Student", filter_function=data.Student.find, draw_function=line_lock)
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

        if second_submission.flag == data.model.SubmissionFlag.NO_SUBMISSION:
            msg = [f"{student.full_name} has not submitted"]
            window.create_popup("No Submissions", msg)

            data.lock.unlock_lab(student, lab)
            return

        options = [first_submission.student.full_name, second_submission.student.full_name, "View Diff", "Done"]

        msg = [f"{first_submission.student.full_name} {first_submission.latest_submission}",
               f"{second_submission.student.full_name} {second_submission.latest_submission}",
               "", "Pick a student's submission to view or view the diff"]

        window.set_header("Pair Programming Submission")
        while True:
            option = window.create_options_popup("Pair Programming", msg, options)

            if option == first_submission.student.full_name:
                pair_programming_submission_callback(first_submission)
            elif option == second_submission.student.full_name:
                pair_programming_submission_callback(second_submission)
            elif option == "View Diff":
                view_diff(first_submission, second_submission)
            else:
                break

        data.lock.unlock_lab(student, lab)
    except KeyboardInterrupt:
        data.lock.unlock_lab(student, lab)
    except curses.error:
        data.lock.unlock_lab(student, lab)
    except Exception:
        data.lock.unlock_lab(student, lab)

def flag_submission(lab, student):
    window = Window.get_window()

    note = window.create_text_input("Flag Note")
    if note == UI_GO_BACK:
        return

    data.flags.flag_submission(student, lab, note)

def student_callback(lab, student_index, use_locks=True):
    window = Window.get_window()
    window.set_header("Student Submission")

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

        # Unlock if student has not submitted
        if submission.flag == data.model.SubmissionFlag.NO_SUBMISSION:
            msg = [f"{student.full_name} has not submitted"]
            window.create_popup("No Submissions", msg)

            if use_locks:
                data.lock.unlock_lab(student, lab)
            return

        options = ["Flag", "Pick Submission", "Run", "View", "Done"]
        if use_locks:
            options.insert(2, "Pair Programming")

        # Add option to diff parts if this lab requires it
        if submission.flag & data.model.SubmissionFlag.DIFF_PARTS:
            options.insert(1, "Diff Parts")

        while True:
            option = window.create_options_popup("Submission", submission.msg, options, components.Popup.ALIGN_LEFT)

            if option == "Pair Programming":
                grade_pair_programming(submission)
            elif option == "Run":
                if not submission.compile_and_run_code():
                    window.create_popup("Error", ["Could not compile and run code"])
            elif option == "View":
                submission.show_files()
            elif option == "Diff Parts":
                submission.diff_parts()
            elif option == "Pick Submission":
                pick_submission(lab, student, submission)
            elif option == "Flag":
                flag_submission(lab, student)
                break
            else:
                break

        config.g_data.running_process = None

        # After popup, unlock student
        if use_locks:
            data.lock.unlock_lab(student, lab)
    except (KeyboardInterrupt, curses.error):
        if use_locks:
            data.lock.unlock_lab(student, lab)

def color_student_lines(lab, student):
    if data.lock.is_lab_locked(student, lab) and type(student) is not str:
        return curses.color_pair(2)
    elif data.flags.is_submission_flagged(student, lab) and type(student) is not str:
        return curses.color_pair(7)
    return curses.color_pair(0)

def lab_callback(lab_index, use_locks=True):
    window = Window.get_window()

    lab = data.get_labs()[lab_index]

    students = data.get_students()

    # Get student
    draw = lambda student: color_student_lines(lab, student)
    window.create_filtered_list(students, "Student", \
        lambda student_index : student_callback(lab, student_index, use_locks), data.Student.find, draw_function=draw)

def grade(use_locks=True):
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
    window.create_filtered_list(labs, "Assignment", lambda lab_index : lab_callback(lab_index, use_locks), data.Lab.find)
