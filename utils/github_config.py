import os

from github import Github, GithubIntegration


def init_github(installation_id: str) -> Github:
  with open(os.getenv("GITHUB_APP_PRIVATE_KEY"), 'r') as key_file:
    PRIVATE_KEY = key_file.read()
  app_id = os.getenv('GITHUB_APP_ID')
  git_integration = GithubIntegration(app_id, PRIVATE_KEY)
  github_token = git_integration.get_access_token(installation_id).token
  return Github(github_token)