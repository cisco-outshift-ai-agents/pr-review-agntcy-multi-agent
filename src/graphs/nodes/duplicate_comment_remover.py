import json
from graphs.states import GitHubPRState
from utils.models import Comments, Comment
from utils.logging_config import logger as log
from utils.wrap_prompt import wrap_prompt
from .contexts import DefaultContext
from langchain_core.runnables import RunnableSerializable


class DuplicateCommentRemover:
    def __init__(self, context: DefaultContext, name: str = "duplicate_comment_remover"):
        print("INIT DuplicateCommentRemover")
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict:
        print("CALL DuplicateCommentRemover")

        log.info(f"{self.name}: called")

        if self.context.chain is None:
            raise ValueError(f"{self.name}: Chain is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self.context.chain, RunnableSerializable):
            raise ValueError(f"{self.name}: Chain is not a RunnableSerializable")

        try:
            # Use existing comments from state
            existing_comments = state["existing_comments"]
            new_comments = state["new_comments"]

            if not existing_comments or not new_comments:
                return {}

            example_schema = [
                Comment(filename="file1", line_number=1, comment="comment1", status="added").model_dump(),
                Comment(filename="file1", line_number=2, comment="comment2", status="added").model_dump(),
            ]

            result: Comments = self.context.chain.invoke(
                {
                    "input_json_format": json.dumps(example_schema, indent=2),
                    "question": wrap_prompt(
                        f"EXISTING COMMENTS: {existing_comments}",
                        f"NEW COMMENTS: {new_comments}",
                    ),
                }
            )

            comments = result.issues

            if not comments:
                # Since there are no new comments, create a simple response for the user
                comments.append(
                    Comment(
                        filename="",
                        line_number=0,
                        comment="Reviewed the changes again, but I didn't find any problems in your code which haven't been     mentioned before.",
                        status="",
                    )
                )
        except Exception as e:
            log.error(f"{self.name}: Error removing duplicate comments: {e}")
            raise

        return {"new_comments": comments}
