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
from .contexts import DefaultContext
from utils.logging_config import logger as log


class Commenter:
    """Commenter creates GitHub issue comments for a given PR"""

    def __init__(self, context: DefaultContext, name: str = "commenter"):
        self.context = context
        self.name = name

    def __call__(self, state: GitHubPRState) -> None:
        log.info(f"{self.name}: called")

        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHubOperations is not set in the context")

        try:
            for u_i_c in state["issue_comments_to_update"]:
                u_i_c.edit(u_i_c.new_body)
        except Exception as e:
            log.error(f"Error updating existing comment: {e}")

        try:
            self.context.github.create_comments(state["new_review_comments"], state["new_issue_comments"])
        except Exception as e:
            log.error(f"{self.name}: Error creating comments: {e}")
            raise
