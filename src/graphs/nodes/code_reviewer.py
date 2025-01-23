import concurrent
import concurrent.futures
import json

from langchain_core.runnables import RunnableSerializable

from graphs.states import GitHubPRState
from utils.logging_config import logger as log
from utils.models import Comment, Comments
from utils.wrap_prompt import wrap_prompt

from .contexts import DefaultContext


class CodeReviewer:
    def __init__(self, context: DefaultContext, name: str = "code_reviewer"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")

        try:
            comments = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                results = list(executor.map(lambda _: self.__code_review(state), range(5)))

            for res in results:
                comments += res

        except Exception as e:
            log.error(f"Error in {self.name}: {e}")
            raise

        log.debug(f"""
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
                    "FILES:",
                    f"{'\n'.join(map(str, state['context_files']))}",
                    "",
                    "CHANGES:" f"{state['changes']}",
                    "",
                    "STATIC_ANALYZER_OUTPUT:",
                    f"{state["static_analyzer_output"]}",
                    "",
                    "VARIABLES:",
                    f"{state["variables_graph"]}",
                    # "USER_CONFIGURATION:",
                    # f"{self.user_config.get("Code Review", "")}",
                    # f"{self.user_config.get("Security & Compliance Policies", "")}",
                )
            }
        )

        return [comment for comment in response.issues if comment.line_number != 0]
