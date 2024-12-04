from typing import List, Union, Type

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.outputs import Generation

from pr_graph.state import CodeReviewResponse, SecurityReviewResponse
from pr_graph.state import Comment


class CommentOutputParser(PydanticOutputParser):
    """
    A parser for extracting comments from code review or security review responses.

    Attributes:
        response_object (Union[Type[CodeReviewResponse], Type[SecurityReviewResponse]]): The type of response object to parse.
        comment_prefix (str): A prefix to add to each comment.
    """

    def __init__(
            self,
            response_object: Union[Type[CodeReviewResponse], Type[SecurityReviewResponse]],
            comment_prefix: str = ""
        ):
        super().__init__(pydantic_object=response_object)
        self._comment_prefix = comment_prefix

    def parse_result(self, result: list[Generation], *, partial: bool = False) -> List[Comment]:
        """
        Parses the result from a list of Generation objects into a list of Comment objects.

        Args:
            result (list[Generation]): The list of Generation objects to parse.
            partial (bool): Whether the result is partial. Defaults to False.

        Returns:
            List[Comment]: A list of Comment objects extracted from the result.
        """
        objects = super().parse_result(result)

        comments: List[Comment] = []
        for issue in objects.issues:
            if issue.line_number == 0:
                continue

            comments.append(
                Comment(
                    filename=issue.filename,
                    line_number=issue.line_number,
                    comment=f"{self._comment_prefix} {issue.comment}",
                    status=issue.status
                )
            )
        return comments

    def get_format_instructions(self) -> str:

        return super().get_format_instructions()

    @property
    def _type(self) -> str:
        return "comment_parser"