import os
from http import HTTPStatus
from typing import Any

from fastapi.responses import JSONResponse

from agents.pr_review_chat import PRReviewChatAgent
from pr_graph.graph import WorkFlow
from utils.config_file_pr import GitHubOperations
from utils.constants import ALFRED_CONFIG_BRANCH
from utils.logging_config import logger as log


def handle_github_event(payload: dict[str, Any], github_event: str, local_run: bool = True):
    try:
        log.debug(f"Header: {github_event}")
        if github_event == "pull_request" and payload["pull_request"]["head"]["ref"] != ALFRED_CONFIG_BRANCH:
            action = payload.get("action")
            if action in ["opened", "synchronize"]:
                handle_pull_request(payload, local_run)
        elif github_event == "installation" and payload.get("action") == "created":
            handle_installation(payload, local_run, "repositories")
        elif github_event == "installation_repositories" and payload.get("action") == "added":
            handle_installation(payload, local_run, "repositories_added")
        elif github_event == "pull_request_review_comment" and \
                payload.get("action") in ["created", "edited"] and \
                __is_commented_by_human(payload):
            handle_pull_request_comment(payload)
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        log.error(f"Error processing webhook: {str(e)}")
        return JSONResponse(content={"status": "server error"}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)


def handle_pull_request(payload, local_run):
    try:
        pr_number = payload["pull_request"]["number"]
        repo_name = payload["repository"]["full_name"]
        installation_id = payload["installation"]["id"]
        log.debug(f"repo: {repo_name}, pr number:{pr_number}, installation id:{installation_id}")
        agency_provider = os.environ.get("agency_provider")
        if agency_provider is None or agency_provider == "graph":
            graph = WorkFlow(installation_id, repo_name, pr_number)
            print(graph.run())
    except Exception as e:
        log.error("Error handling pull request", e)
        raise


def handle_installation(payload, local_run, repositories_key):
    try:
        installation_id = payload["installation"]["id"]
        git_ops = GitHubOperations(installation_id)
        for repo in payload[repositories_key]:
            repo_name = repo["full_name"]
            git_ops.add_alfred_config_file_pr(repo_name)
    except Exception as e:
        log.error(f"Error handling installation: {str(e)}")
        raise


def handle_pull_request_comment(payload):
    comment = payload.get("comment")
    if comment is None:
        raise ValueError("Comment is missing in the payload")
    repo_name = payload.get("repository", {}).get("full_name")
    if repo_name is None:
        raise ValueError("Repository name is missing in the payload")
    pr_number = payload.get("pull_request", {}).get("number")
    if pr_number is None:
        raise ValueError("Pull request number is missing in the payload")
    installation_id = payload.get("installation", {}).get("id")
    if installation_id is None:
        raise ValueError("Installation ID is missing in the payload")

    github_operations = GitHubOperations(installation_id)
    agent = PRReviewChatAgent(github_operations)
    agent.invoke(repo_name, pr_number, comment)


def __is_commented_by_human(payload: dict[str, Any]) -> bool:
    return payload["comment"]["user"]["type"] == "User"

