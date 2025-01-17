import os
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Optional

import github.Auth
from github import Github, GithubException, GithubIntegration, UnknownObjectException
from github.Commit import Commit
from github.PullRequest import PullRequest
from github.Repository import Repository

from utils.logging_config import logger as log
from utils.models import Comment
from utils.secret_manager import secret_manager

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


class CheckRunConclusion(Enum):
    success = "success"
    failure = "failure"


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

            self._app_name = git_integration.get_app().name

            github_token = git_integration.get_access_token(int(installation_id)).token
            return Github(github_token)
        except Exception as e:
            log.error(f"Invalid GitHub credentials: {e}")
            raise

    @staticmethod
    def _get_private_key() -> str:
        """Get private key from file or environment variable"""
        try:
            private_key = secret_manager.get_github_app_private_key()
        except Exception as e:
            log.error(f"Failed to get private key: {e}")
            raise

        return private_key

    @staticmethod
    def _get_app_id() -> str:
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

    def create_pull_request_check_run(self) -> github.CheckRun.CheckRun:
        return self._repo.create_check_run(name="Alfred review", head_sha=self._pr.head.sha, status="in_progress")

    @staticmethod
    def complete_pull_request_check_run(check_run: github.CheckRun.CheckRun, conclusion: CheckRunConclusion):
        try:
            check_run.edit(status="completed", conclusion=conclusion.name)
        except Exception as e:
            log.error(f"Unable to edit pull request check run: {e}")
