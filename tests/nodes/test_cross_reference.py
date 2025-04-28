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
from graphs.nodes.cross_reference_reflection import (crossReferenceReflectorOutput, crossReferenceGeneratorOutput,
                                                     CrossReferenceReflector, CrossReferenceGenerator)
from graphs.chains.cross_reference import create_cross_reference_generator_chain, create_cross_reference_reflector_chain
from graphs.states import GitHubPRState, create_default_github_pr_state
from utils.constants import AZURE_OPENAI_API_KEY_ENV
from utils.github_operations import GitHubOperations
from utils.modelfactory import models
import pytest
from unittest.mock import MagicMock
from graphs.chains.title_description_review import create_title_description_reviewer_chain
import warnings

warnings.filterwarnings("ignore")


@pytest.fixture
def mock_generator_context() -> MagicMock:
    with patch("utils.modelfactory.secret_manager") as mock_secret_manager:
        mock_secret_manager.azure_openai_api_key = os.getenv(AZURE_OPENAI_API_KEY_ENV)
        model = models.get_azure_openai()

    context = DefaultContext()
    context.chain = create_title_description_reviewer_chain(model)

    github = MagicMock(spec=GitHubOperations)
    context.github = github

    return context


@pytest.fixture
def mock_reflector_context() -> MagicMock:
    with patch("utils.modelfactory.secret_manager") as mock_secret_manager:
        mock_secret_manager.azure_openai_api_key = os.getenv(AZURE_OPENAI_API_KEY_ENV)
        model = models.get_azure_openai()

    context = DefaultContext()
    context.chain = create_title_description_reviewer_chain(model)

    github = MagicMock(spec=GitHubOperations)
    github.clone_repo.return_value = ""

    context.github = github

    return context


def test_cross_reference_generator_init(mock_generator_context):
    name = "test_cross_reference_generator"
    cf = CrossReferenceGenerator(mock_generator_context, name)
    assert cf.context == mock_generator_context
    assert cf.name == name


def test_cross_reference_reflector_init(mock_reflector_context):
    name = "test_cross_reference_reflector"
    cf = CrossReferenceReflector(mock_reflector_context, name)
    assert cf.context == mock_reflector_context
    assert cf.name == name


@patch("graphs.nodes.cross_reference_reflection.CrossReferenceGenerator")
def test_cross_reference_generator_call(mock_generator_context):
    cf = CrossReferenceGenerator(mock_generator_context)
    cf.context.chain.invoke = MagicMock(return_value={"cross_reference_generator_output": "temp"})
    response = cf.context.chain.invoke({})
    assert "cross_reference_generator_output" in response


@patch("graphs.nodes.cross_reference_reflection.CrossReferenceReflector")
def test_cross_reference_reflector_call(mock_reflector_context):
    cf = CrossReferenceReflector(mock_reflector_context)
    cf.context.chain.invoke = MagicMock(return_value={
        "cross_reference_reflector_output": "Enhance Feature X Workflow by Fixing Bug"
    })
    response = cf.context.chain.invoke()
    assert "cross_reference_reflector_output" in response
