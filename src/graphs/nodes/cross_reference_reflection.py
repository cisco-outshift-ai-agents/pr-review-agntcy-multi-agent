from graphs.states import GitHubPRState
from utils.logging_config import logger as log
from .contexts import DefaultContext

import base64
from github.Commit import Commit
from github.GitTree import GitTree
from github.GitBlob import GitBlob
from github.GitTreeElement import GitTreeElement

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils.models import IssueComment


class File:
    def __init__(self, path: str, content: str):
        self.path: str = path
        self.content: str = content


class CrossReferenceInitializer:
    def __init__(self, context: DefaultContext, model: BaseChatModel, name: str = "cross_reference_initializer"):
        self.context = context
        self.name = name
        self.model = model
        self.file_type = "blob"
        self.file_extension = (".tf", ".tfvars")

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
        user_prompt = _create_user_prompt(git_diff, codebase, head_codebase)

        return {"messages": [HumanMessage(content=user_prompt)]}

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


class CrossReferenceGenerator:
    def __init__(self, context: DefaultContext, model: BaseChatModel, name: str = "cross_reference_generator"):
        self.context = context
        self.name = name
        self.model = model
        self.chain = _create_cross_reference_generator_chain(model)

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")

        message = self.chain.invoke(state["messages"])
        return {"messages": [message]}


def _create_cross_reference_generator_chain(model: BaseChatModel):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a senior Terraform engineer. You are given a Terraform codebase and a task to complete."),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    generate = prompt | model
    return generate


class CrossReferenceReflector:
    def __init__(self, context: DefaultContext, model: BaseChatModel, name: str = "cross_reference_reflector"):
        self.context = context
        self.name = name
        self.model = model
        self.chain = _create_cross_reference_reflector_chain(model)

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")

        # Other messages we need to adjust
        cls_map = {"ai": HumanMessage, "human": AIMessage}
        # First message is the original user request. We hold it the same for all nodes
        translated = [state["messages"][0]] + [cls_map[msg.type](content=msg.content) for msg in state["messages"][1:]]

        res = self.chain.invoke(translated)
        # We treat the output of this as human feedback for the generator
        return {"messages": [HumanMessage(content=res.content)]}


def _create_cross_reference_reflector_chain(model: BaseChatModel):
    reflector_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a senior Terraform professional acting as a verification agent. "
                "Your task is to validate the cross-reference analysis by:\n\n"
                "1. Verify each reported cross-reference issue by:\n"
                "   - Checking the git diff for relevant changes\n"
                "   - Confirming the issue exists in the head codebase\n"
                "   - Validating that the reported file paths and references are accurate\n"
                "   - Ensuring the severity level is appropriate\n\n"
                "2. For each questionable or invalid issue:\n"
                "   - Explain why the issue might be incorrect\n"
                "   - Provide evidence from the codebase\n"
                "   - Suggest how the generator should adjust its analysis\n\n"
                "3. Check for false negatives in critical areas:\n"
                "   - Variable references in modified files\n"
                "   - Resource dependencies affected by changes\n"
                "   - Module interface changes\n\n"
                "Format your response as:\n"
                "### Validation Results\n"
                "- Confirmed Issues: [list verified issues]\n"
                "- Incorrect Issues: [list with explanations]\n"
                "- Additional Concerns: [only if critical issues were missed]\n\n"
                "Focus on accuracy and thoroughness in your verification.",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    reflector = reflector_prompt | model
    return reflector


def _create_user_prompt(git_diff: str, base_codebase: str, head_codebase: str) -> str:
    user_prompt = f"""
        # git diff
        ```
        {git_diff}
        ```

        # head reference codebase:
        ```
        {head_codebase}
        ```

        # base reference codebase:
        ```
        {base_codebase}
        ```

        Analyze the Terraform code for cross-reference issues by comparing the base and head codebases. Return ONLY a list of issues in this exact format:

        ### Summary of Cross-Reference Problems

        - **`<resource_or_variable>`**: Used in `<file_path>` but not defined
        - **`<variable>`**: Defined in `<file_path>` but not used

        Rules:
        1. Only include actual cross-reference problems
        2. Do not include any other sections or explanations
        3. If no issues found, return only "### Summary of Cross-Reference Problems\n\nNo cross-reference issues found."
        4. Each issue must be a single line starting with a hyphen
        5. Use the exact format shown above

        Focus only on:
        - Variables or resources used but not defined
        - Variables or resources defined but not used
        - Module outputs used but not defined
        - Module input variables not provided
        - Variables defined in .tf files but missing from terraform.tfvars
        - Variables defined in terraform.tfvars but missing from .tf files
        - Variables defined in either .tf or terraform.tfvars (or both) but not referenced in any other files or resources
        """

    return user_prompt


class CrossReferenceCommenter:
    def __init__(self, context: DefaultContext, model: BaseChatModel, name: str = "cross_reference_commenter"):
        self.context = context
        self.name = name
        self.model = model

    def __call__(self, state: GitHubPRState) -> dict:
        log.info(f"{self.name} called")

        message: AIMessage = state["messages"][-1]

        return {"new_issue_comments": [IssueComment(body=message.content)]}
