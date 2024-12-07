from typing import Dict, Any

from langgraph.constants import END
from langgraph.graph import StateGraph

from graphs.reviewchat.chains.review_chat_assistant import create_review_chat_assistant_chain
from graphs.reviewchat.nodes.comment_replier import create_comment_replier_node
from graphs.reviewchat.nodes.contexts import GitHubOperationsContext, ReviewChatAssistantContext
from graphs.reviewchat.nodes.convert_comments_messages import create_convert_comments_to_messages_node
from graphs.reviewchat.nodes.fetch_comment_related_patch import create_fetch_comment_related_patch_node
from graphs.reviewchat.nodes.fetch_comments import create_fetch_comments_node
from graphs.reviewchat.nodes.get_comment_thread import create_get_comment_thread_node
from graphs.reviewchat.nodes.review_chat_assistant import create_review_chat_assistant_node
from graphs.reviewchat.routers import is_replied_to_bot_router, END_ROUTE, CONTINUE_ROUTE, is_skipped_router, \
    REPLIER_NODE_ROUTE
from graphs.reviewchat.state import ReviewChatAssistantState
from utils.github_operations import GitHubOperations
from utils.modelfactory import models

FETCH_COMMENTS_NODE = "fetch_comments"
GET_COMMENT_THREAD_NODE = "get_comment_thread"
CONVERT_COMMENT_THREAD_TO_MESSAGES_NODE = "convert_comment_thread_to_messages"
FETCH_COMMENT_RELATED_PATCH_NODE = "fetch_comment_related_patch"
REVIEW_CHAT_ASSISTANT_NODE = "review_chat_assistant"
COMMENT_REPLIER_NODE = "comment_replier"


class ReviewChatWorkflow:
    def __init__(self, installation_id: int):
        self.__github_ops = GitHubOperations(str(installation_id))
        self.__github_context = GitHubOperationsContext(github_ops=self.__github_ops)
        self.__model = models.get_vertexai()

        self.__graph = self.__create_graph()

    def __call__(self, repo_name: str, pr_number: int, comment: Dict[str, Any]):
        state = ReviewChatAssistantState(
            repo_name=repo_name,
            pr_number=pr_number,
            comment=comment,
            messages=[],
            comments=[],
            thread=[],
            reviewed_patch=None,
            is_skipped=False,
        )
        self.__graph.invoke(state)

    def __create_graph(self):
        workflow = StateGraph(ReviewChatAssistantState)

        workflow.add_node(
            FETCH_COMMENTS_NODE,
            create_fetch_comments_node(self.__github_context))
        workflow.add_node(
            GET_COMMENT_THREAD_NODE,
            create_get_comment_thread_node())
        workflow.add_node(
            CONVERT_COMMENT_THREAD_TO_MESSAGES_NODE,
            create_convert_comments_to_messages_node())
        workflow.add_node(
            FETCH_COMMENT_RELATED_PATCH_NODE,
            create_fetch_comment_related_patch_node(self.__github_context))
        workflow.add_node(
            REVIEW_CHAT_ASSISTANT_NODE,
            create_review_chat_assistant_node(
                ReviewChatAssistantContext(chain=create_review_chat_assistant_chain(self.__model))
            ))
        workflow.add_node(
            COMMENT_REPLIER_NODE,
            create_comment_replier_node(self.__github_context))

        workflow.add_conditional_edges(
            FETCH_COMMENTS_NODE,
            is_replied_to_bot_router,
            {END_ROUTE: END, CONTINUE_ROUTE: [GET_COMMENT_THREAD_NODE, FETCH_COMMENT_RELATED_PATCH_NODE]})
        workflow.add_edge(GET_COMMENT_THREAD_NODE, CONVERT_COMMENT_THREAD_TO_MESSAGES_NODE)
        workflow.add_edge(
            [CONVERT_COMMENT_THREAD_TO_MESSAGES_NODE, FETCH_COMMENT_RELATED_PATCH_NODE],
            REVIEW_CHAT_ASSISTANT_NODE
        )
        workflow.add_conditional_edges(
            REVIEW_CHAT_ASSISTANT_NODE,
            is_skipped_router,
            {END_ROUTE: END, REPLIER_NODE_ROUTE: COMMENT_REPLIER_NODE})

        workflow.set_entry_point(FETCH_COMMENTS_NODE)

        return workflow.compile()
