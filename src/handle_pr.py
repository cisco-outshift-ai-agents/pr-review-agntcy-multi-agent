import os
from http import HTTPStatus
from typing import Any

from fastapi.responses import JSONResponse
from langchain_openai import AzureChatOpenAI

from handlers.pr_comment import handle_pull_request_comment
from pr_graph.graph import WorkFlow
from utils.config_file_pr import GitHubOperations
from utils.logging_config import logger as log


def handle_github_event(payload: dict[str, Any], github_event: str, local_run: bool = True):
    try:
        log.debug(f"Header: {github_event}")
        if github_event == "pull_request" and payload["pull_request"]["head"]["ref"] != "pr_coach_config":
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
            github_ops = GitHubOperations(payload["installation"]["id"])
            model = AzureChatOpenAI(
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
                openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
            )
            handle_pull_request_comment(
                model=model,
                github_operations=github_ops,
                payload=payload,
                local_run=local_run
            )
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
            git_ops.add_pr_coach_config_file_pr(repo_name)
    except Exception as e:
        log.error(f"Error handling installation: {str(e)}")
        raise


def __is_commented_by_human(payload: dict[str, Any]) -> bool:
    return payload["comment"]["user"]["type"] == "User"


def __is_replied_to_bot(payload: dict[str, Any]) -> bool:
    return payload["comment"]["in_reply_to_id"] is not None
