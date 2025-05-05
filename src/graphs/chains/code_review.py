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
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import RunnableSerializable
from typing import cast, Callable
from utils.wrap_prompt import wrap_prompt
from utils.models import ReviewComments, ContextFile
from pydantic import Field, BaseModel


def create_code_reviewer_chain(model: BaseChatModel) -> Callable[
    [list[ReviewComments]], RunnableSerializable[dict, dict | ReviewComments]]:
    def code_reviewer_chain(input_dict: dict) -> RunnableSerializable[dict, dict | ReviewComments]:
        llm_with_structured_output = model.with_structured_output(ReviewComments)

        # If some lines are indented more than others, dedent can't normalize it effectively.
        system_message = SystemMessagePromptTemplate.from_template(
            "You are an expert in Terraform and a diligent code reviewer. Your goal is to support the developer in writing safer, cleaner, and more maintainable Terraform code. \
            Provide your feedback in a professional, clear, constructive, concise with explicit details. \
            ")

        user_message = HumanMessagePromptTemplate.from_template("""

        You will be given all files in the code base, the list of changed files and the static analyzer output.

         files : {files}
         changed_files: {changed}
         static_analyzer_output: {static_analyzer_output}

        Provide feedback based on the following best-practice categories:
            1. **Security**: Secrets management, IAM roles/policies, network configurations, etc.
            2. **Maintainability**: Code organization, DRY principle, module usage, variable naming, version pinning.
            3. **Scalability & Performance**: Resource sizing, autoscaling configurations, load balancing.
            4. **Reliability**: Redundancy, high availability, state management strategies (e.g., remote state with locking).
            5. **Cost Optimization**: Potential oversizing of resources, recommended resource types for cost efficiency.
            6. **Compliance & Governance**: Adherence to organizational policies, tagging conventions, regulatory requirements.
            7. **Documentation & Observability**: Comments, usage docs, logging/monitoring configuration.
            For each category, list:
            - **Strengths** and **Areas of Improvement**
            - **Suggested changes** or additional best practices to consider


        Here are some guidelines on providing feedback:
        - Review all the files to understand the current state of the codebase.
        - Use the STATIC_ANALYZER_OUTPUT to identify potential errors in the new code.
        - Review the changes to understand what was changed in this PR to arrive at the current state of the files.
        - Always check the changes in the CHANGES list and comment only on the changed lines. You MUST NOT comment on unchanged code.
        - Check the status of the changes and comment accordingly. For eg., if the status says 'added' then that piece of code was a new addition and if it says 'removed' then it was deleted from the codebase.
        - You DO NOT have to comment on every code change block, if you do not see an issue, or if you already commented on the other pair of the change, ignore and move on.
        - Each comment MUST refer to a change and the change must be associated with the issue that the comment is mentioning.
        - ONLY comment on changes that have actual code changes (e.g., variable definitions, resource definitions, etc.)
        - DO NOT provide general or positive feedback (e.g., 'This looks good', 'This is a best practice', etc.)
        - Your comments should be brief, clear and professional


        Before returning your response, take your time to review your results:
        - Make sure that each comment belongs to a change.
        - Make sure the properties of the comment are aligned with the change object's properties.
        - Make sure the comment messages are relevant and provide actionable items to the user.
        - Make sure you checked the static analyzer outputs.
            """).format(files=input_dict["files"], changed=input_dict["changes"],
                        static_analyzer_output=input_dict["static_analyzer_output"])
        messages = [system_message, user_message]
        prompt = ChatPromptTemplate.from_messages(messages)
        return prompt | llm_with_structured_output

    return code_reviewer_chain
