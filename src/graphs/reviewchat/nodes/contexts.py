from dataclasses import dataclass
from typing import Callable, Iterable

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableSerializable

from utils.github_operations import GitHubOperations


@dataclass
class GitHubOperationsContext:
    github_ops: GitHubOperations


@dataclass
class ReviewChatAssistantContext:
    chain: Callable[[Iterable[BaseMessage]], RunnableSerializable]
