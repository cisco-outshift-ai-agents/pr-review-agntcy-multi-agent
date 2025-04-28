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

from typing import Callable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import SystemMessagePromptTemplate, ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from pydantic import BaseModel
from pydantic import Field

from utils.wrap_prompt import wrap_prompt


class ReviewChatResponse(BaseModel):
    is_addressed_to_alfred: bool = Field(description="Indicates if the question or instruction is addressed to the pull request reviewer.")
    is_related_to_code: bool = Field(description="Indicates if the question or instruction is related to the code.")
    message: str = Field(description="Your answer must be placed here.")


def create_review_chat_assistant_chain(model: BaseChatModel) -> Callable[[Sequence[BaseMessage]], RunnableSerializable]:
    def review_chat_assistant_chain(message_history: Sequence[BaseMessage]) -> RunnableSerializable[dict, dict | ReviewChatResponse]:
        structured_output_model = model.with_structured_output(ReviewChatResponse)

        system_prompt = wrap_prompt("""\
            You are a Terraform expert and the reviewer of a pull request.

            """)
        
        user_prompt = wrap_prompt("""\
            Other developers have some questions or clarifications on your review. You will be given the code modifications you reviewed
            and the conversation thread. Your task is to answer their questions and provide a detailed explanation, 
            focusing on the specific modification you reviewed.
                                  
            The code modifications you reviewed are as follows:
            ```
            {code}
            ```
            The conversation is about the modification in line {line_number}.

            Here's the question you should respond to : {question},

            Below is the conversation thread, for your reference: 
             """)

        messages = [
             (
                "system",
                system_prompt,
            ),
            ("user", user_prompt),
        ]
        messages.extend(message_history)

        template = ChatPromptTemplate.from_messages(messages)

        return template | structured_output_model

    return review_chat_assistant_chain


