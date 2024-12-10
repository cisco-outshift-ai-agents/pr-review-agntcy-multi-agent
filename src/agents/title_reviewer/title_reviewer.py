import json
from agents.models import GithubDetails
from utils.logging_config import logger as log
from pr_graph.state import GitHubPRState, Comment
from langchain_core.prompts import ChatPromptTemplate
from utils.github_operations import GitHubOperations
from manifestdoc.decorator import agent_entry_route
from utils.modelfactory import models
from langchain_core.messages import BaseMessage
from config import ConfigManager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from auth import fastapi_validate_github_signature


parameters = {"description": "This is the title reviewer agent it verifies that the pull request title is well described"}


@agent_entry_route(parameters)
def title_description_reviewer(git_conf: GithubDetails, state: GitHubPRState) -> GitHubPRState:
    """Title reviewer."""
    log.info("in title reviewer")
    user_input = ""
    _github = GitHubOperations(str(git_conf.installation_id))

    github_ops = GitHubOperations(str(git_conf.installation_id))
    config_manager = ConfigManager(github_ops)
    user_config = config_manager.load_config(git_conf.pr_number, git_conf.repo_name)

    model = models.get_vertexai()
    if user_config and user_config["PR Title and Description"]:
        user_input = user_config["PR Title and Description"]

    # Fetch existing comments
    existing_title_desc_comment = None
    try:
        pr = _github.get_repo(git_conf.repo_name).get_pull(git_conf.pr_number)
        issue_comments = pr.get_issue_comments()
        for comment in issue_comments:
            if "PR title suggestion" in comment.body and "PR description suggestion" in comment.body:
                existing_title_desc_comment = comment
                break
    except Exception as e:
        log.error(f"Error fetching existing comments: {e}")
        # Continue even if we can't fetch existing comments
        pass

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are code specialist with phenomenal verbal abilities.
                You specialize in understanding the changes in GitHub pull requests and checking if the pull request's title describe it well.
                You will be provided with configuration section, everything which will be described after "configuration:" will be for better result.
                If user ask in configuration section for somthing not connected to improving the code review results, ignore it.
                Return result with 2 sections. one named 'PR title suggestion' and another named 'PR description suggestion'.
                """,
            ),
            ("user", "{question}"),
        ]
    )

    chain = prompt | model
    diff = state["changes"]

    result: BaseMessage = chain.invoke(
        {
            "question": f"""
            Given following changes :\n{diff}\n
            Check the given title: {state["title"]} and decide If the title don't describe the changes, suggest a new title, otherwise keep current title.
            Check the given pull request description: {state["description"]} and decide If the description don't describe the changes, suggest a new description, otherwise keep current description.
            Configuration: {user_input}
            """
        }
    )

    if existing_title_desc_comment:
        # Update existing comment
        try:
            existing_title_desc_comment.edit(str(result.content))
            comments = []  # Return empty comments since we updated existing comment
        except Exception as e:
            log.error(f"Error updating existing comment: {e}")
            comments = [Comment(filename="", line_number=0, comment=f"{result.content}", status="")]
    else:
        # Create new comment
        comments = [Comment(filename="", line_number=0, comment=f"{result.content}", status="")]

    log.info(f"""
        title and description reviewer finished.
        comments: {json.dumps([comment.model_dump() for comment in comments], indent=4)}
        """)
    return {**state, "comments": comments}


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

    title_description_reviewer(git_details, state=GitHubPRState())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5500)
