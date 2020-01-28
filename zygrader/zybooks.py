""" A wrapper around the zyBooks API """
import requests
from datetime import datetime, timezone

from . import config

class Zybooks:
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
        Zybooks.session = requests.session()

    def authenticate(self, username, password):
        """Authenticate a user to zyBooks"""
        auth_url = "https://zyserver.zybooks.com/v1/signin"
        payload = {"email": username, "password": password}
        
        r = Zybooks.session.post(auth_url, json=payload)

        # Authentification failed
        if not r.json()["success"]:
            return False
        
        # Store auth token
        Zybooks.token = r.json()["session"]["auth_token"]
        return True

    def get_roster(self):
        """Download the roster of regular and temporary students. TAs can be added by adding "TA" to the roles array"""
        roles = '["Student","Temporary"]'
        roster_url = f"https://zyserver.zybooks.com/v1/zybook/{config.zygrader.CLASS_CODE}/roster?zybook_roles={roles}"

        payload = {"auth_token": Zybooks.token}
        r = Zybooks.session.get(roster_url, json=payload)

        if not r.ok:
            return False

        return r.json()

    def get_zybook_section(self, chapter, section):
        """Given a chapter and section ID, get section information like the zybooks internal ID

        This is useful for running the class manager. To download a submission, the zybooks sectionID
        must be used. It is hard to get manually, but this function returns the id and name.
        """
        class_code = config.zygrader.CLASS_CODE
        url = f"https://zyserver.zybooks.com/v1/zybook/{class_code}/chapter/{chapter}/section/{section}"
        payload = {"auth_token": Zybooks.token}

        r = Zybooks.session.get(url, json=payload)
        response = {"success": False}

        if r.ok:
            section = r.json()["section"]
            content = section["content_resources"][1]

            response["success"] = True
            response["id"] = content["id"]
            response["name"] = content["caption"]

        return response

    def check_valid_class(self, code):
        """Return a boolean indicating if the zybooks class code is valid

        The class code is in the format: BYUCS142Winter2020
        """
        url = f"https://zyserver.zybooks.com/v1/zybooks?zybooks=[\"{code}\"]"
        payload = {"auth_token": Zybooks.token}
        r = Zybooks.session.get(url, json=payload)

        if r.ok:
            return r.json()["zybooks"]

        return False

    def __get_time(self, submission):
        time = submission["date_submitted"]
        date = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
        date = date.replace(tzinfo=timezone.utc).astimezone(tz=None)
        return date

    def get_time_string(self, submission):
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

    def get_all_submissions(self, part_id, user_id):
        """Get the JSON representing all submissions of a given lab"""
        class_code = config.zygrader.CLASS_CODE
        submission_url = f"https://zyserver.zybooks.com/v1/zybook/{class_code}/programming_submission/{part_id}/user/{user_id}"
        payload = {"auth_token": Zybooks.token}

        r = Zybooks.session.get(submission_url, json=payload)

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
        """Used for grading. Download a single submission and return information for grading.
        This is used together with self.download_assignment, as some labs have multiple submission "parts"
        (such as midterms)

        The Lab fetched and information returns depends on the lab options.
        Usually, the most recent score is returned, but the highest score can also be requested.
        """
        response = {"code": Zybooks.NO_ERROR}

        r = self.get_all_submissions(part_id, user_id)

        if not r.ok:
            return response

        # Get submissions
        submissions = r.json()["submissions"]

        # Strip out late submissions
        if submissions and Zybooks.CHECK_LATE_SUBMISSION in options:
            submissions = self.__remove_late_submissions(submissions, options[Zybooks.CHECK_LATE_SUBMISSION])

        # Student has not submitted or did not submit before assignment was due
        if not submissions:
            response["code"] = Zybooks.NO_SUBMISSION
            return response

        # Get highest score
        if Zybooks.SUBMISSION_HIGHEST in options:
            submission = self.__get_submission_highest_score(submissions)
        else:
            submission = self.__get_submission_most_recent(submissions)

        # If student's code did not compile their score is 0
        if "compile_error" in submission["results"]:
            response["code"] = Zybooks.COMPILE_ERROR

        response["score"] = self._get_score(submission)
        response["max_score"] = self._get_max_score(submission)

        response["date"] = self.get_time_string(submission)
        response["zip_url"] = submission["zip_location"]

        # Success
        return response

    def download_assignment(self, student, assignment):
        """Get information from a student's assignment

        An assignment can have multiple submissions within it (midterms...)
        So this function compiles the individual scores from each part
        """
        user_id = str(student.id)
        response = {"code": Zybooks.NO_ERROR, "name": assignment.name, "score": 0, "max_score": 0, "parts": []}
        
        has_submitted = False
        for part in assignment.parts:
            response_part = {"code": Zybooks.NO_ERROR, "name": part["name"]}
            submission = self.download_submission(part["id"], user_id, assignment.options)

            if submission["code"] is not Zybooks.NO_SUBMISSION:
                has_submitted = True

                response["score"] += submission["score"]
                response["max_score"] += submission["max_score"]

                response_part["score"] = submission["score"]
                response_part["max_score"] = submission["max_score"]
                response_part["zip_url"] = submission["zip_url"]
                response_part["date"] = submission["date"]

                if submission["code"] is Zybooks.COMPILE_ERROR:
                    response_part["code"] = Zybooks.COMPILE_ERROR
            else:
                response_part["code"] = Zybooks.NO_SUBMISSION

            response["parts"].append(response_part)
        
        # If student has not submitted, just return a non-success message
        if not has_submitted:
            return {"code": Zybooks.NO_SUBMISSION}

        return response
