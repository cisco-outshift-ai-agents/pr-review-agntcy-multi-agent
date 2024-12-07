from typing import TypedDict, Annotated, Sequence, Dict, Any, Optional

from github.PullRequestComment import PullRequestComment
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class ReviewChatAssistantState(TypedDict):
    repo_name: str
    pr_number: int
    comment: Dict[str, Any]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    comments: Sequence[PullRequestComment]
    thread: Sequence[PullRequestComment]
    reviewed_patch: Optional[str]
    is_skipped: Optional[bool]
