from typing import Annotated, Sequence
from typing import Optional
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
        description="The name of the file where the issue was found. Can be found at the beginning of the file. MUST BE the full path to the file."
    )
    line_number: int = Field(description="The line number where the issue was found.")
    comment: str = Field(description="The review comment describing the issue. Must be placed here without markdown formatting.")
    status: str = Field(
        description="Status of the line - must be either 'added' (for lines added in the PR, marked with '+') or 'removed' (for lines removed in the PR, marked with '-'). Can be found at the beginning of the line after the line number."
    )


class CodeReviewResponse(BaseModel):
    issues: List[Comment] = Field(description="List of code review issues found")


class ContextFile(BaseModel):
    path: str
    content: str

    def __str__(self) -> str:
        return f"File: {self.path}\n```\n{self.content}\n```"

    def __repr__(self) -> str:
        return self.__str__()


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
        messages=[],
        changes=[],
        modified_files=[],
        context_files=[],
        new_comments=[],
        existing_comments=[],
        title_desc_comment=None,
        sender="",
        title="",
        description="",
    )
