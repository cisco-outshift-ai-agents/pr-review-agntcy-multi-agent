from typing import List, Union

from langchain_core.messages import HumanMessage, AIMessage

from graphs.states import ReviewChatAssistantState
from utils.logging_config import logger as log

BOT_USER_TYPE = "Bot"
HUMAN_USER_TYPE = "User"

# Define the type for messages
MessageType = Union[HumanMessage, AIMessage]


class CommentsToMessagesConverterNode:
    def __init__(self, name: str = "comments_to_messages_converter_node"):
        self.name = name

    def __call__(self, state: ReviewChatAssistantState) -> dict:
        log.info(f"{self.name} called with state: {state}")

        messages: List[MessageType] = []  # Use the union type for the list
        for comment in state["thread"]:
            if comment.user.type == HUMAN_USER_TYPE:
                messages.append(HumanMessage(content=comment.body, response_metadata={"author": comment.user.id}))
            elif comment.user.type == BOT_USER_TYPE:
                messages.append(AIMessage(content=comment.body, response_metadata={"author": "alfred-bot"}))
            else:
                pass
        return {"messages": messages}
