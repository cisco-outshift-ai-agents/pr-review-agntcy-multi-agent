from typing import List, Union, Type

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.outputs import Generation

from pr_graph.models import CodeReviewResponse, SecurityReviewResponse
from pr_graph.state import Comment, FileChange


class CommentOutputParser(PydanticOutputParser):
    """A parser that converts LLM output into Comment objects.

    This parser extends PydanticOutputParser to handle code review responses and convert them into
    Comment objects that can be posted on pull requests. It processes review responses containing
    issues and maps them to specific files and line numbers.

    Args:
        response_object (Union[CodeReviewResponse, SecurityReviewResponse]): The Pydantic model class
            that defines the expected response structure.
        modified_files (List[FileChange]): List of files that were modified in the PR, containing
            file paths and contents.
        comment_prefix (str, optional): A prefix to add to all generated comments. Defaults to "".
    """
    def __init__(
            self,
            response_object: Union[Type[CodeReviewResponse], Type[SecurityReviewResponse]],
            comment_prefix: str = ""
        ):
        super().__init__(pydantic_object=response_object)
        self._comment_prefix = comment_prefix

    def parse_result(self, result: list[Generation], *, partial: bool = False) -> List[Comment]:
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
