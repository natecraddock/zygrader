""" zyscrape - A wrapper around the zyBooks API """
import requests
import io
import zipfile
from datetime import datetime, timezone

from . import config

class Zyscrape:
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

    def __get_time(self, submission):
        time = submission["date_submitted"]
        date = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
        date = date.replace(tzinfo=timezone.utc).astimezone(tz=None)
        return date.strftime("%I:%M %p - %Y-%m-%d")

    def _get_score(self, submission):        
        score = 0
        results = submission["results"]["test_results"]
        for result in results:
            score += result["score"]

        return score
    
    def _get_max_score(self, submission):
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

    def download_submission(self, part_id, user_id):
        response = {"success": False}

        r = self.get_submission(part_id, user_id)

        if not r.ok:
            return response

        # Strip out important information from the response json
        all_submissions = r.json()["submissions"]

        # Student has not submitted
        if not all_submissions:
            return response

        recent_submission = r.json()["submissions"][-1] 
        response["zip_url"] = recent_submission["zip_location"]

        response["score"] = self._get_score(recent_submission)
        response["max_score"] = self._get_max_score(recent_submission)

        response["date"] = self.__get_time(recent_submission)

        # Success
        response["success"] = True
        return response

    def download_assignment(self, user_id, assignment):
        response = {"success": True, "name": assignment.name, "score": 0, "max_score": 0, "parts": []}
        
        has_submitted = False
        for part in assignment.parts:
            response_part = {"name": part["name"]}
            submission = self.download_submission(part["id"], user_id)

            if submission["success"]:
                has_submitted = True

            if submission["success"]:
                response["score"] += submission["score"]
                response["max_score"] += submission["max_score"]

                response_part["score"] = submission["score"]
                response_part["max_score"] = submission["max_score"]
                response_part["zip_url"] = submission["zip_url"]
                response_part["date"] = submission["date"]

                response["parts"].append(response_part)
        
        # If student has not submitted, just return a non-success message
        if not has_submitted:
            return {"success": False}

        return response

    def extract_zip(self, input_zip):
        return {name: input_zip.read(name).decode('UTF-8') for name in input_zip.namelist()}
            
    def check_submissions(self, user_id, part, string):
        """Check each of a student's submissions for a given string"""
        submission_response = self.get_submission(part["id"], user_id)

        if not submission_response.ok:
            return {"success": False}

        all_submissions = submission_response.json()["submissions"]

        response = {"success": False}

        for submission in all_submissions:
            # Get file from zip url
            r = requests.get(submission["zip_location"], stream=True)

            try:
                z = zipfile.ZipFile(io.BytesIO(r.content))
            except zipfile.BadZipFile:
                response["error"] = "BadZipFile Error"
                continue

            f = self.extract_zip(z)

            # Check each file for the matched string
            for source_file in f.keys():
                if f[source_file].find(string) != -1:

                    # Get the date and time of the submission and return it
                    response["time"] = self.__get_time(submission)
                    response["success"] = True

                    return response
        
        return response
