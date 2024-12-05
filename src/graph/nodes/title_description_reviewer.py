from functools import partial
from graph.state import GitHubPRState, Comment
from .contexts import TitleDescriptionContext
from utils.logging_config import logger as log


def create_title_description_reviewer_node(context: TitleDescriptionContext):
    def title_description_reviewer(state: GitHubPRState) -> GitHubPRState:
        log.info("in title reviewer")
        user_input = context.user_config.get("PR Title and Description", "")

        result = context.chain.invoke(
            {
                "question": f"""
            Given following changes :\n{state["changes"]}\n
            Check the given title: {state["title"]} and decide If the title don't describe the changes, suggest a new title, otherwise keep current title.
            Check the given pull request description: {state["description"]} and decide If the description don't describe the changes, suggest a new description, otherwise keep current description.
            Configuration: {user_input}
            """
            }
        )

        comments = [Comment(filename="", line_number=0, comment=str(result.content), status="")]
        return {**state, "comments": comments}

    return partial(title_description_reviewer)
