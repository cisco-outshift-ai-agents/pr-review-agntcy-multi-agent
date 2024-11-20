class ParserMixin:
    """
    ParserMixin interface to define the parse_content method which must be implemented by the parser classes.
    """

    def parse_content(self, content: str) -> dict[str, str]:
        raise NotImplementedError("Subclasses must implement the parse_content method.")


class ParseContentError(Exception):
    """Exception raised when there is an error in parsing content."""

    def __init__(self, message: str, content: str):
        super().__init__(message)
        self.content = content
