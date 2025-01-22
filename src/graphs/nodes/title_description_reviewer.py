from typing import Any
from graphs.states import GitHubPRState
from utils.logging_config import logger as log
from .contexts import DefaultContext
from langchain_core.messages import BaseMessage
from utils.wrap_prompt import wrap_prompt
from utils.models import Comment
from langchain_core.runnables import RunnableSerializable


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

        user_input = self.context.user_config.get("PR Title and Description", "")

        # Fetch existing comments
        existing_title_desc_comment = None
        try:
            issue_comments = self.context.github.pr.get_issue_comments()
            for issue_comment in issue_comments:
                body = issue_comment.body.lower()
                if "pr title suggestion" in body and "pr description suggestion" in body:
                    existing_title_desc_comment = issue_comment
                    break
        except Exception as e:
            log.error(f"Error fetching existing comments: {e}")
            # Continue even if we can't fetch existing comments
            pass

        diff = state["changes"]

        result: BaseMessage = self.context.chain.invoke(
            {
                "question": wrap_prompt(
                    f"Given following changes :\n{diff}\n",
                    f"Check the given title: {state["title"]} and decide If the title don't describe the changes, suggest a new title, otherwise keep current title.",
                    f"Check the given pull request description: {state["description"]} and decide If the description don't describe the changes, suggest a new description, otherwise keep current description.",
                    f"Configuration: {user_input}",
                ),
            }
        )

        result_content = str(result.content)
        new_title_desc_comment = Comment(filename="", line_number=0, comment=result_content, status="")
        if existing_title_desc_comment:
            # Update existing comment
            try:
                existing_title_desc_comment.edit(result_content)
                return {}
            except Exception as e:
                log.error(f"Error updating existing comment: {e}")

        log.debug(f"""
        title and description reviewer finished.
        comment: {new_title_desc_comment.model_dump_json(indent=2)}
        """)

        return {"title_desc_comment": new_title_desc_comment}
