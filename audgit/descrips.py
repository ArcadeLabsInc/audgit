"""make file descrips for better lookup of relevant files"""

import os
import json
import tempfile

from audgit.get_repo_files import get_file_tree


def complete(prompt):
    wompwomp = "WOMPWOMP: " + prompt + " WOMP"
    return wompwomp


def generate_file_descrips(paths):
    """what"""
    filtered_paths = filter_filepaths(paths)
    print("Generating descriptions for filtered_paths.")
    pierre = ThankYouPierre("ArcadeLabsInc", "arcade", "/tmp/repo/arcade")
    print("Hello pierre.")
    descriptions = pierre.get_descriptions()
    print(descriptions)




def filter_filepaths(paths):
    """filter out non-relevant files"""

    # Filter out file suffixes
    bad_suffixes = ['.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.ttf', '.woff', '.woff2', '.eot', '.mp4', '.mp3', '.wav', '.ogg', '.webm', '.zip', '.tar', '.gz', '.rar', '.7z', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.exe', '.dll', '.so', '.a', '.o', '.obj', '.lib', '.pyc', '.pyo', '.class', '.jar', '.war', '.ear', '.iml', '.idea', '.DS_Store', '.gitignore', '.gitattributes', '.gitmodules', '.gitkeep', '.git', '.hgignore', '.hg', '.svn', '.cvs', '.bzrignore', '.bzr', '.npmignore', '.npmrc', '.yarnrc', '.yarnclean', '.yarn-integrity', '.yarnclean', '.yarn-metadata.json', '.yarn-tarball.tgz', '.yarncl']

    # Filter out file prefixes
    bad_prefixes = ['ios', 'android', '.git', '.hg', '.svn', '.cvs', '.bzr', '.npm', '.yarn']

    # Use list comprehension to filter out bad suffixes and prefixes
    filtered_paths = [path for path in paths if not any(path.endswith(suffix) for suffix in bad_suffixes) and not any(path.startswith(prefix) for prefix in bad_prefixes)]

    return filtered_paths


class ThankYouPierre():
    extensions = ('.js', '.jsx', '.py', '.json', '.html', '.css', '.scss', '.yml', '.yaml', '.ts', '.tsx', '.ipynb', '.c', '.cc', '.cpp', '.go', '.h', '.hpp', '.java', '.sol', '.sh', '.txt')
    directory_blacklist = ('build', 'dist', '.github', 'site', 'tests')
    def __init__(self, org, name, repo_dir='repos'):
        self.org = org
        self.name = name
        self.dir = repo_dir

        self.remote_path = f'{org}/{name}'
        self.local_path = "/tmp/repo/arcade" # f'{repo_dir}/{name}'

        self.num_files = 345

    def walk(self, max_num_files=1000):
        num_files = 0
        for root, dirs, files in os.walk(self.local_path, topdown=True):
            files = [f for f in files if not f[0] == '.' and f.endswith(ThankYouPierre.extensions)]
            dirs[:] = [d for d in dirs if d[0] != '.' and not d.startswith(ThankYouPierre.directory_blacklist)]
            for name in files:
                filename = os.path.join(root, name)

                try:
                    with open(filename, 'r') as f:
                        code = f.read()
                except UnicodeDecodeError:
                    continue

                if code.strip() == '': continue

                if num_files >= max_num_files:
                    return

                yield filename, root, dirs, code

                num_files += 1
                self.num_files = num_files

    def load_descriptions(self):
        save_path = f'embeddings/{self.name}_descriptions.json'
        if not os.path.exists(save_path):
            return None
        with open(save_path, 'rb') as f:
            data = json.load(f)
        return data

    def get_descriptions(self, save=True, save_every=10):
        descriptions = self.load_descriptions()
        print(descriptions)
        if descriptions is not None and len(descriptions) == self.num_files:
            return descriptions

        if descriptions is None:
            descriptions = {}

        generator = self.walk()
        description_prompt = 'A short summary in plain English of the above code is:'
        num_files = len(descriptions)
        for filename, root, dirs, code in generator:
            # Skip files that already have descriptions
            if filename in descriptions:
                continue
            extension = filename.split('.')[-1]
            prompt = f'File: {filename}\n\nCode:\n\n```{extension}\n{code}```\n\n{description_prompt}\nThis file'
            description = 'This file ' + complete(prompt)
            descriptions[filename] = description

            if save and (num_files % save_every == 0):
                print(f'Saving descriptions for {num_files} files')
                self.save_descriptions(descriptions)

            num_files += 1

        if save:
            self.save_descriptions(descriptions)

        return descriptions

    def save_descriptions(self, descriptions):
        save_path = os.path.join(tempfile.gettempdir(), f"{self.name}_descriptions.json")
        # save_path = f'embeddings/{self.name}_descriptions.json'
        with open(save_path, 'w') as f:
            json.dump(descriptions, f)


if __name__ == "__main__":
    REPO = "arcade"
    repo_url = f"https://github.com/ArcadeLabsInc/{REPO}.git"
    local_path = f"/tmp/repo/{REPO}"  # Define the local path where the repo is cloned
    file_paths = get_file_tree(repo_url, local_path)
    generate_file_descrips(file_paths)
