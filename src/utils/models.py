from pydantic import BaseModel, Field
from typing import List


class Comment(BaseModel):
    filename: str
    line_number: int
    comment: str
    status: str


class Comments(BaseModel):
    issues: List[Comment] = Field(description="List of code review issues found")


class ContextFile(BaseModel):
    path: str
    content: str

    def __str__(self) -> str:
        return f"File: {self.path}\n```\n{self.content}\n```"

    def __repr__(self) -> str:
        return self.__str__()
