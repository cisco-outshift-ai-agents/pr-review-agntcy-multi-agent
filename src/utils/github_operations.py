import base64
from http import HTTPStatus
import io
import os
from dataclasses import asdict, dataclass
from typing import Optional, Tuple
import zipfile
from typing import Optional

import github.Auth
from github import Github, GithubException, GithubIntegration, UnknownObjectException
from github.Commit import Commit
from github.PullRequest import PullRequest
from github.Repository import Repository
import requests

from utils.logging_config import logger as log
from utils.models import Comment

GithubOperationException = GithubException


@dataclass
class GitHubReviewComment:
    body: str
    path: str
    line: int
    side: str


class InvalidGitHubInitialization(Exception):
    """Exception raised for invalid GitHub initialization"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class GitHubOperations:
    """
    GitHubOperations class provides generic GitHub operations for managing repositories,
    branches, files, and pull requests.
    """

    def __init__(self, installation_id: str, repo_name: str, pr_number: Optional[int] = None):
        if not isinstance(installation_id, str) or not isinstance(repo_name, str) or not isinstance(pr_number, int):
            raise InvalidGitHubInitialization("Invalid input parameters")

        try:
            self._github: Github = self._init_github(installation_id)
            self._repo: Repository = self._github.get_repo(repo_name)
            if pr_number:
                self._pr: PullRequest = self._repo.get_pull(pr_number)
        except Exception as e:
            log.error(f"Failed to initialize GitHub client: {e}")
            raise InvalidGitHubInitialization(f"Failed to initialize GitHub client: {e}") from e

    @property
    def repo(self) -> Repository:
        return self._repo

    @property
    def pr(self) -> PullRequest:
        return self._pr

    def _init_github(self, installation_id: str) -> Github:
        """Initialize GitHub client with app credentials"""
        try:
            private_key = self._get_private_key()
            app_id = self._get_app_id()

            git_integration = GithubIntegration(auth=github.Auth.AppAuth(app_id, private_key))

            github_token = git_integration.get_access_token(int(installation_id)).token
            self.__github_token = github_token

            return Github(github_token)
        except Exception as e:
            log.error(f"Invalid GitHub credentials: {e}")
            raise

    def _get_private_key(self) -> str:
        """Get private key from file or environment variable"""
        key_file_path = os.getenv("GITHUB_APP_PRIVATE_KEY_FILE")
        if key_file_path:
            try:
                with open(key_file_path, "r") as key_file:
                    return key_file.read()
            except IOError as e:
                log.error(f"Failed to read private key file: {e}")
                raise

        private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
        if not private_key:
            raise ValueError("Neither GITHUB_APP_PRIVATE_KEY_FILE nor GITHUB_APP_PRIVATE_KEY is set")

        try:
            private_key_bytes = base64.b64decode(private_key)
            return private_key_bytes.decode()
        except Exception as e:
            log.error(f"Failed to decode private key: {e}")
            raise

    def _get_app_id(self) -> str:
        """Get GitHub App ID from environment variable"""
        app_id = os.getenv("GITHUB_APP_ID")
        if not app_id:
            raise ValueError("GITHUB_APP_ID environment variable is not set")
        return app_id

    def create_comments(self, new_comments: list[Comment], title_desc_comment: Optional[Comment] = None) -> None:
        try:
            files = self.pr.get_files()
        except UnknownObjectException:
            log.error(f"repo: {self.repo._name} with pr: {self.pr._number} not found")
            return
        except Exception as error:
            log.error(f"General error while fetching repo: {self.repo._name} with pr: {self.pr._number}. error: {error}")
            return
        latest_commit = list(self.pr.get_commits())[-1].commit
        commit = self.repo.get_commit(latest_commit.sha)

        comments_transformed: list[GitHubReviewComment] = []

        for pr_file in files:
            for comment in new_comments:
                if comment.filename == pr_file.filename:
                    c = GitHubReviewComment(
                        comment.comment, pr_file.filename, int(comment.line_number), "LEFT" if comment.status == "removed" else "RIGHT"
                    )

                    comments_transformed.append(c)
        for comment in new_comments:
            if comment.line_number == 0:
                # Response comment for a re-review
                self.pr.create_issue_comment(comment.comment)

        # Create summary comment
        if title_desc_comment:
            self.pr.create_issue_comment(title_desc_comment.comment)

        if len(comments_transformed) > 0:
            self.create_pull_request_review_comments(commit, comments_transformed)

    def create_pull_request(self, repo_name: str, branch_name: str, base_branch: str, title: str, body: str) -> bool:
        """Creates a pull request in the repository"""
        try:
            repo = self._github.get_repo(repo_name)
            if base_branch is None:
                base_branch = repo.default_branch

            pulls = repo.get_pulls(state="open")
            pr_exists = any(pr.head.ref == branch_name for pr in pulls)

            if pr_exists:
                log.info("Pull request already exists.")
                return True

            repo.create_pull(title=title, body=body, head=branch_name, base=base_branch)
            log.info("Pull request created successfully.")
            return True
        except GithubException as e:
            log.error(f"Failed to create pull request: {e.data}")
            return False

    def get_file(self, repo_name: str, file_path: str, ref: Optional[str] = None) -> Tuple[bool, Optional[ContentFile]]:
        """Gets a file from the repository"""
        try:
            repo: Repository = self._github.get_repo(repo_name)
            if ref is None:
                ref = repo.default_branch
            contents: list[ContentFile] | ContentFile = repo.get_contents(file_path, ref=ref)

            if isinstance(contents, list):
                raise ValueError("Expected a single file, but got multiple files")

            return True, contents
        except GithubException as e:
            if e.status == 404:
                return False, None
            raise e

    def get_file_content(self, repo_name: str, file_path: str, ref: Optional[str] = None) -> Optional[str]:
        """Gets the decoded content of a file from the repository"""
        try:
            repo: Repository = self._github.get_repo(repo_name)
            if ref is None:
                ref = repo.default_branch

            file: ContentFile | list[ContentFile] = repo.get_contents(file_path, ref=ref)
            if isinstance(file, list):
                raise ValueError("Expected a single file, but got multiple files")

            return base64.b64decode(file.content).decode("utf-8")
        except Exception as e:
            log.error(f"Error getting file content: {e}")
            return None

    def get_default_branch(self, repo_name: str) -> str:
        """Gets the default branch name of a repository"""
        try:
            repo = self._github.get_repo(repo_name)
            return repo.default_branch
        except GithubException as e:
            log.error(f"Failed to get default branch: {e.data}")
            raise

    def get_repo(self, repo_name: str) -> Repository:
        """Gets a repository from the GitHub API"""
        return self._github.get_repo(repo_name)

    def clone_repo(self, repo_name: str, pr_number: int, destination_folder: str) -> str:
        """Clone the PR's branch content into a folder, returns the path to the repo"""

        log.debug("Cloning the repo into a local folder...")

        repo = self.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        zip_link = repo.get_archive_link("zipball", pr.head.ref)

        response = requests.get(zip_link, headers={"Authorization": f"token {self.__github_token}"})

        if response.status_code != HTTPStatus.OK:
            raise ValueError(f"Error while downloading the repo as ZIP, status code: {response.status_code}")

        log.debug("Repo downloaded successfully")

        zip_file_in_memory = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_file_in_memory, "r") as zip_ref:
            file_list = zip_ref.namelist()
            if not file_list:
                raise ValueError("Cloned repo is empty or the zip is cossupted")

            # Inside the zip there's a folder named (repo-name-<commit-hash>), we would like to return this folder name
            folder_name = file_list[0].split("/")[0]

            zip_ref.extractall(destination_folder)
            log.debug("Repo extracted successfully")

            return f"{destination_folder}/{folder_name}"

    def list_comments_from_pr(self, repo_full_name: str, pr_number: int) -> PaginatedList[PullRequestComment]:
        repo = self._github.get_repo(repo_full_name)
        pull_request = repo.get_pull(pr_number)
        return pull_request.get_review_comments()

    def reply_on_pr_comment(self, repo_full_name: str, pr_number: int, comment_id: int, comment: str) -> None:
        if (
            repo_full_name is None
            or repo_full_name == ""
            or pr_number is None
            or pr_number == 0
            or comment_id is None
            or comment_id == 0
            or comment is None
            or comment == ""
        ):
            raise ValueError("Invalid input parameters")

        repo = self._github.get_repo(repo_full_name)
        pull_request = repo.get_pull(pr_number)

        pull_request.create_review_comment_reply(
            comment_id,
            body=comment,
        )

    def create_pull_request_review_comments(
        self, pull_request: github.PullRequest.PullRequest, commit: github.Commit.Commit, comments: list[GitHubReviewComment]
    ):
    def create_pull_request_review_comments(self, commit: Commit, comments: list[GitHubReviewComment]):
        comments_as_dict = [asdict(c) for c in comments]

        post_parameters = {
            "body": "Reviewed your changes, here is what I found:",
            "event": "COMMENT",
            "commit_id": commit._identity,
            "comments": comments_as_dict,
        }

        try:
            headers, data = self.pr._requester.requestJsonAndCheck("POST", f"{self.pr.url}/reviews", input=post_parameters)
            github.PullRequestComment.PullRequestComment(self.pr._requester, headers, data, completed=True)
        except Exception as e:
            log.error(f"Error during create a new pending pull request: {e}")
