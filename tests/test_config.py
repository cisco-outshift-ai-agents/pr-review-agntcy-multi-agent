from io import StringIO
from unittest.mock import Mock
import pytest
from src.config import AgentConfig, ParserMixin, ParseContentError


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
