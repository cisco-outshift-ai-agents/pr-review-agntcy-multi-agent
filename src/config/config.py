from typing import IO
from .parser_mixin import ParserMixin, ParseContentError


class Config:
    """
    Config class to read and parse configuration using the provided reader and parser. Parser must implement the
    ParserMixin interface which defines the parse_content method.
    """

    def __init__(self, reader: IO, parser: ParserMixin):
        try:
            # Private attribute to hold raw content
            self._content = reader.read()

            # Parse the content using the provided parser
            self.data = parser.parse_content(self._content)
        except ParseContentError as e:
            raise Exception(f"Failed to parse content: {e.message}")
        except (IOError, OSError, ValueError, EOFError) as e:
            raise Exception(f"Failed to read content: {str(e)}")

    def data(self) -> dict[str, str]:
        return self.data
