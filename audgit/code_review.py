import time
from pynostr.event import Event
from typing import Optional
from audgit.get_repo_files import get_file_tree, get_file_contents, print_file_tree
import requests
import json
import os
from dotenv import load_dotenv
from pynostr.key import PrivateKey

# load the .env file. By default, it looks for the .env file in the same directory as the script
# If your .env file is one directory up, you need to specify the path
load_dotenv("/Users/kody/Documents/github/python/audgit/.env")


# Load the token from an environment variable
TOKEN = os.getenv("GITHUB_TOKEN")
print("TOKEN: ", TOKEN)

# Define the headers to be used in the requests
headers = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {TOKEN}",
}

# Generate a new keypair for the demonstration
private_key = PrivateKey.from_hex(os.getenv("NOSTR_PRIVKEY"))

def code_review(issue_url: str):
    parts = issue_url.split("/")
    issue_number = parts[-1]
    repo = parts[-3]
    owner = parts[-4]

    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    response = requests.get(api_url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Error: API request status {response.status_code}")

    issue = response.json()
    print("Got issue...")

    repo_url = f"https://github.com/{owner}/{repo}.git"
    local_path = "/tmp/repo"  # Define the local path where the repo is cloned
    file_paths = get_file_tree(repo_url, local_path)
    print_file_tree(file_paths)
    time.sleep(3)

    file_contents = get_file_contents(local_path, file_paths)

    # Print file paths and contents
    for path, content in file_contents.items():
        print(f"Path: {path}")
        # print(
        #     f"Content: {content[:100]}..."
        # )  # Print only the first 100 characters for brevity

    # convert the file_paths to json and send to the event
    file_paths_json = json.dumps(file_paths)
    file_contents_json = json.dumps(file_contents)

    # create the event
    event = Event(
        kind=65001,  # code review
        content={
            "issue": issue,
            "file_paths": file_paths_json,
            "file_contents": file_contents_json,
        },
        pubkey="",
    )
