from typing import List, Optional, Union
from langchain_core.output_parsers import PydanticOutputParser

from pr_graph.models import CodeReviewResponse, SecurityReviewResponse
from pr_graph.state import Comment, FileChange
from utils.logging_config import logger as log

class CommentOutputParser(PydanticOutputParser):
    def __init__(
            self, 
            response_object: Union[CodeReviewResponse, SecurityReviewResponse],
            modified_files: List[FileChange],
            comment_prefix: str = ""
        ):
        super().__init__(pydantic_object=response_object)

        self._modified_file_dict = {f.path:f.content for f in modified_files}
        self._comment_prefix = comment_prefix

    def parse(self, text: str) -> List[Comment]:
        objects = super().parse(text)

        comments: List[Comment] = []
        for issue in objects.issues:
            content = self._modified_file_dict.get(issue.filename, "")
            if content == "":
                raise ValueError(f"{issue.filename} is not found as a modified file")
            
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
    
    @staticmethod
    def _calculate_line_number(document: str, line: str) -> int:
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
