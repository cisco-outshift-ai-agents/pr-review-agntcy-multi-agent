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
