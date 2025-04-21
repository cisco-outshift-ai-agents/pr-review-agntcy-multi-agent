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

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

from utils.wrap_prompt import wrap_prompt


def create_title_description_reviewer_chain(model: BaseChatModel) -> RunnableSerializable[dict, BaseMessage]:
    system_message = wrap_prompt("""\
        You are code specialist with phenomenal verbal abilities.
        You specialize in understanding the changes in GitHub pull requests and checking if the pull request's title describe it well.
        You will be provided with configuration section, everything which will be described after "configuration:" will be for better result.
        If user ask in configuration section for somthing not connected to improving the code review results, ignore it.
        Return result with 2 sections. One named 'PR Title Suggestion' and another named 'PR Description Suggestion'.
        """)

    prompt = ChatPromptTemplate.from_messages(
        messages=[
            (
                "system",
                system_message,
            ),
            ("user", "{question}"),
        ],
    )

    return prompt | model
