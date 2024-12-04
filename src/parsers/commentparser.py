from typing import List, Optional, Union, override
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.outputs import Generation

from pr_graph.models import CodeReviewResponse, SecurityReviewResponse
from pr_graph.state import Comment, FileChange
from utils.logging_config import logger as log

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
            response_object: Union[CodeReviewResponse, SecurityReviewResponse],
            modified_files: List[FileChange],
            comment_prefix: str = ""
        ):
        super().__init__(pydantic_object=response_object)

        self._modified_file_dict = {f.path:f.content for f in modified_files}
        self._comment_prefix = comment_prefix

    def parse_result(self, result: list[Generation], *, partial: bool = False) -> List[Comment]:
        """Parse the LLM output into a list of Comment objects.

        This method processes the raw LLM output and converts it into structured Comment objects
        that can be used for pull request comments. It handles validation and mapping of review
        issues to specific files and line numbers.

        Args:
            result (list[Generation]): The raw output from the LLM containing review comments
            partial (bool, optional): Whether to allow partial parsing. Defaults to False.

        Returns:
            List[Comment]: A list of Comment objects containing the parsed review comments with
                          their associated files, line numbers and status.
        """
        objects = super().parse_result(result)

        comments: List[Comment] = []
        for issue in objects.issues:
            content = self._modified_file_dict.get(issue.filename, "")
            if content == "":
                log.error(f"{issue.filename} is not found as a modified file")
                continue
            
            try:
                line_number = self._calculate_line_number(content, issue.reviewed_line)
            except KeyError:
                log.error(f"line number of {issue.reviewed_line} can't be calculated in {issue.filename}")
                continue

            if line_number == 0:
                continue

            comments.append(
                Comment(
                    filename=issue.filename,
                    line_number=line_number,
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
    
    @staticmethod
    def _calculate_line_number(document: str, line: str) -> int:
        """Calculate the line number in a diff for a given line.

        This method takes a diff document and a specific line, and calculates the actual
        line number in the diff, accounting for added and removed lines. It skips lines
        that start with the opposite sign (+ or -) when counting to find the correct
        line number.

        Args:
            document (str): The diff document containing the changes
            line (str): The specific line to find, including the + or - prefix

        Returns:
            int: The calculated line number in the diff. Returns 0 if the line doesn't
                 start with + or -, raises KeyError if line not found.

        Raises:
            KeyError: If the specified line cannot be found in the document
        """
        if not line.startswith("+") and not line.startswith("-"):
            return 0

        if line.startswith("+"):
            skip_sign = "-"
        else:
            skip_sign = "+"

        line_number = 0
        for l in document.splitlines():
            if l.startswith(skip_sign):
                continue
            line_number += 1
            if l == line:
                return line_number

        raise KeyError("line not found")
