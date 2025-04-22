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

from typing import List, Union

from langchain_core.messages import HumanMessage, AIMessage

from graphs.states import ReviewChatAssistantState
from utils.logging_config import logger as log

BOT_USER_TYPE = "Bot"
HUMAN_USER_TYPE = "User"

# Define the type for messages
MessageType = Union[HumanMessage, AIMessage]


class CommentsToMessagesConverter:
    def __init__(self, name: str = "comments_to_messages_converter"):
        self.name = name

    def __call__(self, state: ReviewChatAssistantState) -> dict:
        log.info(f"{self.name} called")

        messages: List[MessageType] = []  # Use the union type for the list
        for comment in state["review_comment_thread"]:
            if comment.user.type == HUMAN_USER_TYPE:
                messages.append(HumanMessage(content=comment.body, response_metadata={"author": comment.user.id}))
            elif comment.user.type == BOT_USER_TYPE:
                messages.append(AIMessage(content=comment.body, response_metadata={"author": "alfred-bot"}))
            else:
                pass
        return {"messages": messages}
