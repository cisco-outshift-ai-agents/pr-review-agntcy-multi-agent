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

from graphs.nodes.contexts import DefaultContext
from graphs.states import ReviewChatAssistantState
from utils.logging_config import logger as log


class CommentReplier:
    def __init__(self, context: DefaultContext, name="comment_replier"):
        self.context = context
        self.name = name

    def __call__(self, state: ReviewChatAssistantState) -> dict:
        log.info(f"{self.name} called")

        if not self.context.github:
            raise ValueError("GitHub operations not found")

        try:
            # Ensure the content is a string
            content = state["messages"][-1].content
            if isinstance(content, list):
                content = " ".join(str(item) for item in content)
            self._reply_on_pr_comment(state["comment"]["id"], content)
        except Exception as e:
            raise ValueError(f"Error sending reply to comment on GitHub: {e}") from e

        return {}

    def _reply_on_pr_comment(self, comment_id: int, comment: str) -> None:
        if not self.context.github:
            raise ValueError("GitHub operations not found")

        if comment_id is None or comment_id == 0 or comment is None or comment == "":
            raise ValueError("Invalid input parameters")

        self.context.github.pr.create_review_comment_reply(
            comment_id,
            body=comment,
        )
