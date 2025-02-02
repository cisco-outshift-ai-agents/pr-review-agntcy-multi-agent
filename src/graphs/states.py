from typing import Annotated, Sequence, Dict, Any, Optional

from github.PullRequestComment import PullRequestComment
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict
from utils.models import ContextFile, GitHubIssueCommentUpdate, IssueComment, ReviewComment
from github.IssueComment import IssueComment as GHIssueComment


class FileChange(TypedDict):
    changed_code: str
    filename: str
    start_line: int
    status: str


class GitHubPRState(TypedDict):
    changes: list[FileChange]
    context_files: list[ContextFile]
    description: str
    issue_comments: list[GHIssueComment]
    issue_comments_to_update: list[GitHubIssueCommentUpdate]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # modified_files: list[ContextFile]
    new_issue_comments: list[IssueComment]
    new_review_comments: list[ReviewComment]
    review_comments: list[ReviewComment]
    sender: str
    static_analyzer_output: str
    title: str
    cross_reference_problems: Optional[Comment]


def create_default_github_pr_state() -> GitHubPRState:
    return GitHubPRState(
        changes=[],  # Default to an empty list of changes
        context_files=[],  # Default to an empty list of context files
        description="",  # Default to an empty string
        issue_comments=[],  # Default to an empty list of issue comments
        issue_comments_to_update=[],  # Default to an empty list of issue comments to be updated
        messages=[],  # Default to an empty list of messages
        # modified_files=[],  # Default to an empty list of modified files
        new_issue_comments=[],  # Default to an empty list of new issue commentsissue_comments_to_update
        new_review_comments=[],  # Default to an empty list of new review comments
        review_comments=[],  # Default to an empty list of review comments
        sender="",  # Default to an empty string
        static_analyzer_output="",
        title="",  # Default to an empty string
        cross_reference_problems=None,
    )


class ReviewChatAssistantState(TypedDict):
    comment: Dict[str, Any]
    is_skipped: Optional[bool]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    review_comment_thread: Sequence[PullRequestComment]
    review_comments: Sequence[PullRequestComment]
    reviewed_patch: Optional[str]
