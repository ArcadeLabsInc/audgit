import json
import mimetypes
import re
import threading
import queue
from dataclasses import dataclass
from typing import Generator, Optional

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging as log

from github import Github, Auth

@dataclass
class Repo:
    provider: str
    auth: str
    org: str
    repo: str

@dataclass
class CrawlOutput:
    url: str
    content: bytes
    content_type: str

def safe_get(url: str, max_page_size: int) -> None | tuple[bytes, str | None]:
    try:
        response = requests.get(url, stream=True, timeout=5)
    except requests.exceptions.RequestException as e:
        log.info("exception fetching %s", e)
        return None

    content_size = 0
    content_chunks = []

    for chunk in response.iter_content(chunk_size=1024):
        content_size += len(chunk)
        content_chunks.append(chunk)
        if content_size > max_page_size:
            log.warning("ignoring the rest of %s: too big", url)
            break

    content = b''.join(content_chunks)
    return content, response.headers.get("content-type")


DEFAULT_MAX_DEPTH = 10
DEFAULT_TOTAL_SIZE = 50 * 1000 * 1000
DEFAULT_MAX_PAGE_SIZE = 1 * 1000 * 1000
DEFAULT_MAX_PAGES = 1000

class Crawler:
    """Crawls urls, yields content, content, types."""
    def __init__(self, max_depth = DEFAULT_MAX_DEPTH, max_total_size = DEFAULT_TOTAL_SIZE, max_page_size = DEFAULT_MAX_PAGE_SIZE, max_pages = DEFAULT_MAX_PAGES):
        self.max_depth = max_depth
        self.max_total_size = max_total_size
        self.max_page_size = max_page_size
        self.max_pages = max_pages
        self.abort_reason = ""

    def worker(self, work_queue: queue.Queue[str], output_queue: queue.Queue[CrawlOutput | None], depth: int, within: str):
        visited_urls = set()
        content_count = 0
        content_size = 0
        total_size = 0

        try:
            while True:
                try:
                    current_url = work_queue.get_nowait()
                except queue.Empty:
                    output_queue.put(None)
                    break

                if current_url in visited_urls:
                    continue

                visited_urls.add(current_url)
                log.debug("crawler: processing: %s", current_url)

                try:
                    res = safe_get(current_url, self.max_page_size)
                    if not res:
                        log.info("url returned none %s", current_url)
                        continue
                    content, content_type = res
                except requests.exceptions.RequestException as e:
                    log.error("error: %s", e)
                    continue

                content_count += 1
                content_size += len(content)
                total_size += content_size

                if content_count > self.max_pages or total_size > self.max_total_size:
                    self.abort_reason = "size"
                    log.info("aborting crawl because max size/pages: %s", within)
                    output_queue.put(None)
                    break

                output_queue.put(CrawlOutput(url=current_url, content=content, content_type=content_type))

                if depth > 0:
                    if "html" in content_type:
                        soup = BeautifulSoup(content, 'html.parser')
                        # Find all links on the current page
                        links = soup.find_all('a')
                        for link in links:
                            href = link.get('href')
                            if href:
                                href = href.split('#', 1)[0]
                                # Construct absolute URL for each link
                                absolute_url = urljoin(current_url, href)
                                if absolute_url.startswith(within):
                                    log.debug("crawler: found descendant URL: %s", absolute_url)
                                    work_queue.put(absolute_url)
                else:
                    self.abort_reason = "depth"
                    log.info("aborting crawl because depth: %s", within)

            depth -= 1
        except Exception as e:
            # prevent possibility of infinity
            log.exception("error in worker: %s", e)
            output_queue.put(None)

    def crawl(self, url: str) -> Generator[CrawlOutput, None, None]:
        """Main entry point for crawler, allows url to be of this form: http://site.com/faq/*home

        That means start at /faq/home, but crawl the whole /faq.
        """
        url, within = split_within(url)
        if is_repo_root(url):
            yield from self.crawl_repo(url)
        else:
            yield from self.crawl_web(url, within)

    def crawl_web(self, url: str, within: str) -> Generator[CrawlOutput, None, None]:
        work_queue = queue.Queue[str]()
        output_queue = queue.Queue[CrawlOutput]()
        work_queue.put(url)

        worker_thread = threading.Thread(
            target=self.worker,
            args=(work_queue, output_queue, self.max_depth, within),
            daemon=True
        )
        worker_thread.start()

        while True:
            content = output_queue.get()
            if content is None:
                break

            yield content

    def crawl_repo(self, url: str) -> Generator[CrawlOutput, None, None]:
        repo = parse_repo_url(url)
        if repo.provider == "github":
            yield from self.crawl_github(repo)

    def crawl_github(self, repo: Repo) -> Generator[CrawlOutput, None, None]:
        auth_info = parse_auth(repo.auth)
        gh = Github(auth=auth_info)
        gh_repo = gh.get_repo(repo.org + "/" + repo.repo)

        total_size = 0
        def check_size(cont):
            nonlocal total_size
            total_size += len(cont)
            if total_size > self.max_total_size:
                self.abort_reason = "size"
                log.warning("stopping parse of repo because of size: %s", repo)
                return False
            return True


        issues = gh_repo.get_issues()
        for issue in issues:
            url = issue.url
            content = json.dumps({
            "type": "issue",
            "title": issue.title,
            "state": issue.state,
            "comments": issue.comments,
            "body": issue.body
            }).encode()
            content_type = "text/json"

            total_size += len(content)
            if total_size > self.max_total_size:
                self.abort_reason = "size"
                log.warning("stopping parse of repo because of size: %s", repo)

            if not check_size(content):
                return
            yield CrawlOutput(url=url, content=content, content_type=content_type)

        pulls = gh_repo.get_pulls()
        for pr in pulls:
            url = pr.url
            content = json.dumps({
            "type": "pull_request",
            "title": pr.title,
            "state": pr.state,
            "comments": pr.comments,
            "body": pr.body
            }).encode()
            content_type = "text/json"
            if not check_size(content):
                return
            yield CrawlOutput(url=url, content=content, content_type=content_type)

        sources = gh_repo.get_contents("")
        while sources:
            fil = sources.pop(0)
            if fil.type == "dir":
                sources.extend(gh_repo.get_contents(fil.path))
                continue
            url = fil.url
            if fil.encoding:
                content = fil.decoded_content
            else:
                content = fil.content
            if not content:
                continue
            if not check_size(content):
                return
            content_type, _encoding = mimetypes.guess_type(fil.path, strict=False)
            yield CrawlOutput(url=url, content=content, content_type=content_type)

def parse_auth(auth: str | None) -> Optional[Auth]:
    if auth and ":" in auth:
        user, pwd = auth.split(":", 1)
        return Auth.Login(user, pwd)
    elif auth:
        token = auth
        return Auth.Token(token)
    return None

def parse_github_url(url: str) -> Repo | None:
    # only root links are seen as repo clones
    match = re.match(r"https?://(?:([^@]*)@)?(?:www.)?github.com/([^/]+)/([^/]+)/?$", url)
    if not match:
        return None
    auth = match[1]
    org = match[2]
    repo = match[3]
    return Repo("github", auth, org, repo)

def parse_repo_url(url: str) -> Repo | None:
    repo = parse_github_url(url)
    if repo:
        return repo
    return None

def is_repo_root(url: str) -> bool:
    return bool(parse_repo_url(url))

def split_within(url: str):
    # if the url looks like this, split it
    # http://www.com/where*/index.html
    comp = url.split('*', 1)
    if len(comp) == 1:
        return comp[0], comp[0]
    return "".join(comp), comp[0]
