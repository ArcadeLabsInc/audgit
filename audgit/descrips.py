"""make file descrips for better lookup of relevant files"""

from audgit.get_repo_files import get_file_tree


def generate_file_descrips(paths):
    """what"""
    filtered_paths = filter_filepaths(paths)
    print("Generating descriptions for filtered_paths:", filtered_paths)



def filter_filepaths(paths):
    """filter out non-relevant files"""
    print("Filtering paths.")

    # Filter out file suffixes
    bad_suffixes = ['.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.ttf', '.woff', '.woff2', '.eot', '.mp4', '.mp3', '.wav', '.ogg', '.webm', '.zip', '.tar', '.gz', '.rar', '.7z', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.exe', '.dll', '.so', '.a', '.o', '.obj', '.lib', '.pyc', '.pyo', '.class', '.jar', '.war', '.ear', '.iml', '.idea', '.DS_Store', '.gitignore', '.gitattributes', '.gitmodules', '.gitkeep', '.git', '.hgignore', '.hg', '.svn', '.cvs', '.bzrignore', '.bzr', '.npmignore', '.npmrc', '.yarnrc', '.yarnclean', '.yarn-integrity', '.yarnclean', '.yarn-metadata.json', '.yarn-tarball.tgz', '.yarncl']

    # Filter out file prefixes
    bad_prefixes = ['ios', 'android', '.git', '.hg', '.svn', '.cvs', '.bzr', '.npm', '.yarn']

    # Use list comprehension to filter out bad suffixes and prefixes
    filtered_paths = [path for path in paths if not any(path.endswith(suffix) for suffix in bad_suffixes) and not any(path.startswith(prefix) for prefix in bad_prefixes)]

    print("Filtered paths.", filtered_paths)
    return filtered_paths




if __name__ == "__main__":
    REPO = "arcade"
    repo_url = f"https://github.com/ArcadeLabsInc/{REPO}.git"
    local_path = f"/tmp/repo/{REPO}"  # Define the local path where the repo is cloned
    file_paths = get_file_tree(repo_url, local_path)
    generate_file_descrips(file_paths)
