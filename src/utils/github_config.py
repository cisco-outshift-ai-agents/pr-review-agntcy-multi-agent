import os
import github.Auth
from github import Github, GithubIntegration
from utils.logging_config import logger as log


def init_github(installation_id: str) -> Github:
    key_file_path = os.getenv("GITHUB_APP_PRIVATE_KEY_FILE")
    if key_file_path:
        with open(key_file_path, "r") as key_file:
            private_key = key_file.read()
    else:
        log.debug("GITHUB_APP_PRIVATE_KEY_FILE not set, using GITHUB_APP_PRIVATE_KEY env var")
        private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")

    if not private_key:
        raise Exception("Private key is missing")

    app_id = os.getenv("GITHUB_APP_ID")
    if not app_id:
        raise Exception("App Id is missing")

    git_integration = GithubIntegration(auth=github.Auth.AppAuth(app_id, private_key))
    github_token = git_integration.get_access_token(int(installation_id)).token
    return Github(github_token)
