# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import os
from http import HTTPStatus
from typing import Any

from fastapi.responses import JSONResponse
from openai import APIConnectionError, BadRequestError
from config import ConfigManager
from graphs import CodeReviewerWorkflow, ReviewChatWorkflow
from utils.constants import ALFRED_CONFIG_BRANCH
from utils.github_operations import CheckRunConclusion, GitHubOperations
from utils.logging_config import logger as log


async def handle_github_event(payload: dict[str, Any], github_event: str):
    try:
        log.debug(f"Header: {github_event}")
        if github_event == "pull_request" and payload["pull_request"]["head"]["ref"] != ALFRED_CONFIG_BRANCH:
            action = payload.get("action")
            if action in ["opened", "synchronize"]:
                pr_number = payload["pull_request"]["number"]
                repo_name = payload["repository"]["full_name"]
                installation_id = payload["installation"]["id"]
                # handle_pull_request(pr_number, repo_name, installation_id)
        elif github_event == "issue_comment" and payload.get("action") == "created":
            # Get the comment body and convert to lowercase for case-insensitive comparison
            comment_body = payload["comment"]["body"].lower()
            # Check if both "@alfred" and "review" appear in the comment in that order
            if "alfred" in comment_body and "review" in comment_body[comment_body.index("alfred"):]:
                pr_number = payload["issue"]["number"]
                repo_name = payload["repository"]["full_name"]
                installation_id = payload["installation"]["id"]
                await handle_pull_request(pr_number, repo_name, installation_id)
        # TODO: handle installation correctly
        # elif github_event == "installation" and payload.get("action") == "created":
        #     handle_installation(payload, "repositories")
        # elif github_event == "installation_repositories" and payload.get("action") == "added":
        #     handle_installation(payload, "repositories_added")
        elif github_event == "pull_request_review_comment" and payload.get("action") in [
            "created"] and __is_commented_by_human(payload):
            # TODO: handle edited comments
            handle_pull_request_comment(payload)
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        if type(e) == APIConnectionError:
            log.error("Error handling pull request because of open AI timeout")
            return JSONResponse(content={"status": "Open API Connection Error"}, status_code=HTTPStatus.OK)
        elif type(e) == BadRequestError:
            log.error("Error handling pull request because of context window exceed")
            return JSONResponse(content={"status": "Context Window Exceed Error"}, status_code=HTTPStatus.OK)
        log.error(f"Error processing webhook: {e}")
        log.error(f"Error processing webhook:  repo_name: {payload['repository']['full_name']}, pr_number: {payload['issue']['number']}, installation_id: {payload['installation']['id']}")
        return JSONResponse(content={"status": "server error"}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)


async def handle_pull_request(pr_number: int, repo_name: str, installation_id: int):
    github_ops = GitHubOperations(str(installation_id), repo_name, pr_number)
    check_run = github_ops.create_pull_request_check_run()

    try:
        log.debug(f"repo: {repo_name}, pr number:{pr_number}, installation id:{installation_id}")
        agency_provider = os.environ.get("agency_provider")
        if agency_provider is None or agency_provider == "graph":
            graph = CodeReviewerWorkflow(str(installation_id), repo_name, pr_number)
            result = await graph.run()
            print(result)
    except Exception as e:
        log.error(f"Error handling pull request: {str(e)}")
        log.error(
            f"Error handling pull request: repo_name: {repo_name}, pr_number:{pr_number}, installation_id:{installation_id}")
        github_ops.complete_pull_request_check_run(check_run, CheckRunConclusion.failure, str(e))

        raise

    github_ops.complete_pull_request_check_run(check_run, CheckRunConclusion.success, "")


def handle_installation(payload, repositories_key):
    try:
        installation_id = payload["installation"]["id"]
        # TODO app can be installed into multiple repositories in the same event
        # TODO handling these batch events should be implemented
        # TODO turn back handling installation event
        repo_name = payload["repository"]["full_name"]
        github_ops = GitHubOperations(str(installation_id), repo_name, None)
        config_manager = ConfigManager(github_ops)

        for repo in payload[repositories_key]:
            repo_name = repo["full_name"]
            is_created = config_manager.create_config(repo_name)
            if not is_created:
                log.error(f"Failed to create config for repo: {repo_name}")
    except Exception as e:
        log.error(f"Error handling installation: {e}")
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
    log.info(
        f"Handling pull request comment: repo_name={repo_name}, pr_number={pr_number}, installation_id={installation_id}")

    graph = ReviewChatWorkflow(installation_id, pr_number, repo_name, comment)
    print(graph.run())
    #     todo - better exception handling for ReviewChatWorkflow


def __is_commented_by_human(payload: dict[str, Any]) -> bool:
    return payload["comment"]["user"]["type"] == "User"
