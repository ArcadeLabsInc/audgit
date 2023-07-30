"""make file descrips for better lookup of relevant files"""

from audgit.get_repo_files import get_file_tree


def generate_file_descrips(paths):
    """what"""
    print("Generating descriptions.")



if __name__ == "__main__":
    REPO = "arcade"
    repo_url = f"https://github.com/ArcadeLabsInc/{REPO}.git"
    local_path = f"/tmp/repo/{REPO}"  # Define the local path where the repo is cloned
    file_paths = get_file_tree(repo_url, local_path)
    generate_file_descrips(file_paths)
