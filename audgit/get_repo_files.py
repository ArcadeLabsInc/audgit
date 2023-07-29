import requests
import base64
import os

# Load the token from an environment variable
TOKEN = os.getenv('GITHUB_TOKEN')


def get_repo_files(owner: str, repo: str):
    """
    Expected input is a GitHub owner and repo
    """

    # Construct the GitHub API url
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"

    # use the github api to get the contents of the repo
    headers = {"Accept": "application/vnd.github.v3+json"}
    response = requests.get(api_url, headers=headers)

    # Ensure the request was successful
    if response.status_code != 200:
        raise Exception(f"Error: API request status {response.status_code}")

    contents = response.json()

    # Iterate over each file in the directory
    for content in contents:
        if content["type"] == "file":
            # The content of the file is base64 encoded, so we need to decode it
            file_content = base64.b64decode(content["content"]).decode("utf-8")
            print(f"File {content['name']}:")
            print(file_content)
        else:
            print(f"Directory {content['name']} found, contents not fetched.")
