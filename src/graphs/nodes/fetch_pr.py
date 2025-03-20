import json
import os
import re
from typing import List, Set

from github import GithubException, UnknownObjectException
from github.ContentFile import ContentFile
from github.File import File
from pydantic import BaseModel

from graphs.states import FileChange, GitHubPRState
from utils.logging_config import logger as log
from utils.models import ReviewComment, IssueComment, ContextFile
from .contexts import DefaultContext


class FetchPR:
    terraform_file_types_review_allowed = (".tf", ".tfvars")
    terraform_file_types_push_forbidden = (".tfplan", ".tfstate")
    file_type_warning_template = "The following files are not suggested being pushed to the repository, since those likely contain sensitive data:"

    def __init__(self, context: DefaultContext, name: str = "fetch_pr"):
        self.context = context
        self.name = name
        self.pr_files: list[File] = []
        self.pr_files_to_review: list[File] = []

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name}: called")

        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHubOperations is not set in the context")

        try:
            total_files = self.context.github.pr.get_files()
            self.pr_files = total_files
        except Exception as e:
            raise Exception(f"Error fetching PR files: {e}") from e

        filenames_not_to_review: Set[str] = set()
        new_issue_comments: List[IssueComment] = []

        for file in self.pr_files:
            filename = file.filename
            if filename.endswith(self.terraform_file_types_review_allowed):
                # this file should be reviewed
                self.pr_files_to_review.append(file)

                if ".tfvars" in filename:
                    # warning about pushing .tfvars files to the repo
                    tfvars_warning_text = "You are about to push .tfvars file(s) to the repo. I always check these file types, but please make sure for yourself no sensitive data is published on GitHub."
                    tfvars_warning_comment = IssueComment(body=tfvars_warning_text, conditions=[tfvars_warning_text])
                    new_issue_comments.append(tfvars_warning_comment)

            elif filename.endswith(self.terraform_file_types_push_forbidden):
                # this file should not be reviewed, but we should warn the user about the risks pushing it to the repo
                filenames_not_to_review.add(filename)
            else:
                # this file should not be reviewed
                pass

        title = self.context.github.pr.title
        description = self.context.github.pr.body
        changes = []
        existing_review_comments = []

        # Fetch existing review comments from PR
        try:
            review_comments = self.context.github.pr.get_review_comments()
            for comment in review_comments:
                # original_line is not yet implemented in the PullRequestComment class but it's in the backing data object
                line_number = comment.raw_data.get("original_line")
                if not line_number or not isinstance(line_number, int):
                    raise ValueError(f"Got incorrect line number for existing comment: {line_number}")

                side = comment.raw_data.get("side")
                if not side:
                    raise ValueError("Side for existing comment is missing")

                existing_review_comments.append(
                    ReviewComment(
                        filename=comment.path,
                        line_number=line_number,
                        comment=comment.body,
                        status="added" if side == "RIGHT" else "removed",
                    )
                )
        except Exception as e:
            log.error(f"Error fetching existing review comments: {e}")
            pass

        for file in self.pr_files_to_review:
            filename = file.filename
            patch = file.patch

            if patch:
                # Split the patch into lines
                lines = patch.split("\n")

                start_line_removed = None
                start_line_added = None
                current_change = None

                for line_number in lines:
                    # Match the line number information
                    if line_number.startswith("@@"):
                        match = re.search(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line_number)
                        if match:
                            start_line_removed = int(match.group(1))
                            start_line_added = int(match.group(2))
                            current_change = None
                    elif line_number.startswith("-") and start_line_removed is not None:
                        if current_change and current_change["status"] == "removed":
                            current_change["changed_code"] += "\n" + line_number
                        else:
                            if current_change:
                                changes.append(current_change)
                            current_change = FileChange(filename=filename, start_line=start_line_removed, changed_code=line_number, status="removed")
                        start_line_removed += 1
                    elif line_number.startswith("+") and start_line_added is not None:
                        if current_change and current_change["status"] == "added":
                            current_change["changed_code"] += "\n" + line_number
                        else:
                            if current_change:
                                changes.append(current_change)
                            current_change = FileChange(filename=filename, start_line=start_line_added, changed_code=line_number, status="added")
                        start_line_added += 1
                    elif start_line_removed is not None and start_line_added is not None:
                        if current_change:
                            changes.append(current_change)
                            current_change = None
                        start_line_removed += 1
                        start_line_added += 1

        try:
            existing_issue_comments = self.context.github.pr.get_issue_comments()

        except Exception as e:
            log.error(f"Error fetching existing comments: {e}")
            # Continue even if we can't fetch existing comments
            pass

        # TODO: Currently we don't deal with modified files.
        # modified_files = self.__get_modified_files()
        context_files = self.__get_context_for_modified_files()

        if filenames_not_to_review:
            wrong_files_to_push_message = (
                self.file_type_warning_template
                + f"""
            {"\n - " + " \n  - ".join(filenames_not_to_review)}
            """
            )
            new_filetype_restriction_comment = IssueComment(body=wrong_files_to_push_message, conditions=[self.file_type_warning_template])
            new_issue_comments.append(new_filetype_restriction_comment)

        log.debug(f"""
        fetch pr finished.
        changes: {json.dumps(changes, indent=4)},
        title: {title},
        description: {description},
        new_issue_comments: ", \n".join([comment.body for comment in new_issue_comments]),
        issue_comments: ", \n".join([comment.body for comment in existing_issue_comments]),
        review_comments: {json.dumps([comment.model_dump() for comment in existing_review_comments], indent=4)}
        """)

        return {
            "changes": changes,
            "title": title,
            "description": description,
            "review_comments": existing_review_comments,
            "issue_comments": existing_issue_comments,
            "new_issue_comments": new_issue_comments,
            # "modified_files": modified_files,
            "context_files": context_files,
        }

    def __get_modified_files(self) -> List[ContextFile]:
        """Get a list of modified files with annotated content from a pull request.
            This method retrieves all files from a pull request and merge the files' patch with the original file content
            to provide a full context of the changes made in the PR. The returned object's content property includes
            the full file with diff annotations (+ for additions, - for deletions) showing the changes made in the PR.
            Args:
            repo (Repository): The GitHub repository object
            pr (PullRequest): The pull request object to get modified files from
        Returns:
            List[ContextFile]: List of ContextFile objects containing the path and annotated content
                               of each modified file
        """

        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHubOperations is not set in the context")

        return [ContextFile(path=file.filename, content=self.__get_modified_file(file)) for file in self.pr_files_to_review]

    def __get_modified_file(self, pr_file: File) -> str:
        class Changes(BaseModel):
            start: int
            end: int
            change: str

        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHubOperations is not set in the context")

        if not pr_file.patch:
            # If it's an empty file or a deleted file or a moved file, then there is no patch. This way the file remains part of the diff, but it will be marked empty.
            return ""

        # Split the files into patch blocks
        patch_blocks = re.split(r"(@@ -\d+,?\d* \+\d+,?\d* @@.*\n)", pr_file.patch)
        # If the file is not found on the base branch it means it is new, so all lines in it are new.
        # Return the whole file without the annotation
        try:
            contents = self.context.github.repo.get_contents(pr_file.filename, ref=self.context.github.pr.base.sha)
            if isinstance(contents, list):
                o_file = contents[0].decoded_content.decode("utf-8").splitlines()
            else:
                o_file = contents.decoded_content.decode("utf-8").splitlines()
        except GithubException as e:
            if e.status == 404:
                new_file = patch_blocks[2].splitlines()
                self.__append_line_number(new_file)
                return "\n".join(new_file)
            raise e
        # Parse the patch blocks to get the code lines in it and get the starting and ending point of the patch block
        # in the ORIGINAL file.
        # Every patch block starts with the following expression:
        # @@ -{where the code block starts in the original file},{length of code block} +{where the code block starts in    new file},{length of code block} @@
        changes: list[Changes] = []
        for i in range(1, len(patch_blocks), 2):
            change = patch_blocks[i + 1]
            change.removesuffix("<<EOF")
            boundaries = re.match(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@", patch_blocks[i])
            if not boundaries:
                continue
            original_start = int(boundaries.group(1))
            original_end = original_start + int(boundaries.group(2)) - 1
            changes.append(Changes(start=original_start, end=original_end, change=change))
        # Add a space to the beginning of each line in the original file because the patch blocks are shifted
        # by the annotations
        for i in range(len(o_file)):
            o_file[i] = " " + o_file[i]
        # Merge the original file with the patch blocks.
        # Replace the lines, that presented in patch blocks, in the original file.
        merged_file: list[str] = []
        cursor_pos: int = 0
        for c in changes:
            merged_file.extend(o_file[cursor_pos : c.start - 1])
            merged_file.extend(c.change.splitlines())
            cursor_pos = c.end
        merged_file.extend(o_file[cursor_pos:])
        self.__append_line_number(merged_file)
        return "\n".join(merged_file)

    def __get_context_for_modified_files(self) -> List[ContextFile]:
        """Get context files for modified files in a pull request.
        This method retrieves additional context files from the same directories as modified files
        in the pull request. It specifically looks for Terraform (.tf) files that were not modified
        in the PR to provide additional context.
        Returns:
            List[ContextFile]: A list of ContextFile objects containing paths and contents of
                relevant Terraform files that provide context
        """
        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHubOperations is not set in the context")

        unique_dirs: Set[str] = set()
        pr_filenames: List[str] = []
        for file in self.pr_files_to_review:
            pr_filenames.append(file.filename)
            directory = os.path.dirname(file.filename)
            unique_dirs.add(directory)
        all_files: List[ContentFile] = []
        for directory in unique_dirs:
            try:
                contents = self.context.github.repo.get_contents(directory, ref=self.context.github.pr.head.ref)
                if isinstance(contents, list):
                    all_files.extend(contents)
                else:
                    all_files.append(contents)
            except UnknownObjectException:
                log.error(f"Error fetching directory: {directory}")
        return [
            ContextFile(path=f.path, content=f.decoded_content.decode("utf-8"))
            for f in all_files
            if os.path.splitext(f.name)[1] in self.terraform_file_types_review_allowed and f.type == "file"
            # TODO: If we want to refactor how we get the files for the code review nodes
            # if f.name.endswith(".tf") and f.type == "file" and f.path not in pr_filenames
        ]

    def __append_line_number(self, lines: List[str]):
        """
        Append line numbers to modified lines. Line numbers reflect the line number of a removed line in the original file.
        And the line number of an added line in the new file. Lines that are unchanged are assigned a line number of 0.
        The function modifies the input list in place.
        Args:
            lines (List[str]): The list of lines to process.
        """
        added_line_idx = 0
        removed_line_idx = 0
        for i in range(len(lines)):
            if lines[i].startswith("+"):
                added_line_idx += 1
                lines[i] = f"{str(added_line_idx).rjust(4)} {lines[i]}"
            elif lines[i].startswith("-"):
                removed_line_idx += 1
                lines[i] = f"{str(removed_line_idx).rjust(4)} {lines[i]}"
            else:
                added_line_idx += 1
                removed_line_idx += 1
                lines[i] = f"{'0'.rjust(4)} {lines[i]}"
