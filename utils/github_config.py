import os

import github.Auth
from github import Github, GithubIntegration


def init_github(installation_id: str) -> Github:
  with open(os.getenv("GITHUB_APP_PRIVATE_KEY"), 'r') as key_file:
    private_key = key_file.read()

  app_id = os.getenv('GITHUB_APP_ID')
  git_integration = GithubIntegration(auth=github.Auth.AppAuth(app_id, private_key))
  github_token = git_integration.get_access_token(int(installation_id)).token
  return Github(github_token)