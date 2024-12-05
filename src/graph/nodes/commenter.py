from functools import partial
from github import UnknownObjectException
from graph.state import GitHubPRState
from .contexts import GitHubContext
from utils.logging_config import logger as log


def create_commenter_node(context: GitHubContext):
    def commenter(state: GitHubPRState) -> GitHubPRState:
        try:
            repo = context.github.get_repo(context.repo_name)
            pull_request = repo.get_pull(context.pr_number)
            files = pull_request.get_files()
            latest_commit = list(pull_request.get_commits())[-1].commit
            commit = repo.get_commit(latest_commit.sha)

            for pr_file in files:
                for comment in state["comments"]:
                    if comment.filename == pr_file.filename:
                        pull_request.create_review_comment(
                            comment.comment,
                            commit,
                            path=pr_file.filename,
                            line=int(comment.line_number),
                            side="LEFT" if comment.status == "removed" else "RIGHT",
                        )

            for comment in state["comments"]:
                if comment.filename == "":
                    pull_request.create_issue_comment(comment.comment)

        except UnknownObjectException:
            log.error(f"repo: {context.repo_name} with pr: {context.pr_number} not found")
        except Exception as error:
            log.error(f"General error while fetching repo: {context.repo_name} with pr: {context.pr_number}. error: {error}")

        return state

    return partial(commenter)
