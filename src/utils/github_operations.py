# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import io
import os
import zipfile
from dataclasses import asdict, dataclass
from enum import Enum
from http import HTTPStatus
from typing import Optional

import github.Auth
import requests
from github import Github, GithubException, GithubIntegration, UnknownObjectException
from github.CheckRun import CheckRun
from github.Commit import Commit
from github.PullRequest import PullRequest
from github.PullRequestComment import PullRequestComment
from github.Repository import Repository

from utils.logging_config import logger as log
from utils.models import ReviewComment, IssueComment
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
            self._github_token: str = self._get_access_token(installation_id)
            self._github: Github = self._init_github(self._github_token)
            log.info("GitHub client initialized successfully")
            self._repo: Repository = self._github.get_repo(repo_name)
            if pr_number:
                self._pr: PullRequest = self._repo.get_pull(pr_number)
                log.debug(f"PR #{pr_number}: {self._pr}")
            log.info("GitHub repository and pull request initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize GitHub client: {e}")
            raise InvalidGitHubInitialization(f"Failed to initialize GitHub client: {e}") from e

    @property
    def repo(self) -> Repository:
        return self._repo

    @property
    def pr(self) -> PullRequest:
        return self._pr

    def _init_github(self, github_token: str) -> Github:
        """Initialize GitHub client with app credentials"""
        try:
            return Github(github_token)
        except Exception as e:
            log.error(f"Invalid GitHub credentials: {e}")
            raise

    def _get_access_token(self, installation_id: str) -> str:
        if secret_manager is None:
            raise ValueError("Secret manager is not initialized")

        private_key = secret_manager.github_app_private_key
        app_id = self._get_app_id()
        git_integration = GithubIntegration(auth=github.Auth.AppAuth(app_id, private_key))

        github_token = git_integration.get_access_token(int(installation_id)).token
        return github_token

    @staticmethod
    def _get_app_id() -> str:
        """Get GitHub App ID from environment variable"""
        app_id = os.getenv("GITHUB_APP_ID")
        if not app_id:
            raise ValueError("GITHUB_APP_ID environment variable is not set")
        return app_id

    def get_github_details(self) -> dict:
        return {
            "repo_url": self._repo.html_url,
            "branch": self._pr.head.ref,
            "github_token": self._github_token,
        }

    def create_comments(
        self,
        new_review_comments: list[ReviewComment] = None,
        new_issue_comments: list[IssueComment] = None,
    ) -> None:
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

        review_comments_transformed: list[GitHubReviewComment] = []

        for pr_file in files:
            for r_comment in new_review_comments:
                if r_comment.filename == pr_file.filename:
                    c = GitHubReviewComment(
                        r_comment.comment, pr_file.filename, int(r_comment.line_number), "LEFT" if r_comment.status == "removed" else "RIGHT"
                    )

                    review_comments_transformed.append(c)
        for r_comment in new_review_comments:
            if r_comment.line_number == 0:
                # TODO: Is this stil necessary?
                # Response comment for a re-review
                self.pr.create_issue_comment(r_comment.comment)

        # create issue comments
        for i_comment in new_issue_comments:
            self.pr.create_issue_comment(i_comment.body)

        # create review comments
        if len(review_comments_transformed) > 0:
            self.create_pull_request_review_comments(commit, review_comments_transformed)

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
            PullRequestComment(self.pr._requester, headers, data, completed=True)
        except Exception as e:
            log.error(f"Error during create a new pending pull request: {e}")

    def clone_repo(self, destination_folder: str) -> str:
        """Clone the PR's branch content into a folder, returns the path to the repo"""

        log.debug("Cloning the repo into a local folder...")

        repo = self._repo
        pr = self._pr

        zip_link = repo.get_archive_link("zipball", pr.head.ref)

        response = requests.get(zip_link, headers={"Authorization": f"token {self._github_token}"})

        if response.status_code != HTTPStatus.OK:
            raise ValueError(f"Error while downloading the repo as ZIP, status code: {response.status_code}")

        log.debug("Repo downloaded successfully")

        zip_file_in_memory = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_file_in_memory, "r") as zip_ref:
            file_list = zip_ref.namelist()
            if not file_list:
                raise ValueError("Cloned repo is empty or the zip is corrupted")

            # Inside the zip there's a folder named (repo-name-<commit-hash>), we would like to return this folder name
            folder_name = file_list[0].split("/")[0]

            zip_ref.extractall(destination_folder)
            log.debug("Repo extracted successfully")

            return f"{destination_folder}/{folder_name}"

    def create_pull_request_check_run(self) -> CheckRun:
        return self._repo.create_check_run(name="Alfred review", head_sha=self._pr.head.sha, status="in_progress")

    @staticmethod
    def complete_pull_request_check_run(check_run: CheckRun, conclusion: CheckRunConclusion, error_message: str):
        try:
            if conclusion.name == "success":
                log.info("Check run completed successfully")
                check_run.edit(status="completed", conclusion=conclusion.name, output={"title": "PR review successful", "summary": "Alfred review completed successfully"})
            else:
                log.info("Check run completed with failure")
                check_run.edit(
                    status="completed",
                    conclusion=conclusion.name,
                    output={"title": "PR review failed", "summary": error_message},
                )
        except Exception as e:
            log.error(f"Unable to edit pull request check run: {e}")

    def get_git_diff(self) -> str:
        git_diff = ""
        # Request the diff format directly using the diff media type
        _, data = self._pr._requester.requestJsonAndCheck("GET", f"{self._pr.url}", headers={"Accept": "application/vnd.github.diff"})

        if data:
            git_diff = data["data"]

        return git_diff
