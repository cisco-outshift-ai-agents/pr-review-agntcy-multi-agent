from graphs.reviewchat.nodes.contexts import GitHubOperationsContext
from graphs.reviewchat.state import ReviewChatAssistantState


def create_comment_replier_node(context: GitHubOperationsContext):
    def comment_replier_node(state: ReviewChatAssistantState) -> ReviewChatAssistantState:
        try:
            context.github_ops.reply_on_pr_comment(
                state["repo_name"],
                state["pr_number"],
                state["comment"]["in_reply_to_id"],
                state["messages"][-1].content
            )
        except Exception as e:
            raise ValueError(f"Error sending reply to comment on GitHub: {e}")

        return {}

    return comment_replier_node
