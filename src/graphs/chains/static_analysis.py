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


def create_static_analyzer_chain(model: BaseChatModel) -> RunnableSerializable[dict, BaseMessage]:
    system_message = wrap_prompt("""\
                Your are an experienced software egineer who's task is to organize Terraform related linter outputs.
                You will get different linter outputs from the user (tflint, tfsec, terraform validate etc.).
                
                Organize the issues into a list, but keep every detail!
                Remove ONLY the line numbers but keep everything else, don't remove any detail from the issue message.
                DO NOT remove any information from the issues, keep every detail! You are only allowed to delete the line numbers, nothing else!
                Each item in the list should have the following format: {{file name}}: {{full issue description}}
                Remove the warnings, only keep the errors in the final list.
                                
                Only return the list of issues in your response, nothing else.
                """)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_message,
            ),
            ("user", "{linter_outputs}"),
        ]
    )

    return prompt | model
