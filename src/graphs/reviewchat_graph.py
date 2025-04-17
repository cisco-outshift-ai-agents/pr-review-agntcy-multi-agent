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

from typing import Dict, Any

from langgraph.constants import END
from langgraph.graph import StateGraph
from utils.logging_config import logger as log

from graphs.chains import create_review_chat_assistant_chain
from graphs.nodes import (
    CommentsFetcher,
    CommentsToThreadConverter,
    CommentsToMessagesConverter,
    CommentRelatedPatchFetcher,
    ReviewChatAssistant,
    CommentReplier,
)
from graphs.nodes.contexts import DefaultContext
from graphs.states import ReviewChatAssistantState
from utils.github_operations import GitHubOperations
from utils.modelfactory import models

COMMENTS_FETCHER_NODE = "comments_fetcher"
COMMENTS_TO_THREAD_CONVERTER_NODE = "comments_to_thread_converter"
COMMENTS_TO_MESSAGES_CONVERTER_NODE = "comments_to_messages_converter"
COMMENT_RELATED_PATCH_FETCHER_NODE = "comment_related_patch_fetcher"
REVIEW_CHAT_ASSISTANT_NODE = "review_chat_assistant"
COMMENT_REPLIER_NODE = "comment_replier"

BOT_USER_TYPE = "Bot"


class ReviewChatWorkflow:
    def __init__(self, installation_id: int, pr_number: int, repo_name: str, comment: Dict[str, Any]):
        log.info(
            f"Initializing ReviewChatWorkflow with installation_id: {installation_id}, pr_number: {pr_number}, repo_name: {repo_name}")
        self.__repo_name = repo_name
        self.__pr_number = pr_number
        self.__comment = comment

        github = GitHubOperations(str(installation_id), self.__repo_name, self.__pr_number)
        self.__context = DefaultContext(github=github, chain=create_review_chat_assistant_chain(models.get_azure_openai()))

        self.__graph = self.__create_graph()

    def run(self):
        state = ReviewChatAssistantState(
            comment=self.__comment,
            messages=[],
            review_comments=[],
            review_comment_thread=[],
            reviewed_patch=None,
            is_skipped=False,
        )
        return self.__graph.invoke(state)

    def __create_graph(self):
        workflow = StateGraph(ReviewChatAssistantState)

        workflow.add_node(COMMENTS_FETCHER_NODE, CommentsFetcher(self.__context))
        workflow.add_node(COMMENTS_TO_THREAD_CONVERTER_NODE, CommentsToThreadConverter())
        workflow.add_node(COMMENTS_TO_MESSAGES_CONVERTER_NODE, CommentsToMessagesConverter())
        workflow.add_node(COMMENT_RELATED_PATCH_FETCHER_NODE, CommentRelatedPatchFetcher(self.__context))
        workflow.add_node(REVIEW_CHAT_ASSISTANT_NODE, ReviewChatAssistant(self.__context))
        workflow.add_node(COMMENT_REPLIER_NODE, CommentReplier(self.__context))

        workflow.add_conditional_edges(
            COMMENTS_FETCHER_NODE,
            self.is_replied_to_bot_router,
            [COMMENTS_TO_THREAD_CONVERTER_NODE, COMMENT_RELATED_PATCH_FETCHER_NODE, END],
        )
        workflow.add_edge(COMMENTS_TO_THREAD_CONVERTER_NODE, COMMENTS_TO_MESSAGES_CONVERTER_NODE)
        workflow.add_edge([COMMENTS_TO_MESSAGES_CONVERTER_NODE, COMMENT_RELATED_PATCH_FETCHER_NODE], REVIEW_CHAT_ASSISTANT_NODE)
        workflow.add_conditional_edges(REVIEW_CHAT_ASSISTANT_NODE, self.is_skipped_router, [COMMENT_REPLIER_NODE, END])

        workflow.set_entry_point(COMMENTS_FETCHER_NODE)

        try:
            compiled_graph = workflow.compile()
        except Exception as e:
            raise ValueError(f"Error compiling graph: {e}") from e

        return compiled_graph

    @staticmethod
    def is_replied_to_bot_router(state: ReviewChatAssistantState):
        if len(state["review_comments"]) == 0:
            return END

        if state["review_comments"][0].user.type != BOT_USER_TYPE:
            return END

        return [COMMENTS_TO_THREAD_CONVERTER_NODE, COMMENT_RELATED_PATCH_FETCHER_NODE]

    @staticmethod
    def is_skipped_router(state: ReviewChatAssistantState):
        if state["is_skipped"]:
            return END

        return COMMENT_REPLIER_NODE
