import json
from typing import Any

from sentence_transformers import SentenceTransformer
from graphs.states import GitHubPRState
from utils.models import ReviewComments, ReviewComment
from utils.logging_config import logger as log
from utils.wrap_prompt import wrap_prompt
from .contexts import DefaultContext
from langchain_core.runnables import RunnableSerializable


class CommentFilterer:
    # When two comments considered similar in the same or close lines
    __similarity_limit = 0.6
    # When two comments considered equal, regardless the line
    __total_similarity_limit = 0.9

    def __init__(self, context: DefaultContext, name: str = "comment_filterer"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict[str, Any]:
        log.info(f"{self.name}: called")

        if self.context.chain is None:
            raise ValueError(f"{self.name}: Chain is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self.context.chain, RunnableSerializable):
            raise ValueError(f"{self.name}: Chain is not a RunnableSerializable")

        # FILTER REVIEW COMMENTS
        try:
            # Use existing comments from state
            review_comments = state["review_comments"]
            new_review_comments = state["new_review_comments"]

            if not new_review_comments:
                # TODO: this return has to be fixed when the filter of the issue comments is implemented here
                return {}

            filtered_review_comments = self.__remove_duplicate_comments(review_comments, new_review_comments)

            if filtered_review_comments:
                # Filter not useful comments with LLM (this part is not perfect, LLMs are not good at this)
                example_schema = [
                    ReviewComment(filename="file1", line_number=1, comment="comment1", status="added").model_dump(),
                    ReviewComment(filename="file1", line_number=2, comment="comment2", status="added").model_dump(),
                ]

                result: ReviewComments = self.context.chain.invoke(
                    {
                        "input_json_format": json.dumps(example_schema, indent=2),
                        "question": wrap_prompt(
                            f"comments: {filtered_review_comments}",
                        ),
                    }
                )

                filtered_review_comments = result.issues

            if not filtered_review_comments:
                # Since there are no new comments, create a simple response for the user
                filtered_review_comments.append(
                    ReviewComment(
                        filename="",
                        line_number=0,
                        comment="Reviewed the changes again, but I didn't find any problems in your code which haven't been mentioned before.",
                        status="",
                    )
                )

        except Exception as e:
            log.error(f"{self.name}: Error removing duplicate review comments: {e}")
            raise

        log.debug(f"""
        review comment filtering finished.
        new review comments: {json.dumps([comment.model_dump() for comment in filtered_review_comments], indent=4)}
        """)

        # FILTER ISSUE COMMENTS
        # TODO:

        filtered_issue_comments = []

        log.debug(f"""
        issue comment filtering finished.
        new issue comments: {json.dumps([comment.model_dump() for comment in filtered_issue_comments], indent=4)}
        """)

        updated_state = {}
        if len(filtered_review_comments) > 0:
            updated_state["new_review_comments"] = filtered_review_comments
        if len(filtered_issue_comments) > 0:
            updated_state["new_issue_comments"] = filtered_issue_comments

        log.debug("comment filterer finished.")

        return updated_state

    def __remove_duplicate_comments(self, review_comments: ReviewComments, new_review_comments: ReviewComments) -> ReviewComments:
        # We use a simple embeding model to create vector embedings
        # We calculate the embedings first and then the similarities
        # The similarities are the cosine of the angle between the vectors, [-1, 1], the closer to 1 the more similar two sentences are
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        # First we remove the duplications from the new_review_comments:
        new_messages = [c.comment for c in new_review_comments]
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
        to_exclude: set[int] = set()
        new_review_comments_filtered: ReviewComments = []

        for i, similarities in enumerate(new_message_similarity):
            if i in to_exclude:
                continue

            # This comment wasn't flagged for exlusion, so it's not similar to any existing comment before it
            new_review_comments_filtered.append(new_review_comments[i])

            # If there's another comment with a similar message, a close line number and the same file, add that one to the exlusion list
            for j in range(i + 1, new_comment_count):
                if self.__comments_similar(new_review_comments[i], new_review_comments[j], similarities[j].item()):
                    to_exclude.add(j)

        if not review_comments:
            return new_review_comments_filtered

        # Now filter new comments against the existing ones
        # This time the matrix will be a bit different, the rows are the filtered new comments and the columns are the existing ones.
        # We go through the rows and if it has even one similarity with an existing comment, we remove it from the final list:

        #    0   1   2
        # 0 0.2 0.1 0.3
        # 1 0.8 0.2 0.5 --> This new comment is similar to the first existing comment (0.8)
        # 2 0.1 0.2 0.1
        # 3 0.2 0.1 0.3
        # 4 0.1 0.4 0.2

        new_messages = [c.comment for c in new_review_comments_filtered]
        existing_messages = [c.comment for c in review_comments]

        new_message_embeddings = model.encode(new_messages)
        existing_message_embeddings = model.encode(existing_messages)

        # nxm matrix where n is the number of new messages
        new_and_existing_similarity = model.similarity(new_message_embeddings, existing_message_embeddings)

        # We go through each line (new comment) in the matrix and if there's a similarity in the line greater then a treshold it means the new comment is similar to an existing one.
        merged_review_comments_filtered = []
        for i, similarities in enumerate(new_and_existing_similarity):
            comment_exists = False
            for j in range(len(similarities)):
                if self.__comments_similar(new_review_comments_filtered[i], review_comments[j], similarities[j].item()):
                    comment_exists = True
                    break

            if not comment_exists:
                merged_review_comments_filtered.append(new_review_comments_filtered[i])

        return merged_review_comments_filtered

    def __comments_similar(self, comment1: ReviewComment, comment2: ReviewComment, similarity: float) -> bool:
        return (similarity > self.__total_similarity_limit and comment1.filename == comment2.filename) or (
            similarity > self.__similarity_limit and abs(comment1.line_number - comment2.line_number) < 5 and comment1.filename == comment2.filename
        )
