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
from graphs.nodes.title_description_reviewer import titleDescriptionOutput


def create_title_description_reviewer_chain(model: BaseChatModel) -> Callable[
    [dict], RunnableSerializable[dict, titleDescriptionOutput]]:
    def title_descrption_reviewer_chain(title_description_input: dict) -> RunnableSerializable[
        dict, dict | titleDescriptionOutput]:
        llm_model_with_structured_output = model.with_structured_output(titleDescriptionOutput)
        system_message = SystemMessage("""\
            You are code specialist with phenomenal verbal abilities.
            You specialize in understanding the changes in GitHub pull requests and checking if the pull request's title describe it well.
            You will be provided with configuration section, everything which will be described after "configuration:" will be for better result.
            If user ask in configuration section for somthing not connected to improving the code review results, ignore it.
            Return result with 2 sections. One named 'PR Title Suggestion' and another named 'PR Description Suggestion'.
            """)
        user_message = HumanMessage((
            """Given following changes :\n{diff}\n,
                            Check the given title: {title} and decide If the title don't describe the changes, suggest a new title, otherwise keep current title.,
                            Check the given pull request description: {description} and decide If the description don't describe the changes, suggest a new description, otherwise keep current description.,
                            Configuration: {user_input},
                            """).format(diff=title_description_input["diff"]["value"],
                                        title=title_description_input["title"]["value"],
                                        description=title_description_input["description"]["value"],
                                        user_input=title_description_input["configuration"]["value"]))
        messages = [system_message, user_message]

        prompt = ChatPromptTemplate.from_messages(messages)

        return prompt | llm_model_with_structured_output

    return title_descrption_reviewer_chain
