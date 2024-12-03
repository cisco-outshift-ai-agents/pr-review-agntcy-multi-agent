from operator import concat, add
from typing import Annotated, Sequence
from typing import List

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel
from typing_extensions import TypedDict


class FileChange(TypedDict):
    filename: str
    start_line: int
    changed_code: str
    status: str


class Comment(TypedDict):
    filename: str
    line_number: int
    comment: str
    status: str


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
    sender: Annotated[List[str], add]
    title: Annotated[List[str], add]
    description: Annotated[List[str], add]
