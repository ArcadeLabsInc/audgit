import re
from pynostr.event import Event
from audgit.claude_call import which_files_claude_call
from audgit.get_repo_files import get_file_tree
import requests
import json
import os
from dotenv import load_dotenv
from pynostr.key import PrivateKey
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
private_key = PrivateKey.from_hex(os.getenv("NOSTR_PRIVKEY"))


def code_review(event: Event):
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
    # print_file_tree(file_paths)

    # file_contents = get_file_contents(local_path, file_paths)

    # Print file paths and contents
    # for path, content in file_contents.items():
    #     print(f"Path: {path}")
    #     # print(
    #     #     f"Content: {content[:100]}..."
    #     # )  # Print only the first 100 characters for brevity

    # convert the file_paths to json and send to the event
    file_paths_json = json.dumps(file_paths)
    claude_res = which_files_claude_call(issue["title"], issue["body"], file_paths_json)
    print("Got claude_res...")
    print(claude_res)
    pattern = r"\[[^\]]*\]"

    match = re.findall(pattern, claude_res)

    # parse the matched json string back to list
    file_paths_to_review = json.loads(match[0]) if match else []
    print("Got file_paths_to_review...")
    print(file_paths_to_review)
    # file_contents_json = json.dumps(file_contents)

    log.debug("Creating event...")
    # create the event
    # Convert the dictionary into a JSON string
    content_str = json.dumps(
        {
            "issue": issue,
            "file_paths": file_paths_to_review,
            "claude_res": claude_res,
            # "file_contents": file_contents_json,
        }
    )

    stringified_event = json.loads(str(event))
    print("Stringified event: " + str(stringified_event))

    job_result_event = Event(
        kind=65001,  # code review job result
        content=content_str,  # use the JSON string here
        tags=[
            ["p", event.pubkey],
            ["e", event.id],
            ["R", "tree_summary"],
            ["status", "partial"]
        ],  # add a tag to indicate the status of the job
        pubkey=private_key.public_key.hex(),  # assuming you want the hex value of the public key
    )

    log.debug("Signing event...")
    # sign event
    job_result_event.sign(private_key.hex())
    # send event
    return event


print(code_review(Event(content="https://github.com/ArcadeLabsInc/arcade/issues/466")))
