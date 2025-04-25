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

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableSerializable
from typing import Any, Callable, Optional, Dict, List
from .contexts import DefaultContext
from graphs.states import GitHubPRState
from utils.logging_config import logger as log
from utils.models import IssueComment
from pydantic import BaseModel, Field


# class titleDescriptionInput(BaseModel):
#     diff: list[dict] = Field(description="A list of dictionary entries containing file-level diffs from the pull request. "
#                                          "Each dictionary includes metadata like filename, lines added/removed, and code changes. Use this to understand what has been changed.")
#     title: str = Field(description="The title of the PR ")
#     description: Optional[str] = Field(description="The description")
#     configuration: Optional[str] = Field(description="Configuration")

class TitleDescriptionInput(BaseModel):
    diff: List[Dict] = Field(
        description="A list of dictionaries representing the git diffs in the pull request. "
                    "Each dictionary contains details about the file changes such as file path, added/removed lines, and line numbers."
    )
    title: str = Field(
        description="The current title of the pull request. This will be evaluated to determine if it accurately reflects the code changes."
    )
    description: Optional[str] = Field(
        default=None,
        description="The current description provided in the pull request. "
                    "This will be reviewed to check if it sufficiently summarizes the purpose and content of the changes."
    )
    configuration: Optional[str] = Field(
        default=None,
        description="Additional instructions or context provided by the user to guide how the title and description should be improved. "
                    "If irrelevant to title/description quality, it should be ignored."
    )


class TitleDescriptionOutput(BaseModel):
    PR_title_suggestion: Optional[str] = Field(
        default="",
        description="A clear and concise title that best represents the changes introduced in the pull request. "
    )
    PR_description_suggestion: Optional[str] = Field(
        default="",
        description="A well-written summary that explains the purpose and content of the pull request. "
                    "Should highlight key changes, and include reasoning or context if necessary."
    )


@staticmethod
def get_model_dump_with_metadata(model_instance):
    data = model_instance.model_dump()
    metadata = model_instance.model_fields

    result = {}
    for field_name, value in data.items():
        description = metadata[field_name].description
        result[field_name] = {
            "value": value,
            "description": description
        }
    return result


class TitleDescriptionReviewer:
    def __init__(self, context: DefaultContext, name: str = "title_description_reviewer"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict[str, Any]:
        log.info(f"{self.name} called")

        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHubOperations is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self.context.chain, RunnableSerializable) and not isinstance(self.context.chain, Callable):
            raise ValueError(f"{self.name}: Chain is not a RunnableSerializable")

        user_input = ""
        if self.context.user_config:
            user_input = self.context.user_config.get("PR Title and Description", "")
        # Fetch existing comments
        titledescription = TitleDescriptionInput(diff=state["changes"],
                                                 title=state["title"],
                                                 description=state["description"],
                                                 configuration=user_input)
        title_desc_chain_result = self.context.chain(get_model_dump_with_metadata(titledescription)).invoke({})
        pr_title_suggestion = title_desc_chain_result.PR_title_suggestion
        pr_description_suggestion = title_desc_chain_result.PR_description_suggestion
        new_title_desc_comment = IssueComment(body=",".join([pr_title_suggestion, pr_description_suggestion]),
                                              conditions=["PR title suggestion", "PR description suggestion"])
        log.debug(f"""
        title and description reviewer finished. issue comment added.
        title and description comment: {new_title_desc_comment.model_dump_json(indent=2)}
        """)
        return {"new_issue_comments": [new_title_desc_comment]}
