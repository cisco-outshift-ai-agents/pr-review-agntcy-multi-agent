from graphs.states import GitHubPRState
from utils.logging_config import logger as log
from .contexts import DefaultContext
from langchain_core.messages import BaseMessage
from utils.wrap_prompt import wrap_prompt
from utils.models import IssueComment_

from langchain_core.runnables import RunnableSerializable


class IssueCommentReviewer:
    def __init__(self, context: DefaultContext, name: str = "issue_comment_reviewer"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")

        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHubOperations is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self.context.chain, RunnableSerializable):
            raise ValueError(f"{self.name}: Chain is not a RunnableSerializable")

        user_input = self.context.user_config.get("PR Title and Description", "")

        existing_issue_comments = state["existing_issue_comments"]
        new_issue_comments = state["new_issue_comments"]
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
        new_title_desc_comment = IssueComment_(body=title_desc_chain_result_content, conditions=["PR title suggestion", "PR description suggestion"])
        new_issue_comments.append(new_title_desc_comment)

        def check_conditions(comment: str, conditions: list[str]) -> bool:
            for c in conditions:
                if c not in comment:
                    return False
            return True

        # check new issue comments for duplications
        for new_issue_comment in new_issue_comments:
            existing_issue_comment = next(
                (e_i_comment for e_i_comment in existing_issue_comments if check_conditions(e_i_comment.body, new_issue_comment.conditions)),
                None,
            )

            if existing_issue_comment:
                # Update existing comment
                try:
                    existing_issue_comment.edit(new_issue_comment.body)
                except Exception as e:
                    log.error(f"Error updating existing comment: {e}")
            else:
                new_issue_comments.append(new_issue_comment)

        log.info(f"""
        issue comment reviewer finished.
        comments: {"\\".join(c.body for c in new_issue_comments)}
        """)

        return {"new_issue_comments": new_issue_comments}
