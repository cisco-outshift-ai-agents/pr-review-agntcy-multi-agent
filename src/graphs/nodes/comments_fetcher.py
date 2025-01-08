from typing import Sequence

from github.PaginatedList import PaginatedList
from github.PullRequestComment import PullRequestComment

from graphs.states import ReviewChatAssistantState
from utils.logging_config import logger as log
from .contexts import DefaultContext


class CommentsFetcher:
    def __init__(self, context: DefaultContext, name: str = "comments_fetcher"):
        self.context = context
        self.name = name

    def __call__(self, state: ReviewChatAssistantState) -> dict:
        log.info(f"{self.name} called")

        if not self.context.github:
            raise ValueError("GitHub operations not found")

        try:
            comments_paginated: PaginatedList[PullRequestComment] = self.context.github.pr.get_comments()
            comments: Sequence[PullRequestComment] = list(comments_paginated)
        except Exception as e:
            raise ValueError(f"Error getting comments from GitHub: {e}") from e

        return {"comments": comments}
