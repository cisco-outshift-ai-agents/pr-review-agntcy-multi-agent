from graphs.reviewchat.nodes.contexts import GitHubOperationsContext
from graphs.reviewchat.state import ReviewChatAssistantState


def create_fetch_comments_node(context: GitHubOperationsContext):
    def fetch_comments_node(state: ReviewChatAssistantState) -> ReviewChatAssistantState:
        try:
            repo = context.github_ops.get_repo(state["repo_name"])
        except Exception as e:
            raise ValueError(f"Error getting repository from GitHub: {e}")

        try:
            pr = repo.get_pull(state["pr_number"])
        except Exception as e:
            raise ValueError(f"Error getting pull request from GitHub: {e}")

        try:
            comments = pr.get_comments()
        except Exception as e:
            raise ValueError(f"Error getting comments from GitHub: {e}")

        return {"comments": comments}

    return fetch_comments_node
