from graphs.reviewchat.state import ReviewChatAssistantState


def create_get_comment_thread_node():
    def get_comment_thread_node(state: ReviewChatAssistantState) -> ReviewChatAssistantState:
        comment = state["comment"]
        comments = state["comments"]
        thread_comments = [
            c for c in comments if
            comment["in_reply_to_id"] == c.id or c.id == comment["id"] or c.in_reply_to_id == comment["in_reply_to_id"]
        ]
        thread_comments.sort(key=lambda x: x.created_at)
        return {"thread": thread_comments}

    return get_comment_thread_node
