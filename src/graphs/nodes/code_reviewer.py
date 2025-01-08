import json

from graphs.states import GitHubPRState
from utils.logging_config import logger as log
from .contexts import DefaultContext
from utils.wrap_prompt import wrap_prompt
from utils.models import Comments
from langchain_core.runnables import RunnableSerializable


class CodeReviewer:
    def __init__(self, context: DefaultContext, name: str = "code_reviewer"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")

        if self.context.chain is None:
            raise ValueError(f"{self.name}: Chain is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self.context.chain, RunnableSerializable):
            raise ValueError(f"{self.name}: Chain is not a RunnableSerializable")

        try:
            response: Comments = self.context.chain.invoke(
                {
                    "question": wrap_prompt(
                        "Review the following MODIFIED FILES:",
                        f"{'\n'.join(map(str, state['modified_files']))}",
                        "",
                        "Consider the following CONTEXT FILES that are related to the MODIFIED FILES:",
                        f"{'\n'.join(map(str, state['context_files']))}",
                        "Configuration:",
                        f"{self.context.user_config.get('Code Review', '')}",
                        f"{self.context.user_config.get('Security & Compliance Policies', '')}",
                    )
                }
            )

            comments = [comment for comment in response.issues if comment.line_number != 0]

        except Exception as e:
            log.error(f"Error in {self.name}: {e}")
            raise

        log.info(f"""
        code reviewer finished.
        comments: {json.dumps([comment.model_dump() for comment in comments], indent=4)}
        """)

        return {"new_comments": comments}
