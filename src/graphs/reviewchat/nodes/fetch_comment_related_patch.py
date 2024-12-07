from graphs.reviewchat.nodes.contexts import GitHubOperationsContext
from graphs.reviewchat.state import ReviewChatAssistantState


def create_fetch_comment_related_patch_node(context: GitHubOperationsContext):
    def fetch_comment_related_patch_node(state: ReviewChatAssistantState) -> ReviewChatAssistantState:
        try:
            repo = context.github_ops.get_repo(state["repo_name"])
        except Exception as e:
            raise ValueError(f"Error getting repository from GitHub: {e}")

        try:
            pr = repo.get_pull(state["pr_number"])
        except Exception as e:
            raise ValueError(f"Error getting pull request from GitHub: {e}")

        try:
            files = pr.get_files()
        except Exception as e:
            raise ValueError(f"Error getting patch from GitHub: {e}")

        for f in files:
            if f.filename == state["comment"]["path"]:
                return {"reviewed_patch": f.patch}

        raise ValueError(f"File {state["comment"]["path"]} not found in the PR's files")

    return fetch_comment_related_patch_node
