from pydantic import BaseModel, Field
from typing import List


class Comment(BaseModel):
    filename: str = Field(
        description="The name of the file where the issue was found. Can be found at the beginning of the file. MUST BE the full path to the file."
    )
    line_number: int = Field(description="The line number where the issue was found.")
    comment: str = Field(description="The review comment describing the issue. Must be placed here without markdown formatting.")
    status: str = Field(
        description="Status of the line - must be either 'added' (for lines added in the PR, marked with '+') or 'removed' (for lines removed in the PR, marked with '-'). Can be found at the beginning of the line after the line number."
    )


class Comments(BaseModel):
    issues: List[Comment] = Field(description="List of code review issues found")


class ContextFile(BaseModel):
    path: str
    content: str

    def __str__(self) -> str:
        return f"File: {self.path}\n```\n{self.content}\n```"

    def __repr__(self) -> str:
        return self.__str__()
