import subprocess
import datetime
import tempfile
import requests
import zipfile
import io
import os

from ..zyscrape import Zyscrape
from .. import config

class Lab:
    def __init__(self, name, assignment_type, parts, options):
        self.name = name
        self.type = assignment_type
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

    def __init__(self, student, lab, response):
        self.student = student
        self.lab = lab
        self.flag = Submission.OK

        # Read the response data
        # Only grade if student has submitted
        if response["code"] is Zyscrape.NO_SUBMISSION:
            self.flag = Submission.NO_SUBMISSION
            return

        self.files_directory = self.read_files(response)

        self.create_submission_string(response)

    def create_submission_string(self, response):
        msg = [f"{self.student.full_name}'s submission downloaded", ""]

        for part in response["parts"]:
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
        msg.append(f"Total Score: {response['score']}/{response['max_score']}")

        self.msg = msg

    def read_files(self, response):
        tmp_dir = tempfile.mkdtemp()

        # Look through each part
        for part in response["parts"]:
            if part["code"] == Zyscrape.NO_SUBMISSION:
                continue

            # Open zip of student's file(s) in memory
            zip_response = requests.get(part["zip_url"])

            # Sometimes the zip file URL reported by zyBooks is invalid. Not sure if this
            # is an error with Amazon (the host) or zyBooks but in this rare case, just skip
            # the file. Also flag this Submission as having missing file(s).
            if not zip_response.ok:
                self.flag |= Submission.BAD_ZIP_URL
                continue

            zip_file = zipfile.ZipFile(io.BytesIO(zip_response.content))
            files = self.extract_zip(part["name"], zip_file)

            # Write file to temporary directory
            for file_name in files.keys():
                with open(os.path.join(tmp_dir, file_name), "w") as source_file:
                    source_file.write(files[file_name])

        return tmp_dir

    def show_files(self):
        user_editor = config.user.get_config()["editor"]
        editor_path = config.user.EDITORS[user_editor]

        subprocess.Popen(f"{editor_path} {self.files_directory}/*", shell=True)

    def open_folder(self):
        subprocess.Popen(f"xdg-open {self.files_directory}", shell=True)

    def extract_zip(self, file_prefix, input_zip):
        if file_prefix:
            return {f"{file_prefix}_{name}": input_zip.read(name).decode('UTF-8') for name in input_zip.namelist()}
        else:
            return {f"{name}": input_zip.read(name).decode('UTF-8') for name in input_zip.namelist()}
