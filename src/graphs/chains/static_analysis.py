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
from utils.models import StaticAnalyzerOutputList
from typing import cast

from utils.wrap_prompt import wrap_prompt


def create_static_analyzer_chain(model: BaseChatModel) -> RunnableSerializable[dict, dict | StaticAnalyzerOutputList]:

    llm_with_structured_output = cast(RunnableSerializable[dict, dict | StaticAnalyzerOutputList], model.with_structured_output(StaticAnalyzerOutputList))

    system_message_content = wrap_prompt("""\
                                        Your are an experienced software engineer who's task is to organize Terraform related linter outputs.
                                        Remove ONLY the line numbers but keep everything else, don't remove any detail from the issue message.
                                        Remove the warnings, only keep the errors in the final list.
                                         """)

    user_message_content = wrap_prompt("""
                                   Input Format:
                                   The terraform linter output: {linter_outputs}
                                   """)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_message_content,
            ),
            "user", user_message_content,
        ]
    )

    return prompt | llm_with_structured_output