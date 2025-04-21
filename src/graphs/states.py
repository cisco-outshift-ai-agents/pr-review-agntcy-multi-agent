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

from typing import Annotated, Sequence, Dict, Any, Optional, List
from operator import add

from github.PullRequestComment import PullRequestComment
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict
from utils.models import ContextFile, GitHubIssueCommentUpdate, IssueComment, ReviewComment
from github.IssueComment import IssueComment as GHIssueComment


class FileChange(TypedDict):
    changed_code: str
    filename: str
    start_line: int
    status: str


class GithubRequest(TypedDict):
    repo_url: str
    branch: str
    github_token: str

class GitHubPRState(TypedDict):
    github_details: GithubRequest
    changes: list[FileChange]
    context_files: list[ContextFile]
    description: str
    issue_comments: list[GHIssueComment]
    issue_comments_to_update: list[GitHubIssueCommentUpdate]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # modified_files: list[ContextFile]
    new_issue_comments: Annotated[List[IssueComment], add]
    new_review_comments: list[ReviewComment]
    review_comments: list[ReviewComment]
    sender: str
    static_analyzer_output: str
    title: str
    cross_reference_problems: Optional[IssueComment]


def create_default_github_pr_state() -> GitHubPRState:
    return GitHubPRState(
        changes=[],  # Default to an empty list of changes
        context_files=[],  # Default to an empty list of context files
        description="",  # Default to an empty string
        issue_comments=[],  # Default to an empty list of issue comments
        issue_comments_to_update=[],  # Default to an empty list of issue comments to be updated
        messages=[],  # Default to an empty list of messages
        # modified_files=[],  # Default to an empty list of modified files
        new_issue_comments=[],  # Default to an empty list of new issue commentsissue_comments_to_update
        new_review_comments=[],  # Default to an empty list of new review comments
        review_comments=[],  # Default to an empty list of review comments
        sender="",  # Default to an empty string
        static_analyzer_output="",
        title="",  # Default to an empty string
        cross_reference_problems=None,
    )


class ReviewChatAssistantState(TypedDict):
    comment: Dict[str, Any]
    is_skipped: Optional[bool]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    review_comment_thread: Sequence[PullRequestComment]
    review_comments: Sequence[PullRequestComment]
    reviewed_patch: Optional[str]
