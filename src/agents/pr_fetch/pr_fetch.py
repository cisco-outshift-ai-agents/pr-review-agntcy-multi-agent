import json
import re
from typing import TYPE_CHECKING
from utils.logging_config import logger as log
from pr_graph.state import FileChange, GitHubPRState, Comment

from dotenv import load_dotenv
from fastapi import FastAPI, Request


from manifestdoc.decorator import agent_entry_route
from utils.github_operations import GitHubOperations
from agents.models import GithubDetails
from auth import fastapi_validate_github_signature


if TYPE_CHECKING:
    from github.Repository import Repository
    from github.PullRequest import PullRequest


parameters = {"description": "This is the title reviewer agent it verifies that the pull request title is well described"}


@agent_entry_route(parameters)
def fetch_pr(git_conf: GithubDetails, state: GitHubPRState) -> GitHubPRState:
    log.info("in fetch_pr")
    _github = GitHubOperations(str(git_conf.installation_id))
    repo: Repository = _github.get_repo(git_conf.repo_name)
    pull_request: PullRequest = repo.get_pull(git_conf.pr_number)

    files = pull_request.get_files()
    title = [pull_request.title]
    description = [pull_request.body]

    changes = []
    existing_comments = []

    # Fetch existing comments from PR
    try:
        pr_comments = _github.list_comments_from_pr(git_conf.repo_name, git_conf.pr_number)
        for comment in pr_comments:
            existing_comments.append(
                Comment(
                    filename=comment.path,
                    line_number=comment.position,
                    comment=comment.body,
                    status="added" if comment.position is not None else "removed",
                )
            )
    except Exception as e:
        log.error(f"Error fetching existing comments: {e}")
        pass

    for file in files:
        filename = file.filename
        patch = file.patch

        if patch:
            # Split the patch into lines
            lines = patch.split("\n")

            start_line_removed = None
            start_line_added = None
            current_change = None

            for line in lines:
                # Match the line number information
                if line.startswith("@@"):
                    match = re.search(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                    if match:
                        start_line_removed = int(match.group(1))
                        start_line_added = int(match.group(2))
                        current_change = None
                elif line.startswith("-") and start_line_removed is not None:
                    if current_change and current_change["status"] == "removed":
                        current_change["changed_code"] += "\n" + line
                    else:
                        if current_change:
                            changes.append(current_change)
                        current_change = FileChange(filename=filename, start_line=start_line_removed, changed_code=line, status="removed")
                    start_line_removed += 1
                elif line.startswith("+") and start_line_added is not None:
                    if current_change and current_change["status"] == "added":
                        current_change["changed_code"] += "\n" + line
                    else:
                        if current_change:
                            changes.append(current_change)
                        current_change = FileChange(filename=filename, start_line=start_line_added, changed_code=line, status="added")
                    start_line_added += 1
                elif start_line_removed is not None and start_line_added is not None:
                    if current_change:
                        changes.append(current_change)
                        current_change = None
                    start_line_removed += 1
                    start_line_added += 1
    log.info(f"""
        fetch pr finished.
        changes: {json.dumps(changes, indent=4)},
        title: {title},
        description: {description},
        existing_comments: {json.dumps([comment.model_dump() for comment in existing_comments], indent=4)}
        """)

    return {
        **state,
        "changes": changes,
        "title": title,
        "description": description,
        "existing_comments": existing_comments,
        "comments": [],
    }  # Initialize empty list for new comments


load_dotenv()

app = FastAPI()


# Just to test entrypoint for dockerfile
@app.post("/api/webhook")
@fastapi_validate_github_signature
def invoke(request: Request):
    git_details = GithubDetails(
        installation_id="",
        repo_name="",
        branch_name="",
        pr_number="",
    )

    fetch_pr(git_details, state=GitHubPRState())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5500)
