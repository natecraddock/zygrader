"""
utils.py

General algorithms/utilties to be shared between modules
"""

import curses
import difflib
import os
import subprocess
from subprocess import PIPE, STDOUT, DEVNULL
import tempfile

from .ui.window import Window
from .ui import components, UI_GO_BACK
from . import data


def diff_files(first, second, title_a, title_b, use_html):
    """Given two lists of equal length containing file paths, return a diff of each pair of files"""
    diffs = {}

    num_files = len(first)

    for index in range(num_files):
        path_a = first[index]
        path_b = second[index]

        file_name = os.path.splitext(os.path.basename(path_a))[0]

        diff_name = f"{file_name} - {title_a} against {title_b}"

        diff = ""
        if use_html:
            with open(path_a, 'r') as file_a:
                with open(path_b, 'r') as file_b:
                    html = difflib.HtmlDiff(4, 80)
                    diff = html.make_file(file_a.readlines(), file_b.readlines(), title_a, title_b, context=True)
        else:
            p = subprocess.Popen(f"diff -w -u --color=always {path_a} {path_b}", shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            diff = str(p.communicate()[0])

        diffs[diff_name] = diff

    return diffs

def make_diff_string(first, second, title_a, title_b, use_html=False):
    """Given to lists of equal length containing file paths, return a string containing the diffs"""
    diffs = diff_files(first, second, title_a, title_b, use_html)

    diff_str = ""

    for diff in diffs:
        if use_html:
            diff_str += f"<h1>{diff}</h1>\n"
        else:
            diff_str += f"\n\nFILE: {diff}\n"
        diff_str += diffs[diff]

    return diff_str

def view_string(string, file_name, use_html=False):
    """Given a string, open in `less` or the grader's default browser"""

    tmp_dir = tempfile.mkdtemp()
    file_path = f"{os.path.join(tmp_dir, file_name)}"

    with open(file_path, 'w') as _file:
        _file.write(string)

    if use_html:
        subprocess.Popen(f"xdg-open {file_path}", shell=True, stdout=DEVNULL, stderr=DEVNULL)
    else:
        curses.endwin()
        subprocess.run(["less", "-r", f"{file_path}"])
        curses.initscr()

def extract_zip(input_zip, file_prefix=None):
    """Given a ZipFile object, return a dictionary of the files of the form
        {"filename": "contents...", ...}
    """
    if file_prefix:
        return {f"{file_prefix}_{name}": input_zip.read(name).decode('UTF-8') for name in input_zip.namelist()}
    else:
        return {f"{name}": input_zip.read(name).decode('UTF-8') for name in input_zip.namelist()}

def get_source_file_paths(directory):
    paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            paths.append(os.path.join(root, file))
    return paths

def prep_lab_score_calc():
    window = Window.get_window()
    window.set_header("Prep Lab Calculator")

    try:
        old_score = float(window.create_text_input("What was the student's original score"))
        if old_score == Window.CANCEL:
            return
        current_completion = float(window.create_text_input("What is the student's current completion % in zyBooks", "100"))
        if current_completion == Window.CANCEL:
            return

        new_score = old_score + ((current_completion - old_score) * 0.6)
        window.create_popup("New Score", [f"The student's new score is: {new_score}"])
    except ValueError:
        window.create_popup("Error", ["Invalid input"])

def view_students_callback(student_index):
    window = Window.get_window()
    students = data.get_students()

    student = students[student_index]

    msg = [f"Name: {student.full_name}", f"Email: {student.email}", f"Section: {student.section}", f"ID: {student.id}"]
    window.create_popup("Student Info", msg, components.Popup.ALIGN_LEFT)

def view_students():
    window = Window.get_window()
    students = data.get_students()
    window.set_header("View Students")

    window.create_filtered_list(students, "Student Name", callback=view_students_callback)
