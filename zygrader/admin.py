"""Admin: Functions for more "administrator" users of zygrader to manage
the class, scan through student submissions, and access to other menus"""
import time
import requests

from zygrader.ui.templates import filename_input
from zygrader.zybooks import Zybooks
from zygrader import ui
from zygrader import data
from zygrader import class_manager
from zygrader import grade_puller
from zygrader import utils


def check_student_submissions(zy_api, student_id, lab, search_string):
    """Search for a substring in all of a student's submissions for a given lab"""
    response = {"code": Zybooks.NO_SUBMISSION}

    all_submissions = zy_api.get_all_submissions(lab["id"], student_id)
    if not all_submissions:
        return response

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

        extracted_zip_files = utils.extract_zip(zip_file)

        # Check each file for the matched string
        for source_file in extracted_zip_files.keys():
            if extracted_zip_files[source_file].find(search_string) != -1:

                # Get the date and time of the submission and return it
                response["time"] = zy_api.get_time_string(submission)
                response["code"] = Zybooks.NO_ERROR

                return response

    return response


def submission_search(lab, search_string, output_path):
    """Search through student submissions for a given string

    This is used mainly to look for suspicious code (cheaters)"""
    window = ui.get_window()
    students = data.get_students()
    zy_api = Zybooks()

    logger = window.new_logger()

    with open(output_path, "w") as log_file:
        student_num = 1

        for student in students:
            while True:
                counter = f"[{student_num}/{len(students)}]"
                logger.log(f"{counter:12} Checking {student.full_name}")

                match_result = check_student_submissions(
                    zy_api, str(student.id), lab, search_string
                )

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

        window.remove_logger()


def submission_search_init(window, labs):
    """Get lab part and string from the user for searching"""
    window.set_header("Submissions Search")

    # Choose lab
    assignment_index = window.create_filtered_list(
        "Assignment", input_data=labs, filter_function=data.Lab.find
    )
    if assignment_index is ui.GO_BACK:
        return

    assignment = labs[assignment_index]

    # Select the lab part if needed
    if len(assignment.parts) > 1:
        part_index = window.create_list_popup(
            "Select Part", input_data=[name["name"] for name in assignment.parts]
        )
        if part_index is ui.GO_BACK:
            return
        part = assignment.parts[part_index]
    else:
        part = assignment.parts[0]

    search_string = window.create_text_input("Search String", "Enter a search string")
    if search_string == ui.Window.CANCEL:
        return

    # Get a valid output path
    output_path = filename_input(purpose="the output")
    if output_path is None:
        return

    # Run the submission search
    submission_search(part, search_string, output_path)


ADMIN_MENU_OPTIONS = [
    "Submissions Search",
    "Grade Puller",
    "Find Unmatched Students",
    "Remove Locks",
    "Class Management",
]


def admin_menu_callback(context: ui.WinContext):
    """Run the chosen option on the admin menu"""
    menu_index = context.data

    option = ADMIN_MENU_OPTIONS[menu_index]

    if option == "Submissions Search":
        labs = data.get_labs()

        submission_search_init(context.window, labs)
    elif option == "Grade Puller":
        grade_puller.GradePuller().pull()
    elif option == "Find Unmatched Students":
        grade_puller.GradePuller().find_unmatched_students()
    elif option == "Remove Locks":
        while True:
            all_locks = data.lock.get_lock_files()
            lock_index = context.window.create_filtered_list(
                "Choose a lock file", input_data=all_locks
            )
            if lock_index != ui.GO_BACK:
                data.lock.remove_lock_file(all_locks[lock_index])
            else:
                break
    elif option == "Class Management":
        class_manager.start()


def admin_menu():
    """Create the admin menu"""
    window = ui.get_window()
    window.set_header("Admin")

    window.create_filtered_list(
        "Option", input_data=ADMIN_MENU_OPTIONS, callback=admin_menu_callback
    )
