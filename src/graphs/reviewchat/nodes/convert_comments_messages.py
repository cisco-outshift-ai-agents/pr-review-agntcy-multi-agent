from langchain_core.messages import HumanMessage, AIMessage

from graphs.reviewchat.state import ReviewChatAssistantState

BOT_USER_TYPE = "Bot"
HUMAN_USER_TYPE = "User"


def create_convert_comments_to_messages_node():
    def convert_comments_to_messages_node(state: ReviewChatAssistantState) -> ReviewChatAssistantState:
        messages = []
        for comment in state["thread"]:
            if comment.user.type == HUMAN_USER_TYPE:
                messages.append(HumanMessage(content=comment.body, id=comment.user.id))
            elif comment.user.type == BOT_USER_TYPE:
                messages.append(AIMessage(content=comment.body))
            else:
                pass
        return {"messages": messages}

    return convert_comments_to_messages_node
