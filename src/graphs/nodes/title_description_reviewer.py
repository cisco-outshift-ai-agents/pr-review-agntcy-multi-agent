from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableSerializable
from typing import Any

from .contexts import DefaultContext
from graphs.states import GitHubPRState
from utils.logging_config import logger as log
from utils.models import IssueComment
from utils.wrap_prompt import wrap_prompt


class TitleDescriptionReviewer:
    def __init__(self, context: DefaultContext, name: str = "title_description_reviewer"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict[str, Any]:
        log.info(f"{self.name} called")

        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHubOperations is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self.context.chain, RunnableSerializable):
            raise ValueError(f"{self.name}: Chain is not a RunnableSerializable")

        user_input = ""
        if self.context.user_config:
            user_input = self.context.user_config.get("PR Title and Description", "")

        # Fetch existing comments
        diff = state["changes"]

        title_desc_chain_result: BaseMessage = self.context.chain.invoke(
            {
                "question": wrap_prompt(
                    f"Given following changes :\n{diff}\n",
                    f"Check the given title: {state["title"]} and decide If the title don't describe the changes, suggest a new title, otherwise keep current title.",
                    f"Check the given pull request description: {state["description"]} and decide If the description don't describe the changes, suggest a new description, otherwise keep current description.",
                    f"Configuration: {user_input}",
                ),
            }
        )

        title_desc_chain_result_content = str(title_desc_chain_result.content)
        new_title_desc_comment = IssueComment(body=title_desc_chain_result_content, conditions=["PR title suggestion", "PR description suggestion"])

        log.debug(f"""
        title and description reviewer finished. issue comment added.
        title and description comment: {new_title_desc_comment.model_dump_json(indent=2)}
        """)

        return {"new_issue_comments": [new_title_desc_comment]}
