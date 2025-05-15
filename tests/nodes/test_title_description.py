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

import os
from unittest.mock import MagicMock, patch
from graphs.nodes.contexts import DefaultContext
from graphs.nodes.title_description_reviewer import TitleDescriptionReviewer, TitleDescriptionOutput, \
    TitleDescriptionInput, get_model_dump_with_metadata
from graphs.states import GitHubPRState, create_default_github_pr_state
from utils.constants import AZURE_OPENAI_API_KEY_ENV
from utils.github_operations import GitHubOperations
from utils.modelfactory import models
import pytest
from unittest.mock import MagicMock
from graphs.chains.title_description_review import create_title_description_reviewer_chain
from graphs.states import GitHubPRState
from utils.models import IssueComment
import warnings

warnings.filterwarnings("ignore")

new_issue_comments = [IssueComment(
    body=f"PR Title Suggestion:\nEnhance Feature X Workflow by Fixing Bug\n\n"
         f"PR Description Suggestion:\n This pull request fixes a bug in the X feature, which improves the overall workflow.The changes include adding 5 lines and removing 2 lines in the 'example.py' file to address the issue effectively.",
    conditions=["PR title suggestion", "PR description suggestion"]
)

]
@pytest.fixture
def mock_context() -> MagicMock:
    with patch("utils.modelfactory.secret_manager") as mock_secret_manager:
        mock_secret_manager.azure_openai_api_key = os.getenv(AZURE_OPENAI_API_KEY_ENV)
        model = models.get_azure_openai()

    context = DefaultContext()
    context.chain = create_title_description_reviewer_chain(model)


    github = MagicMock(spec=GitHubOperations)
    github.clone_repo.return_value = new_issue_comments

    context.github = github

    return context


@pytest.fixture
def mock_state() -> GitHubPRState:
    state = create_default_github_pr_state()
    state["changes"] = [{"file": "example.py", "lines_added": 5, "lines_removed": 2}]
    state["title"] = "Fix bug in feature X"
    state["description"] = "This PR addresses a bug in the X feature, improving the workflow."
    state["new_issue_comments"] = new_issue_comments
    return state


def test_title_description_init(mock_context):
    name = "test_title_description"
    cf = TitleDescriptionReviewer(mock_context, name)
    assert cf.context == mock_context
    assert cf.name == name

@patch("graphs.nodes.title_description_reviewer.TitleDescriptionReviewer")
def test_title_description_call(mock_context):
    cf = TitleDescriptionReviewer(mock_context)
    cf.context.chain.invoke = MagicMock(return_value={
        "PR_title_suggestion": "Enhance Feature X Workflow by Fixing Bug",
        "PR_description_suggestion": "This pull request fixes a bug in the X feature, which improves the overall workflow.The changes include adding 5 lines and removing 2 lines in the 'example.py' file to address the issue effectively."
    })
    response = cf.context.chain.invoke()
    assert "PR_title_suggestion" in response
    assert "PR_description_suggestion" in response
