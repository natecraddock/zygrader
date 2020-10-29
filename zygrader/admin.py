"""Admin: Functions for more "administrator" users of zygrader to manage
the class, scan through student submissions, and access to other menus"""
import time

import requests
import re

from zygrader import class_manager, data, grade_puller, ui, utils
from zygrader.zybooks import Zybooks


def check_student_submissions(zy_api, student_id, lab, search_string):
    """Search for a substring in all of a student's submissions for a given lab.
    Supports regular expressions.
    """
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
            response[
                "error"] = f"Error fetching submission {zy_api.get_time_string(submission)}"
            continue

        extracted_zip_files = utils.extract_zip(zip_file)

        # Check each file for the matched string
        pattern = re.compile(fr'{search_string}')
        for source_file in extracted_zip_files.keys():
            if pattern.search(extracted_zip_files[source_file]):

                # Get the date and time of the submission and return it
                response["time"] = zy_api.get_time_string(submission)
                response["code"] = Zybooks.NO_ERROR

                return response

    return response


def submission_search_fn(logger, lab, search_string, output_path):
    students = data.get_students()
    zy_api = Zybooks()

    with open(output_path, "w") as log_file:
        student_num = 1

        for student in students:
            while True:
                counter = f"[{student_num}/{len(students)}]"
                logger.log(f"{counter:12} Checking {student.full_name}")

                match_result = check_student_submissions(
                    zy_api, str(student.id), lab, search_string)

                if match_result["code"] == Zybooks.DOWNLOAD_TIMEOUT:
                    logger.log(
                        "Download timed out... trying again after a few seconds"
                    )
                    log_file.write(
                        "Download timed out... trying again after a few seconds\n"
                    )
                    time.sleep(5)
                else:
                    break

            if match_result["code"] == Zybooks.NO_ERROR:
                log_file.write(
                    f"{student.full_name} matched {match_result['time']}\n")

                logger.append(f" found {search_string}")

            # Check for and log errors
            if "error" in match_result:
                log_file.write(
                    f"ERROR on {student.full_name}: {match_result['error']}\n")

            student_num += 1


def submission_search_init():
    """Get lab part and string from the user for searching"""
    window = ui.get_window()
    labs = data.get_labs()

    menu = ui.layers.ListLayer()
    menu.set_searchable("Assignment")
    for lab in labs:
        menu.add_row_text(str(lab))
    window.run_layer(menu, "Submissions Search")
    if menu.was_canceled():
        return

    assignment = labs[menu.selected_index()]

    # Select the lab part if needed
    if len(assignment.parts) > 1:
        popup = ui.layers.ListLayer("Select Part", popup=True)
        for part in assignment.parts:
            popup.add_row_text(part["name"])
        window.run_layer(popup, "Submissions Search")
        if popup.was_canceled():
            return

        part = assignment.parts[popup.selected_index()]
    else:
        part = assignment.parts[0]

    text_input = ui.layers.TextInputLayer("Search String")
    text_input.set_prompt(["Enter a search string"])
    window.run_layer(text_input, "Submissions Search")
    if text_input.was_canceled():
        return

    search_string = text_input.get_text()

    # Get a valid output path
    filename_input = ui.layers.PathInputLayer("Output File")
    filename_input.set_prompt(["Enter the filename to save the search results"])
    window.run_layer(filename_input, "Submissions Search")
    if filename_input.was_canceled():
        return

    logger = ui.layers.LoggerLayer()
    logger.set_log_fn(lambda _: submission_search_fn(
        logger, part, search_string, filename_input.get_path()))
    window.run_layer(logger, "Submission Search")


class LockToggle(ui.layers.Toggle):
    def __init__(self, name, list):
        super().__init__()
        self.__name = name
        self.__list = list
        self.get()

    def toggle(self):
        self.__list[self.__name] = not self.__list[self.__name]
        self.get()

    def get(self):
        self._toggled = self.__list[self.__name]


def remove_locks():
    window = ui.get_window()
    all_locks = {lock: False for lock in data.lock.get_lock_files()}

    popup = ui.layers.ListLayer("Select Locks to Remove", popup=True)
    popup.set_exit_text("Confirm")
    for lock in all_locks:
        popup.add_row_toggle(lock, LockToggle(lock, all_locks))
    window.run_layer(popup)

    selected_locks = [lock for lock in all_locks if all_locks[lock]]

    if not selected_locks or popup.was_canceled():
        return

    # Confirm
    popup = ui.layers.BoolPopup("Confirm Removal")
    popup.set_message(
        [f"Are you sure you want to remove {len(selected_locks)} lock(s)?"])
    window.run_layer(popup)
    if not popup.get_result() or popup.was_canceled():
        return

    # Remove selected locked content
    for lock in selected_locks:
        if lock:
            data.lock.remove_lock_file(lock)


def admin_menu():
    """Create the admin menu"""
    window = ui.get_window()

    menu = ui.layers.ListLayer()
    menu.add_row_text("Submissions Search", submission_search_init)
    menu.add_row_text("Grade Puller", grade_puller.GradePuller().pull)
    menu.add_row_text("Find Unmatched Students",
                      grade_puller.GradePuller().find_unmatched_students)
    menu.add_row_text("Remove Locks", remove_locks)
    menu.add_row_text("Class Management", class_manager.start)

    window.register_layer(menu, "Admin")
