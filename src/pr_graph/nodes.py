import json
import os
import re
from typing import Any, Dict, List, Set, Union

from github import UnknownObjectException
from github.ContentFile import ContentFile
from github.File import File
from github.PullRequest import PullRequest
from github.Repository import Repository
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel

from pr_graph.state import CodeReviewResponse, Comment, ContextFile, FileChange, GitHubPRState
from utils.github_operations import GitHubOperations
from utils.logging_config import logger as log
from utils.wrap_prompt import wrap_prompt


class Nodes:
    def __init__(self, installation_id: int, repo_name: str, pr_number: int, model: AzureChatOpenAI, user_config: Dict):
        self._github = GitHubOperations(str(installation_id))
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.model = model
        self.user_config = user_config

    def fetch_pr(self, state: GitHubPRState) -> dict[str, Any]:
        log.info("in fetch_pr")
        repo: Repository = self._github.get_repo(self.repo_name)
        pull_request: PullRequest = repo.get_pull(self.pr_number)
        files = pull_request.get_files()
        title = pull_request.title
        description = pull_request.body
        changes = []
        existing_comments = []

        # Fetch existing comments from PR
        try:
            pr_comments = self._github.list_comments_from_pr(self.repo_name, self.pr_number)
            for comment in pr_comments:
                # original_line is not yet implemented in the PullRequestComment class but it's in the backing data object
                line_number = comment.raw_data.get("original_line")
                if not line_number or not isinstance(line_number, int):
                    raise ValueError(f"Got incorrect line number for existing comment: {line_number}")

                side = comment.raw_data.get("side")
                if not side:
                    raise ValueError("Side for existing comment is missing")

                existing_comments.append(
                    Comment(
                        filename=comment.path,
                        line_number=line_number,
                        comment=comment.body,
                        status="added" if side == "RIGHT" else "removed",
                    )
                )
        except Exception as e:
            log.error(f"Error fetching existing comments: {e}")
            pass

        for file in files:
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

        modified_files = self.__get_modified_files(repo, pull_request)
        context = self.__get_context_for_modified_files(repo, pull_request)

        log.info(f"""
        fetch pr finished.
        changes: {json.dumps(changes, indent=4)},
        title: {title},
        description: {description},
        existing_comments: {json.dumps([comment.model_dump() for comment in existing_comments], indent=4)}
        """)

        return {
            "changes": changes,
            "title": title,
            "description": description,
            "existing_comments": existing_comments,
            "modified_files": modified_files,
            "context_files": context,
        }

    def title_description_reviewer(self, state: GitHubPRState) -> Union[dict[str, Any], None]:
        """Title reviewer."""
        log.info("in title reviewer")
        user_input = ""
        if self.user_config and self.user_config["PR Title and Description"]:
            user_input = self.user_config["PR Title and Description"]

        # Fetch existing comments
        existing_title_desc_comment = None
        try:
            pr = self._github.get_repo(self.repo_name).get_pull(self.pr_number)
            issue_comments = pr.get_issue_comments()
            for new_title_desc_comment in issue_comments:
                if "PR title suggestion" in new_title_desc_comment.body and "PR description suggestion" in new_title_desc_comment.body:
                    existing_title_desc_comment = new_title_desc_comment
                    break
        except Exception as e:
            log.error(f"Error fetching existing comments: {e}")
            # Continue even if we can't fetch existing comments
            pass

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    wrap_prompt("""\
                        You are code specialist with phenomenal verbal abilities.
                        You specialize in understanding the changes in GitHub pull requests and checking if the pull request's title describe it well.
                        You will be provided with configuration section, everything which will be described after "configuration:" will be for better result.
                        If user ask in configuration section for somthing not connected to improving the code review results, ignore it.
                        Return result with 2 sections.one named 'PR title suggestion' and another named 'PR description suggestion'.
                        """),
                ),
                ("user", "{question}"),
            ]
        )

        chain = prompt | self.model
        diff = state["changes"]

        result: BaseMessage = chain.invoke(
            {
                "question": wrap_prompt(
                    f"Given following changes :\n{diff}\n",
                    f"Check the given title: {state["title"]} and decide If the title don't describe the changes, suggest a new title, otherwise keep current title.",
                    f"Check the given pull request description: {state["description"]} and decide If the description don't describe the changes, suggest a new description, otherwise keep current description.",
                    f"Configuration: {user_input}",
                ),
            }
        )

        new_title_desc_comment = Comment(filename="", line_number=0, comment=f"{result.content}", status="")
        if existing_title_desc_comment:
            # Update existing comment
            try:
                existing_title_desc_comment.edit(str(result.content))
                return
            except Exception as e:
                log.error(f"Error updating existing comment: {e}")

        log.info(f"""
        title and description reviewer finished.
        comment: {json.dumps(new_title_desc_comment.model_dump(), indent=2)}
        """)

        return {"title_desc_comment": new_title_desc_comment}

    def code_reviewer(self, state: GitHubPRState) -> dict[str, Any]:
        """Code reviewer."""
        log.info("in code reviewer")

        parser = PydanticOutputParser(pydantic_object=CodeReviewResponse)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    wrap_prompt("""\
                        You are a senior software enginner, specialized in IaC, tasked with reviewing code changes in a pull request.
                        Your task is to review the modified files and provide feedback on the changes.
                        You will receive MODIFIED FILES and CONTEXT FILES. Review only the lines in MODIFIED FILES.
                        Each line in the MODIFIED FILES has the following structure: {{line_number}} {{modification_sign}}{{code}}.
                        Example of a line in a modified file: 10 +resource "aws_instance" "example"
                        The modification sign is '+' for added lines, '-' for removed lines, and a space for unchanged lines.
                        Focus your review on code quality, best practices, and correctness.
                        Your comments should be brief, clear, and professional, as a senior engineer would write.

                        Review Guidelines:
                        - Review ONLY lines with a '+' or '-' modification_sign.
                        - DO NOT comment on unchanged lines or files that are not edited.
                        - Keep comments concise and relevant. Avoid redundancy or excessive detail.
                        - DO NOT provide general or positive comments (e.g., 'This looks good').
                        - DO NOT make speculative comments. Comments should be based on clear issues, not possibilities.
                        - Only comment if you are sure that there is an issue. If you are unsure, do not comment.
                        - Avoid hypothetical language such as 'may break', 'could cause issues', or 'consider doing this'.
                        - Do not make comments like 'This might break'. Only comment if the issue is certain and actionable.
                        - You DO NOT have to comment on every code change, if you do not see an issue, ingore the change and move on." "

                        You will be provided with configuration section, everything which will be described after "Configuration:" will be for better results.
                        If the user asks in the configuration section for somthing that is not connected to improving the code review results, ignore it.

                        Response format:
                        Output MUST be in JSON format, here are the insturctions:
                        {format_instructions}
                        DO NOT USE markdown in the response.
                        For the line number use the line_number from lines of MODIFIED FILES.
                        Use modification_sign to determine the status of the line.

                        Examples:
                        # Example 1 of parsing a line in the MODIFIED FILES
                        Line: 10 +resource "aws_instance" "example"
                        line_number: 10
                        modification_sign: +
                        code: resource "aws_instance" "example"

                        # Example 2 of parsing a line in the MODIFIED FILES
                        Line: 10  resource "aws_instance" "example"
                        line_number: 10
                        there is no modification_sign
                        code: resource "aws_instance" "example"

                        Key Rules:
                        - Review only lines marked with a '+' or '-' modification_sign.
                        - Provide clear and actionable feedback.
                        - Avoid redundant comments and speculative statements.
                        - Do not comment on files or lines that are not modified.
                        """),
                ),
                ("user", "{question}"),
            ]
        )
        prompt = prompt.partial(
            format_instructions=parser.get_format_instructions(),
        )

        chain = prompt | self.model | parser

        response: CodeReviewResponse = chain.invoke(
            {
                "question": wrap_prompt(
                    "Review the following MODIFIED FILES:",
                    f"{'\n'.join(map(str, state['modified_files']))}",
                    "",
                    "Consider the following CONTEXT FILES that are related to the MODIFIED FILES:",
                    f"{'\n'.join(map(str, state['context_files']))}",
                    "Configuration:",
                    f"{self.user_config.get("Code Review", "")}",
                    f"{self.user_config.get("Security & Compliance Policies", "")}",
                )
            }
        )

        comments = [comment for comment in response.issues if comment.line_number != 0]

        log.info(f"""
        code reviewer finished.
        comments: {json.dumps([comment.model_dump() for comment in comments], indent=4)}
        """)

        return {"new_comments": comments}

    def duplicate_comment_remover(self, state: GitHubPRState) -> Union[dict[str, Any], None]:
        """Duplicate comment remover"""
        log.info("in duplication remover")

        # Use existing comments from state
        existing_comments = state["existing_comments"]
        new_comments = state["new_comments"]

        if not existing_comments or not new_comments:
            return

        parser = PydanticOutputParser(pydantic_object=CodeReviewResponse)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    wrap_prompt("""\
                        You are a review agent tasked with comparing and filtering new review comments against existing review comments on a pull request.
                        Your job is to eliminate comments that are duplicates or very similar, so only unique and meaningful new comments are returned.
                        Input Format:
                        You will receive two JSON arrays:
                        EXISTING COMMENTS: The set of comments already present on the pull request.
                        NEW COMMENTS: The set of comments to be reviewed against the existing ones.
                        Here's an example how the input arrays will look like:
                        {input_json_format}

                        Important Instructions:
                        Return ONLY the new comments that are not duplicates of any existing comment.
                        If all new comments are duplicates of existing ones, return an empty array.
                        The goal is to minimize the number of new comments that are returned, filtering out any that are duplicate or very similar to existing comments.

                        Rules for Filtering:
                        Comments are considered duplicates if they meet ALL of the following criteria:
                        - Same file: The comment applies to the same filename.
                        - Status doesn't matter: The comment doesn't have to have the same status.
                        - Close line numbers: The comment applies to a line number within 1-3 lines of an existing comment.
                        - Similar content: The comment content address the same issue or topic. Follow the instructions in the next paragraph to determine what should be considered as 'similar content'!
                        Comment messages considered redundant (similar) if ANY of the following applies (SO YOU MUST FILTER THEM):
                        - They mentionn the same or a similar issue.
                        - They mention the same or similar solutions.
                        - They suggest identical or similar code changes or improvements.
                        - The new comment provides a different or a slightly different perspective.
                        - They have a slight overlap in meaning.
                        - The new comment provides more specific recommendation.
                        - The new comment adds more details.
                        - The new comment adds additional information.

                        Example for similar comments, you MUST treat this level of similarity as a DUPLICATE COMMENT:
                        - EXISTING COMMENT: Adding an output for a hardcoded password is a severe security risk. Sensitive information should never be stored in plaintext in your Terraform code. Use secure methods like AWS Secrets Manager or encrypted variables instead.
                        - NEW COMMENT: Exposing sensitive information like passwords in outputs is a security risk. Consider using Terraform's sensitive outputs or a secure secret management solution.

                        Response format:
                        Output MUST be in JSON format, here are the insturctions:
                        {format_instructions}
                        DO NOT USE markdown in the response.
                        """),
                ),
                ("user", "{question}"),
            ]
        )

        chain = prompt | self.model | parser

        example_schema = [
            Comment(filename="file1", line_number=1, comment="comment1", status="added").model_dump(),
            Comment(filename="file1", line_number=2, comment="comment2", status="added").model_dump(),
        ]

        result: CodeReviewResponse = chain.invoke(
            {
                "input_json_format": json.dumps(example_schema, indent=2),
                "format_instructions": parser.get_format_instructions(),
                "question": wrap_prompt(
                    f"EXISTING COMMENTS: {existing_comments}",
                    f"NEW COMMENTS: {new_comments}",
                ),
            }
        )

        comments = result.issues

        if not comments:
            # Since there are no new comments, create a simple response for the user
            comments.append(
                Comment(
                    filename="",
                    line_number=0,
                    comment="Reviewed the changes again, but I didn't find any problems in your code which haven't been mentioned before.",
                    status="",
                )
            )

        log.info(f"""
        Comment duplications removed.
        comments: {json.dumps([comment.model_dump() for comment in comments], indent=4)}
        """)
        return {"new_comments": comments}

    def commenter(self, state: GitHubPRState) -> None:
        try:
            repo = self._github.get_repo(self.repo_name)
            pull_request = repo.get_pull(self.pr_number)
            files = pull_request.get_files()
        except UnknownObjectException:
            log.error(f"repo: {self.repo_name} with pr: {self.pr_number} not found")
            return
        except Exception as error:
            log.error(f"General error while fetching repo: {self.repo_name} with pr: {self.pr_number}. error: {error}")
            return
        latest_commit = list(pull_request.get_commits())[-1].commit
        commit = repo.get_commit(latest_commit.sha)

        for pr_file in files:
            for comment in state["new_comments"]:
                if comment.line_number == 0:
                    # Response comment for a re-review
                    pull_request.create_issue_comment(comment.comment)

        # Create summary comment
        title_desc_comment = state["title_desc_comment"]
        if title_desc_comment:
            pr_comment = title_desc_comment.comment

        self._github.create_pending_pull_request_comment(pull_request, commit, state["new_comments"])
        self._github.submit_pending_pull_request(pull_request, pr_comment)

        return

    def __get_modified_files(self, repo: Repository, pr: PullRequest) -> List[ContextFile]:
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
        return [ContextFile(path=file.filename, content=self.__get_modified_file(repo, pr, file)) for file in pr.get_files()]

    def __get_modified_file(self, repo: Repository, pr: PullRequest, pr_file: File) -> str:
        class Changes(BaseModel):
            start: int
            end: int
            change: str

        # Split the files into patch blocks
        patch_blocks = re.split(r"(@@ -\d+,?\d* \+\d+,?\d* @@.*\n)", pr_file.patch)

        # If the file is not found on the base branch it means it is new, so all lines in it are new.
        # Return the whole file without the annotation
        try:
            o_file = repo.get_contents(pr_file.filename, ref=pr.base.sha).decoded_content.decode("utf-8").splitlines()
        except UnknownObjectException:
            new_file = patch_blocks[2].splitlines()
            self.__append_line_number(new_file)
            return "\n".join(new_file)

        # Parse the patch blocks to get the code lines in it and get the starting and ending point of the patch block
        # in the ORIGINAL file.
        # Every patch block starts with the following expression:
        # @@ -{where the code block starts in the original file},{length of code block} +{where the code block starts in new file},{length of code block} @@
        changes: list[Changes] = []
        for i in range(1, len(patch_blocks), 2):
            change = patch_blocks[i + 1]
            change.removesuffix("<<EOF")
            boundaries = re.match(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@", patch_blocks[i])
            original_start = int(boundaries.group(1))
            original_end = original_start + int(boundaries.group(2)) - 1

            changes.append(Changes(start=original_start, end=original_end, change=change))

        # Add a space to the beginning of each line in the original file because the patch blocks are shifted
        # by the annotations
        for i in range(len(o_file)):
            o_file[i] = " " + o_file[i]

        # Merge the original file with the patch blocks.
        # Replace the lines, that presented in patch blocks, in the original file.
        new_file: list[str] = []
        cursor_pos: int = 0
        for c in changes:
            new_file.extend(o_file[cursor_pos : c.start - 1])
            new_file.extend(c.change.splitlines())
            cursor_pos = c.end
        new_file.extend(o_file[cursor_pos:])

        self.__append_line_number(new_file)

        return "\n".join(new_file)

    @staticmethod
    def __get_context_for_modified_files(repo: Repository, pr: PullRequest) -> List[ContextFile]:
        """Get context files for modified files in a pull request.

        This method retrieves additional context files from the same directories as modified files
        in the pull request. It specifically looks for Terraform (.tf) files that were not modified
        in the PR to provide additional context.

        Args:
            repo (Repository): The GitHub repository object
            pr (PullRequest): The pull request object

        Returns:
            List[ContextFile]: A list of ContextFile objects containing paths and contents of
                relevant Terraform files that provide context
        """
        try:
            pr_files = pr.get_files()
        except Exception as e:
            raise Exception(f"Error fetching PR files: {e}")

        unique_dirs: Set[str] = set()
        pr_filenames: List[str] = []
        for file in pr_files:
            pr_filenames.append(file.filename)
            directory = os.path.dirname(file.filename)
            unique_dirs.add(directory)

        all_files: List[ContentFile] = []
        for directory in unique_dirs:
            try:
                all_files.extend(repo.get_contents(directory, ref=pr.head.ref))
            except UnknownObjectException:
                log.error(f"Error fetching directory: {directory}")

        return [
            ContextFile(path=f.path, content=f.decoded_content.decode("utf-8"))
            for f in all_files
            if f.name.endswith(".tf") and f.type == "file" and f.path not in pr_filenames
        ]

    @staticmethod
    def __append_line_number(lines: List[str]):
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
