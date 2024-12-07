from operator import concat, add
from typing import Annotated, Sequence
from typing import List

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class FileChange(TypedDict):
    filename: str
    start_line: int
    changed_code: str
    status: str


class Comment(BaseModel):
    filename: str = Field(
        description="The name of the file where the issue was found. Can be found at the beginning of the file. MUST BE the full path to the file.")
    line_number: int = Field(
        description="The line number where the issue was found.")
    comment: str = Field(description="The review comment describing the issue. Must be placed here without markdown formatting.")
    status: str = Field(
        description="Status of the line - must be either 'added' (for lines added in the PR, marked with '+') or 'removed' (for lines removed in the PR, marked with '-'). Can be found at the beginning of the line after the line number."
    )


class ContextFile(BaseModel):
    path: str
    content: str

    def __str__(self) -> str:
        return f"File: {self.path}\n```\n{self.content}\n```"

    def __repr__(self) -> str:
        return self.__str__()

class GitHubPRState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    changes: Annotated[List[FileChange], concat]
    modified_files: Annotated[List[ContextFile], concat]
    context_files: Annotated[List[ContextFile], concat]
    comments: Annotated[List[Comment], concat]
    existing_comments: Annotated[List[Comment], concat]
    sender: Annotated[List[str], add]
    title: Annotated[List[str], add]
    description: Annotated[List[str], add]

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


class CodeReviewResponse(BaseModel):
    issues: List[Comment] = Field(description="List of code review issues found")
