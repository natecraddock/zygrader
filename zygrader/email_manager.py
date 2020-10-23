"""Email: Manage locking of student emails from zygrader to prevent double-answering."""

import curses
import getpass

from zygrader import data
from zygrader import ui


def lock_student_callback(student):
    window = ui.get_window()

    if data.lock.is_locked(student):
        netid = data.lock.get_locked_netid(student)
        if netid != getpass.getuser():
            msg = [f"{netid} is replying to {student.first_name}'s email"]
            popup = ui.layers.Popup("Student Locked", msg)
            window.run_layer(popup)
            return

    try:
        data.lock.lock(student)
        msg = [f"You have locked {student.full_name} for emailing."]
        popup = ui.layers.Popup("Student Locked", msg)
        window.run_layer(popup)
    finally:
        data.lock.unlock(student)


def watch_students(student_list, students):
    """Register paths when the filtered list is created"""
    paths = [data.SharedData.get_locks_directory()]
    data.fs_watch.fs_watch_register(paths, "student_email_list_watch",
                                    fill_student_list, student_list, students)


def get_student_row_color_sort_index(student):
    if data.lock.is_locked(student):
        return curses.color_pair(2), 0
    return curses.color_pair(1), 1


def fill_student_list(student_list: ui.layers.ListLayer, students):
    student_list.clear_rows()
    for student in students:
        row = student_list.add_row_text(str(student), lock_student_callback,
                                        student)
        color, sort_index = get_student_row_color_sort_index(student)
        row.set_row_color(color)
        row.set_row_sort_index(sort_index)
    student_list.rebuild = True


def email_menu():
    """Show the list of students with auto-update and locking."""
    window = ui.get_window()
    students = data.get_students()

    student_list = ui.layers.ListLayer()
    student_list.set_searchable("Student")
    student_list.set_sortable()
    fill_student_list(student_list, students)
    watch_students(student_list, students)
    window.register_layer(student_list, "Email Manager")
