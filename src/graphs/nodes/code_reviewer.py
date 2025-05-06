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

import concurrent.futures
import json

import concurrent
from typing import Optional, List, Callable
from graphs.states import GitHubPRState, FileChange
from utils.logging_config import logger as log
from utils.wrap_prompt import wrap_prompt
from .contexts import DefaultContext
from pydantic import BaseModel, Field
from utils.models import ReviewComments, ReviewComment, ContextFile, StaticAnalyzerOutputList
from langchain_core.runnables import RunnableSerializable


# class codeReviewInput(BaseModel):
#     files: Optional[list[ContextFile]] = Field(default_factory=list,
#                                                description=
#                                                """receive all the Terraform files from the user in the "FILES" list..""")
#     changes: list[FileChange] = Field(
#         description="""List of code changes across Terraform files. The changes have the following format:
#             - filename: the name of the file where the change was done
#             - start_line: the line number where the change was added
#             - changed_code: the code that was removed/added after the start line, there's a + or - sign at the beginning of every change line, it indicates if it was added or removed, ignore this sign.
#             - status: indicates if the changed_code was added/removed
#         - Changes with "removed" status mean that the code in that change was deleted from the codebase, it's not part of the code anymore.
#         - Changes with "added" status mean that the code in that change was added the codebase.
#         - Always focus on whether a change was added or removed from the codebase. If it was removed then that code is not part of the codebase anymore.
#         - Sometimes the changes are in pairs, one change with a 'removed' status and one with 'added', but they belong together, even when their line numbers are far apart.
#             Identify these pairs and DO NOT add the same comment to the removed and added part twice!""")
#     static_analyzer_output: list[str] = Field(
#         description="""
#         - A list of multiple static code analyzers (tflint, tfsec, etc.) on the new code.
#         - The static_analyzer_output could be useful for understanding the potential issues introduced by the user, like missing references, undefined or unused variables etc.
#         - The static_analyzer_output could have issues which are not related to the current code changes, you MUST ignore these issues as they weren't introduced by this PR.
#         """)
#
#
# @staticmethod
# def get_model_dump_with_metadata(model_instance):
#     data = model_instance.model_dump()
#     metadata = model_instance.model_fields
#
#     result = {}
#     for field_name, value in data.items():
#         description = metadata[field_name].description
#         result[field_name] = {
#             "value": value,
#             "description": description
#         }
#     return result
#
#
# class CodeReviewer:
#     def __init__(self, context: DefaultContext, name: str = "code_reviewer"):
#         self.context = context
#         self.name = name
#
#     def __call__(self, state: GitHubPRState) -> dict:
#         log.info(f"{self.name} called")
#
#         try:
#             comments: List[ReviewComment] = []
#             with concurrent.futures.ThreadPoolExecutor() as executor:
#                 results: List[List[ReviewComment]] = list(executor.map(lambda _: self.__code_review(state), range(5)))
#
#             for res in results:
#                 comments.extend(res)
#
#         except Exception as e:
#             log.error(f"Error in {self.name}: {e}")
#             raise
#
#         log.debug(f"""
#         code reviewer finished.
#         review comments: {json.dumps([comment.model_dump() for comment in comments], indent=4)}
#         """)
#
#         return {"new_review_comments": comments}
#
#     def __code_review(self, state: GitHubPRState) -> List[ReviewComment]:
#         """
#         :param state:
#         :return:
#
#         """
#         if self.context.chain is None:
#             raise ValueError(f"{self.name}: Chain is not set in the context")
#
#         # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
#         if not isinstance(self.context.chain, RunnableSerializable) and not isinstance(self.context.chain, Callable):
#             raise ValueError(f"{self.name}: Chain is not a RunnableSerializable or Callable")
#         if isinstance(state['static_analyzer_output'], StaticAnalyzerOutputList):
#             static_analyzer_response = [f"{res.file_name}: {res.full_issue_description}" for res in
#                                         state['static_analyzer_output'].issues]
#         else:
#             static_analyzer_response = []
#         codereview = codeReviewInput(files=state['context_files'], changes=state['changes'],
#                                      static_analyzer_output=static_analyzer_response)
#         response: ReviewComments = self.context.chain(get_model_dump_with_metadata(codereview)).invoke({})
#         return [comment for comment in response.issues if comment.line_number != 0]

class CodeReviewer:
    def __init__(self, context: DefaultContext, name: str = "code_reviewer"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")

        try:
            comments: List[ReviewComment] = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                results: List[List[ReviewComment]] = list(executor.map(lambda _: self.__code_review(state), range(5)))

            for res in results:
                comments.extend(res)

        except Exception as e:
            log.error(f"Error in {self.name}: {e}")
            raise

        log.debug(f"""
        code reviewer finished.
        review comments: {json.dumps([comment.model_dump() for comment in comments], indent=4)}
        """)

        return {"new_review_comments": comments}

    def __code_review(self, state: GitHubPRState) -> List[ReviewComment]:
        if self.context.chain is None:
            raise ValueError(f"{self.name}: Chain is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self.context.chain, RunnableSerializable):
            raise ValueError(f"{self.name}: Chain is not a RunnableSerializable")

        if isinstance(state['static_analyzer_output'], StaticAnalyzerOutputList):
            static_analyzer_response = [f"{res.file_name}: {res.full_issue_description}" for res in
                                                state['static_analyzer_output'].issues]
        else:
            static_analyzer_response = []


        response: ReviewComments = self.context.chain.invoke(
            {
                "question": wrap_prompt(
                    "FILES:",
                    f"{'\n'.join(map(str, state['context_files']))}",
                    "",
                    "CHANGES:" f"{state['changes']}",
                    "",
                    "STATIC_ANALYZER_OUTPUT:",
                    f"{static_analyzer_response}",
                    # "USER_CONFIGURATION:",
                    # f"{self.user_config.get("Code Review", "")}",
                    # f"{self.user_config.get("Security & Compliance Policies", "")}",
                )
            }
        )

        return [comment for comment in response.issues if comment.line_number != 0]
