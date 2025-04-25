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
from typing import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import RunnableSerializable
from graphs.nodes.title_description_reviewer import TitleDescriptionOutput


def create_title_description_reviewer_chain(model: BaseChatModel) -> Callable[
    [dict], RunnableSerializable[dict, TitleDescriptionOutput]]:
    def title_descrption_reviewer_chain(title_description_input: dict) -> RunnableSerializable[
        dict, dict | TitleDescriptionOutput]:
        llm_model_with_structured_output = model.with_structured_output(TitleDescriptionOutput)
        system_message = SystemMessage("""
        You are a code review agent with strong communication skills.
        Your task is to analyze GitHub pull requests and determine whether the pull request title accurately summarizes the code changes."
        """)
        user_message = HumanMessage(f"""
            You will be provided with the following Inputs:
            - 'diff`: {title_description_input['diff']['description']}
            - `title`: {title_description_input["title"]['description']}
            - `description`: {title_description_input["description"]['description']}
            - `configuration`: {title_description_input["configuration"]['description']}
            Instructions:
            Only use the configuration if it directly helps improve the title or description.
            Ignore unrelated or irrelevant configuration details.
            Output Format: Return two sections:
            PR Title Suggestion : {TitleDescriptionOutput.__fields__.get("PR_title_suggestion").description}
            PR Description Suggestion: {TitleDescriptionOutput.__fields__.get("PR_description_suggestion").description}
            Inputs:
            Git Diff: {title_description_input["diff"]["value"]}
            Title: {title_description_input["title"]["value"]}
            Description: {title_description_input["description"]["value"]}
            Configuration: {title_description_input["configuration"]["value"]}
            """)
        messages = [system_message, user_message]

        prompt = ChatPromptTemplate.from_messages(messages)

        return prompt | llm_model_with_structured_output

    return title_descrption_reviewer_chain
