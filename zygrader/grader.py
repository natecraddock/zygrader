import io
import os
import zipfile
import requests
import tempfile
import subprocess
import curses
import difflib

from . import data

from .ui import components
from .ui.window import Window
from .zyscrape import Zyscrape
from . import config

def get_submission(lab, student):
    window = Window.get_window()
    scraper = Zyscrape()

    # Lock student
    data.lock.lock_lab(student, lab)
    # Update the window to draw the student in red
    window.draw()

    submission_response = scraper.download_assignment(student, lab)
    return data.model.Submission(student, lab, submission_response)

def diff_submissions(first, second):
    window = Window.get_window()


    pass

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

    second_submission = get_submission(lab, student)

    if second_submission.flag == data.model.Submission.NO_SUBMISSION:
        msg = [f"{student.full_name} has not submitted"]
        window.create_popup("No Submissions", msg)

        data.lock.unlock_lab(student, lab)
        return

    # Diff the two students
    diff_submissions(first_submission, second_submission)

def student_callback(lab, student):
    window = Window.get_window()
    # Wait for student's assignment to be available
    if data.lock.is_lab_locked(student, lab):
        netid = data.lock.get_locked_netid(student, lab)

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

        submission.show_files()

        options = ["Open Folder", "Pair Programming", "Done"]
        while True:
            option = window.create_options_popup("Downloaded", submission.msg, options, components.Popup.ALIGN_LEFT)

            if option == "Pair Programming":
                grade_pair_programming(submission)
            elif option == "Open Folder":
                submission.open_folder()
            else:
                break

        # After popup, unlock student
        data.lock.unlock_lab(student, lab)
    except KeyboardInterrupt:
        data.lock.unlock_lab(student, lab)
    except curses.error:
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

    # Pick a lab
    window.filtered_list(labs, "Assignment", lab_callback, data.Lab.find)
