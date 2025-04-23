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

from typing import Sequence

from github.PaginatedList import PaginatedList
from github.PullRequestComment import PullRequestComment

from graphs.states import ReviewChatAssistantState
from utils.logging_config import logger as log
from .contexts import DefaultContext


class CommentsFetcher:
    def __init__(self, context: DefaultContext, name: str = "comments_fetcher"):
        self.context = context
        self.name = name

    def __call__(self, state: ReviewChatAssistantState) -> dict:
        log.info(f"{self.name} called")

        if not self.context.github:
            raise ValueError("GitHub operations not found")

        try:
            comments_paginated: PaginatedList[PullRequestComment] = self.context.github.pr.get_comments()
            review_comments: Sequence[PullRequestComment] = list(comments_paginated)
        except Exception as e:
            raise ValueError(f"Error getting comments from GitHub: {e}") from e

        return {"review_comments": review_comments}
