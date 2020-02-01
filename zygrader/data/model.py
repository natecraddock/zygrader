import subprocess
import datetime
import tempfile
import requests
import zipfile
import curses
import glob
import io
import os
import difflib

from ..zybooks import Zybooks
from .. import config
from .. import logger

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
    def find(cls, assignment, text):
        name = assignment.name.lower()
        text = text.lower()

        return name.find(text) is not -1

    def to_json(self):
        lab = {"name": self.name, "parts": self.parts, "options": self.options}
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
    def find(cls, student, text):
        first_name = student.first_name.lower()
        last_name = student.last_name.lower()
        full_name = student.full_name.lower()
        email = student.email.lower()
        text = text.lower()

        return first_name.find(text) is not -1 or last_name.find(text) is not -1 or \
               full_name.find(text) is not -1 or email.find(text) is not -1

class Submission:
    NO_SUBMISSION = (1 << 0)
    OK = (1 << 1)
    BAD_ZIP_URL = (1 << 2)
    DIFF_PARTS = (1 << 3)

    def __init__(self, student, lab, response):
        self.student = student
        self.lab = lab
        self.flag = Submission.OK

        # Read the response data
        # Only grade if student has submitted
        if response["code"] is Zybooks.NO_SUBMISSION:
            self.flag = Submission.NO_SUBMISSION
            return

        self.files_directory = self.read_files(response)

        self.create_submission_string(response)

        if "diff_parts" in lab.options:
            self.flag |= Submission.DIFF_PARTS

    def create_submission_string(self, response):
        msg = [f"{self.student.full_name}'s submission downloaded", ""]

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
        tmp_dir = tempfile.mkdtemp()

        # Look through each part
        for part in response["parts"]:
            if part["code"] == Zybooks.NO_SUBMISSION:
                continue

            zy_api = Zybooks()
            zip_file = zy_api.get_submission_zip(part["zip_url"])

            # Sometimes the zip file URL reported by zyBooks is invalid. Not sure if this
            # is an error with Amazon (the host) or zyBooks but in this rare case, just skip
            # the file. Also flag this Submission as having missing file(s).
            if zip_file == Zybooks.ERROR:
                self.flag |= Submission.BAD_ZIP_URL
                continue

            files = zy_api.extract_zip(zip_file, part["name"])

            # Write file to temporary directory
            for file_name in files.keys():
                with open(os.path.join(tmp_dir, file_name), "w") as source_file:
                    source_file.write(files[file_name])

        return tmp_dir

    def show_files(self):
        user_editor = config.user.get_config()["editor"]
        editor_path = config.user.EDITORS[user_editor]

        if user_editor in {"Vim", "Emacs", "Nano", "Less"}:
            curses.endwin()

            if user_editor == "Vim":
                # Use "-p" to open in tabs
                subprocess.run([editor_path, "-p"] + glob.glob(f"{self.files_directory}/*"))
            elif user_editor == "Emacs":
                # Force terminal with "-nw"
                subprocess.run([editor_path, "-nw"] + glob.glob(f"{self.files_directory}/*"))
            else:
                subprocess.run([editor_path] + glob.glob(f"{self.files_directory}/*"))

            curses.initscr()
            return

        subprocess.Popen(f"{editor_path} {self.files_directory}/*", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def open_folder(self):
        subprocess.Popen(f"xdg-open {self.files_directory}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def run_code(self):
        executable_name = os.path.join(self.files_directory, "run")
        source_files = [os.path.join(self.files_directory, f) for f in os.listdir(self.files_directory) if f.endswith(".cpp")]
        compile_command = ["g++", "-o", executable_name] + source_files

        compile_exit = subprocess.run(compile_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if compile_exit.returncode != 0:
            return False

        # Compiled successfully, run code
        executable = os.path.abspath(executable_name)
        cmd = executable
        curses.endwin()
        print(f"\nRunning {self.student.full_name}'s code\n\n")
        subprocess.run([cmd])
        print("\nPress ENTER to continue")
        input()
        curses.initscr()
        os.remove(executable)

        return True

    def diff_parts(self):
        # This runs under the assumption that we only want to compare parts A and B
        if len(self.lab.parts) != 2:
            return

        part_prefixes = [part["name"] for part in self.lab.parts]
        part_files = os.listdir(self.files_directory)

        parts = []
        for pre in part_prefixes:
            for part in part_files:
                if part.startswith(pre):
                    parts.append(os.path.join(self.files_directory, part))

        with open(parts[0], 'r') as part_a:
            with open(parts[1], 'r') as part_b:
                html = difflib.HtmlDiff(4, 80)
                diff = html.make_file(part_a.readlines(), part_b.readlines(), parts[0], parts[1], context=True)

                tmp_dir = tempfile.mkdtemp()
                with open(f"{os.path.join(tmp_dir, 'parts.html')}", 'w') as diff_file:
                    diff_file.write(diff)

                subprocess.Popen(f"xdg-open {os.path.join(tmp_dir, 'parts.html')}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
