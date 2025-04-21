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

from src.graphs.nodes.fetch_pr import validate_branch_name


def test_validates_valid_branch_name():
    valid_branch_name = "feature/valid-branch_name"
    validate_branch_name(valid_branch_name)


def test_raises_error_for_invalid_repo_name_with_special_characters():
    invalid_repo_name = "ab-&-&-c-7-d"
    with pytest.raises(ValueError, match="Invalid branch name: 'ab-&-&-c-7-d'"):
        validate_branch_name(invalid_repo_name)


def test_raises_error_for_empty_branch_name():
    invalid_branch_name = ""
    with pytest.raises(ValueError, match="Invalid branch name: ''"):
        validate_branch_name(invalid_branch_name)
