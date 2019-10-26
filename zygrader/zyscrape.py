""" zyscrape - A wrapper around the zyBooks API """

import requests
import io
import zipfile
from datetime import datetime, timezone

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
        submission_url = f"https://zyserver.zybooks.com/v1/zybook/BYUCS142Fall2019/programming_submission/{part_id}/user/{user_id}"
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
        
        time = recent_submission["date_submitted"]

        response["score"] = self._get_score(recent_submission)
        response["max_score"] = self._get_max_score(recent_submission)

        date = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
        date = date.replace(tzinfo=timezone.utc).astimezone(tz=None)
        response["date"] = date.strftime("%I:%M %p - %Y-%m-%d")

        # Success
        response["success"] = True
        return response

    def download_assignment(self, user_id, assignment):
        # TODO: Check if this assignment is already being graded
        response = {"success": True, "name": assignment.name, "score": 0, "max_score": 0, "parts": []}
        
        for part in assignment.parts:
            response_part = {"name": part["name"]}
            submission = self.download_submission(part["id"], user_id)

            if submission["success"]:
                response["score"] += submission["score"]
                response["max_score"] += submission["max_score"]

                response_part["score"] = submission["score"]
                response_part["max_score"] = submission["max_score"]
                response_part["zip_url"] = submission["zip_url"]
                response_part["date"] = submission["date"]

                response["parts"].append(response_part)
        
        return response

    def extract_zip(self, input_zip):
        return {name: input_zip.read(name).decode('UTF-8') for name in input_zip.namelist()}
            
    def check_submissions(self, user_id, part, string):
        """Check each of a student's submissions for a given string"""
        sr = self.get_submission(part["id"], user_id)

        if not sr.ok:
            return False

        all_submissions = sr.json()["submissions"]

        for submission in all_submissions:
            # Get file from zip url
            r = requests.get(submission["zip_location"], stream=True)
            z = zipfile.ZipFile(io.BytesIO(r.content))

            f = self.extract_zip(z)

            for source_file in f.keys():
                if f[source_file].find(string) != -1:
                    return True
        
        return False
