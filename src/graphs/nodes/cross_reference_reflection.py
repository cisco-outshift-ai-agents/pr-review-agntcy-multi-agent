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

from graphs.states import GitHubPRState
from utils.logging_config import logger as log
from .contexts import DefaultContext

import base64
from github.Commit import Commit
from github.GitTree import GitTree
from github.GitBlob import GitBlob
from github.GitTreeElement import GitTreeElement
from langchain_core.messages import HumanMessage, AIMessage
from utils.models import IssueComment
from pydantic import BaseModel, Field


class File:
    def __init__(self, path: str, content: str):
        self.path: str = path
        self.content: str = content

    def __str__(self):
        return f"##FILE: {self.path}\n{self.content}\n##END_OF_FILE\n\n"


class crossReferenceGeneratorOutput(BaseModel):
    cross_reference_generator_output: str = Field(description="Sample generator response")


class crossReferenceReflectorOutput(BaseModel):
    cross_reference_reflector_output: str = Field(description="Sample reflector response")


class CrossReferenceInitializer:
    """
    This class is used to get the code base and git diff
    """

    def __init__(self, context: DefaultContext, name: str = "cross_reference_initializer"):
        self.context = context
        self.name = name
        self.file_type = "blob"
        self.file_extension = (".tf", ".tfvars")

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")

        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHub is not set in the context")

        # modified_files = self.context.github.pr.get_files()  # modified files
        head_sha = self.context.github.pr.head.sha
        base_sha = self.context.github.pr.base.sha

        # Get all files from the head commit
        head_files: list[File] = self._get_files_from_sha(head_sha)

        # Get all files from the base commit
        base_files: list[File] = self._get_files_from_sha(base_sha)

        codebase = self._codebase(base_files)
        head_codebase = self._codebase(head_files)
        git_diff = self.context.github.get_git_diff()
        user_prompt = _create_user_prompt(git_diff, codebase, head_codebase)
        return {"messages": [HumanMessage(content=user_prompt)]}

    def _get_files_from_sha(self, sha: str) -> list[File]:
        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHub is not set in the context")

        # Get the commit object
        commit: Commit = self.context.github.repo.get_commit(sha)

        # Get the tree associated with the commit
        tree: GitTree = commit.commit.tree

        # Get all files in the tree
        files: list[GitTreeElement] = self.context.github.repo.get_git_tree(tree.sha, recursive=True).tree

        # Create a list of File objects
        file_objects = []
        for file in files:
            if file.type == self.file_type:
                # need only ".tf" and ".tfvars" files
                if not file.path.endswith(self.file_extension):
                    continue
                # Read the file content
                blob: GitBlob = self.context.github.repo.get_git_blob(file.sha)
                # Decode the base64 content
                content = base64.b64decode(blob.content).decode("utf-8")
                file_objects.append(File(file.path, content))

        return file_objects

    def _codebase(self, files: list[File]) -> str:
        codebase = ""
        for file in files:
            codebase += str(file)

        return codebase


class CrossReferenceGenerator:
    def __init__(self, context: DefaultContext, name: str = "cross_reference_generator"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")
        if self.context.chain is None:
            raise ValueError(f"{self.name}: Chain is not set in the context")
        response = self.context.chain.invoke(state['messages'])
        return {"messages": response.cross_reference_generator_output}


class CrossReferenceReflector:
    def __init__(self, context: DefaultContext, name: str = "cross_reference_reflector"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")

        if self.context.chain is None:
            raise ValueError(f"{self.name}: Chain is not set in the context")

        # Other messages we need to adjust
        cls_map = {"ai": HumanMessage, "human": AIMessage}
        # First message is the original user request. We hold it the same for all nodes
        translated = [state["messages"][0]] + [cls_map[msg.type](content=msg.content) for msg in state["messages"][1:]]
        res = self.context.chain(translated).invoke({})
        return {"messages": [HumanMessage(content=res.cross_reference_reflector_output)]}


def _create_user_prompt(git_diff: str, base_codebase: str, head_codebase: str) -> str:
    user_prompt = """
        # git diff
        ```
        {git_diff}
        ```

        # head reference codebase:
        ```
        {head_codebase}
        ```

        # base reference codebase:
        ```
        {base_codebase}
        ```

        Analyze the Terraform code for cross-reference issues by comparing the base and head codebases. Return ONLY a list of issues in this exact format:

        ### Summary of Cross-Reference Problems

        - **`<resource_or_variable>`**: Used in `<file_path>` but not defined
        - **`<variable>`**: Defined in `<file_path>` but not used

        Rules:
        1. Only include actual cross-reference problems
        2. Do not include any other sections or explanations
        3. If no issues found, return only "### Summary of Cross-Reference Problems\n\nNo cross-reference issues found."
        4. Each issue must be a single line starting with a hyphen
        5. Use the exact format shown above

        Focus only on:
        - Variables or resources used but not defined
        - Variables or resources defined but not used
        - Module outputs used but not defined
        - Module input variables not provided
        - Variables defined in .tf files but missing from terraform.tfvars
        - Variables defined in terraform.tfvars but missing from .tf files
        - Variables defined in either .tf or terraform.tfvars (or both) but not referenced in any other files or resources
        """
    # Now fill in values
    filled_prompt = user_prompt.format(
        git_diff=git_diff,
        head_codebase=head_codebase,
        base_codebase=base_codebase
    )
    return filled_prompt


class CrossReferenceCommenter:
    """
    This class is used to post issue comments for the cross reference comments
    """

    def __init__(self, name: str = "cross_reference_commenter"):
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")
        messages = []
        for res in state["messages"][1:]:
            if isinstance(res, HumanMessage):
                messages.append(res)
        print("The list of messages", messages)
        return {"new_issue_comments": [IssueComment(body=messages[-1].content)]}
