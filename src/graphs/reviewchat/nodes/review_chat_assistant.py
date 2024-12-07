from langchain_core.messages import AIMessage

from agents.pr_review_chat import PRReviewChatResponse
from graphs.reviewchat.nodes.contexts import ReviewChatAssistantContext
from graphs.reviewchat.state import ReviewChatAssistantState


def create_review_chat_assistant_node(ctx: ReviewChatAssistantContext):
    def review_chat_assistant_node(state: ReviewChatAssistantState) -> ReviewChatAssistantState:
        message_history = state["messages"]
        if message_history is None or len(message_history) < 2:
            raise ValueError("At least the original review and a comment should be presented in the message history")

        response: PRReviewChatResponse = (ctx
        .chain(message_history)
        .invoke(
            {"line_number": state["comment"]["line"], "code": state["reviewed_patch"]}))

        if response.is_skipped:
            return {"is_skipped": True}

        return {"is_skipped": False, "response": AIMessage(content=response.response)}

    return review_chat_assistant_node
