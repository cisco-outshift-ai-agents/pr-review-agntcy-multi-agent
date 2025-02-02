import base64

from graphs.states import GitHubPRState
from utils.logging_config import logger as log
from .contexts import DefaultContext


from github.Commit import Commit
from github.GitTree import GitTree
from github.GitBlob import GitBlob
from github.GitTreeElement import GitTreeElement

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage, SystemMessage
from typing import List, cast
from pydantic import BaseModel
from utils.models import Comment


class CrossReferenceProblem(BaseModel):
    resource_or_variable: str
    context: str


class CrossReferenceProblems(BaseModel):
    problems: List[CrossReferenceProblem]


class File:
    def __init__(self, path: str, content: str):
        self.path: str = path
        self.content: str = content


class CrossReferenceValidator:
    def __init__(self, context: DefaultContext, model: BaseChatModel, name: str = "cross_reference_validator"):
        self.context = context
        self.name = name
        self.file_type = "blob"
        self.file_extension = (".tf", ".tfvars")
        self.messages: List[BaseMessage] = []
        self.model = model

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")

        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHub is not set in the context")

        # modified_files = self.context.github.pr.get_files()  # modified files
        head_sha = self.context.github.pr.head.sha
        base_sha = self.context.github.pr.base.sha

        # Get all files from the head commit
        head_files: list[File] = self._get_files_from_sha(head_sha)

        # Get all files from the base commit
        base_files: list[File] = self._get_files_from_sha(base_sha)

        codebase = self._codebase(base_files)
        head_codebase = self._codebase(head_files)
        git_diff = self.context.github.get_git_diff()

        self._analyze_cross_references(codebase)
        self._analyze_cross_references_from_diff(git_diff, head_codebase)
        cross_reference_problems = self._create_issue_comments()

        comment = Comment(filename="", line_number=0, comment=cross_reference_problems, status="")

        return {"cross_reference_problems": comment}
        # review_comments = self._create_review_comment()
        # return {"cross_reference_problems": review_comments}

    def _get_files_from_sha(self, sha: str) -> list[File]:
        if self.context.github is None:
            raise ValueError(f"{self.name}: GitHub is not set in the context")

        # Get the commit object
        commit: Commit = self.context.github.repo.get_commit(sha)

        # Get the tree associated with the commit
        tree: GitTree = commit.commit.tree

        # Get all files in the tree
        files: list[GitTreeElement] = self.context.github.repo.get_git_tree(tree.sha, recursive=True).tree

        # Create a list of File objects
        file_objects = []
        for file in files:
            if file.type == self.file_type:
                # need only ".tf" and ".tfvars" files
                if not file.path.endswith(self.file_extension):
                    continue
                # Read the file content
                blob: GitBlob = self.context.github.repo.get_git_blob(file.sha)
                # Decode the base64 content
                content = base64.b64decode(blob.content).decode("utf-8")
                file_objects.append(File(file.path, content))

        return file_objects

    def _codebase(self, files: list[File]) -> str:
        codebase = ""
        for file in files:
            codebase += f"##FILE: {file.path}\n"
            codebase += file.content
            codebase += "\n##END_OF_FILE\n\n"

        return codebase

    def _analyze_cross_references(self, codebase: str) -> None:
        system_message = SystemMessage(content="You are a senior Terraform engineer. You are given a Terraform codebase and a task to complete.")
        self.messages.append(system_message)

        user_prompt = f"""
        # base reference codebase:
        {codebase}
        # End of base reference codebase

        You are given a Terraform codebase and a task to complete. Your task is to analyze the Terraform files provided and list all variable and resource cross-references. This includes identifying where variables are defined and used, as well as how resources are interconnected. Provide a short report of these cross-references. Specifically, I need you to return the cross-references in the following format:

        ### Cross-References

        #### Used but Not Provided
        - **`<resource_or_variable>`**: Used in `<context>` but not defined.

        #### Provided but Not Used
        - **`<variable>`**: Defined in `<context>` but not used.

        What are the cross-references in the codebase? List only those which
        - are used but not provided in the codebase
        - are provided but not directly used in the codebase
        - if a variable is provided in either in a file or in the terraform.tfvars file, but not used in the codebase, list it as a cross-reference

        Let's think step by step.
        """

        self.messages.append(HumanMessage(content=user_prompt))

        ai_message: AIMessage = cast(AIMessage, self.model.invoke(self.messages))
        self.messages.append(ai_message)

    def _analyze_cross_references_from_diff(self, git_diff: str, codebase: str) -> str:
        user_prompt = f"""
        # git diff
        ```
        {git_diff}
        ```
        # End of git diff

        # head reference codebase:
        {codebase}
        # End of head reference codebase

        Please compare the above 'git diff' and the 'head reference codebase' with the cross-references found in the chat history.
        Identify and point out any cross-reference problems that could be caused by the changes in the 'git diff'. Summarize the problems in a bulleted list.

        ### Summary of Cross-Reference Problems

        - **`<resource_or_variable>`**: Used in `<context>` but not defined.
        - **`<variable>`**: Defined in `<context>` but not used.

        Let's first understand the problem and devise a plan to solve the problem. Then, let's carry out the plan and solve the problem step-by-step.
        """
        self.messages.append(HumanMessage(content=user_prompt))
        ai_message: AIMessage = cast(AIMessage, self.model.invoke(self.messages))
        self.messages.append(ai_message)

        return str(ai_message.content)

    def _create_issue_comments(self) -> str:
        user_prompt = """
        Return only the '### Summary of Cross-Reference Problems' summary section in markdown format.
        """

        self.messages.append(HumanMessage(content=user_prompt))
        ai_message: AIMessage = cast(AIMessage, self.model.invoke(self.messages))
        self.messages.append(ai_message)

        return str(ai_message.content)


