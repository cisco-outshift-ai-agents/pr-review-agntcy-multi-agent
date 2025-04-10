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

from abc import ABC, abstractmethod


class ParserMixin(ABC):
    """
    ParserMixin interface to define the parse_content method which must be implemented by the parser classes.
    """

    @abstractmethod
    def parse_content(self, content: str) -> dict[str, str]:
        """
        Parse the content and return a dictionary of key-value pairs.

        :param content: Content to parse
        :return: Dictionary of key-value pairs
        """
        pass


class ParseContentError(Exception):
    """Exception raised when there is an error in parsing content."""

    def __init__(self, message: str, content: str):
        super().__init__(message)
        self.content = content
