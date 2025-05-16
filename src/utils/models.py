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
    filename: str = Field(description = "The 'filename' property of the change object associated with the comment")
    line_number: int = Field(description = "The 'start_line' property of the change object associated with the comment")
    status: str = Field(description = "The 'status' property of the change object associated with the comment")
    comment: str = Field(description = "Your review comment for the change - this is where you describe the issues you found")
    

class IssueComment(BaseModel):
    body: str
    conditions: Optional[List[str]] = None


class GitHubIssueCommentUpdate(GHIssueComment):
    new_body: str


class ReviewComments(BaseModel):
    issues: List[ReviewComment] = Field(description="List of code review comments, where each comment is associated with a change object from the list of changes")


class ContextFile(BaseModel):
    path: str
    content: str

    def __str__(self) -> str:
        return f"File: {self.path}\n```\n{self.content}\n```"

    def __repr__(self) -> str:
        return self.__str__()


class StaticAnalyzerInput(BaseModel):

    tf_validate_out_stderr: str = Field(description="This is the stderr output after running terraform validate -no-color")
    tf_validate_out_stdout: str = Field(description="This is the stdout output after running terraform validate -no-color")
    tflint_output_stderr: str = Field(description="This is the stderr output after running tflint --format=compact --recursive")
    tflint_output_stdout: str = Field(description="This is the stdout output after running tflint --format=compact --recursive")


class StaticAnalyzerOutputIssues(BaseModel):

    file_name: str = Field(description="This is the filename which has terraform issues")
    full_issue_description: str = Field(description="This is the full description of terraform issue")


class StaticAnalyzerOutputList(BaseModel):

    issues: List[StaticAnalyzerOutputIssues] = Field(description="List of terraform issues found")