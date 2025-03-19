from enum import Enum
from pydantic import BaseModel, field_validator, ConfigDict, Field
from typing import Literal, List, Optional, Dict, Union, Annotated
import json
import logging
from datetime import datetime


class CommentType(str, Enum):
    issue = "issue"
    review = "review"
    filec = "filec"


class Comment(BaseModel):
    id: str
    type: CommentType
    comment_timestamp: Optional[datetime] = None
    commit_id: Optional[str] = None
    original_commit_id: Optional[str] = None
    user: Optional[str] = None
    comment: Optional[str] = None
    reference_filename: Optional[str] = None


class Commit(BaseModel):
    commit_sha: Optional[str] = None
    commit_author: Optional[str] = None
    commit_message: Optional[str] = None
    commit_timestamp: Optional[datetime] = None
    comments: Optional[List[Comment]] = Field(default_factory=list)


class FileObject(BaseModel):
    filename: str
    comments: Optional[List[Comment]] = Field(default_factory=list)


class PR(BaseModel):
    pr_number: int
    title: Optional[str] = None
    url: Optional[str] = None
    body: Optional[str] = None
    state: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    base_branch: Optional[str] = None
    final_merged_branch: Optional[str] = None
    commits: Optional[List[Commit]] = Field(default_factory=list)
    files: Optional[List[FileObject]] = Field(default_factory=list)
    comments: Optional[List[Comment]] = Field(default_factory=list)
    use_cases: Optional[List[Dict]] = Field(default_factory=list)


class PRDataset(BaseModel):
    PRs: Optional[list[PR]] = Field(default_factory=list)


if __name__ == "__main__":
    a_issue_comment = Comment(id="cid", type=CommentType.issue, comment="my_comnent")
    a_file_comment = Comment(
        id="cid",
        type=CommentType.filec,
        original_commit_id="original_commit_id",
        commit_id="commit_id",
        comment="my_comnent",
    )
    a_review_comment = Comment(
        id="cid", type=CommentType.review, commit_id="commit_id", comment="my_comnent"
    )

    a_file = FileObject(filename="file1", comments=[a_file_comment])
    a_file2 = FileObject(filename="file2")

    a_commit = Commit(
        commit_sha="708a45ea5ae43565383944135bf8a4fa7e14a952",
        commit_author="aheumaier",
        commit_message="Added samples for compliance testing with terraform-compliance",
        commit_timestamp="2020-06-11 08:57:02+00:00",
        comments=[a_review_comment, a_file_comment],
    )
    mypr = PR(
        pr_number=0,
        title="My title",
        url="myurl",
        body="body",
        state="closed",
        created_at="",
        updated_at="",
        base_branch="",
        final_merged_branch="",
        commits=[a_commit],
        files=[a_file, a_file2],
        comments=[a_issue_comment],
    )
    prdst = PRDataset(PRs=[mypr])
    with open("sample.json", "w") as outfile:
        outfile.write(prdst.model_dump_json(indent=4))
