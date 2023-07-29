import requests
import os
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT

from dotenv import load_dotenv

# load the .env file. By default, it looks for the .env file in the same directory as the script
# If your .env file is one directory up, you need to specify the path
load_dotenv("/Users/kody/Documents/github/python/audgit/.env")

# Load the token from an environment variable
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """
You are a Rust open source developer conducting a code review. 
Your name is Rusty the Rustacean, the most sarcastic and full of himself developer to ever write Rust code. 
You know better and aren't afraid to let the other coder who you're reviewing know. You exclusively write Rust code. 
Whenever anyone asks you to review code for them not written in Rust, 
you sarcastically respond with a joke and story about why they shouldn't be using the langauge they're using. 
You then attempt to rewrite their code in Rust. 
You include inline comments remarking on the amazing things you're able to do with Rust. 
After rewriting their code, you make some observations about all the trouble you've saved them by rewriting their code in Rust.
"""

# remove all newlines from the prompt
SYSTEM_PROMPT = SYSTEM_PROMPT.replace("\n", " ")
print(SYSTEM_PROMPT)


def claude_call(code: str):
    anthropic = Anthropic()
    completion = anthropic.completions.create(
        model="claude-2",
        max_tokens_to_sample=3000,
        prompt=f"{HUMAN_PROMPT} \n\nPersona: {SYSTEM_PROMPT} \n\nCode You're reviewing:{code} {AI_PROMPT}",
    )
    print(completion.completion)
    return completion.completion


code_to_review = """
import requests
import base64
import os
from dotenv import load_dotenv
from typing import Optional
import subprocess

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


def get_file_tree(repo_url: str, local_path: str = "/tmp/repo"):
   \"\"\"
    Clone a repository and return the tree structure
    \"\"\"
    if not os.path.exists(local_path):
        print("Cloning...")
        # Clone the repository
        result = subprocess.run(
            ["git", "clone", repo_url, local_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if result.returncode != 0:
            print(f"Error cloning repository: {result.stderr.decode('utf-8')}")
            return []
    else:
        print("Repository already exists. Skipping clone.")

    file_paths = []

    # Walk the repository
    for root, dirs, files in os.walk(local_path):
        for file in files:
            # Get the full file path
            full_path = os.path.join(root, file)

            # Remove the local path from the start of the file path
            relative_path = os.path.relpath(full_path, local_path)

            file_paths.append(relative_path)

    return file_paths


def get_file_contents(local_path: str, file_paths: list):
   \"\"\"
    This function opens each file in a repository and reads its contents.
    It returns a dictionary where the keys are the file paths and the values are the file contents.
    \"\"\"
    # Dictionary to hold the file contents
    contents = {}

    for file_path in file_paths:
        # Combine the base local path with the file path to get the full path
        full_path = os.path.join(local_path, file_path)

        try:
            with open(full_path, "r") as file:
                # Read the file content and store it in the dictionary
                contents[file_path] = file.read()
        except Exception as e:
            print(f"Error reading file {full_path}: {e}")

    return contents


def print_file_tree(file_paths: list):
    \"\"\"
    Prints the file tree structure
    \"\"\"
    file_tree = {}

    for file_path in file_paths:
        current_level = file_tree
        parts = file_path.split("/")
        for part in parts:
            if part not in current_level:
                current_level[part] = {}
            current_level = current_level[part]

    def print_tree(current_level: dict, prefix: str = ""):
        for part in current_level:
            new_prefix = os.path.join(prefix, part)
            print(f"└─ {new_prefix}")
            if len(current_level[part]) > 0:
                print_tree(current_level[part], new_prefix)

    # def print_tree(current_level: dict, prefix: str = ""):
    #     for part in current_level:
    #         print(f"{prefix}└─ {part}")
    #         if len(current_level[part]) > 0:
    #             print_tree(current_level[part], prefix + "  ")

    print_tree(file_tree)

"""

claude_call(code_to_review)
