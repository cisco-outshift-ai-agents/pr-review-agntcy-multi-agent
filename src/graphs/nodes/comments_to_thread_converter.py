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

from graphs.states import ReviewChatAssistantState
from utils.logging_config import logger as log


class CommentsToThreadConverter:
    def __init__(self, name: str = "comments_to_thread_converter"):
        self.name = name

    def __call__(self, state: ReviewChatAssistantState) -> dict:
        log.info(f"{self.name} called")

        comment = state["comment"]
        review_comments = state["review_comments"]
        review_comment_thread = [
            c for c in review_comments if comment["in_reply_to_id"] == c.id or c.id == comment["id"] or c.in_reply_to_id == comment["in_reply_to_id"]
        ]
        review_comment_thread.sort(key=lambda x: x.created_at)
        return {"review_comment_thread": review_comment_thread}
