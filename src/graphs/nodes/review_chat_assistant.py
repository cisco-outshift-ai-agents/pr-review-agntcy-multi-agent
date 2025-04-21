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

import re
from typing import Sequence

from langchain_core.messages import AIMessage, BaseMessage

from graphs.chains.review_chat_assistant import ReviewChatResponse
from graphs.nodes.contexts import DefaultContext
from graphs.states import ReviewChatAssistantState
from utils.logging_config import logger as log

NOT_RELATED_MESSAGE = "I apologize but your question or instruction is not related to the code so I cannot provide a response."


class ReviewChatAssistant:
    def __init__(self, context: DefaultContext, name: str = "review_chat_assistant"):
        self.context = context
        self.name = name

    def __call__(self, state: ReviewChatAssistantState) -> dict:
        log.info(f"{self.name} called")

        if not self.context.chain:
            raise ValueError("Chain not found")

        message_history = state["messages"]
        if message_history is None or len(message_history) < 2:
            raise ValueError("At least the original review and a comment should be presented in the message history")
        try:
            response: ReviewChatResponse = self.context.chain(message_history).invoke(
                {"code": state["reviewed_patch"], "line_number": state["comment"]["line"], "question": message_history.pop().content}
            )
        except Exception as e:
            raise ValueError(f"Error invoking LLM model: {e}") from e

        if (not response.is_addressed_to_alfred and not self.get_num_of_participants(state["messages"][:-1]) == 2) or self.is_comment_tagged(
            state["messages"][-1]
        ):
            return {"is_skipped": True}

        if not response.is_related_to_code:
            return {"is_skipped": False, "messages": AIMessage(content=NOT_RELATED_MESSAGE, response_meta={"author": "alfred-bot"})}

        return {"is_skipped": False, "messages": AIMessage(content=response.message, response_meta={"author": "alfred-bot"})}

    @staticmethod
    def get_num_of_participants(thread: Sequence[BaseMessage]) -> int:
        participants = set()
        for comment in thread:
            if comment.response_metadata.get("author", None) is not None:
                participants.add(comment.response_metadata["author"])
        return len(participants)

    @staticmethod
    def is_comment_tagged(comment: BaseMessage) -> bool:
        return re.match(r"@[a-zA-Z0-9]+", comment.content) is not None