#     def _create_review_comment(self) -> List[ReviewComment]:
#         llm_with_structured_output = self.model.with_structured_output(ReviewComments)
#         user_prompt = """
# Here is the GitHib ReviewComment specification.
# ## ReviewComment Specification
# ### Body Parameters

# - **body** (`string`, Required)
#   The text of the review comment.

# - **commit_id** (`string`, Required)
#   The SHA of the commit needing a comment. Not using the latest commit SHA may render your comment outdated if a subsequent commit modifies the line you specify as the position.

# - **path** (`string`, Required)
#   The relative path to the file that necessitates a comment.

# - **position** (`integer`, Deprecated)
#   This parameter is being deprecated; use `line` instead. It represents the position in the diff where you want to add a review comment.
#   Note that this value is **not** the same as the line number in the file. The position is counted from the first "@@" hunk header in the file.
#   - The line just below the "@@" line is position `1`, the next line is `2`, and so on.
#   - The position count increases through lines of whitespace and additional hunks until the start of a new file.

# - **side** (`string`)
#   Defines the side of the diff where the pull request’s changes appear in a split diff view.
#   - Use `LEFT` for deletions (red).
#   - Use `RIGHT` for additions (green) or unchanged lines (white, shown for context).
#   - For multi-line comments, `side` represents whether the **last line** of the comment range is a deletion or an addition.

#   **Accepted values:** `LEFT`, `RIGHT`

# - **line** (`integer`, Required unless using `subject_type:file`)
#   The line of the blob in the pull request diff that the comment applies to.
#   - For a multi-line comment, this represents the **last line** of the range your comment applies to.

# - **start_line** (`integer`, Required for multi-line comments unless using `in_reply_to`)
#   The first line in the pull request diff that your multi-line comment applies to.

# - **start_side** (`string`, Required for multi-line comments unless using `in_reply_to`)
#   The starting side of the diff that the comment applies to.

#   **Accepted values:** `LEFT`, `RIGHT`
# ## End of ReviewComment Specification

# Use the 'specification', the 'git diff', the 'base reference codebase', the 'head reference codebase' and the chat history to create a review comment for the ### Summary of Cross-Reference Problems section. Calculate the best line, side, start_line, start_side for the review comment using the 'git diff' line numbers, the 'head reference codebase' line numbers and the 'base reference codebase' line numbers. Make sure that the review comment lines must be part of the 'git diff' hunks.

# Think step by step.
# """
#         self.messages.append(HumanMessage(content=user_prompt))
#         ai_message: AIMessage = cast(AIMessage, llm_with_structured_output.invoke(self.messages))
#         self.messages.append(ai_message)
#         review_comments: List[ReviewComment] = ai_message["review_comments"]
#         return review_comments
