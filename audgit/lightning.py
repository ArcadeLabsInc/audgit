import requests

import os
from dotenv import load_dotenv

# load the .env file. By default, it looks for the .env file in the same directory as the script
# If your .env file is one directory up, you need to specify the path
load_dotenv("/Users/kody/Documents/github/python/audgit/.env")

# Load the lightning address from an environment variable
LIGHTNING_ADDRESS = os.getenv("LIGHTNING_ADDRESS")


def get_callback_url(lnaddr: str):
    # split the lightning address into username@domain.com
    parts = lnaddr.split("@")
    username = parts[0]
    domain = parts[1]

    res = requests.get(f"https://{domain}/.well-known/lnurlp{username}")
    if res.status_code != 200:
        raise Exception(f"Error: API request status {res.status_code}")
    callback = res.json()["callback"]
    return callback


def callback(msats: int):
    c = get_callback_url(LIGHTNING_ADDRESS)
    res = requests.get(f"{callback}?amount={msats}")
    if res.status_code != 200:
        raise Exception(f"Error: API request status {res.status_code}")
    return res.json()

