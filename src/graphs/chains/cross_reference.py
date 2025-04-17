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
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableSerializable
from langchain_core.messages import BaseMessage


def create_cross_reference_generator_chain(model: BaseChatModel) -> RunnableSerializable[dict, BaseMessage]:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a senior Terraform engineer. You are given a Terraform codebase and a task to complete."),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    generate = prompt | model
    return generate


def create_cross_reference_reflector_chain(model: BaseChatModel) -> RunnableSerializable[dict, BaseMessage]:
    reflector_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a senior Terraform professional acting as a verification agent. "
                "Your task is to validate the cross-reference analysis by:\n\n"
                "1. Verify each reported cross-reference issue by:\n"
                "   - Checking the git diff for relevant changes\n"
                "   - Confirming the issue exists in the head codebase\n"
                "   - Validating that the reported file paths and references are accurate\n"
                "   - Ensuring the severity level is appropriate\n\n"
                "2. For each questionable or invalid issue:\n"
                "   - Explain why the issue might be incorrect\n"
                "   - Provide evidence from the codebase\n"
                "   - Suggest how the generator should adjust its analysis\n\n"
                "3. Check for false negatives in critical areas:\n"
                "   - Variable references in modified files\n"
                "   - Resource dependencies affected by changes\n"
                "   - Module interface changes\n\n"
                "Format your response as:\n"
                "### Validation Results\n"
                "- Confirmed Issues: [list verified issues]\n"
                "- Incorrect Issues: [list with explanations]\n"
                "- Additional Concerns: [only if critical issues were missed]\n\n"
                "Focus on accuracy and thoroughness in your verification.",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    reflector = reflector_prompt | model
    return reflector
