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
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

from utils.wrap_prompt import wrap_prompt
from utils.models import ReviewComments
from typing import cast


def create_comment_filter_chain(model: BaseChatModel) -> RunnableSerializable[dict, dict | ReviewComments]:
    llm_with_structured_output = cast(RunnableSerializable[dict, dict | ReviewComments], model.with_structured_output(ReviewComments))
    system_message = wrap_prompt("""\
        You are a review agent tasked with filtering a list of PR review comments.
        Your peer has created several comments on a GitHub pull request but it could be that some of them are not useful. 
        Your job is to filter these comments based on the insturctions below, follow them carefully.
        
        Input Format:
        comments: The set of comments that you need to filter.
        Here's an example how the input array will look like:
        {input_json_format}
        
        Rules for Filtering:
        A comment considered not useful if ANY of the following applies:
        - It's a simple statement without a clear issue.
        - It's just some positive feedpack without stating a clear issue.
        - It doesn't mention an actionable issue.
        - The message just states what the user changed in the code without mentioning a clear issue.

        Response format:
        Return ONLY the remaining comments.
        DO NOT change anything in the returned comments.
        Output MUST be in JSON format, keep the format of the original comments:
        DO NOT USE markdown in the response.
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

    return prompt | llm_with_structured_output