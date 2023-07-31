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

    ln_callback = get_callback(msats=10000000)

    invoice = ln_callback["pr"]

    log.info(ln_callback)

    verify_url = ln_callback["verify"]

    ack_event = Event(
        kind=65001,  # code review job result
        content=f"""
I'm your claude code auditor.   I will be auditing github issue:

## {issue["title"]}
```
{issue["body"]}
```

Prepare to be claudited.
        """,  # use the JSON string here
        tags=[
            ["p", event.public_key],
            ["e", event.id],
            ["R", "issue_ack"],
            ["issue", issue_msg],
            ["status", "processing"],
            ["amount", "10000000", invoice],
            ["verify_url", verify_url],
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

    fil_str = ""
    for fil in file_paths_to_review:
        descr = pruned_descriptions.get(fil, "")
        fil_str += f"""
 - {fil} : {descr}
        """

    content_str = f"""
I have analyzed the repository, and determined that these files need 
a closer review for this issue.   It will take a couple minutes to 
analyze further.

Files:

{fil_str}
"""
    job_result_tmp = Event(
        kind=65001,  # code review job result
        content=content_str,  # use the JSON string here
        tags=[
            ["p", event.public_key],
            ["e", event.id],
            ["R", "claude_files"],
            ["issue", issue_msg],
            ["file_paths", json.dumps(file_paths_to_review)],
            ["status", "payment_required"],
            ["amount", "10000000", invoice],
            ["verify_url", verify_url],
        ],
    )

    yield job_result_tmp

    # Wait for the payment to be made by polling against the verify_url

    got_payment = False
    done_waiting = time.monotonic() + 300
    while time.monotonic() < done_waiting:
        res = requests.get(verify_url)
        if res.status_code != 200:
            raise Exception(f"Error: payment verification failure  {res.status_code}")
        if res.json()["settled"]:
            log.debug("Payment received!")
            got_payment = True
            break
        log.debug("Waiting for payment...")
        time.sleep(3)

    if not got_payment:
        pay_fail_event = Event(
            kind=65001,  # code review job result
            content="Payment failed.  Try again later.",  # use the JSON string here
            tags=[
                ["p", event.public_key],
                ["e", event.id],
                ["R", "claude_solution"],
                ["status", "error"],
            ]
        )
        yield pay_fail_event
        return

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
