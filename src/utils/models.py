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

from pydantic import BaseModel, Field
from typing import List, Optional
from github.IssueComment import IssueComment as GHIssueComment


class ReviewComment(BaseModel):
    filename: str = Field(description="The filename on which the review comment is.")
    line_number: int = Field(description="The line number of the review comment in the file.")
    comment: str = Field(description="The review comment.")
    status: str = Field(description="The status of the review comment.")
    relevant: bool = Field(description="Is the review comment relevant or not?")
    reason: str = Field(description="The reason for why the review comment is relevant or non-relevant?")


class IssueComment(BaseModel):
    body: str
    conditions: Optional[List[str]] = None


class GitHubIssueCommentUpdate(GHIssueComment):
    new_body: str


class ReviewComments(BaseModel):
    issues: List[ReviewComment] = Field(description="List of code review issues found")


class ContextFile(BaseModel):
    path: str
    content: str

    def __str__(self) -> str:
        return f"File: {self.path}\n```\n{self.content}\n```"

    def __repr__(self) -> str:
        return self.__str__()
