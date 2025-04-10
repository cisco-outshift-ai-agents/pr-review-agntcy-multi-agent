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

from graphs.states import ReviewChatAssistantState
from utils.logging_config import logger as log
from .contexts import DefaultContext


class CommentRelatedPatchFetcher:
    def __init__(self, context: DefaultContext, name: str = "comment_related_patch_fetcher"):
        self.context = context
        self.name = name

    def __call__(self, state: ReviewChatAssistantState) -> dict:
        log.info(f"{self.name} called")

        if not self.context.github:
            raise ValueError("GitHub operations not found")

        try:
            files = self.context.github.pr.get_files()
        except Exception as e:
            raise ValueError(f"Error getting patch from GitHub: {e}") from e

        for f in files:
            if f.filename == state["comment"]["path"]:
                return {"reviewed_patch": f.patch}

        raise ValueError(f"File {state["comment"]["path"]} not found in the PR's files")
