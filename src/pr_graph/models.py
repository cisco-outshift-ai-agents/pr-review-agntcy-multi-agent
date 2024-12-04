
from typing import List

from pydantic import BaseModel, Field


class CodeReviewIssue(BaseModel):
    filename: str = Field(
        description="The name of the file where the issue was found. It can be found at the beginning of the file. Must be the full path of the file.")
    line_number: int = Field(
        description="The line number where the issue was found. It can be found at the beginning of the line.")
    comment: str = Field(description="The review comment describing the issue. Must be placed here without markdown formatting.")
    status: str = Field(
        description="Status of the line - must be either 'added' (for lines added in the PR) or 'removed' (for lines removed in the PR). Must be 'added' if the"
    )

class CodeReviewResponse(BaseModel):
    issues: List[CodeReviewIssue] = Field(description="List of code review issues found")


class SecurityReviewResponse(BaseModel):
    issues: List[CodeReviewIssue] = Field(description="List of security review issues found")