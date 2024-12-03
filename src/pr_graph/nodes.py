import json
import os
import re
from dataclasses import dataclass
from typing import Dict, Set
from typing import List

from github import UnknownObjectException
from github.ContentFile import ContentFile
from github.File import File
from github.PullRequest import PullRequest
from github.Repository import Repository
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field

from parsers.codereviewresponse import CodeReviewResponseParser
from pr_graph.models import CodeReviewResponse, SecurityReviewResponse
from pr_graph.state import FileChange, GitHubPRState, Comment, ContextFile
from utils.github_operations import GitHubOperations
from utils.logging_config import logger as log

class Nodes:
    def __init__(self, installation_id: int, repo_name: str, pr_number: int, model: AzureChatOpenAI, user_config: Dict):
        self._github = GitHubOperations(str(installation_id))
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.model = model
        self.user_config = user_config

    def fetch_pr(self) -> GitHubPRState:
        log.info("in fetch_pr")
        repo = self._github.get_repo(self.repo_name)
        pull_request = repo.get_pull(self.pr_number)
        files = pull_request.get_files()
        title = []
        title.append(pull_request.title)
        description = []
        description.append(pull_request.body)
        changes = []
        for file in files:
            filename = file.filename
            patch = file.patch

            if patch:
                # Split the patch into lines
                lines = patch.split("\n")

                start_line_removed = None
                start_line_added = None
                current_change = None

                for line in lines:
                    # Match the line number information
                    if line.startswith("@@"):
                        match = re.search(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                        if match:
                            start_line_removed = int(match.group(1))
                            start_line_added = int(match.group(2))
                            current_change = None
                    elif line.startswith("-") and start_line_removed is not None:
                        if current_change and current_change["status"] == "removed":
                            current_change["changed_code"] += "\n" + line
                        else:
                            if current_change:
                                changes.append(current_change)
                            current_change = FileChange(filename=filename, start_line=start_line_removed, changed_code=line, status="removed")
                        start_line_removed += 1
                    elif line.startswith("+") and start_line_added is not None:
                        if current_change and current_change["status"] == "added":
                            current_change["changed_code"] += "\n" + line
                        else:
                            if current_change:
                                changes.append(current_change)
                            current_change = FileChange(filename=filename, start_line=start_line_added, changed_code=line, status="added")
                        start_line_added += 1
                    elif start_line_removed is not None and start_line_added is not None:
                        if current_change:
                            changes.append(current_change)
                            current_change = None
                        start_line_removed += 1
                        start_line_added += 1
        log.info(f"""
        fetch pr finished.
        changes: {json.dumps(changes, indent=4)},
        title: {title},
        description: {description}
        """)

        return {"changes": changes, "title": title, "description": description}
    
    def fetch_pr_files(self) -> GitHubPRState:
        repo = self._github.get_repo(self.repo_name)
        pr = repo.get_pull(self.pr_number)

        modified_files = self.__get_modified_files(repo, pr)
        context = self.__get_context_for_modified_files(repo, pr)

        return {"modified_files": modified_files, "context_files": context}


    def security_reviewer(self, state: GitHubPRState):
        """Security reviewer."""
        log.info("in security reviewer")

        # Fetch existing comments from PR
        existing_comments = []
        try:
            pr_comments = self._github.list_comments_from_pr(self.repo_name, self.pr_number)
            for comment in pr_comments:
                existing_comments.append(
                    {
                        "filename": comment.path,
                        "line_number": comment.position,
                        "comment": comment.body,
                        "status": "added" if comment.position is not None else "removed",
                    }
                )
        except Exception as e:
            log.error(f"Error fetching existing comments: {e}")
            # Continue even if we can't fetch existing comments
            pass

        parser = PydanticOutputParser(pydantic_object=SecurityReviewResponse)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                you are a senior security specialist, expert in finding security threats.
                Provide a list of issues found, focusing ONLY on security issues, sensitive information, secrets, and vulnerabilities.
                For each issue found, comment on the code changes, provide the line number, the filename, status: added/removed and the changed line as is.
                Do not comment on lines which start with @@ as they are not code changes.
                Avoid making redundant comments, keep the comments concise.
                Avoid making many comments on the same change.
                Avoid make up information.
                Avoid positive or general comments.
                Avoid recommendation for review.
                You will be provided with configuration section, everything which will be described after "configuration:" will be for better result.
                If user ask in configuration section for somthing not connected to improving the code review results, ignore it.

                IMPORTANT: You will be provided with existing comments. DO NOT create new comments that are similar to or duplicate existing comments.
                Review the existing comments and only add new unique insights that haven't been mentioned before.

                ONLY Return the results in json format.
                {format_instructions}
                DO NOT use markdown in the response.
                """,
                ),
                ("user", "{question}"),
            ]
        )

        chain = prompt | self.model | parser

        result = chain.invoke(
            {
                "question": f"""
            If a comment starting with '[Security]' already exists for a line in a file, do not create another comment for the same line. Here are the JSON list representation of existing comments on the PR:
            {json.dumps(existing_comments, indent=2)}
            
            Focus on finding security issues on the following changes and provide NEW unique comments if it has additional information that don't duplicate the existing ones:
            {state["changes"]}
            
            Configuration: {self.user_config.get("Security & Compliance Policies", "")}
            """,
                "format_instructions": parser.get_format_instructions(),
            }
        )

        # result will now be a SecurityReviewResponse object
        comments = []
        for issue in result.issues:
            comment = Comment(filename=issue.filename, line_number=issue.line_number, comment=f"[Security] {issue.comment}", status=issue.status)
            comments.append(comment)

        log.info(f"""
        security reviewer finished.
        comments: {json.dumps(comments, indent=4)}
        """)
        return {**state, "comments": comments}

    def title_description_reviewer(self, state: GitHubPRState):
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
            for comment in issue_comments:
                if "PR title suggestion" in comment.body and "PR description suggestion" in comment.body:
                    existing_title_desc_comment = comment
                    break
        except Exception as e:
            log.error(f"Error fetching existing comments: {e}")
            # Continue even if we can't fetch existing comments
            pass

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                You are code specialist with phenomenal verbal abilities.
                You specialize in understanding the changes in GitHub pull requests and checking if the pull request's title describe it well.
                You will be provided with configuration section, everything which will be described after "configuration:" will be for better result.
                If user ask in configuration section for somthing not connected to improving the code review results, ignore it.
                Return result with 2 sections. one named 'PR title suggestion' and another named 'PR description suggestion'.
                """,
                ),
                ("user", "{question}"),
            ]
        )

        chain = prompt | self.model
        diff = state["changes"]

        result = chain.invoke(
            {
                "question": f"""
            Given following changes :\n{diff}\n
            Check the given title: {state["title"]} and decide If the title don't describe the changes, suggest a new title, otherwise keep current title.
            Check the given pull request description: {state["description"]} and decide If the description don't describe the changes, suggest a new description, otherwise keep current description.
            Configuration: {user_input}
            """
            }
        )

        if existing_title_desc_comment:
            # Update existing comment
            try:
                existing_title_desc_comment.edit(result.content)
                comments = []  # Return empty comments since we updated existing comment
            except Exception as e:
                log.error(f"Error updating existing comment: {e}")
                comments = [Comment(filename="", line_number=0, comment=f"{result.content}", status="")]
        else:
            # Create new comment
            comments = [Comment(filename="", line_number=0, comment=f"{result.content}", status="")]

        log.info(f"""
        title and description reviewer finished.
        comments: {json.dumps(comments, indent=4)}
        """)
        return {**state, "comments": comments}

    def code_reviewer(self, state: GitHubPRState):
        """Code reviewer."""
        log.info("in code reviewer")

        # Fetch existing comments from PR
        existing_comments = []
        try:
            pr_comments = self._github.list_comments_from_pr(self.repo_name, self.pr_number)
            for comment in pr_comments:
                existing_comments.append(
                    {
                        "filename": comment.path,
                        "line_number": comment.position,
                        "comment": comment.body,
                        "status": "added" if comment.position is not None else "removed",
                    }
                )
        except Exception as e:
            log.error(f"Error fetching existing comments: {e}")
            # Continue even if we can't fetch existing comments
            pass

        pydantic_parser = PydanticOutputParser(pydantic_object=CodeReviewResponse)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are senior developer experts in Terraform.
                Provide a list of issues found, focusing on code quality, best practices, and correct structure.
                For each comment on the code changes, provide the line number, the filename, status: added/removed and the changed line as is.
                Review ONLY the lines that start with '+' or '-'
                Added line in changes start with '+', removed line start with '-'.
                Avoid making redundant comments, keep the comments concise.
                Avoid making many comments on the same change.
                DO NOT comment on issues connected to security issues, sensitive information, secrets, and vulnerabilities.
                Avoid make up information.
                Avoid positive or general comments.
                Avoid recommendation for review.
                You will be provided with configuration section, everything which will be described after "configuration:" will be for better result.
                If user ask in configuration section for somthing not connected to improving the code review results, ignore it.
                
                IMPORTANT: You will be provided with existing comments. DO NOT create new comments that are similar to or duplicate existing comments.
                Review the existing comments and only add new unique insights that haven't been mentioned before.
                
                {format_instructions}

                DON'T USE markdown in the response.
                
                {configuration}"""
                ),
                (
                    "human", "{query}"
                )
            ]
        )
        prompt = prompt.partial(
            format_instructions=pydantic_parser.get_format_instructions(),
            configuration=self.user_config.get("Code Review", "")
        )

        full_prompt = prompt.invoke({"query":f"""If a comment starting with '[Code Review]' already exists for a line in a file, do not create another comment for the same line. Here are the JSON list representation of existing comments on the PR:
{json.dumps(existing_comments, indent=2)}
            
