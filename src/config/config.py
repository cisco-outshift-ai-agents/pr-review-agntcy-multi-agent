from typing import IO
from config.parser_mixin import ParserMixin, ParseContentError


class Config:
    """
    Config class to read and parse configuration using the provided reader and parser. Parser must implement the
    ParserMixin interface which defines the parse_content method.
    """

    def __init__(self, reader: IO, parser: ParserMixin):
        # Private attribute to hold raw content
        self._content = reader.read()

        try:
            # Parse the content using the provided parser
            self.data = parser.parse_content(self._content)
        except ParseContentError as e:
            raise Exception(f"Failed to parse content: {e.message}")

    def data(self) -> dict[str, str]:
        return self.data


if __name__ == "__main__":
    # Example usage
    from md_parser import MarkdownParser

    with open("PRCoach_CONFIG.md", "r", encoding="utf-8") as file:
        config = Config(file, MarkdownParser())
        print(config.data["Code Review"])
