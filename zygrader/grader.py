import curses
import difflib
import getpass
import io
import os
import subprocess
import tempfile

from . import config
from . import data
from . import logger

from .ui import components
from .ui.window import Window
from .zybooks import Zybooks

def get_submission(lab, student):
    window = Window.get_window()
    zy_api = Zybooks()

    # Lock student
    data.lock.lock_lab(student, lab)
    # Update the window to draw the student in red
    window.draw()

    submission_response = zy_api.download_assignment(student, lab)
    submission = data.model.Submission(student, lab, submission_response)

    # Report missing files
    if submission.flag & data.model.Submission.BAD_ZIP_URL:
        msg = [f"One or more URLs for {student.full_name}'s code submission are bad.",
               "Some files could not be downloaded. Please",
               "View the most recent submission on zyBooks."]
        window.create_popup("Warning", msg)

    return submission

def diff_submissions(first, second):
    diffs = {}

    name_a = first.student.full_name
    name_b = second.student.full_name

    # Read lines into two dictionaries
    for file_name in os.listdir(first.files_directory):
        with open(os.path.join(first.files_directory, file_name), 'r') as file_a:
            with open(os.path.join(second.files_directory, file_name), 'r') as file_b:
                html = difflib.HtmlDiff(4, 80)
                diff = html.make_file(file_a.readlines(), file_b.readlines(), name_a, name_b, context=True)

                diffs[file_name] = diff

    return diffs

def pair_programming_submission_callback(submission):
    window = Window.get_window()

    options = ["Open Folder", "Run", "View", "Done"]
    while True:
        option = window.create_options_popup("Downloaded", submission.msg, options, components.Popup.ALIGN_LEFT)

        if option == "View":
            submission.show_files()
        elif option == "Open Folder":
            submission.open_folder()
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
    line_lock = lambda student : data.lock.is_lab_locked(student, lab) if type(student) is not str else False
    student = window.filtered_list(students, "Student", filter_function=data.Student.find, draw_function=line_lock)

    if data.lock.is_lab_locked(student, lab):
        netid = data.lock.get_locked_netid(student, lab)

        msg = [f"This student is already being graded by {netid}"]
        window.create_popup("Student Locked", msg)
        return

    try:
        second_submission = get_submission(lab, student)

        if second_submission.flag == data.model.Submission.NO_SUBMISSION:
            msg = [f"{student.full_name} has not submitted"]
            window.create_popup("No Submissions", msg)

            data.lock.unlock_lab(student, lab)
            return

        # Diff the two students
        diffs = diff_submissions(first_submission, second_submission)

        tmp_dir = tempfile.mkdtemp()
        with open(f"{os.path.join(tmp_dir, 'submissions.html')}", 'w') as diff_file:
            for diff in diffs:
                diff_file.write(f"<h1>{diff}</h1>")
                diff_file.write(diffs[diff])

        options = [first_submission.student.full_name, second_submission.student.full_name, "View Diff", "Done"]
        msg = ["Pick a student's submission to view", "or view the diff"]
        while True:
            option = window.create_options_popup("Pair Programming", msg, options)

            if option == first_submission.student.full_name:
                pair_programming_submission_callback(first_submission)
            elif option == second_submission.student.full_name:
                pair_programming_submission_callback(second_submission)
            elif option == "View Diff":
                # Open diffs in favorite browser
                subprocess.Popen(f"xdg-open {os.path.join(tmp_dir, 'submissions.html')}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                break

        data.lock.unlock_lab(student, lab)
    except KeyboardInterrupt:
        data.lock.unlock_lab(student, lab)
    except curses.error:
        data.lock.unlock_lab(student, lab)
    except Exception:
        data.lock.unlock_lab(student, lab)

def student_callback(lab, student):
    window = Window.get_window()
    # Wait for student's assignment to be available
    if data.lock.is_lab_locked(student, lab):
        netid = data.lock.get_locked_netid(student, lab)

        # If being graded by the user who locked it, allow grading
        if netid != getpass.getuser():
            msg = [f"This student is already being graded by {netid}"]
            window.create_popup("Student Locked", msg)
            return

    try:
        # Get the student's submission
        submission = get_submission(lab, student)

        # Unlock if student has not submitted
        if submission.flag == data.model.Submission.NO_SUBMISSION:
            msg = [f"{student.full_name} has not submitted"]
            window.create_popup("No Submissions", msg)

            data.lock.unlock_lab(student, lab)
            return

        options = ["Open Folder", "Pair Programming", "Run", "View", "Done"]

        # Add option to diff parts if this lab requires it
        if submission.flag & data.model.Submission.DIFF_PARTS:
            options.insert(1, "Diff Parts")

        while True:
            option = window.create_options_popup("Downloaded", submission.msg, options, components.Popup.ALIGN_LEFT)

            if option == "Pair Programming":
                grade_pair_programming(submission)
            elif option == "Run":
                if not submission.compile_and_run_code():
                    window.create_popup("Error", ["Could not compile and run code"])
            elif option == "View":
                submission.show_files()
            elif option == "Open Folder":
                submission.open_folder()
            elif option == "Diff Parts":
                submission.diff_parts()
            else:
                break

        config.g_data.running_process = None

        # After popup, unlock student
        data.lock.unlock_lab(student, lab)
    except KeyboardInterrupt:
        data.lock.unlock_lab(student, lab)
    except curses.error:
        data.lock.unlock_lab(student, lab)
    except Exception:
        data.lock.unlock_lab(student, lab)


def lab_callback(lab):
    window = Window.get_window()
    students = data.get_students()

    # Get student
    line_lock = lambda student : data.lock.is_lab_locked(student, lab) if type(student) is not str else False
    window.filtered_list(students, "Student", lambda student : student_callback(lab, student), data.Student.find, draw_function=line_lock)

def grade():
    window = Window.get_window()
    labs = data.get_labs()

    if not labs:
        window.create_popup("Error", ["No labs have been created yet"])
        return

    # Pick a lab
    window.filtered_list(labs, "Assignment", lab_callback, data.Lab.find)
