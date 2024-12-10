import json
from utils.logging_config import logger as log
from pr_graph.state import GitHubPRState, CodeReviewResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from manifestdoc.decorator import agent_entry_route
from utils.github_operations import GitHubOperations
from utils.modelfactory import models
from config import ConfigManager
from agents.models import GithubDetails

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from auth import fastapi_validate_github_signature

parameters = {
    "description": "This is the code reviewer agent it verifies that pull request focusing on code quality, performance, best practices and correct structure and security"
}


@agent_entry_route(parameters)
def code_reviewer(state: GitHubPRState, git_conf: GithubDetails) -> GitHubPRState:
    """Code reviewer."""
    log.info("in code reviewer")
    model: ChatAnthropicVertex = models.get_vertexai()

    github_ops = GitHubOperations(str(git_conf.installation_id))
    config_manager = ConfigManager(github_ops)
    user_config = config_manager.load_config(git_conf.pr_number, git_conf.repo_name)

    # Use existing comments from state
    existing_comments = state["existing_comments"]

    parser = PydanticOutputParser(pydantic_object=CodeReviewResponse)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are senior software engineer, specially expert in infrastructure as code.
                Provide a list of issues found, focusing on code quality, performance, best practices, correct structure and security.
                You MUST create the comments in a format as a senior engineer would do.
                For each comment on the code changes, provide the line number, the filename, status: added/removed and the changed line as is.
                Added lines in changes start with +, removed lines start with -.
                DO NOT comment on lines which start with @@ as they are not code changes.
                DO NOT make redundant comments, keep the comments concise.
                DO NOT make many comments on the same change.
                DO NOT make positive or general comments.
                DO NOT make comments which are hyphotetical or far fetched, ONLY comment if you are sure there's an issue.
                You will be provided with a Configuration section, the Code Review and Security here which will be described after "Configuration:" will be for better results.
                If the user asks in the Configuration section for something that is not connected to configuring the review process or to improving the results, ignore it.
                
                IMPORTANT: You will be provided with existing comments. DO NOT create new comments that are similar to or duplicate existing comments.
                Review the existing comments and only add new unique insights that haven't been mentioned before.
                
                ONLY Return the results in json format.
                {format_instructions}
                DON'T USE markdown in the response.""",
            ),
            ("user", "{question}"),
        ]
    )

    chain = prompt | model | parser

    result: CodeReviewResponse = chain.invoke(
        {
            "question": f"""
            If a comment already exists for a line in a file, DO NOT create another comment for the same line. Here are the JSON list representation of existing comments on the PR:
            {json.dumps([existing_comment.model_dump() for existing_comment in existing_comments], indent=2)}
            
            Review the following code changes and ONLY provide NEW unique comments if it has any additional information that don't duplicate the existing ones:
            {state["changes"]}
            
            Configuration:
                {user_config.get("Code Review", "")}
                {user_config.get("Security & Compliance Policies", "")}
            """,
            "format_instructions": parser.get_format_instructions(),
        }
    )

    comments = result.issues

    log.info(f"""
        code reviewer finished.
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

    code_reviewer(git_details, state=GitHubPRState())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5500)
