from graphs.reviewchat.state import ReviewChatAssistantState

BOT_USER_TYPE = "Bot"

END_ROUTE = "END"
CONTINUE_ROUTE = "continue"
REPLIER_NODE_ROUTE = "comment_replier_node"


def is_replied_to_bot_router(state: ReviewChatAssistantState):
    if len(state["comments"]) == 0:
        return END_ROUTE

    if state["comments"][0].user.type != BOT_USER_TYPE:
        return END_ROUTE

    return CONTINUE_ROUTE


def is_skipped_router(state: ReviewChatAssistantState):
    if state["is_skipped"]:
        return END_ROUTE

    return REPLIER_NODE_ROUTE
