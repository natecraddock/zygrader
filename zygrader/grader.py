import io
import os
import zipfile
import requests
import tempfile
import subprocess
import curses

from . import data

from .ui import components
from .ui.window import Window
from .zyscrape import Zyscrape
from . import config

def extract_zip(file_prefix, input_zip):
    if file_prefix:
        return {f"{file_prefix}_{name}": input_zip.read(name).decode('UTF-8') for name in input_zip.namelist()}
    else:
        return {f"{name}": input_zip.read(name).decode('UTF-8') for name in input_zip.namelist()}

def open_files(window: Window, submission):
    # Don't actually delete the temporary directory,
    # Let the system handle it
    tmp_dir =  tempfile.mkdtemp()

    for part in submission["parts"]:
        if part["code"] == Zyscrape.NO_SUBMISSION:
            continue
        r = requests.get(part["zip_url"])
        z = zipfile.ZipFile(io.BytesIO(r.content))
        zip_files = extract_zip(part["name"], z)

        for source_file in zip_files.keys():
            with open(os.path.join(tmp_dir, source_file), 'w') as source_out:
                source_out.write(zip_files[source_file])

    user_editor = config.user.get_config()["editor"]
    editor_path = config.user.EDITORS[user_editor]
    subprocess.Popen(f"{editor_path} {tmp_dir}/*", shell=True)

def student_callback(lab, student):
    window = Window.get_window()
    scraper = Zyscrape()

    # Wait for student's assignment to be available
    if data.lock.is_lab_locked(student, lab):
        netid = data.lock.get_locked_netid(student, lab)

        msg = [f"This student is already being graded by {netid}"]
        window.create_popup("Student Locked", msg)
        return

    try:
        # Lock student for grading
        data.lock.lock_lab(student, lab)
        window.draw()

        submission = scraper.download_assignment(str(student.id), lab)

        # Only grade if student has submitted
        if submission["code"] is Zyscrape.NO_SUBMISSION:
            msg = [f"{student.full_name} has not submitted"]
            window.create_popup("No Submissions", msg)

            data.lock.unlock_lab(student, lab)
            return

        open_files(window, submission)

        msg = [f"{student.full_name}'s submission downloaded", ""]

        for part in submission["parts"]:
            if part["code"] == Zyscrape.NO_SUBMISSION:
                msg.append(f"{part['name']:4} No Submission")
            else:
                score = f"{part['score']}/{part['max_score']}"

                if part["name"]:
                    msg.append(f"{part['name']:4} {score:8} {part['date']}")
                else:
                    msg.append(f"{score:8} {part['date']}")

                if part["code"] == Zyscrape.COMPILE_ERROR:
                    msg[-1] += f" [Compile Error]"

        msg.append("")
        msg.append(f"Total Score: {submission['score']}/{submission['max_score']}")

        window.create_popup("Downloaded", msg, components.Popup.ALIGN_LEFT)

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
