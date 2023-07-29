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

# Define the headers to be used in the requests
headers = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {TOKEN}",
}

# Generate a new keypair for the demonstration
private_key = PrivateKey.from_hex(os.getenv("NOSTR_PRIVKEY"))


def code_review(event: Event):
    print("Got event...")
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
    print("Got issue...")

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
    # file_contents_json = json.dumps(file_contents)

    print("Creating event...")
    # create the event
    # Convert the dictionary into a JSON string
    content_str = json.dumps(
        {
            "issue": issue,
            "file_paths": file_paths_json,
            # "file_contents": file_contents_json,
        }
    )

    event = Event(
        kind=65001,  # code review job result
        content=content_str,  # use the JSON string here
        pubkey=private_key.public_key.hex(),  # assuming you want the hex value of the public key
    )
    print("Created event...")

    print("Signing event...")
    # sign event
    event.sign(private_key.hex())
    print("Signed event: " + str(event))

    # send event
    return event
