import time
from pynostr.event import Event
from typing import Optional
from audgit.get_repo_files import get_repo_files
import requests
import json


def code_review(issue_url: str):
    """
    Expected input is a GitHub issue URL.
    """

    # Parse the issue url to get owner, repo and issue number
    parts = issue_url.split("/")
    issue_number = parts[-1]
    repo = parts[-3]
    owner = parts[-4]

    # Construct the GitHub API url
    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"

    # use the github api to get the issue
    headers = {"Accept": "application/vnd.github.v3+json"}
    response = requests.get(api_url, headers=headers)

    # Ensure the request was successful
    if response.status_code != 200:
        raise Exception(f"Error: API request status {response.status_code}")

    issue = response.json()
    print("issue: ", json.dumps(issue, indent=4))

    # wait for a second
    time.sleep(1)

    # After getting the issue, get the contents of the repo
    get_repo_files(owner, repo)

    return "OK"


code_review("https://github.com/fedimint/fedimint/issues/2858")
