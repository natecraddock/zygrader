""" A wrapper around the zyBooks API """
import os
import zipfile
from datetime import datetime, timedelta, timezone

import requests

from zygrader.config.shared import SharedData
from zygrader.config import preferences


class SectionResponse:
    def __init__(self):
        self.success = False
        self.id = ""
        self.name = ""


class Zybooks:
    NO_ERROR = 0
    NO_SUBMISSION = 1
    COMPILE_ERROR = 2
    DOWNLOAD_TIMEOUT = 3
    ERROR = 4

    SUBMISSION_HIGHEST = "highest_score"  # Grade the most recent of the highest score
    CHECK_LATE_SUBMISSION = "due"  # Remove late submissions

    session = None
    token = ""

    def __init__(self):
        Zybooks.session = requests.session()

    def __load_session(self):
        return preferences.get("token")

    def __save_session(self, token: str):
        preferences.set("token", token)

    def __check_auth(self):
        """Ensure the auth token is valid through a "useless" request"""
        check_url = f'https://zyserver.zybooks.com/v1/zybooks?zybooks=["{SharedData.CLASS_CODE}"]'
        check_url += f"&auth_token={Zybooks.token}"
        r = Zybooks.session.get(check_url)
        if not r.ok:
            return False
        resp = r.json()
        return resp.get("success")

    def authenticate(self, username: str, password: str):
        """Authenticate a user to zyBooks"""
        if not username and not password:
            token = self.__load_session()
            Zybooks.token = token

            # Ensure that this auth is valid
            return self.__check_auth()

        auth_url = "https://zyserver.zybooks.com/v1/signin"
        payload = {"email": username, "password": password}

        r = Zybooks.session.post(auth_url, json=payload)

        # Authentication failed
        if not r.ok or not r.json()["success"]:
            return False

        # Store auth token
        Zybooks.token = r.json()["session"]["auth_token"]
        self.__save_session(Zybooks.token)
        return True

    def get_roster(self):
        """Download the roster of regular and temporary students. TAs can be added by adding "TA" to the roles array"""
        roles = '["Student","Temporary"]'
        roster_url = f"https://zyserver.zybooks.com/v1/zybook/{SharedData.CLASS_CODE}/roster?zybook_roles={roles}"

        payload = {"auth_token": Zybooks.token}
        r = Zybooks.session.get(roster_url, json=payload)

        if not r.ok:
            return False

        return r.json()

    def get_table_of_contents(self):
        """Download the table of contents (toc) for the current zybook"""
        payload = {"auth_token": Zybooks.token}
        toc_url = f'https://zyserver2.zybooks.com/v1/zybook/{SharedData.CLASS_CODE}/ordering?include=["content_ordering"]'

        r = Zybooks.session.get(toc_url, json=payload)

        if not r.json()["success"]:
            return False

        return r.json()["ordering"]["content_ordering"]["chapters"]

    def get_completion_report(self, due_time: datetime, zybook_sections):
        """Download a completion report for the whole class

        Previous versions of this software allowed for downloading completion by class section,
        but the zybooks api does not provide a consistent way to do so for all textbooks,
        so if a particular class section is desired the filtering must be done after

        This function returns the report as a string to be parsed as needed by the user
        """
        section_ids = [
            section["canonical_section_id"] for section in zybook_sections
        ]

        aware_due_time = due_time.astimezone()
        offset_minutes = int(-(aware_due_time.tzinfo.utcoffset(None) /
                               timedelta(minutes=1)))

        due_time_for_zybook = aware_due_time.astimezone(
            tz=timezone(timedelta()))
        due_time_str = due_time_for_zybook.strftime(
            "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        query_string = f"?time_zone_offset={offset_minutes}&end_date={due_time_str}&sections={str(section_ids).replace(' ', '')}"

        report_url = f"https://zyserver.zybooks.com/v1/zybook/{SharedData.CLASS_CODE}/activities/export{query_string}"
        payload = {"auth_token": Zybooks.token}

        r1 = Zybooks.session.get(report_url, json=payload)
        if not r1.json()["success"]:
            return False

        csv_url = r1.json()["url"]
        csv_response = requests.get(csv_url)
        if not csv_response.ok:
            return False

        return csv_response.content.decode("utf-8")

    def get_zybook_section(self, chapter, section) -> SectionResponse:
        """Given a chapter and section ID, get section information like the zybooks internal ID

        This is useful for running the class manager. To download a submission, the zybooks sectionID
        must be used. It is hard to get manually, so this function returns the id and name.
        """
        class_code = SharedData.CLASS_CODE
        url = f"https://zyserver.zybooks.com/v1/zybook/{class_code}/chapter/{chapter}/section/{section}"
        payload = {"auth_token": Zybooks.token}

        r = Zybooks.session.get(url, json=payload)
        response = SectionResponse()

        if r.ok:
            if "section" not in r.json():
                return response
            section = r.json()["section"]
            content = section["content_resources"][1]

            response.success = True
            response.id = content["id"]
            response.name = content["caption"]

        return response

    def check_valid_class(self, code: str) -> bool:
        """Return a boolean indicating if the zybooks class code is valid

        The class code is of the format: BYUCS142Winter2020
        """
        url = f'https://zyserver.zybooks.com/v1/zybooks?zybooks=["{code}"]'
        payload = {"auth_token": Zybooks.token}
        r = Zybooks.session.get(url, json=payload)

        if r.ok:
            return r.json()["zybooks"]

        return False

    def __get_time(self, submission: dict) -> datetime:
        time = submission["date_submitted"]
        date = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
        date = date.replace(tzinfo=timezone.utc).astimezone(tz=None)
        return date

    def get_time_string(self, submission: dict) -> str:
        time = self.__get_time(submission)
        return time.strftime("%I:%M %p - %m-%d-%Y")

    def _get_score(self, submission: dict) -> int:
        if "compile_error" in submission["results"]:
            return 0

        if submission["error"]:
            return 0

        score = 0
        results = submission["results"]["test_results"]
        for result in results:
            score += result["score"]

        return score

    def _get_max_score(self, submission: dict) -> int:
        if submission["error"]:
            return 0

        score = 0

        tests = submission["results"]["config"]["test_bench"]
        for test in tests:
            score += test["max_score"]

        return score

    def get_all_submissions(self, part_id, user_id):
        """Get the JSON representing all submissions of a given lab"""
        class_code = SharedData.CLASS_CODE
        submission_url = f"https://zyserver.zybooks.com/v1/zybook/{class_code}/programming_submission/{part_id}/user/{user_id}"
        payload = {"auth_token": Zybooks.token}

        r = Zybooks.session.get(submission_url, json=payload)
        if not r.ok:
            return None

        return r.json()["submissions"]

    def get_submissions_list(self, part_id, user_id) -> list:
        submissions = self.get_all_submissions(part_id, user_id)
        if not submissions:
            return []

        return [
            f"{self.get_time_string(s)}  Score: {self._get_score(s):3}/{self._get_max_score(s)}"
            for s in submissions
        ]

    def __remove_late_submissions(self, submissions: list,
                                  due_time: datetime) -> list:
        for submission in submissions[:]:
            submission_time = self.__get_time(submission)

            if submission_time > due_time:
                submissions.remove(submission)

        return submissions

    def __get_submission_highest_score(self, submissions) -> dict:
        return max(reversed(submissions), key=self._get_score)  # Thanks Teikn

    def __get_submission_most_recent(self, submissions) -> dict:
        return submissions[-1]

    def download_submission(self, part_id, user_id, options,
                            submission_index: int) -> dict:
        """Used for grading. Download a single submission and return information for grading.
        This is used together with self.download_assignment, as some labs have multiple submission "parts"
        (such as midterms)

        The Lab fetched and information returns depends on the lab options.
        Usually, the most recent score is returned, but the highest score can also be requested.
        """
        response = {"code": Zybooks.NO_ERROR}

        submissions = self.get_all_submissions(part_id, user_id)

        if not submissions:
            response["code"] = Zybooks.NO_SUBMISSION
            return response

        if submission_index is not None:
            submission = submissions[submission_index]
        else:
            # Strip out late submissions
            if submissions and Zybooks.CHECK_LATE_SUBMISSION in options:
                submissions = self.__remove_late_submissions(
                    submissions, options[Zybooks.CHECK_LATE_SUBMISSION])

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

    def download_assignment_part(self,
                                 assignment,
                                 user_id,
                                 part,
                                 submission_index=None) -> dict:
        response_part = {
            "code": Zybooks.NO_ERROR,
            "name": part["name"],
            "id": str(part["id"])
        }
        submission = self.download_submission(part["id"], user_id,
                                              assignment.options,
                                              submission_index)

        if submission["code"] is not Zybooks.NO_SUBMISSION:
            response_part["score"] = submission["score"]
            response_part["max_score"] = submission["max_score"]
            response_part["zip_url"] = submission["zip_url"]
            response_part["date"] = submission["date"]

            if submission["code"] is Zybooks.COMPILE_ERROR:
                response_part["code"] = Zybooks.COMPILE_ERROR
        else:
            response_part["code"] = Zybooks.NO_SUBMISSION

        return response_part

    def download_assignment(self, student, assignment) -> dict:
        """Get information from a student's assignment

        An assignment can have multiple submissions within it (midterms...)
        So this function compiles the individual scores from each part
        """
        user_id = str(student.id)
        response = {
            "code": Zybooks.NO_ERROR,
            "name": assignment.name,
            "score": 0,
            "max_score": 0,
            "parts": [],
        }

        has_submitted = False
        for part in assignment.parts:
            response_part = self.download_assignment_part(
                assignment, user_id, part)
            if response_part["code"] is not Zybooks.NO_SUBMISSION:
                has_submitted = True

            response["parts"].append(response_part)

        # If student has not submitted, just return a non-success message
        if not has_submitted:
            response["code"] = Zybooks.NO_SUBMISSION

        return response

    def get_submission_zip(self, url):
        """Download the submission at the given URL, or from a local cache if available

        While this is technically accessing files at Amazon's servers, it is coupled closely
        enough to zyBooks to include it in this file, rather than making a new file for just
        this feature.

        The cache is stored in the zygrader_data/SEMESTER_FOLDER/.cache/ directory

        Returns a ZipFile
        """
        # Check if the zip file is already cached. Only use the basename of the url
        cached_name = os.path.join(SharedData.get_cache_directory(),
                                   os.path.basename(url))
        if os.path.exists(cached_name):
            return zipfile.ZipFile(cached_name)

        # If not cached, download
        zip_response = requests.get(url)
        if not zip_response.ok:
            return Zybooks.ERROR

        # Write zip to cache
        with open(cached_name, "wb") as _file:
            _file.write(zip_response.content)
        return zipfile.ZipFile(cached_name)
