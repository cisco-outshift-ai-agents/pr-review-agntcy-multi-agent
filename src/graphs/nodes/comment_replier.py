from graphs.nodes.contexts import DefaultContext
from graphs.states import ReviewChatAssistantState
from utils.logging_config import logger as log


class CommentReplier:
    def __init__(self, context: DefaultContext, name="comment_replier"):
        self.context = context
        self.name = name

    def __call__(self, state: ReviewChatAssistantState) -> dict:
        log.info(f"{self.name} called")

        if not self.context.github:
            raise ValueError("GitHub operations not found")

        try:
            # Ensure the content is a string
            content = state["messages"][-1].content
            if isinstance(content, list):
                content = " ".join(str(item) for item in content)
            self._reply_on_pr_comment(state["comment"]["id"], content)
        except Exception as e:
            raise ValueError(f"Error sending reply to comment on GitHub: {e}") from e

        return {}

    def _reply_on_pr_comment(self, comment_id: int, comment: str) -> None:
        if not self.context.github:
            raise ValueError("GitHub operations not found")

        if comment_id is None or comment_id == 0 or comment is None or comment == "":
            raise ValueError("Invalid input parameters")

        self.context.github.pr.create_review_comment_reply(
            comment_id,
            body=comment,
        )