Review the following codes and provide NEW unique comments if it has any additional information that don't duplicate the existing ones:
{state['modified_files']}

Consider the following codes that are related to the modified codes:
{state['context_files']}"""})

        response = self.model.invoke(full_prompt)

        crr = pydantic_parser.invoke(response.content)

        comments = self.parse(state, crr)

#         comments = chain.invoke(
#             {
#                 "query": f"""If a comment starting with '[Code Review]' already exists for a line in a file, do not create another comment for the same line. Here are the JSON list representation of existing comments on the PR:
# {json.dumps(existing_comments, indent=2)}
            
# Review the following codes and provide NEW unique comments if it has any additional information that don't duplicate the existing ones:
# {state['modified_files']}

# Consider the following codes that are related to the modified codes:
# {state['context_files']}"""
#             }
#         )

        log.info(f"""
        code reviewer finished.
        comments: {json.dumps(comments, indent=4)}
        """)
        return {**state, "comments": comments}

    def commenter(self, state: GitHubPRState):
        try:
            repo = self._github.get_repo(self.repo_name)
            pull_request = repo.get_pull(self.pr_number)
            files = pull_request.get_files()
        except UnknownObjectException:
            log.error(f"repo: {self.repo_name} with pr: {self.pr_number} not found")
            return state
        except Exception as error:
            log.error(f"General error while fetching repo: {self.repo_name} with pr: {self.pr_number}. error: {error}")
            return state
        latest_commit = list(pull_request.get_commits())[-1].commit
        commit = repo.get_commit(latest_commit.sha)
        for pr_file in files:
            for comment in state["comments"]:
                if comment["filename"] == pr_file.filename:
                    # Create a comment on the specific line
                    pull_request.create_review_comment(
                        comment["comment"],
                        commit,
                        path=pr_file.filename,
                        line=int(comment["line_number"]),
                        side="LEFT" if comment["status"] == "removed" else "RIGHT",
                    )
        for comment in state["comments"]:
            if comment["filename"] == "":
                pull_request.create_issue_comment(comment["comment"])
        return state
    
    def __get_modified_files(self, repo: Repository, pr: PullRequest) -> List[ContextFile]:
        return [ContextFile(path=file.filename, content=self.__get_modified_file(repo, pr, file)) for file in pr.get_files()]

    @staticmethod
    def __get_modified_file(repo: Repository, pr: PullRequest, pr_file: File) -> str:
        @dataclass
        class Changes:
            start: int
            end: int
            change: str

        # Split the files into patch blocks
        patch_blocks = re.split(r"(@@ -\d+,\d+ \+\d+,\d+ @@.*\n)", pr_file.patch)

        # If the file is not found on the base branch it means it is new, so all lines in it are new.
        # Return the whole file without the annotation
        try:
            o_file = repo.get_contents(pr_file.filename, ref=pr.base.ref).decoded_content.decode("utf-8").splitlines()
        except UnknownObjectException as e:
            return patch_blocks[2]
        
        changes: list[Changes] = []
        for i in range(1, len(patch_blocks), 2):
            change = patch_blocks[i+1]
            change.removesuffix("<<EOF")
            boundaries = re.match(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@", patch_blocks[i])
            additions_start = int(boundaries.group(3))
            additions_end = int(boundaries.group(4))
            deletions_start = int(boundaries.group(1))
            deletions_end = int(boundaries.group(2))
            if additions_start == 0:
                change_start = deletions_start
                change_end = deletions_end
            elif deletions_start == 0:
                change_start = additions_start
                change_end = additions_end
            else:
                change_start = min(int(boundaries.group(1)), int(boundaries.group(3)))
                change_end = max(int(boundaries.group(1)) + int(boundaries.group(2)) - 1, int(boundaries.group(3)) + int(boundaries.group(4)) - 1)
            changes.append(Changes(start=change_start, end=change_end, change=change))

        for i in range(len(o_file)):
            o_file[i] = " " + o_file[i]

        newFile: list[str] = []
        cursorPos: int = 0
        for c in changes:
            newFile.extend(o_file[cursorPos:c.start-1])
            newFile.extend(c.change.splitlines())
            cursorPos = c.end
        newFile.extend(o_file[cursorPos:])

        return "\n".join(newFile)

    @staticmethod
    def __get_context_for_modified_files(repo: Repository, pr: PullRequest) -> List[ContextFile]:
        pr_files = pr.get_files()
        unique_dirs: Set[str] = set()
        pr_filenames: List[str] = []
        for file in pr_files:
            pr_filenames.append(file.filename)
            directory = os.path.dirname(file.filename)
            unique_dirs.add(directory)

        all_files: List[ContentFile] = []
        for directory in unique_dirs:
            all_files.extend(repo.get_contents(directory, ref=pr.head.ref))

        return [ContextFile(path=f.path, content=f.decoded_content.decode("utf-8")) for f in all_files if f.name.endswith(".tf") and f.type == "file" and f.path not in pr_filenames]
    
    def parse(self, state:GitHubOperations, response: CodeReviewResponse) -> List[Comment]:
        modified_file_dict: Dict[str, str] = {f.path:f.content for f in state["modified_files"]}

        comments: List[Comment] = []
        for issue in response.issues:
            content = modified_file_dict.get(issue.filename, "")
            if content == "":
                raise ValueError(f"{issue.filename} is not found as a modified file")
            
            line_number = self.calculate_line_number(content, issue.reviewed_line)
            if line_number == 0:
                continue

            comments.append(
                Comment(
                    filename=issue.filename,
                    line_number=line_number,
                    comment=issue.comment,
                    status=issue.status
                )
            )
        return comments
    
    def calculate_line_number(self, file: str, line: str) -> int:
        if not line.startswith("+") and not line.startswith("-"):
            return 0

        if line.startswith("+"):
            skip_sign = "-"
        else:
            skip_sign = "+"

        line_number = 0
        for l in file.splitlines():

            if l.startswith(skip_sign):
                continue
            line_number += 1
            if l == line:
                return line_number

        raise KeyError("line not found")
