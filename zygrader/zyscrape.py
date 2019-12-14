""" zyscrape - A wrapper around the zyBooks API """
import requests
import io
import zipfile
from datetime import datetime, timezone

from . import config

class Zyscrape:
    NO_ERROR = 0
    NO_SUBMISSION = 1
    COMPILE_ERROR = 2
    DOWNLOAD_TIMEOUT = 3
    ERROR = 4

    SUBMISSION_HIGHEST = "highest_score"  # Grade the most recent of the highest score
    CHECK_LATE_SUBMISSION = "due" # Remove late submissions

    session = None
    token = ""

    def __init__(self):
        Zyscrape.session = requests.session()

    def authenticate(self, username, password):
        auth_url = "https://zyserver.zybooks.com/v1/signin"
        payload = {"email": username, "password": password}
        
        r = Zyscrape.session.post(auth_url, json=payload)

        # Authentification failed
        if not r.json()["success"]:
            return False
        
        # Store auth token
        Zyscrape.token = r.json()["session"]["auth_token"]
        return True

    def get_roster(self):
        roles = '["TA","Student","Temporary","Dropped"]'
        roster_url = f"https://zyserver.zybooks.com/v1/zybook/{config.zygrader.CLASS_CODE}/roster?zybook_roles={roles}"

        payload = {"auth_token": Zyscrape.token}
        r = Zyscrape.session.get(roster_url, json=payload)

        if not r.ok:
            return False

        return r.json()

    def __get_time(self, submission):
        time = submission["date_submitted"]
        date = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
        date = date.replace(tzinfo=timezone.utc).astimezone(tz=None)
        return date

    def __get_time_string(self, submission):
        time = self.__get_time(submission)
        return time.strftime("%I:%M %p - %m-%d-%Y")

    def _get_score(self, submission):
        if "compile_error" in submission["results"]:
            return 0

        if submission["error"]:
            return 0

        score = 0
        results = submission["results"]["test_results"]
        for result in results:
            score += result["score"]

        return score
    
    def _get_max_score(self, submission):
        if submission["error"]:
            return 0

        score = 0

        tests = submission["results"]["config"]["test_bench"]
        for test in tests:
            score += test["max_score"]
        
        return score

    def get_submission(self, part_id, user_id):
        class_code = config.zygrader.CLASS_CODE
        submission_url = f"https://zyserver.zybooks.com/v1/zybook/{class_code}/programming_submission/{part_id}/user/{user_id}"
        payload = {"auth_token": Zyscrape.token}

        r = Zyscrape.session.get(submission_url, json=payload)

        return r

    def __remove_late_submissions(self, submissions, due_time):
        for submission in submissions[:]:
            submission_time = self.__get_time(submission)

            if submission_time > due_time:
                submissions.remove(submission)

        return submissions

    def __get_submission_highest_score(self, submissions):
        return max(reversed(submissions), key=self._get_score) # Thanks Teikn

    def __get_submission_most_recent(self, submissions):
        return submissions[-1]

    def download_submission(self, part_id, user_id, options):
        response = {"code": Zyscrape.NO_ERROR}

        r = self.get_submission(part_id, user_id)

        if not r.ok:
            return response

        # Get submissions
        submissions = r.json()["submissions"]

        # Strip out late submissions
        if submissions and Zyscrape.CHECK_LATE_SUBMISSION in options:
            submissions = self.__remove_late_submissions(submissions, options[Zyscrape.CHECK_LATE_SUBMISSION])

        # Student has not submitted or did not submit before assignment was due
        if not submissions:
            response["code"] = Zyscrape.NO_SUBMISSION
            return response

        # Get highest score
        if Zyscrape.SUBMISSION_HIGHEST in options:
            submission = self.__get_submission_highest_score(submissions)
        else:
            submission = self.__get_submission_most_recent(submissions)

        # If student's code did not compile their score is 0
        if "compile_error" in submission["results"]:
            response["code"] = Zyscrape.COMPILE_ERROR

        response["score"] = self._get_score(submission)
        response["max_score"] = self._get_max_score(submission)

        response["date"] = self.__get_time_string(submission)
        response["zip_url"] = submission["zip_location"]

        # Success
        return response

    def download_assignment(self, student, assignment):
        user_id = str(student.id)
        response = {"code": Zyscrape.NO_ERROR, "name": assignment.name, "score": 0, "max_score": 0, "parts": []}
        
        has_submitted = False
        for part in assignment.parts:
            response_part = {"code": Zyscrape.NO_ERROR, "name": part["name"]}
            submission = self.download_submission(part["id"], user_id, assignment.options)

            if submission["code"] is not Zyscrape.NO_SUBMISSION:
                has_submitted = True

                response["score"] += submission["score"]
                response["max_score"] += submission["max_score"]

                response_part["score"] = submission["score"]
                response_part["max_score"] = submission["max_score"]
                response_part["zip_url"] = submission["zip_url"]
                response_part["date"] = submission["date"]


                if submission["code"] is Zyscrape.COMPILE_ERROR:
                    response_part["code"] = Zyscrape.COMPILE_ERROR
            else:
                response_part["code"] = Zyscrape.NO_SUBMISSION


            response["parts"].append(response_part)

        
        # If student has not submitted, just return a non-success message
        if not has_submitted:
            return {"code": Zyscrape.NO_SUBMISSION}

        return response

    def extract_zip(self, input_zip):
        return {name: input_zip.read(name).decode('UTF-8', "replace") for name in input_zip.namelist()}
            
    def check_submissions(self, user_id, part, string):
        """Check each of a student's submissions for a given string"""
        submission_response = self.get_submission(part["id"], user_id)

        if not submission_response.ok:
            return {"code": Zyscrape.NO_SUBMISSION}

        all_submissions = submission_response.json()["submissions"]

        response = {"code": Zyscrape.NO_SUBMISSION}

        for submission in all_submissions:
            # Get file from zip url
            try:
                r = requests.get(submission["zip_location"], stream=True)
            except requests.exceptions.ConnectionError:
                # Bad connection, wait a few seconds and try again
                return {"code": Zyscrape.DOWNLOAD_TIMEOUT}

            try:
                z = zipfile.ZipFile(io.BytesIO(r.content))
            except zipfile.BadZipFile:
                response["error"] = f"BadZipFile Error on submission {self.__get_time_string(submission)}"
                continue

            f = self.extract_zip(z)

            # Check each file for the matched string
            for source_file in f.keys():
                if f[source_file].find(string) != -1:

                    # Get the date and time of the submission and return it
                    response["time"] = self.__get_time_string(submission)
                    response["code"] = Zyscrape.NO_ERROR

                    return response
        
        return response
