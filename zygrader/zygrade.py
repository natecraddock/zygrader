import os
import io
import zipfile
import requests
import tempfile
import subprocess
import curses
import sys

from . import data

from .data import load_students, load_assignments
from .data.model import Lab
from .data.model import Student

from . import config

from .zyscrape import Zyscrape

from .ui import window
from .ui.window import Window

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
        r = requests.get(part["zip_url"])
        z = zipfile.ZipFile(io.BytesIO(r.content))
        zip_files = extract_zip(part["name"], z)

        for source_file in zip_files.keys():
            with open(os.path.join(tmp_dir, source_file), 'w') as source_out:
                source_out.write(zip_files[source_file])
    
    # TODO: Custom text editor
    subprocess.Popen(f"/usr/bin/pluma {tmp_dir}/*", shell=True)

def grade(window: Window, scraper, students, assignments):
    while True:
        # Choose lab
        assignment = window.filtered_list(assignments, "Assignment", Lab.find)
        if assignment is 0:
            break

        while True:
            # Get student
            student = window.filtered_list(students, "Student", Student.find)
            if student is 0:
                break

            # Wait for student's assignment to be available
            if data.lock.is_lab_locked(student, assignment):
                msg = ["This student is already being graded"]
                window.create_popup("Sorry...", msg)
                continue
            
            try:
                # Lock student for grading
                data.lock.lock_lab(student, assignment)

                submission = scraper.download_assignment(str(student.id), assignment)

                open_files(window, submission)

                msg = [f"{student.full_name}'s submission downloaded", ""]

                for part in submission["parts"]:
                    msg.append(f"{part['name']} {part['score']}/{part['max_score']} {part['date']}")
                msg.append("")
                msg.append(f"Total Score: {submission['score']}/{submission['max_score']}")

                window.create_popup("Downloaded", msg)

                # After popup, unlock student
                data.lock.unlock_lab(student, assignment)
            except KeyboardInterrupt:
                data.lock.unlock_lab(student, assignment)
            except curses.error:
                data.lock.unlock_lab(student, assignment)

def config_menu(window: Window, scraper, config_file):
    if config_file["password"]:
        password_option = "Remove Saved Password"
    else:
        password_option = "Save Password"
    
    options = ["Change Credentials", password_option, "Back"]
    option = ""

    while option != "Back":
        window.set_header(f"Config | {config_file['email']}")
        option = window.menu_input(options)

        if option == "Change Credentials":
            email, password = config.user.create_account(window, scraper)
            save_password = window.create_bool_popup("Save Password", ["Would you like to save your password?"])

            config_file["email"] = email

            if save_password:
                config.user.encode_password(config_file, password)

            config.user.write_config(config_file)

        elif option == "Save Password":
            # First, get password and verify it is correct
            email = config_file["email"]
            while True:
                password = config.user.get_password(window)

                if config.user.authenticate(window, scraper, email, password):
                    config.user.encode_password(config_file, password)
                    config.user.write_config(config_file)
                    break
            
            window.create_popup("Saved Password", ["Password successfully saved"])

        elif option == "Remove Saved Password":
            config_file["password"] = ""
            config.user.write_config(config_file)

            window.create_popup("Removed Password", ["Password successfully removed"])

def other_menu(window: Window, students, assignments):
    scraper = Zyscrape()

    # Choose lab
    assignment = window.filtered_list(assignments, Lab.find)
    if assignment is 0:
        return

    # Select the lab part if needed
    if len(assignment.parts) > 1:
        p = window.filtered_list([name for name in assignment.parts])
        if p is 0:
            return
        part = assignment.parts[assignment.parts.index(p)]
    else:
        part = assignment.parts[0]

    search_string = window.text_input("Enter a search string")

    print(search_string)

    matches = []

    f = open("test.txt", "a")
    for student in students:
        if scraper.check_submissions(str(student.id), part, search_string):
            matches.append(student)
            f.write(student.full_name)
            f.write("\n")
            print(student.full_name)

""" Main program loop """
def mainloop(window: Window, scraper, students, assignments, config, admin_mode):
    if admin_mode:
        options = ["Grade", "Config", "String Match", "Quit"]
    else:
        options = ["Grade", "Config", "Quit"]
    option = ""

    while option != "Quit":
        window.set_header(f"Menu | {config['email']}")
        option = window.menu_input(options)

        if option == "Grade":
            grade(window, scraper, students, assignments)
        elif option == "Config":
            config_menu(window, scraper, config)
        elif option == "String Match":
            other_menu(window, students, assignments)

""" zygrade startpoint """
def main(window: Window):
    # Read args to set admin mode
    if "-a" in sys.argv:
        admin = True
    else:
        admin = False

    # TODO: apply versioning

    # Load student and lab data
    students = load_students(config.zygrader.STUDENT_DATA)
    assignments = load_assignments(config.zygrader.LABS_DATA)
    
    # Ensure config directories exist
    config.zygrader.start()

    # Get user configuration
    config_data = config.user.initial_config(window)

    scraper = Zyscrape()
    mainloop(window, scraper, students, assignments, config_data, admin)

def start():
    # Create a zygrader window
    Window(main, "zygrader")
