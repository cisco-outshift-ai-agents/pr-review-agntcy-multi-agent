from typing import Annotated, Sequence
from typing import List
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict
from operator import concat


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


class GitHubPRState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    changes: Annotated[List[FileChange], concat]
    comments: Annotated[List[Comment], concat]
    sender: str
    title: str
    description: str
