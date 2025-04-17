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

from io import StringIO
from unittest.mock import Mock

import pytest

from config import AgentConfig, ParserMixin, ParseContentError


class MockParser(ParserMixin):
    def parse_content(self, content: str) -> dict[str, str]:
        if content == "invalid":
            raise ParseContentError("Mock parsing error", content)
        return {"key": "value"}


@pytest.mark.parametrize(
    "content, parser, expected_result, expected_exception",
    [
        # Valid case
        ("test content", MockParser(), {"key": "value"}, None),
        # Parser error case
        ("invalid", MockParser(), None, "Failed to parse content: Mock parsing error"),
        # IO error case
        (None, MockParser(), None, "Failed to read content: Mock IO error"),
    ],
)
def test_agent_config_initialization(content, parser, expected_result, expected_exception):
    # Create a mock reader
    if content is not None:
        mock_reader = StringIO(content)
    else:
        mock_reader = Mock()
        mock_reader.read = Mock(side_effect=IOError("Mock IO error"))

    if expected_exception:
        with pytest.raises(Exception) as excinfo:
            AgentConfig(mock_reader, parser)
        assert str(excinfo.value).startswith(expected_exception)
    else:
        config = AgentConfig(mock_reader, parser)
        assert config.data == expected_result


def test_agent_config_data_method():
    mock_reader = StringIO("test content")
    config = AgentConfig(mock_reader, MockParser())
    # Access data as a property, not a method
    assert config.data == {"key": "value"}
