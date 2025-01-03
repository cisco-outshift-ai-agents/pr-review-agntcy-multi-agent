from graphs.states import ReviewChatAssistantState
from utils.logging_config import logger as log
from .contexts import DefaultContext


class CommentRelatedPatchFetcherNode:
    def __init__(self, context: DefaultContext, name: str = "comment_related_patch_fetcher_node"):
        self.context = context
        self.name = name

    def __call__(self, state: ReviewChatAssistantState) -> dict:
        log.info(f"{self.name} called with state: {state}")

        if not self.context.github:
            raise ValueError("GitHub operations not found")

        try:
            files = self.context.github.pr.get_files()
        except Exception as e:
            raise ValueError(f"Error getting patch from GitHub: {e}") from e

        for f in files:
            if f.filename == state["comment"]["path"]:
                return {"reviewed_patch": f.patch}

        raise ValueError(f"File {state["comment"]["path"]} not found in the PR's files")
