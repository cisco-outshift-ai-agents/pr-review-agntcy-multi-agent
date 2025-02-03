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
from utils.models import IssueComment


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

        comment = IssueComment(body=cross_reference_problems)

        return {"new_issue_comments": [comment]}

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
