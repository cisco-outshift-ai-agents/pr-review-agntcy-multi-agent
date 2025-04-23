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

"""
TODO:
1. input Model(need to define) - define the fields
2. output model(ReviewComments) - add more fields
3. refine the instructions for reviewing the changed files and how to write the comment - add instruction to include actionable items
"""


def create_code_reviewer_chain(model: BaseChatModel) -> Callable[
    [list[ReviewComments]], RunnableSerializable[dict, dict | ReviewComments]]:
    def code_reviewer_chain(input_dict: dict) -> RunnableSerializable[dict, dict | ReviewComments]:
        llm_with_structured_output = model.with_structured_output(ReviewComments)

        # If some lines are indented more than others, dedent can't normalize it effectively.
        system_message = SystemMessagePromptTemplate.from_template(
            "You are an expert in Terraform. Analyze the Terraform code changes in the pull request.")

        user_message = HumanMessagePromptTemplate.from_template("""
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
            files : {files}
            changed_files: {changed}
            static_analyzer_output: {static_analyzer_output}
            """).format(files=input_dict["files"], changed=input_dict["changes"],
                        static_analyzer_output=input_dict["static_analyzer_output"])
        messages = [system_message, user_message]
        prompt = ChatPromptTemplate.from_messages(messages)
        return prompt | llm_with_structured_output

    return code_reviewer_chain
