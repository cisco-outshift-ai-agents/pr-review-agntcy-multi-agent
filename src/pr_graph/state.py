from typing import Annotated, Sequence
from typing import List
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict
from operator import concat, add
from pydantic import BaseModel, Field


class FileChange(TypedDict):
    filename: str
    start_line: int
    changed_code: str
    status: str


class Comment(BaseModel):
    filename: str = Field(description="The name of the file where the issue was found. Must match the 'filename' field from the change.")
    line_number: int = Field(description="The line number where the issue was found. Must match the 'start_line' field from the change.")
    comment: str = Field(description="The review comment describing the issue. Must be placed here without markdown formatting.")
    status: str = Field(
        description="Status of the line - must be either 'added' (for lines added in the PR) or 'removed' (for lines removed in the PR). Must match the 'status' field from the change."
    )


class GitHubPRState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    changes: Annotated[List[FileChange], concat]
    comments: Annotated[List[Comment], concat]
    existing_comments: Annotated[List[Comment], concat]
    sender: Annotated[List[str], add]
    title: Annotated[List[str], add]
    description: Annotated[List[str], add]


class CodeReviewResponse(BaseModel):
    issues: List[Comment] = Field(description="List of code review issues found")


class SecurityReviewResponse(BaseModel):
    issues: List[Comment] = Field(description="List of security review issues found")


def create_default_github_pr_state() -> GitHubPRState:
    return GitHubPRState(
        messages=[],  # Default to an empty list of messages
        changes=[],  # Default to an empty list of changes
        comments=[],  # Default to an empty list of comments
        existing_comments=[],  # Default to an empty list of existing comments
        sender=[],  # Default to an empty list of senders
        title=[],  # Default to an empty list of titles
        description=[],  # Default to an empty list of descriptions
    )
