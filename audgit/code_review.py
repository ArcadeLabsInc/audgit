from pynostr.event import Event
from audgit.claude_call import which_files_claude_call, best_solution_claude_call
from audgit.descrips import generate_file_descrips
from audgit.get_repo_files import get_file_tree
import requests
import json
import os
from dotenv import load_dotenv
import logging

log = logging.getLogger("audgit")

# load the .env file. By default, it looks for the .env file in the same directory as the script
# If your .env file is one directory up, you need to specify the path
load_dotenv()

# Load the token from an environment variable
TOKEN = os.getenv("GITHUB_TOKEN")

# Define the headers to be used in the requests
headers = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {TOKEN}",
}


# Generate a new keypair for the demonstration

def code_review(event: Event) -> Event:
    log.debug("Got event...")
    issue_url = event.content

    parts = issue_url.split("/")
    issue_number = parts[-1]
    repo = parts[-3]
    owner = parts[-4]

    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    response = requests.get(api_url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Error: API request status {response.status_code}")

    issue = response.json()
    log.debug("Got issue...")

    repo_url = f"https://github.com/{owner}/{repo}.git"
    local_path = f"/tmp/repo/{repo}"  # Define the local path where the repo is cloned

    file_paths = get_file_tree(repo_url, local_path)

    files_with_descriptions = generate_file_descrips(file_paths)

    file_paths_to_review = which_files_claude_call(
        issue["title"],
        issue["body"],
        files_with_descriptions
    )

    content_str = json.dumps(
        {
            "issue": issue,
            "file_paths": file_paths_to_review,
            # "file_contents": file_contents_json,
        }
    )

    job_result_event = Event(
        kind=65001,  # code review job result
        content=content_str,  # use the JSON string here
        tags=[
            ["p", event.pubkey],
            ["e", event.id],
            ["R", "claude_files"],
            ["status", "partial"]
        ]
    )

    yield job_result_event

    final = best_solution_claude_call(issue["title"], issue["body"], file_paths_to_review)

    job_result_event = Event(
        kind=65001,  # code review job result
        content=final,  # use the JSON string here
        tags=[
            ["p", event.pubkey],
            ["e", event.id],
            ["R", "claude_solution"],
            ["status", "success"]
        ]
    )

    yield job_result_event



print(code_review(Event(content="https://github.com/ArcadeLabsInc/arcade/issues/466")))