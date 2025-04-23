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
from typing import List, Callable
from graphs.states import GitHubPRState, FileChange
from utils.logging_config import logger as log
from .contexts import DefaultContext
from pydantic import BaseModel
from utils.wrap_prompt import wrap_prompt
from utils.models import ReviewComments, ReviewComment, ContextFile
from langchain_core.runnables import RunnableSerializable


class codeReviewInput(BaseModel):
    files: list[ContextFile]
    changes: list[FileChange]
    static_analyzer_output: str


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
        """
        :param state:
        :return:
        """
        if self.context.chain is None:
            raise ValueError(f"{self.name}: Chain is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self.context.chain, RunnableSerializable) and not isinstance(self.context.chain,Callable):
            raise ValueError(f"{self.name}: Chain is not a RunnableSerializable or Callable")
        codereview = codeReviewInput(files=state['context_files'], changes=state['changes'],
                                     static_analyzer_output=state['static_analyzer_output'])
        response: ReviewComments = self.context.chain(codereview.model_dump()).invoke({})
        return [comment for comment in response.issues if comment.line_number != 0]
