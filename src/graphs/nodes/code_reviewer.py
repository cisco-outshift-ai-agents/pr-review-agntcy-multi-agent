import json

from graphs.states import GitHubPRState
from utils.logging_config import logger as log
from .contexts import DefaultContext
from utils.wrap_prompt import wrap_prompt
from utils.models import Comment, Comments
from langchain_core.runnables import RunnableSerializable


class CodeReviewer:
    def __init__(self, context: DefaultContext, name: str = "code_reviewer"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")

        try:
            comments = []
            for _ in range(3):
                comments += self.__code_review(state)

        except Exception as e:
            log.error(f"Error in {self.name}: {e}")
            raise

        log.info(f"""
        code reviewer finished.
        comments: {json.dumps([comment.model_dump() for comment in comments], indent=4)}
        """)

        return {"new_comments": comments}

    def __code_review(self, state: GitHubPRState) -> list[Comment]:
        if self.context.chain is None:
            raise ValueError(f"{self.name}: Chain is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self.context.chain, RunnableSerializable):
            raise ValueError(f"{self.name}: Chain is not a RunnableSerializable")

        response: Comments = self.context.chain.invoke(
            {
                "question": wrap_prompt(
                    # "MODIFIED FILES:",
                    # f"{'\n'.join(map(str, state['modified_files']))}",
                    # "",
                    "FILES:",
                    f"{'\n'.join(map(str, state['context_files']))}",
                    "",
                    "CHANGES:" f"{state['changes']}",
                    "",
                    "STATIC_ANALYZER_OUTPUT:",
                    f"{state["static_analyzer_output"]}",
                    # "USER_CONFIGURATION:",
                    # f"{self.user_config.get("Code Review", "")}",
                    # f"{self.user_config.get("Security & Compliance Policies", "")}",
                )
            }
        )

        return [comment for comment in response.issues if comment.line_number != 0]
