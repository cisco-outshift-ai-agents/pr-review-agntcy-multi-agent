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
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from graphs.nodes.cross_reference_reflection import crossReferenceGeneratorOutput, crossReferenceReflectorOutput


def create_cross_reference_generator_chain(model: BaseChatModel) -> Callable[[list[BaseMessage]], RunnableSerializable]:
    def cross_reference_generator_chain(user_messages: list[HumanMessage]) -> RunnableSerializable[
        dict, dict | crossReferenceGeneratorOutput]:
        structured_output_model = model.with_structured_output(crossReferenceGeneratorOutput)
        system_message = SystemMessage(
            "You are a Terraform Agent. "
            "Given a terraform codebase and a task, "
            "analyze and take necessary steps to complete it, "
            "following best practices."
        )
        user_message = HumanMessage(f"{user_messages}")
        messages = [system_message, user_message]
        template = ChatPromptTemplate.from_messages(messages)
        return template | structured_output_model

    return cross_reference_generator_chain


# def create_cross_reference_generator_chain(model: BaseChatModel) -> RunnableSerializable[
#     dict, crossReferenceGeneratorOutput]:
#     model_with_structured = model.with_structured_output(crossReferenceGeneratorOutput)
#
#     prompt = ChatPromptTemplate.from_messages(
#         [
#             ("system",
#              "You are a senior Terraform Agent. You are given a Terraform codebase and a task to complete."),
#             MessagesPlaceholder(variable_name="messages"),
#         ]
#     )
#
#     generate = prompt | model_with_structured
#     return generate


def create_cross_reference_reflector_chain(model: BaseChatModel) -> Callable[[list[BaseMessage]], RunnableSerializable]:
    def cross_reference_reflector_chain(user_messages: list[HumanMessage]) -> RunnableSerializable[
        dict, dict | crossReferenceReflectorOutput]:
        structured_output_model = model.with_structured_output(crossReferenceReflectorOutput)
        system_message = SystemMessage(
            "You are a Terraform verification agent. Validate cross-reference analysis by:\n\n"
            "1. Verifying reported issues via:\n"
            "   - git diff checks\n"
            "   - confirming existence in HEAD\n"
            "   - validating file paths and references\n"
            "   - assessing severity\n\n"
            "2. For invalid/questionable issues:\n"
            "   - explain why\n"
            "   - give supporting evidence\n"
            "   - suggest improvements to the generator\n\n"
            "3. Identify false negatives in:\n"
            "   - variable references\n"
            "   - resource dependencies\n"
            "   - module interface changes\n\n"
            "Respond with:\n"
            "### Validation Results\n"
            "- Confirmed Issues: [...]\n"
            "- Incorrect Issues: [... with reasons]\n"
            "- Additional Concerns: [... if critical]\n\n"
            "Be accurate and thorough.",
        )
        user_message = HumanMessage(f"{user_messages}")
        messages = [system_message, user_message]
        print("The input to the cross_Reference reflector", messages)
        template = ChatPromptTemplate.from_messages(messages)
        return template | structured_output_model

    return cross_reference_reflector_chain
