import curses
import datetime
import enum
import io
import os
import requests
import signal
import subprocess
import tempfile
import time
import zipfile

from .. import config
from .. import logger
from .. import utils
from .. import ui
from ..zybooks import Zybooks

class Lab:
    def __init__(self, name, parts, options):
        self.name = name
        self.parts = parts
        self.options = options

        # Convert due datetime strings to objects
        if "due" in self.options:
            self.options["due"] = datetime.datetime.strptime(self.options["due"], "%m.%d.%Y:%H.%M.%S").astimezone(tz=None)

    def __str__(self):
        return f"{self.name}"

    @classmethod
    def find(cls, line, text):
        assignment = line.data

        name = assignment.name.lower()
        text = text.lower()

        return name.find(text) is not -1

    def to_json(self):
        lab = {"name": self.name, "parts": self.parts, "options": self.options.copy()}
        if "due" in lab["options"] and type(lab["options"]["due"]) is not str:
            lab["options"]["due"] = lab["options"]["due"].strftime("%m.%d.%Y:%H.%M.%S")

        return lab


class Student:
    def __init__(self, first_name, last_name, email, section, id):
        self.first_name = first_name
        self.last_name = last_name
        self.full_name = f"{first_name} {last_name}"
        self.email = email
        self.section = section
        self.id = id

    def __str__(self):
        return f"{self.full_name} - {self.email} - Section {self.section}"

    @classmethod
    def find(cls, line, text):
        student = line.data

        first_name = student.first_name.lower()
        last_name = student.last_name.lower()
        full_name = student.full_name.lower()
        email = student.email.lower()
        text = text.lower()

        return first_name.find(text) is not -1 or last_name.find(text) is not -1 or \
               full_name.find(text) is not -1 or email.find(text) is not -1


class SubmissionFlag(enum.Flag):
    NO_SUBMISSION = enum.auto()
    OK = enum.auto()
    BAD_ZIP_URL = enum.auto()
    DIFF_PARTS = enum.auto()


