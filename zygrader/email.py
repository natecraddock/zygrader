"""Email: Manage locking of student emails from zygrader to prevent double-answering."""

import curses
import getpass

from zygrader.grader import update_student_list
from zygrader import data
from zygrader import ui

def lock_student_callback(context: ui.WinContext):
    window: ui.Window = context.window
    student = data.get_students()[context.data]

    if data.lock.is_locked(student):
        netid = data.lock.get_locked_netid(student)
        if (netid != getpass.getuser()):
            msg = [f"{netid} is replying to {student.first_name}'s email"]
            window.create_popup("Student Locked", msg)
            return

    try:
        data.lock.lock(student)
        msg = [f"You have locked {student.full_name} for emailing."]
        window.create_popup("Student Locked", msg)
    finally:
        data.lock.unlock(student)

def fill_student_list(students):
    lines = []
    for i, student in enumerate(students):
        line = ui.components.FilteredList.ListLine(i + 1, student)
        if (data.lock.is_locked(student)):
            line.color = curses.color_pair(2)
            lines.insert(0, line)
        else:
            line.color = curses.color_pair(1)
            lines.append(line)
    return lines

def update_student_list(window: ui.Window, student_list: ui.components.FilteredList):
    """Update the list of students when the locks change"""
    student_list.refresh()
    window.push_refresh_event()

def watch_students(window: ui.Window, student_list: ui.components.FilteredList):
    """Register paths when the filtered list is created"""
    paths = [data.SharedData.get_locks_directory()]

    update_list = lambda _: update_student_list(window, student_list)
    data.fs_watch.fs_watch_register(paths, "student_email_list_watch", update_list)

def email_menu():
    """Show the list of students with auto-update and locking."""
    window = ui.get_window()
    students = data.get_students()

    window.set_header("Email Manager")

    window.create_filtered_list("Student Name", list_fill=lambda: fill_student_list(students),
                                callback=lock_student_callback, filter_function=data.Student.find,
                                create_fn=lambda student_list: watch_students(window, student_list))
