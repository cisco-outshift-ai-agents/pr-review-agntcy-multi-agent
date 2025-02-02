from graphs.states import GitHubPRState
from .contexts import DefaultContext
from utils.logging_config import logger as log


class Commenter:
    """Commenter creates GitHub issue comments for a given PR"""

    def __init__(self, context: DefaultContext, name: str = "commenter"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> None:
        log.info(f"{self.name}: called")

        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHubOperations is not set in the context")

        try:
            for u_i_c in state["issue_comments_to_update"]:
                u_i_c.edit(u_i_c.new_body)
        except Exception as e:
            log.error(f"Error updating existing comment: {e}")

        try:
            self.context.github.create_comments(state["new_review_comments"], state["new_issue_comments"], state["cross_reference_problems"])
        except Exception as e:
            log.error(f"{self.name}: Error creating comments: {e}")
            raise