class Submission:
    def get_part_identifier(self, part):
        """Some parts are not named, use ID in that case"""
        if part["name"]:
            return part["name"]
        return part["id"]

    def update_part(self, part, part_index):
        self.response["parts"][part_index] = part

        self.construct_submission()

    def construct_submission(self):
        # Read the response data
        # Only grade if student has submitted
        if self.response["code"] is Zybooks.NO_SUBMISSION:
            self.flag = SubmissionFlag.NO_SUBMISSION
            return

        # Calculate score
        self.response["score"] = 0
        self.response["max_score"] = 0
        for part in self.response["parts"]:
            if part["code"] is not Zybooks.NO_SUBMISSION:
                self.response["score"] += part["score"]
                self.response["max_score"] += part["max_score"]

        self.files_directory = self.read_files(self.response)

        self.create_submission_string(self.response)
        self.latest_submission = self.get_latest_submission(self.response)

        if "diff_parts" in self.lab.options:
            self.flag |= SubmissionFlag.DIFF_PARTS

    def __init__(self, student, lab, response):
        self.student = student
        self.lab = lab
        self.flag = SubmissionFlag.OK

        # Save the response to be potentially updated later
        self.response = response

        self.construct_submission()

    def get_latest_submission(self, response):
        latest = None
        for part in response["parts"]:
            if part["code"] is Zybooks.NO_SUBMISSION:
                continue

            t = time.strptime(part["date"], "%I:%M %p - %m-%d-%Y")
            if not latest or time.mktime(latest) < time.mktime(t):
                latest = t

        if not latest:
            return ""
        return time.strftime("%I:%M %p - %m-%d-%Y", latest)

    def create_submission_string(self, response):
        msg = [f"{self.student.full_name} - {self.lab.name}", ""]

        for part in response["parts"]:
            if part["code"] == Zybooks.NO_SUBMISSION:
                msg.append(f"{part['name']:4} No Submission")
            else:
                score = f"{part['score']}/{part['max_score']}"

                if part["name"]:
                    msg.append(f"{part['name']:4} {score:8} {part['date']}")
                else:
                    msg.append(f"{score:8} {part['date']}")

                if part["code"] == Zybooks.COMPILE_ERROR:
                    msg[-1] += f" [Compile Error]"

        msg.append("")
        msg.append(f"Total Score: {response['score']}/{response['max_score']}")

        self.msg = msg

    def read_files(self, response):
        zy_api = Zybooks()
        tmp_dir = tempfile.mkdtemp()

        # Look through each part
        for part in response["parts"]:
            if part["code"] == Zybooks.NO_SUBMISSION:
                continue

            zip_file = zy_api.get_submission_zip(part["zip_url"])

            # Sometimes the zip file URL reported by zyBooks is invalid. Not sure if this
            # is an error with Amazon (the host) or zyBooks but in this rare case, just skip
            # the file. Also flag this Submission as having missing file(s).
            if zip_file == Zybooks.ERROR:
                self.flag |= SubmissionFlag.BAD_ZIP_URL
                continue

            # TODO: Can the name be removed from the file itself?
            files = utils.extract_zip(zip_file)

            # Write file to subdirectory in temporary directory
            part_directory = os.path.join(tmp_dir, self.get_part_identifier(part))
            os.mkdir(part_directory)
            for file_name in files.keys():
                with open(os.path.join(part_directory, file_name), "w") as source_file:
                    source_file.write(files[file_name])

        return tmp_dir

    def show_files(self):
        user_editor = config.user.get_config()["editor"]
        editor_path = config.user.EDITORS[user_editor]

        files = utils.get_source_file_paths(self.files_directory)

        # Terminal-based editors
        if user_editor in {"Vim", "Emacs", "Nano", "Less"}:
            curses.endwin()

            files.sort()

            if user_editor == "Vim":
                # Use "-p" to open in tabs
                cmds = ["--cmd", "set tabpagemax=100", "--cmd", "set laststatus=2", "--cmd", "set number"]
                subprocess.run([editor_path, "-p"] + files + cmds)
            elif user_editor == "Emacs":
                # Force terminal with "-nw"
                subprocess.run([editor_path, "-nw"] + files)
            else:
                subprocess.run([editor_path] + files)

            curses.initscr()
        # Graphical editors
        else:
            paths = " ".join(files)
            subprocess.Popen(f"{editor_path} {paths}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def open_folder(self):
        subprocess.Popen(f"xdg-open {self.files_directory}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def do_resume_code(self, process):
        if process:
            config.g_data.RUNNING_CODE = True
            curses.endwin()
            process.send_signal(signal.SIGCONT)
            print("Resumed student code")
            print("#############################################################")
            return True
        return False

    def compile_and_run_code(self):
        if self.do_resume_code(config.g_data.running_process):
            stopped = self.wait_on_child(config.g_data.running_process)
        else:
            # Get path to executable
            executable = self.compile_code()
            if not executable:
                return False # Could not compile code

            # Suspend curses
            config.g_data.RUNNING_CODE = True
            curses.endwin()

            stopped = self.run_code(executable)

        if not stopped:
            config.g_data.running_process = None

            config.g_data.RUNNING_CODE = False
            print("\n#############################################################")
            print("Press ENTER to continue")
            input()
        else:
            print("\n#############################################################")
            print("Paused student code\n")

        return True

    def pick_part(self):
        window = ui.window.Window.get_window()
        part_names = [self.get_part_identifier(x) for x in self.lab.parts]

        picked = window.create_list_popup("Choose a part", part_names)
        return picked

    def compile_code(self):
        # Use a separate tmp dir to avoid opening the binary in a text editor
        tmp_dir = tempfile.mkdtemp()
        executable_name = os.path.join(tmp_dir, "run")

        root_dir = self.files_directory
        if len(self.lab.parts) > 1:
            part = self.pick_part()
            if part == ui.UI_GO_BACK:
                return False

            root_dir = os.path.join(self.files_directory, self.get_part_identifier(self.lab.parts[part]))

        files = utils.get_source_file_paths(root_dir)

        source_files = [f for f in files if f.endswith(".cpp")]
        compile_command = ["g++", "-o", executable_name, f"-I{root_dir}"] + source_files

        compile_exit = subprocess.run(compile_command)
        if compile_exit.returncode != 0:
            return False

        # Compiled successfully, run code
        return os.path.abspath(executable_name)

    def wait_on_child(self, child):
        while child.poll() is None:
            time.sleep(0.1)
            if not config.g_data.RUNNING_CODE:
                break

        # If the running process still exists
        if config.g_data.running_process and config.g_data.running_process.poll() is None:
            return True

        return False

    def run_code(self, executable):
        print(chr(27) + "[2J", end='') # Clear the terminal
        print("#############################################################")
        print(f"Running {self.student.full_name}'s code")
        print("CTRL+C to terminate")
        print("CTRL+Z to stop (pause)")
        print("#############################################################\n")

        process = subprocess.Popen([executable])
        config.g_data.running_process = process

        # Return indicator if child terminated or stopped
        return self.wait_on_child(process)

    def diff_parts(self):
        # This runs under the assumption that we only want to compare parts A and B
        if len(self.lab.parts) != 2:
            return

        use_browser = config.user.is_preference_set("browser_diff")

        path_a = os.path.join(self.files_directory, self.get_part_identifier(self.lab.parts[0]))
        path_b = os.path.join(self.files_directory, self.get_part_identifier(self.lab.parts[1]))
        part_a = [os.path.join(path_a, f) for f in os.listdir(path_a)]
        part_b = [os.path.join(path_b, f) for f in os.listdir(path_b)]

        diff = utils.make_diff_string(part_a, part_b, path_a, path_b, use_browser)
        utils.view_string(diff, "parts.diff", use_browser)
