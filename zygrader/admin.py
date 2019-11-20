import os

from .ui.window import Window
from .zyscrape import Zyscrape
from . import data

def submission_search(lab, search_string, output_path):
    window = Window.get_window()
    students = data.get_students()
    scraper = Zyscrape()

    logger = window.new_logger()

    with open(os.path.expanduser(output_path), "w") as log_file:
        student_num = 1

        for student in students:
            counter = f"[{student_num}/{len(students)}]"
            logger.log(f"{counter:12} Checking {student.full_name}")

            match_result = scraper.check_submissions(str(student.id), lab, search_string)

            if match_result["success"]:
                log_file.write(f"{student.full_name} matched {match_result['time']}\n")

                logger.append(f" found {search_string}")

            # Check for and log errors
            if "error" in match_result:
                log_file.write(f"ERROR on {student.full_name}: {match_result['error']}")

            student_num += 1

        window.remove_logger(logger)

def admin_menu_callback(option):
    window = Window.get_window()
    labs = data.get_labs()

    if option == "Submissions Search":
        # Choose lab
        assignment = window.filtered_list(labs, "Assignment", filter_function=data.Lab.find)
        if assignment is 0:
            return

        # Select the lab part if needed
        if len(assignment.parts) > 1:
            part_name = window.filtered_list([name["name"] for name in assignment.parts], "Part")
            if part_name is 0:
                return
            index = [assignment.parts.index(p) for p in assignment.parts if p["name"] == part_name][0]
            part = assignment.parts[index]
        else:
            part = assignment.parts[0]

        search_string = window.text_input("Enter a search string")
        output_path = window.text_input("Enter the output path including filename [~ is supported]")

        submission_search(part, search_string, output_path)


def admin_menu():
    window = Window.get_window()

    options = ["Submissions Search"]

    window.filtered_list(options, "Option", admin_menu_callback)