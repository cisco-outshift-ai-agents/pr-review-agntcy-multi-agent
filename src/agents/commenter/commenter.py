from utils.logging_config import logger as log
from pr_graph.state import GitHubPRState
from github import UnknownObjectException
from agents.models import GithubDetails
from utils.github_operations import GitHubOperations
from manifestdoc.decorator import agent_entry_route


from dotenv import load_dotenv
from fastapi import FastAPI, Request


from auth import fastapi_validate_github_signature


parameters = {"description": "This is the commenter agent it is reponsible to take all comments produced and push it to the repo"}


@agent_entry_route(parameters)
def commenter(git_conf: GithubDetails, state: GitHubPRState) -> GitHubPRState:
    try:
        _github = GitHubOperations(str(git_conf.installation_id))
        repo = _github.get_repo(git_conf.repo_name)
        pull_request = repo.get_pull(git_conf.pr_number)
        files = pull_request.get_files()
    except UnknownObjectException:
        log.error(f"repo: {git_conf.repo_name} with pr: {git_conf.pr_number} not found")
        return state
    except Exception as error:
        log.error(f"General error while fetching repo: {git_conf.repo_name} with pr: {git_conf.pr_number}. error: {error}")
        return state
    latest_commit = list(pull_request.get_commits())[-1].commit
    commit = repo.get_commit(latest_commit.sha)
    for pr_file in files:
        for comment in state["comments"]:
            if comment.filename == pr_file.filename:
                # Create a comment on the specific line
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
    return state


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

    commenter(git_details, state=GitHubPRState())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5500)
