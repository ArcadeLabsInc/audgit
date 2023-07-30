import time
from nostr.event import Event
from audgit.claude_call import which_files_claude_call, best_solution_claude_call
from audgit.descrips import generate_file_descrips
from audgit.get_repo_files import get_file_tree
import requests
import json
import os
from dotenv import load_dotenv
import logging

from audgit.lightning import get_callback

log = logging.getLogger("audgit")

# load the .env file. By default, it looks for the .env file in the same directory as the script
# If your .env file is one directory up, you need to specify the path
load_dotenv()

# Load the token from an environment variable
TOKEN = os.environ["GITHUB_TOKEN"]

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

    issue_msg = json.dumps(
        {
            "issue_title": issue["title"],
            "issue_body": issue["body"],
        }
    )

    ack_event = Event(
        kind=65001,  # code review job result
        content=issue_msg,  # use the JSON string here
        tags=[
            ["p", event.public_key],
            ["e", event.id],
            ["R", "issue_ack"],
            ["status", "processing"],
            ["amount", "1000", invoice],
        ],
    )

    yield ack_event

    repo_url = f"https://github.com/{owner}/{repo}.git"
    local_path = f"/tmp/repo/{repo}"  # Define the local path where the repo is cloned

    file_paths = get_file_tree(repo_url, local_path)

    files_with_descriptions = generate_file_descrips(
        file_paths, owner, repo, f"/tmp/repo/{repo}"
    )

    pruned_descriptions = {
        k.replace(local_path, "").lstrip("/").lstrip("\\"): v
        for k, v in files_with_descriptions.items()
    }

    file_paths_to_review: list[str] = which_files_claude_call(
        issue["title"], issue["body"], pruned_descriptions
    )

    full_paths = [
        os.path.join(local_path, fil.lstrip("/").lstrip("\\"))
        for fil in file_paths_to_review
    ]

    content_str = json.dumps(
        {
            "issue": issue["title"],
            "file_paths": file_paths_to_review,
            # "file_contents": file_contents_json,
        }
    )

    ln_callback = get_callback(msats=1000)
    invoice = ln_callback["pr"]
    verify_url = ln_callback["verify"]

    job_result_event = Event(
        kind=65001,  # code review job result
        content=content_str,  # use the JSON string here
        tags=[
            ["p", event.public_key],
            ["e", event.id],
            ["R", "claude_files"],
            ["status", "payment_required"],
            ["amount", "1000", invoice],
        ],
    )

    yield job_result_event

    # Wait for the payment to be made by polling against the verify_url
    #    while True:
    #        res = requests.get(verify_url)
    #        if res.status_code != 200:
    #            raise Exception(f"Error: API request status {res.status_code}")
    #        if res.json()["settled"]:
    #            log.debug("Payment received!")
    #            break
    #        log.debug("Waiting for payment...")
    #        time.sleep(3)

    final = best_solution_claude_call(issue["title"], issue["body"], full_paths)

    job_result_event = Event(
        kind=65001,  # code review job result
        content=final,  # use the JSON string here
        tags=[
            ["p", event.public_key],
            ["e", event.id],
            ["R", "claude_solution"],
            ["status", "success"],
        ],
    )

    yield job_result_event
