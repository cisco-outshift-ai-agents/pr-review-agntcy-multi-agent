from typing import Annotated, Sequence, Dict, Any
from typing import Optional

from github.PullRequestComment import PullRequestComment
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict
from utils.models import Comment, ContextFile


class FileChange(TypedDict):
    filename: str
    start_line: int
    changed_code: str
    status: str


class GitHubPRState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    changes: list[FileChange]
    modified_files: list[ContextFile]
    context_files: list[ContextFile]
    new_comments: list[Comment]
    existing_comments: list[Comment]
    title_desc_comment: Optional[Comment]
    sender: str
    title: str
    description: str


def create_default_github_pr_state() -> GitHubPRState:
    return GitHubPRState(
        messages=[],  # Default to an empty list of messages
        changes=[],  # Default to an empty list of changes
        modified_files=[],  # Default to an empty list of modified files
        context_files=[],  # Default to an empty list of context files
        new_comments=[],  # Default to an empty list of new comments
        existing_comments=[],  # Default to an empty list of existing comments
        title_desc_comment=None,  # Default to None
        sender="",  # Default to an empty string
        title="",  # Default to an empty string
        description="",  # Default to an empty string
    )


class ReviewChatAssistantState(TypedDict):
    comment: Dict[str, Any]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    review_comments: Sequence[PullRequestComment]
    review_comment_thread: Sequence[PullRequestComment]
    reviewed_patch: Optional[str]
    is_skipped: Optional[bool]
