from typing import Dict, Optional
import io
import os
import base64
from utils.github_operations import GitHubOperations, GithubOperationException
from github.ContentFile import ContentFile
from .agent_config import AgentConfig
from .md_parser import MarkdownParser
from .parser_mixin import ParseContentError
from utils.logging_config import logger as log
from utils.constants import ALFRED_CONFIG_BRANCH, ALFRED_CONFIG_FILE
from typing import Tuple


class ConfigManager:
    """
    ConfigManager class to handle configuration file operations using GitHub.
    Uses GitHubOperations for GitHub interactions and AgentConfig for parsing.
    """

    def __init__(self, github_ops: GitHubOperations):
        self.github_ops = github_ops
        self.default_config_path = ALFRED_CONFIG_FILE

    def create_config(
        self,
        repo_name: str,
        branch_name: str = ALFRED_CONFIG_BRANCH,
        commit_message: str = "Add Alfred config file",
        pr_title: str = "Alfred config file",
        pr_body: str = "This pull request adds Alfred default config file.",
    ) -> bool:
        """Creates and submits a PR with the default config file"""
        # Read default config content
        try:
            alfred_config_path = os.getenv("ALFRED_CONFIG_PATH", ".")
            config_file_path = os.path.join(alfred_config_path, ALFRED_CONFIG_FILE)
            with open(config_file_path, "r") as file:
                config_content = file.read()
        except Exception as e:
            log.error(f"Failed to read default config file: {e}")
            return False

        # Create branch
        if not self.create_branch(repo_name, branch_name):
            return False

        # Create config file
        if not self.create_file(branch_name, self.default_config_path, config_content, commit_message):
            return False

        # Create pull request
        return self.create_pull_request(branch_name, "main", pr_title, pr_body)

    def load_config(self) -> Optional[Dict[str, str]]:
        """Loads and parses the config file from a PR or default branch"""
        # Try to get config from PR branch
        content = self._get_config_from_pr()
        if not content:
            # Try to get config from default branch
            content = self._get_config_from_default_branch()

        if not content:
            log.error("Could not retrieve config content")
            return None

        try:
            content_reader = io.StringIO(content)
            config = AgentConfig(content_reader, MarkdownParser())
            return config.data
        except ParseContentError as e:
            log.error(f"Error parsing config content: {e.content}")
            return None

    def create_branch(self, branch_name: str, base_branch: Optional[str] = None) -> bool:
        """Creates a new branch in the repository"""
        try:
            if base_branch is None:
                base_branch = self.github_ops.repo.default_branch

            base_ref = self.github_ops.repo.get_git_ref(f"heads/{base_branch}")
            self.github_ops.repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_ref.object.sha)
            log.info(f"Branch {branch_name} created successfully.")
            return True
        except GithubOperationException as e:
            if "Reference already exists" in e.data.get("message", ""):
                log.info("Branch already exists")
                return True
            log.error(f"Failed to create branch: {e.data}")
            return False

    def create_file(self, branch_name: str, file_path: str, content: str, commit_message: str) -> bool:
        """Creates or updates a file in the repository"""
        try:
            file_exists, file_contents = self.get_file(file_path, branch_name)

            if file_exists:
                if file_contents is None:
                    raise ValueError("File contents are None")

                log.info(f"File {file_path} already exists in branch {branch_name}.")
                self.github_ops.repo.update_file(path=file_path, message=commit_message, content=content, branch=branch_name, sha=file_contents.sha)
                return True

            self.github_ops.repo.create_file(path=file_path, message=commit_message, content=content, branch=branch_name)
            log.info(f"File {file_path} created successfully.")
            return True
        except GithubOperationException as e:
            log.error(f"Failed to create file: {e.data}")
            return False

    def get_file(self, file_path: str, ref: Optional[str] = None) -> Tuple[bool, Optional[ContentFile]]:
        """Gets a file from the repository"""
        try:
            if ref is None:
                ref = self.github_ops.repo.default_branch
            contents: list[ContentFile] | ContentFile = self.github_ops.repo.get_contents(file_path, ref=ref)

            if isinstance(contents, list):
                raise ValueError("Expected a single file, but got multiple files")

            return True, contents
        except GithubOperationException as e:
            if e.status == 404:
                return False, None
            raise e

    def get_file_content(self, file_path: str, ref: Optional[str] = None) -> Optional[str]:
        """Gets the decoded content of a file from the repository"""
        try:
            if ref is None:
                ref = self.github_ops.repo.default_branch

            file: ContentFile | list[ContentFile] = self.github_ops.repo.get_contents(file_path, ref=ref)
            if isinstance(file, list):
                raise ValueError("Expected a single file, but got multiple files")

            return base64.b64decode(file.content).decode("utf-8")
        except Exception as e:
            log.error(f"Error getting file content: {e}")
            return None

    def create_pull_request(self, branch_name: str, base_branch: str, title: str, body: str) -> bool:
        """Creates a pull request in the repository"""
        try:
            pulls = self.github_ops.repo.get_pulls(state="open")
            pr_exists = any(pr.head.ref == branch_name for pr in pulls)

            if pr_exists:
                log.info("Pull request already exists.")
                return True

            self.github_ops.repo.create_pull(title=title, body=body, head=branch_name, base=base_branch)
            log.info("Pull request created successfully.")
            return True
        except GithubOperationException as e:
            log.error(f"Failed to create pull request: {e.data}")
            return False

    def _get_config_from_pr(self) -> Optional[str]:
        """Gets config content from PR branch"""
        try:
            branch_name = self.github_ops.pr.head.ref
            return self.get_file_content(self.default_config_path, branch_name)
        except Exception:
            log.info("No config file found in PR")
            return None

    def _get_config_from_default_branch(self) -> Optional[str]:
        """Gets config content from default branch"""
        return self.get_file_content(self.default_config_path)
