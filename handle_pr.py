from http import HTTPStatus
import os
from typing import Any
from fastapi.responses import JSONResponse
import init
from crew import PRCoachCrew
from pr_graph.graph import WorkFlow
from utils.config_file_pr import GitHubOperations
from utils.logging_config import logger as log


def handle_github_event(payload: dict[str, Any], github_event: str, local_run: bool = True):
    try:
        log.info(f"Header: {github_event}")
        log.info(f"Payload: {payload}")
        if github_event == "pull_request" and payload["pull_request"]["head"]["ref"] != "pr_coach_config":
            action = payload.get("action")
            if action in ["opened", "synchronize"]:
                handle_pull_request(payload, local_run)
        elif github_event == "installation" and payload.get("action") == "created":
            handle_installation(payload, local_run, "repositories")
        elif github_event == "installation_repositories" and payload.get("action") == "added":
            handle_installation(payload, local_run, "repositories_added")
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        log.error(f"Error processing webhook: {str(e)}")
        return JSONResponse(content={"status": "server error"}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)


def handle_pull_request(payload, local_run):
    try:
        init.initialize_environment(local_run)
        pr_number = payload["pull_request"]["number"]
        repo_name = payload["repository"]["full_name"]
        installation_id = payload["installation"]["id"]
        log.debug(f"repo: {repo_name}, pr number:{pr_number}, installation id:{installation_id}")
        agency_provider = os.environ.get("agency_provider")
        if agency_provider is None or agency_provider == "graph":
            graph = WorkFlow(installation_id, repo_name, pr_number)
            print(graph.run())
        else:
            crew = PRCoachCrew()
            run = crew.run(installation_id, pr_number, repo_name)
            print(run)
    except Exception as e:
        log.error("Error handling pull request", e)
        raise


def handle_installation(payload, local_run, repositories_key):
    try:
        init.initialize_environment(local_run)
        installation_id = payload["installation"]["id"]
        git_ops = GitHubOperations(installation_id)
        for repo in payload[repositories_key]:
            repo_name = repo["full_name"]
            git_ops.add_pr_coach_config_file_pr(repo_name)
    except Exception as e:
        log.error(f"Error handling installation: {str(e)}")
        raise
