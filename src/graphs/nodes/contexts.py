from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Dict, Any

from langchain_core.runnables import RunnableSerializable

from utils.github_operations import GitHubOperations


@dataclass
class DefaultContext:
    """Default context for all operations"""

    github: GitHubOperations | None = None
    user_config: Dict[str, Any] = field(default_factory=dict)
    chain: Callable[..., RunnableSerializable] | RunnableSerializable | None = None
