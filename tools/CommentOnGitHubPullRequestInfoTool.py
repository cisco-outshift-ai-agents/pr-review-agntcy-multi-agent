import os
from typing import Any
from github import Github, GithubIntegration, UnknownObjectException

from typing import Type
from crewai_tools.tools.base_tool import BaseTool
from pydantic.v1 import BaseModel, Field


class CommentOnGitHubPullRequestInfoInput(BaseModel):
    """Input for CommentOnGitHubPullRequestInfo."""

    installation_id: str = Field(..., description="The GitHub application installation ID.")
    pr_number: int = Field(..., description="The GitHub pull request number.")
    repo_name: str = Field(..., description="The GitHub repository name.")
    file_name: str = Field(..., description="The name of the file to comment on in GitHub")
    line_number: str = Field(..., description="The line number to comment on in the file")
    comment_content: str = Field(..., description="The content of the comment")
    changed_line: str = Field(..., description="The line on which the comment should be made")


class CommentOnGitHubPullRequestOutput(BaseModel):
    result: str = Field(..., description="Result of adding comment on pull request.")


class CommentOnGitHubPullRequestInfoTool(BaseTool):
    name: str = "Comment on GitHub pull request"
    description: str = "Add comment on GitHub pull request for App with: installation_id, pr_number, repo_name, file_name, and line_number."
    args_schema: Type[BaseModel] = CommentOnGitHubPullRequestInfoInput

    def _run(
        self, installation_id: str, pr_number: int, repo_name: str, file_name: str, line_number: str, comment_content: str, changed_line: str
    ) -> Any:
        # print(f'FILE_PATH: {file_path}')
        # if repo_name == "your_repo_name":
        #     return CommentOnGitHubPullRequestOutput(result="Failure. repo name is not correct. try using the repo_name you received as input")
        # if installation_id == "string":
        #     return CommentOnGitHubPullRequestOutput(result="Failure. installation id is not correct. try using the installation_id you received as input")
        with open(os.getenv("GITHUB_APP_PRIVATE_KEY"), "r") as key_file:
            PRIVATE_KEY = key_file.read()
        try:
            app_id = os.getenv("GITHUB_APP_ID")
            git_integration = GithubIntegration(app_id, PRIVATE_KEY)
            access_token = git_integration.get_access_token(installation_id).token
            github = Github(access_token)
            repo = github.get_repo(repo_name)
            pull_request = repo.get_pull(pr_number)
            files = pull_request.get_files()
        except UnknownObjectException as error:
            return CommentOnGitHubPullRequestOutput(
                result="Failure. got 404 from GitHub API, installation_id or pr_number or repo_name are incorrect"
            )
        except Exception as error:
            return CommentOnGitHubPullRequestOutput(result="Failure. got error from GitHub API")
        latest_commit = list(pull_request.get_commits())[-1].commit
        commit = repo.get_commit(latest_commit.sha)
        commentedOnFile = False
        for pr_file in files:
            if pr_file.filename == file_name:
                # Create a comment on the specific line
                try:
                    pull_request.create_review_comment(
                        comment_content,
                        commit,
                        path=pr_file.filename,
                        line=int(line_number),
                        side="LEFT" if changed_line.startswith("-") else "RIGHT",
                    )
                except Exception as error:
                    return CommentOnGitHubPullRequestOutput(result=f"Failure, reason: {error}")
                commentedOnFile = True
                print(f"Commented on {pr_file.filename}")
                break
        if not commentedOnFile:
            return CommentOnGitHubPullRequestOutput(result="Failure. file_name doesn't exist in GitHub changed files")
        return CommentOnGitHubPullRequestOutput(result="Success")
