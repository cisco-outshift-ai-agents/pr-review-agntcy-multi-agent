import json
from typing import Any

from sentence_transformers import SentenceTransformer
from graphs.states import GitHubPRState
from utils.models import Comments, Comment
from utils.logging_config import logger as log
from utils.wrap_prompt import wrap_prompt
from .contexts import DefaultContext
from langchain_core.runnables import RunnableSerializable


class CommentFilterer:
    def __init__(self, context: DefaultContext, name: str = "duplicate_comment_remover"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict[str, Any]:
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

            if not new_comments:
                return {}

            new_comments = self.__remove_duplicate_comments(existing_comments, new_comments)

            if new_comments:
                example_schema = [
                    Comment(filename="file1", line_number=1, comment="comment1", status="added").model_dump(),
                    Comment(filename="file1", line_number=2, comment="comment2", status="added").model_dump(),
                ]

                result: Comments = self.context.chain.invoke(
                    {
                        "input_json_format": json.dumps(example_schema, indent=2),
                        "question": wrap_prompt(
                            f"comments: {new_comments}",
                        ),
                    }
                )

                new_comments = result.issues

            if not new_comments:
                # Since there are no new comments, create a simple response for the user
                new_comments.append(
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

        log.debug(f"""
        comment filterer finished.
        new comments: {json.dumps([comment.model_dump() for comment in new_comments], indent=4)}
        """)

        return {"new_comments": new_comments}

    def __remove_duplicate_comments(self, existing_comments: list[Comment], new_comments: list[Comment]) -> list[Comment]:
        # We use a simple embeding model to create vector embedings
        # We calculate the embedings first and then the similarities
        # The similarities are the cosine of the angle between the vectors, [-1, 1], the closer to 1 the more similar two sentences are
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        # First we remove the duplications from the new_comments:
        new_messages = [c.comment for c in new_comments]
        new_message_embeddings = model.encode(new_messages)
        new_message_similarity = model.similarity(new_message_embeddings, new_message_embeddings)

        # We have the following similarity matrix
        # We only need to iterate over either the top or the bottom triangle, this code uses the top
        # In each line if we find that there's a comment with a similar meaning, close line number and same file, we exlude that comment

        #   0  1   2   3   4
        # 0 1 0.1 0.3 0.8 0.1 -- The comment with index 3 is similar to index 0, so it's removed
        # 1 -  1  0.2 0.3 0.9 -- The comment with index 4 is similar to index 1, so it's removed
        # 2 -  -   1  0.2 0.3
        # 3 -  -   -   1  0.1
        # 4 -  -   -   -   1

        new_comment_count = new_message_similarity.shape[0]
        to_exclude: list[int] = []
        new_comments_filtered: list[Comment] = []

        for i, similarities in enumerate(new_message_similarity):
            if i in to_exclude:
                continue

            # This comment wasn't flagged for exlusion, so it's not similar to any existing comment before it
            new_comments_filtered.append(new_comments[i])

            # If there's another comment with a similar message, a close line number and the same file, add that one to the exlusion list
            for j in range(i + 1, new_comment_count):
                if self.__comments_similar(new_comments[i], new_comments[j], similarities[j].item()):
                    to_exclude.append(j)

        if not existing_comments:
            return new_comments_filtered

        # Now filter new comments against the existing ones
        # This time the matrix will be a bit different, the rows are the filtered new comments and the columns are the existing ones.
        # We go through the rows and if it has even one similarity with an existing comment, we remove it from the final list:

        #    0   1   2
        # 0 0.2 0.1 0.3
        # 1 0.8 0.2 0.5 --> This new comment is similar to the first existing comment (0.8)
        # 2 0.1 0.2 0.1
        # 3 0.2 0.1 0.3
        # 4 0.1 0.4 0.2

        new_messages = [c.comment for c in new_comments_filtered]
        existing_messages = [c.comment for c in existing_comments]

        new_message_embeddings = model.encode(new_messages)
        existing_message_embeddings = model.encode(existing_messages)

        # nxm matrix where n is the number of new messages
        new_and_existing_similarity = model.similarity(new_message_embeddings, existing_message_embeddings)

        # We go through each line (new comment) in the matrix and if there's a similarity in the line greater then a treshold it means the new comment is similar to an existing one.
        new_comments = []
        for i, similarities in enumerate(new_and_existing_similarity):
            comment_exists = False
            for j in range(len(similarities)):
                if self.__comments_similar(new_comments_filtered[i], existing_comments[j], similarities[j].item()):
                    comment_exists = True
                    break

            if not comment_exists:
                new_comments.append(new_comments_filtered[i])

        return new_comments

    @staticmethod
    def __comments_similar(comment1: Comment, comment2: Comment, similarity: float) -> bool:
        similarity_limit = 0.6
        total_similarity_limit = 0.8

        return (similarity > total_similarity_limit and comment1.filename == comment2.filename) or (
            similarity > similarity_limit and abs(comment1.line_number - comment2.line_number) < 5 and comment1.filename == comment2.filename
        )
