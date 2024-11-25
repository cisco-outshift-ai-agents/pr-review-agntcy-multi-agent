from typing import Dict, Optional
import io
from utils.github_operations import GitHubOperations
from .agent_config import AgentConfig
from .md_parser import MarkdownParser
from .parser_mixin import ParseContentError
from utils.logging_config import logger as log
from utils.constants import ALFRED_CONFIG_BRANCH, ALFRED_CONFIG_FILE


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
            with open(f"./{ALFRED_CONFIG_FILE}", "r") as file:
                config_content = file.read()
        except Exception as e:
            log.error(f"Failed to read default config file: {e}")
            return False

        # Create branch
        if not self.github_ops.create_branch(repo_name, branch_name):
            return False

        # Create config file
        if not self.github_ops.create_file(repo_name, branch_name, self.default_config_path, config_content, commit_message):
            return False

        # Create pull request
        return self.github_ops.create_pull_request(repo_name, branch_name, "main", pr_title, pr_body)

    def load_config(self, pr_number: int, repo_name: str) -> Optional[Dict[str, str]]:
        """Loads and parses the config file from a PR or default branch"""
        # Try to get config from PR branch
        content = self._get_config_from_pr(pr_number, repo_name)
        if not content:
            # Try to get config from default branch
            content = self._get_config_from_default_branch(repo_name)

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

    def _get_config_from_pr(self, pr_number: int, repo_name: str) -> Optional[str]:
        """Gets config content from PR branch"""
        try:
            repo = self.github_ops.get_repo(repo_name)
            pull_request = repo.get_pull(pr_number)
            branch_name = pull_request.head.ref
            return self.github_ops.get_file_content(repo_name, self.default_config_path, branch_name)
        except Exception:
            log.info("No config file found in PR")
            return None

    def _get_config_from_default_branch(self, repo_name: str) -> Optional[str]:
        """Gets config content from default branch"""
        return self.github_ops.get_file_content(repo_name, self.default_config_path)
