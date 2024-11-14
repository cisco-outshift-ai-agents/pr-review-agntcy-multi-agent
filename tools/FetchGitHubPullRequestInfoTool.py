import os
from typing import List, Type, Optional
from crewai_tools.tools.base_tool import BaseTool
from github import Github, GithubIntegration
from pydantic.v1 import BaseModel, Field


class FetchGitHubPullRequestInfoInput(BaseModel):
    """Input for FetchGitHubPullRequestInfo."""

    installation_id: str = Field(..., description="The GitHub application installation ID.")
    pr_number: int = Field(..., description="The GitHub pull request number.")
    repo_name: str = Field(..., description="The GitHub repository name.")


class FileChangeInfo(BaseModel):
    file_name: str = Field(..., description="The file name where the changes occurred.")
    changes: str = Field(..., description="The the changes in diff format.")


class FetchGitHubPullRequestInfoOutput(BaseModel):
    title: str = Field(..., description="The title of the GitHub pull request.")
    description: Optional[str] = Field(..., description="The description of the GitHub pull request.")
    changes: List[FileChangeInfo] = Field(..., description="The changes in GitHub pull request.")


class FetchGitHubPullRequestInfoTool(BaseTool):
    name: str = "Fetches GitHub pull request information"
    description: str = "Fetches GitHub pull request information for a specified App installation_id, pr_number, and repo_name."
    args_schema: Type[BaseModel] = FetchGitHubPullRequestInfoInput
    return_schema: Type[BaseModel] = FetchGitHubPullRequestInfoOutput

    def _run(
        self,
        installation_id: str,
        pr_number: int,
        repo_name: str,
    ) -> FetchGitHubPullRequestInfoOutput:
        app_id = os.getenv("GITHUB_APP_ID")
        with open(os.getenv("GITHUB_APP_PRIVATE_KEY"), "r") as key_file:
            github_private_key = key_file.read()

        git_integration = GithubIntegration(app_id, github_private_key)
        access_token = git_integration.get_access_token(installation_id).token
        github = Github(access_token)
        repo = github.get_repo(repo_name)
        pull_request = repo.get_pull(pr_number)
        files = pull_request.get_files()
        file_change_infos = [FileChangeInfo(file_name=file.filename, changes=file.patch) for file in files]
        return FetchGitHubPullRequestInfoOutput(title=pull_request.title, description=pull_request.body, changes=file_change_infos)
