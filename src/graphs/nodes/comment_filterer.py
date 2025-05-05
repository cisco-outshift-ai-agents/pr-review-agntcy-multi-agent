# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, List

from sentence_transformers import SentenceTransformer
from graphs.states import GitHubPRState
from utils.models import GitHubIssueCommentUpdate, IssueComment, ReviewComments, ReviewComment
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
        self._context = context
        self._name = name

    def __call__(self, state: GitHubPRState) -> dict[str, Any]:
        log.info(f"{self._name}: called")

        if self._context.chain is None:
            raise ValueError(f"{self._name}: Chain is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self._context.chain, RunnableSerializable):
            raise ValueError(f"{self._name}: Chain is not a RunnableSerializable")

        # FILTER REVIEW COMMENTS
        filtered_review_comments = self.__filter_review_comments(state)

        log.debug(f"""
        review comment filtering finished.
        new review comments: {json.dumps([comment.model_dump() for comment in filtered_review_comments], indent=4)}
        """)

        # FILTER ISSUE COMMENTS

        filtered_issue_comments = self.__filter_issue_comments(state)

        log.debug(f"""
        issue comment filtering finished.
        new issue comments: {json.dumps([comment.model_dump() for comment in filtered_issue_comments], indent=4)}
        """)

        log.debug("comment filterer finished.")

        # Clean-up Issue Comments and set only the unique ones
        state["new_issue_comments"].clear()

        return {
            "new_review_comments": filtered_review_comments,
            "new_issue_comments": filtered_issue_comments,
            "issue_comments_to_update": state["issue_comments_to_update"],
        }

    def __filter_review_comments(self, state: GitHubPRState) -> ReviewComments:
        try:
            # Use existing comments from state
            review_comments = state["review_comments"]
            new_review_comments = state["new_review_comments"]
            filtered_review_comments = self._remove_duplicate_comments(review_comments, new_review_comments)

            if filtered_review_comments:
                # Filter not useful comments with LLM (this part is not perfect, LLMs are not good at this)
                example_schema = [
                    ReviewComment(filename="file1", line_number=1, comment="comment1", status="added").model_dump(),
                    ReviewComment(filename="file1", line_number=2, comment="comment2", status="added").model_dump(),
                ]

                result: ReviewComments = self._context.chain.invoke(
                    {
                        "input_json_format": json.dumps(example_schema, indent=2),
                        "question": wrap_prompt(
                            f"comments: {filtered_review_comments}",
                        ),
                    }
                )

                filtered_review_comments: List[ReviewComment] = result.issues

            if not filtered_review_comments:
                # Since there are no new comments, create a simple response for the user
                no_new_problems_text = "Reviewed the changes again, but I didn't find any problems in your code which haven't been mentioned before."

                state["new_issue_comments"].append(
                    IssueComment(
                        body=no_new_problems_text,
                        conditions=[],
                    )
                )

            return filtered_review_comments

        except Exception as e:
            log.error(f"{self._name}: Error removing duplicate comments: {e}")
            raise

    def __filter_issue_comments(self, state: GitHubPRState) -> List[IssueComment]:
        def contains_all_condition(comment: str, conditions: list[str]) -> bool:
            for c in conditions:
                if c.lower() not in comment.lower():
                    return False
            return True

        # check new issue comments for duplications
        existing_issue_comments = state["issue_comments"]
        new_issue_comments = state["new_issue_comments"]

        # Remove duplicate issue comments from the new_issue_comments
        unique_new_issue_comments = {c.body: c for c in new_issue_comments}
        filtered_issue_comments = []
        for new_i_c in unique_new_issue_comments.values():
            if "##FILE" in new_i_c.body or "##END_OF_FILE" in new_i_c.body:
                # Skip this file content
                continue
            if not new_i_c.conditions:
                # no conditions, add the comment, skip looking for duplicates
                filtered_issue_comments.append(new_i_c)
                continue

            existing_issue_comment: GitHubIssueCommentUpdate = next(
                (existing_i_c for existing_i_c in existing_issue_comments if contains_all_condition(existing_i_c.body, new_i_c.conditions)),
                None,
            )
            if existing_issue_comment:
                # save the new body content in the comment dict - gh issue comment is not yet updated
                existing_issue_comment.new_body = new_i_c.body
                state["issue_comments_to_update"].append(existing_issue_comment)
            else:
                # add new comment
                filtered_issue_comments.append(new_i_c)

        return filtered_issue_comments

    def _remove_duplicate_comments(self, review_comments: ReviewComments, new_review_comments: ReviewComments) -> ReviewComments:
        if not new_review_comments:
            return []
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
