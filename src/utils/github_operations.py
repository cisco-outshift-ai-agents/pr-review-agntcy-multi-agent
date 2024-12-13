import base64
import os
from typing import Optional, Tuple

import github.Auth
from github import Github, GithubException, GithubIntegration
from github.ContentFile import ContentFile
from github.PaginatedList import PaginatedList
from github.PullRequestComment import PullRequestComment
from github.Repository import Repository

from utils.logging_config import logger as log


class GitHubOperations:
    """
    GitHubOperations class provides generic GitHub operations for managing repositories,
    branches, files, and pull requests.
    """

    def __init__(self, installation_id: str):
        self._github = self._init_github(installation_id)

    def _init_github(self, installation_id: str) -> Github:
        """Initialize GitHub client with app credentials"""
        try:
            private_key = self._get_private_key()
            app_id = self._get_app_id()

            git_integration = GithubIntegration(auth=github.Auth.AppAuth(app_id, private_key))

            self._app_name = git_integration.get_app().name

            github_token = git_integration.get_access_token(int(installation_id)).token
            return Github(github_token)
        except Exception as e:
            log.error(f"Failed to initialize GitHub client: {e}")
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

    def create_branch(self, repo_name: str, branch_name: str, base_branch: Optional[str] = None) -> bool:
        """Creates a new branch in the repository"""
        try:
            repo = self._github.get_repo(repo_name)
            if base_branch is None:
                base_branch = repo.default_branch

            base_ref = repo.get_git_ref(f"heads/{base_branch}")
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_ref.object.sha)
            log.info(f"Branch {branch_name} created successfully.")
            return True
        except GithubException as e:
            if "Reference already exists" in e.data.get("message", ""):
                log.info("Branch already exists")
                return True
            log.error(f"Failed to create branch: {e.data}")
            return False

    def create_file(self, repo_name: str, branch_name: str, file_path: str, content: str, commit_message: str) -> bool:
        """Creates or updates a file in the repository"""
        try:
            repo: Repository = self._github.get_repo(repo_name)
            file_exists, file_contents = self.get_file(repo_name, file_path, branch_name)

            if file_exists:
                if file_contents is None:
                    raise ValueError("File contents are None")

                log.info(f"File {file_path} already exists in branch {branch_name}.")
                repo.update_file(path=file_path, message=commit_message, content=content, branch=branch_name, sha=file_contents.sha)
                return True

            repo.create_file(path=file_path, message=commit_message, content=content, branch=branch_name)
            log.info(f"File {file_path} created successfully.")
            return True
        except GithubException as e:
            log.error(f"Failed to create file: {e.data}")
            return False

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

    def create_pull_request_review_comments(self, pull_request: github.PullRequest.PullRequest, commit: github.Commit.Commit, comments: list):
        post_parameters = {"event": "COMMENT", "commit_id": commit._identity, "comments": comments}

        try:
            headers, data = pull_request._requester.requestJsonAndCheck("POST", f"{pull_request.url}/reviews", input=post_parameters)
            github.PullRequestComment.PullRequestComment(pull_request._requester, headers, data, completed=True)
        except Exception as e:
            log.error(f"Error during create a new pending pull request: {e}")
