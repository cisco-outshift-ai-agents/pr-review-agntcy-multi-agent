import base64
import os
import re
from typing import Union, Dict

import requests
from dotenv import load_dotenv
from github import Github, GithubIntegration
from github import GithubException
from github.Repository import Repository

from utils.github_config import init_github
from utils.logging_config import logger as log

load_dotenv()

class GitHubOperations:
  def __init__(self, installation_id: str):
    self.github = init_github(installation_id)


  def __init_token(self, installation_id: str) -> Github:
    with open(os.getenv("GITHUB_APP_PRIVATE_KEY"), 'r') as key_file:
      PRIVATE_KEY = key_file.read()
    app_id = os.getenv('GITHUB_APP_ID')
    git_integration = GithubIntegration(app_id, PRIVATE_KEY)
    github_token = git_integration.get_access_token(installation_id).token
    return Github(github_token)

  def __create_branch(self, repo: Repository, branch_name: str, base_branch: str = 'master') -> bool:
    try:
      base_ref = repo.get_git_ref(f"heads/{base_branch}")
      repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_ref.object.sha)
      log.info(f'Branch {branch_name} created successfully.')
      return True
    except GithubException as e:
      if 'Reference already exists' in e.data.get('message'):
        log.info(f'Branch already exist')
        return True
      log.error(f'Failed to create branch: {e.data}')
      return False

  def __file_exists(self, repo: Repository,  branch_name: str, file_path: str) -> (bool, str):
    try:
      contents = repo.get_contents(file_path, ref=branch_name)
      return True, contents
    except GithubException as e:
      if e.status == 404:
        return False, ""
      else:
        raise e

  def __create_file(self, repo: Repository, branch_name: str, file_path: str, file_content: str, commit_message: str) -> bool:
    try:
      file_exists, file_contents = self.__file_exists(repo, branch_name, file_path)
      if file_exists:
        log.info(f'File {file_path} already exists in branch {branch_name}.')
        repo.update_file(path=file_path, message=commit_message, content=file_content, branch=branch_name, sha=file_contents.sha)
        return True

      repo.create_file(path=file_path, message=commit_message, content=file_content, branch=branch_name)
      log.info(f'File {file_path} created successfully.')
      return True
    except GithubException as e:
      log.info(f'Failed to create file: {e.data}')
      return False

  def __create_pull_request(self, repo: Repository, branch_name: str, pr_title: str, pr_body: str, base_branch: str = 'master') -> bool:
    try:
      pulls = repo.get_pulls(state='open')
      pr_exists = any(pr.head.ref == branch_name for pr in pulls)
      if pr_exists:
        log.info('Pull request already exists.')
        return True
      repo.create_pull(title=pr_title, body=pr_body, head=branch_name, base=base_branch)
      log.info('Pull request created successfully.')
      return True
    except GithubException as e:
      log.error(f'Failed to create pull request: {e.data}')
      return False


  def add_pr_coach_config_file_pr(self,
      repo_name: str,
      branch_name: str = 'pr_coach_config',
      file_path: str = 'PRCoach_CONFIG.md',
      commit_message: str = 'Add PR coach config file',
      pr_title: str = 'PR coach config file',
      pr_body: str = 'This pull request adds PR coach default config file.'
  ) -> None:
    with open('./PRCoach_CONFIG.md', 'r') as file:
      file_content = file.read()
      repo = self.github.get_repo(repo_name)
      base_branch = repo.default_branch
      if self.__create_branch(repo, branch_name, base_branch):
        if self.__create_file(repo, branch_name, file_path, file_content, commit_message):
          self.__create_pull_request(repo, branch_name, pr_title, pr_body, base_branch)


  def retrieve_md_content_from_pr(self, pr_number, repo_name) -> Dict[str, str]:
    success, result = self.__parse_md_content_from_pr(repo_name, pr_number, self.github)
    if not success:
      log.error(f"Missing or invalid PR coach configuration: {result}")
      return None
    return result


  def __parse_md_content_from_pr(self, repo_name: str, pr_number: int, github: Github) -> Union[bool, Dict[str, str]]:
    repo = github.get_repo(repo_name)
    pull_request = repo.get_pull(pr_number)
    md_content = ""
    # try to get the file from the pr
    try:
      branch_name = pull_request.head.ref
      file = repo.get_contents("PRCoach_CONFIG.md", ref=branch_name)
      md_content = base64.b64decode(file.content).decode('utf-8')
    except Exception as e:
      log.info("no config file found in pr")
    if not md_content:
      # if not found try to fetch from the main branch
      default_branch = repo.default_branch
      branch_ref = repo.get_git_ref(f'heads/{default_branch}')

      # Get the SHA of the latest commit on the default branch
      commit_sha = branch_ref.object.sha

      # Get the tree of the latest commit on the default branch
      tree = repo.get_git_tree(commit_sha, recursive=False).tree
      md_content = ""
      files = [file for file in tree if file.path == "PRCoach_CONFIG.md"]

      if len(files) == 1:
        file = requests.get(files[0].raw_data.get("url"))
        md_content = base64.b64decode(file.json()['content']).decode('utf-8')

    if not md_content:
      return False, "No MD file found in the pull request."

    if not self.__validate_md_structure(md_content):
      return False, "The MD file structure is invalid."

    sections = re.split(r'^##\s+', md_content, flags=re.MULTILINE)
    sections = sections[1:] if len(sections) > 1 else sections
    structured_content = {}

    for section in sections:
      lines = section.strip().split('\n')
      main_title = lines[0].strip()
      content = '\n'.join(lines[1:]).strip()

      # Split content by subtitles (-)
      subsections = re.split(r'^-\s+\*\*(.*?):?\*\*', content, flags=re.MULTILINE)

      if len(subsections) > 1:
        structured_content[main_title] = {}
        for i in range(1, len(subsections), 2):
          subtitle = subsections[i].strip()
          subcontent = subsections[i+1].strip() if i+1 < len(subsections) else ""
          if i == 1:
            structured_content[main_title]= f"{subtitle}: {subcontent}"
          else:
            structured_content[main_title]= structured_content[main_title] + f"\n{subtitle}: {subcontent}"

      else:
        structured_content[main_title] = content

    return True, structured_content

  def __validate_md_structure(self, content: str) -> bool:
    expected_structure = [
      r"^# PRCoach Configuration File\s*$",
      r"^## Overview\s*$",
      r"^## PR Title and Description\s*$",
      r"^## PR Summary of Changes\s*$",
      r"^## Code Review\s*$",
      r"^- \*\*Terraform Syntax and Style Checks:\*\*\s*$",
      r"^## Documentation and Explanation\s*$",
      r"^- \*\*Auto-Documentation:\*\*\s*$",
      r"^- \*\*Code Comments:\*\*\s*$",
      r"^## File Structure Review\s*$",
      r"^- \*\*Consistency Checks:\*\*\s*$",
      r"^- \*\*Best Practices Comparison:\*\*\s*$",
      r"^## Cloud Environment \(as discovered by the system from your repo\)\s*$",
      r"^- \*\*Primary Cloud Provider:\*\*",
      r"^- \*\*Secondary Cloud Providers:\*\*",
      r"^## Security & Compliance Policies\s*$",
      r"^- \*\*Security Requirements:\*\*\s*$",
      r"^- \*\*Compliance Requirements:\*\*\s*$",
      r"^## Change Impact Analysis\s*$",
      r"^- \*\*Dependency Analysis:\*\*\s*$",
      r"^- \*\*Risk Assessment:\*\*\s*$",
      r"^## Continuous review\s*$",
      r"^- \*\*Linting Review:\*\*\s*$",
      r"^- \*\*Scanning Review:\*\*\s*$",
      r"^## Learning and Improvement\s*$",
      r"^- \*\*Knowledge Base:\*\*\s*$",
      r"^- \*\*KPI Tracking:\*\*\s*$",
      r"^## Expert Reviewers\s*$",
      r"^- \*\*Designated Expert Reviewers:\*\*\s*$",
      r"^## Continuous Improvement\s*$",
      r"^- \*\*Feedback Loop:\*\*\s*$"
    ]

    lines = content.split('\n')
    index = 0

    for pattern in expected_structure:
      while index < len(lines) and not re.match(pattern, lines[index].strip()):
        index += 1

      if index >= len(lines):
        return False

      index += 1

    return True

if __name__ == '__main__':
  installation_id:str = '55482007'
  repo_name = 'bensagi/terraform-aws-eks'
  git_ops=GitHubOperations(installation_id)
  git_ops.add_pr_coach_config_file_pr(repo_name)


  print(git_ops.retrieve_md_content_from_pr(10, repo_name))
