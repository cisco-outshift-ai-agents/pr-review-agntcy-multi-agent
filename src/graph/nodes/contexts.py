from dataclasses import dataclass
from typing import Dict, Any
from utils.github_operations import GitHubOperations
from langchain_core.runnables import RunnableSerializable


@dataclass
class GitHubContext:
    """Context for GitHub operations"""

    github: GitHubOperations
    repo_name: str
    pr_number: int


@dataclass
class CodeReviewContext:
    """Context for code review operations"""

    chain: RunnableSerializable
    user_config: Dict[str, Any]


@dataclass
class TitleDescriptionContext:
    """Context for title/description review operations"""

    chain: RunnableSerializable
    user_config: Dict[str, Any]
