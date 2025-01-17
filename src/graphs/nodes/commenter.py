from graphs.states import GitHubPRState
from .contexts import DefaultContext
from utils.logging_config import logger as log


class Commenter:
    """Commenter creates GitHub issue comments for a given PR"""

    def __init__(self, context: DefaultContext, name: str = "commenter"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name}: called")

        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHubOperations is not set in the context")

        try:
            self.context.github.create_comments(state["new_comments"], state["title_desc_comment"], state["manually_added_comments"])
        except Exception as e:
            log.error(f"{self.name}: Error creating comments: {e}")
            raise

        return {}
