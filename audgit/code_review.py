import time
from pynostr.event import Event
from typing import Optional
from audgit.get_repo_files import get_file_tree, get_file_contents, print_file_tree
import requests
import json
import os
from dotenv import load_dotenv

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
    file_paths = get_file_tree(repo_url)
    print_file_tree(file_paths)
    time.sleep(3)

    file_contents = get_file_contents(owner, repo, file_paths)

    # Print file paths and contents
    for path, content in file_contents.items():
        print(f"Path: {path}")
        print(
            f"Content: {content[:100]}..."
        )  # Print only the first 100 characters for brevity

    return "OK"


code_review("https://github.com/fedimint/fedimint/issues/2858")
