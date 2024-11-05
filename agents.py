from crewai import Agent

from tools.CommentOnGitHubPullRequestInfoTool import CommentOnGitHubPullRequestInfoTool
from tools.FetchGitHubPullRequestInfoTool import FetchGitHubPullRequestInfoTool
from azure_client import AzureClient
from langchain.tools import tool
from typing import List, Tuple


@tool("find_diff_line_numbers")
def find_diff_line_numbers(diff_text:str) -> List[str]:
  """
  Find the line numbers of the diff text.
  Input: diff_text: str
  """
  lines = diff_text.split('\n')
  changes = []
  current_line_number = None
  added_line_number = None
  removed_line_number = None
  last_change_type = None

  for line in lines:
    if line.startswith('@@'):
      # Extract the line numbers from the diff header
      parts = line.split(' ')
      removed_line_number = int(parts[1].split(',')[0][1:])
      added_line_number = int(parts[2].split(',')[0][1:])
      last_change_type = None
    elif line.startswith('+') and not line.startswith('+++'):
      if last_change_type != 'added':
        changes.append(f"Line {added_line_number}: {line}")
      added_line_number += 1
      last_change_type = 'added'
    elif line.startswith('-') and not line.startswith('---'):
      if last_change_type != 'removed':
        changes.append(f"Line {removed_line_number}: {line}")
      removed_line_number += 1
      last_change_type = 'removed'
    else:
      if removed_line_number is not None:
        removed_line_number += 1
      if added_line_number is not None:
        added_line_number += 1
      last_change_type = None
  return changes

class PRCoachAgents:
  def __init__(self):
    self.llm = AzureClient().get_azure_client()

  def github_agent(self):
    return Agent(
        role="GitHub Agent",
        goal="Fetch content from GitHub pull request and send it to code review",
        backstory=(
          """
          A dedicated professional specializing in GitHub API operations.
          You have access to the GitHub API and can retrieve pull requests information.
          """
        ),
        verbose=True,
        allow_delegation=True,
        tools=[FetchGitHubPullRequestInfoTool()],
        llm=self.llm,
        max_rpm=5,
    )

  def github_commenter_agent(self):
    return Agent(
        role="GitHub Commenter Agent",
        goal="Comment in GitHub",
        backstory=(
          """
          A dedicated professional specializing in GitHub API operations.
          You have the ability to add comments to GitHub pull requests.
          """
        ),
        verbose=True,
        allow_delegation=True,
        tools=[CommentOnGitHubPullRequestInfoTool()],
        llm=self.llm,
        max_rpm=5,
    )

  def code_reviewer(self):
    return Agent(
        role="Terraform Code Reviewer",
        goal="Perform code review on changes in Terraform file.",
        backstory=(
          """
          A senior developer adapt in code reviews.
          You give comments only on changes that can be improved.
          You have the capability to find the lines of all changes in the diff text.
          """
        ),
        verbose=True,
        allow_delegation=True,
        tools=[find_diff_line_numbers],
        llm=self.llm,
        max_rpm=5,
    )

  def security_reviewer(self):
    return Agent(
        role="Terraform Security Reviewer",
        goal="Perform security analysis on changes in Terraform file.",
        backstory=(
          """
          A senior security specialist adapt in finding security threats.
          You give comments only on changes that can be improved.
          """
        ),
        verbose=True,
        allow_delegation=True,
        tools=[],
        llm=self.llm,
        max_rpm=5,
    )

  def title_reviewer(self):
    return Agent(
        role="Pull Request Title Review Agent",
        goal="Check if the current title describe well the changes in pull request and suggest new title if needed.",
        backstory=(
          """
          You are code specialist with phenomenal verbal abilities. 
          You specialize in understanding the changes in GitHub pull requests and checking if the pull request's title describe it well.
          """
        ),
        verbose=True,
        allow_delegation=False,
        llm=self.llm,
        max_rpm=5,
    )

  def description_reviewer(self):
    return Agent(
        role="Pull Request Description Review Agent",
        goal="Check if the current description describe well the changes in pull request and suggest new description if needed.",
        backstory=(
          """
          You are code specialist with phenomenal verbal abilities. 
          You specialize in understanding the changes in GitHub pull requests and checking if the pull request's description describe it well.
          """
        ),
        verbose=True,
        allow_delegation=False,
        llm=self.llm,
        max_rpm=5,
    )