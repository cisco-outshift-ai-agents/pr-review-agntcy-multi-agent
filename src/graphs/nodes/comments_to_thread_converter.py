from graphs.states import ReviewChatAssistantState
from utils.logging_config import logger as log


class CommentsToThreadConverter:
    def __init__(self, name: str = "comments_to_thread_converter"):
        self.name = name

    def __call__(self, state: ReviewChatAssistantState) -> dict:
        log.info(f"{self.name} called")

        comment = state["comment"]
        comments = state["comments"]
        thread_comments = [
            c for c in comments if comment["in_reply_to_id"] == c.id or c.id == comment["id"] or c.in_reply_to_id == comment["in_reply_to_id"]
        ]
        thread_comments.sort(key=lambda x: x.created_at)
        return {"thread": thread_comments}
