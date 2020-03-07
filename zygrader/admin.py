import os
import time
import json
import requests
import zipfile
import io

from .ui.window import Window
from .ui import UI_GO_BACK
from .zybooks import Zybooks
from . import data
from . import config
from . import class_manager

def check_student_submissions(zy_api, student_id, lab, search_string):
    """Search for a substring in all of a student's submissions for a given lab"""
    submission_response = zy_api.get_all_submissions(lab["id"], student_id)

    if not submission_response.ok:
        return {"code": Zybooks.NO_SUBMISSION}

    all_submissions = submission_response.json()["submissions"]

    response = {"code": Zybooks.NO_SUBMISSION}

    for submission in all_submissions:
        # Get file from zip url
        try:
            zip_file = zy_api.get_submission_zip(submission["zip_location"])
        except requests.exceptions.ConnectionError:
            # Bad connection, wait a few seconds and try again
            return {"code": Zybooks.DOWNLOAD_TIMEOUT}

        # If there was an error
        if zip_file == Zybooks.ERROR:
            response["error"] = f"Error fetching submission {zy_api.get_time_string(submission)}"
            continue

        f = zy_api.extract_zip(zip_file)

        # Check each file for the matched string
        for source_file in f.keys():
            if f[source_file].find(search_string) != -1:

                # Get the date and time of the submission and return it
                response["time"] = zy_api.get_time_string(submission)
                response["code"] = Zybooks.NO_ERROR

                return response

    return response

def submission_search(lab, search_string, output_path):
    window = Window.get_window()
    students = data.get_students()
    zy_api = Zybooks()

    logger = window.new_logger()

    with open(output_path, "w") as log_file:
        student_num = 1

        for student in students:
            while True:
                counter = f"[{student_num}/{len(students)}]"
                logger.log(f"{counter:12} Checking {student.full_name}")

                match_result = check_student_submissions(zy_api, str(student.id), lab, search_string)

                if match_result["code"] == Zybooks.DOWNLOAD_TIMEOUT:
                    logger.log("Download timed out... trying again after a few seconds")
                    log_file.write("Download timed out... trying again after a few seconds\n")
                    time.sleep(5)
                else:
                    break

            if match_result["code"] == Zybooks.NO_ERROR:
                log_file.write(f"{student.full_name} matched {match_result['time']}\n")

                logger.append(f" found {search_string}")

            # Check for and log errors
            if "error" in match_result:
                log_file.write(f"ERROR on {student.full_name}: {match_result['error']}\n")

            student_num += 1

        window.remove_logger(logger)


def submission_search_init(window, labs):
    """Get lab part and string from the user for searching"""
    # Choose lab
    assignment_index = window.filtered_list(labs, "Assignment", filter_function=data.Lab.find)
    if assignment_index is UI_GO_BACK:
        return

    assignment = labs[assignment_index]

    # Select the lab part if needed
    if len(assignment.parts) > 1:
        part_index = window.filtered_list([name["name"] for name in assignment.parts], "Part")
        if part_index is UI_GO_BACK:
            return
        part = assignment.parts[part_index]
    else:
        part = assignment.parts[0]

    search_string = window.text_input("Enter a search string")
    if search_string == Window.CANCEL:
        return

    # Get a valid output path
    while True:
        output_path = window.text_input("Enter the output path including filename [~ is supported]")
        if output_path == Window.CANCEL:
            return

        output_path = os.path.expanduser(output_path)
        if os.path.exists(os.path.dirname(output_path)):
            break

        msg = [f"Path {os.path.dirname(output_path)} does not exist!"]
        window.create_popup("Invalid Path", msg)

    # Run the submission search
    submission_search(part, search_string, output_path)

admin_menu_options = ["Submissions Search", "Remove Locks", "Class Management"]

def admin_menu_callback(menu_index):
    window = Window.get_window()

    option = admin_menu_options[menu_index]

    if option == "Submissions Search":
        labs = data.get_labs()

        submission_search_init(window, labs)
    elif option == "Remove Locks":
        while True:
            all_locks = data.lock.get_lock_files()
            lock_index = window.filtered_list(all_locks, "Choose a lock file")
            if lock_index != UI_GO_BACK:
                data.lock.remove_lock_file(all_locks[lock_index])
            else:
                break
    elif option == "Class Management":
        class_manager.start()

def admin_menu():
    window = Window.get_window()

    window.filtered_list(admin_menu_options, "Option", admin_menu_callback)
