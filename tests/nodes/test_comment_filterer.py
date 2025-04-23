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

import pytest
from unittest.mock import MagicMock
from graphs.nodes.comment_filterer import CommentFilterer
from graphs.nodes.contexts import DefaultContext
from langchain_core.runnables import RunnableSerializable

from graphs.states import GitHubPRState, create_default_github_pr_state
from utils.models import ReviewComment

new_review_comments = [
    ReviewComment(
        filename="main.tf",
        line_number=10,
        comment="The CIDR block '10.0.2.0.12/24' is invalid. CIDR blocks must follow the correct format, such as '10.0.2.0/24'. This will cause errors during resource creation.",
        status="added",
    ),
    ReviewComment(
        filename="main.tf",
        line_number=12,
        comment="The CIDR block '10.0.2.0.12/24' is invalid. CIDR blocks must follow the correct format, such as '10.0.2.0/24'. This will cause errors during resource creation.",
        status="added",
    ),
    ReviewComment(
        filename="main.tf",
        line_number=20,
        comment="The 'aws_route_table' resource for 'public_rt' has been removed, but it is still being referenced in 'aws_route_table_association.public_rt_assoc'. This will result in a reference error.",
        status="removed",
    ),
    ReviewComment(
        filename="main.tf",
        line_number=21,
        comment="The 'aws_route_table' resource for 'public_rt' has been deleted, yet it is still being referenced in 'aws_route_table_association.public_rt_assoc', which will cause a reference error.",
        status="removed",
    ),
    ReviewComment(
        filename="main.tf",
        line_number=22,
        comment="The 'aws_route_table' resource for 'public_rt' has been removed, but it is still referenced in 'aws_route_table_association.public_rt_assoc', leading to a reference error.",
        status="removed",
    ),
    ReviewComment(
        filename="main.tf",
        line_number=30,
        comment="The instance type has been changed to 't2.xlarge'. This could significantly increase costs compared to 't2.micro'. Ensure this change is intentional and aligns with the project's budget and performance requirements.",
        status="added",
    ),
    ReviewComment(
        filename="main.tf",
        line_number=31,
        comment="The instance type has been updated to 't2.xlarge', which may lead to a notable increase in costs compared to 't2.micro'. Please confirm that this change is intentional and consistent with the project's budget and performance needs.",
        status="added",
    ),
    ReviewComment(
        filename="outputs.tf",
        line_number=50,
        comment="Storing sensitive information like passwords in plain text outputs is a security risk. Consider using a secure method to manage secrets, such as AWS Secrets Manager.",
        status="added",
    ),
    ReviewComment(
        filename="outputs.tf",
        line_number=50,
        comment="Storing sensitive information, such as passwords, in plain text outputs poses a security risk. It's recommended to use a secure solution for managing secrets, like AWS Secrets Manager.",
        status="added",
    ),
]

existing_review_comments = [
    ReviewComment(
        filename="main.tf",
        line_number=10,
        comment="The CIDR block '10.0.2.0.12/24' is invalid. CIDR blocks must follow the correct format, such as '10.0.2.0/24'. This will cause errors during resource creation.",
        status="added",
    ),
    ReviewComment(
        filename="main.tf",
        line_number=20,
        comment="The 'aws_route_table' resource for 'public_rt' has been removed, but it is still being referenced in 'aws_route_table_association.public_rt_assoc'. This will result in a reference error.",
        status="removed",
    ),
]

new_review_comments_filtered = [
    ReviewComment(
        filename="main.tf",
        line_number=30,
        comment="The instance type has been changed to 't2.xlarge'. This could significantly increase costs compared to 't2.micro'. Ensure this change is intentional and aligns with the project's budget and performance requirements.",
        status="added",
    ),
    ReviewComment(
        filename="outputs.tf",
        line_number=50,
        comment="Storing sensitive information like passwords in plain text outputs is a security risk. Consider using a secure method to manage secrets, such as AWS Secrets Manager.",
        status="added",
    ),
]


@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock(spec=DefaultContext)
    context.chain = MagicMock(spec=RunnableSerializable)
    context.chain.invoke.return_value.issues = new_review_comments_filtered
    return context


@pytest.fixture
def mock_state() -> GitHubPRState:
    state = create_default_github_pr_state()
    state["new_review_comments"] = new_review_comments
    state["review_comments"] = existing_review_comments
    return state


def test_comment_filterer_init(mock_context):
    name = "test_comment_filterer"
    cf = CommentFilterer(mock_context, name)
    assert cf._context == mock_context
    assert cf._name == name


def test_comment_filterer_call_chain_error(mock_context, mock_state):
    mock_context.chain = None
    cf = CommentFilterer(mock_context)

    with pytest.raises(ValueError):
        cf(mock_state)

    mock_context.chain = MagicMock(spec=list)
    cf = CommentFilterer(mock_context)

    with pytest.raises(ValueError):
        cf(mock_state)


def test_comment_filterer_call(mock_context, mock_state):
    cf = CommentFilterer(mock_context)
    resp = cf(mock_state)
    assert resp == {
        "new_review_comments": new_review_comments_filtered,
        "new_issue_comments": [],
        "issue_comments_to_update": [],
    }


def test_comment_filterer_remove_duplicate_comments(mock_context, mock_state):
    cf = CommentFilterer(mock_context)
    resp = cf._remove_duplicate_comments(existing_review_comments, new_review_comments)
    assert resp == new_review_comments_filtered
