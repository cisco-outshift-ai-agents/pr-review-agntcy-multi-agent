from subprocess import CalledProcessError, run, PIPE
from typing import Any
import os
import shutil

from .contexts import DefaultContext
from graphs.states import GitHubPRState
from langchain_core.runnables import RunnableSerializable
from utils.constants import TMP_DIR_ENV
from utils.logging_config import logger as log
from utils.wrap_prompt import wrap_prompt


class StaticAnalyzer:
    def __init__(self, context: DefaultContext, name: str = "static_analyzer"):
        self._context = context
        self._name = name

    def __call__(self, state: GitHubPRState) -> dict[str, Any]:
        log.info(f"{self._name} called")

        if not self._context.chain:
            raise ValueError(f"{self._name}: Chain is not set in the context")

        if not self._context.github:
            raise ValueError(f"{self._name}: GithubOps is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self._context.chain, RunnableSerializable):
            raise ValueError(f"{self._name}: Chain is not a RunnableSerializable")

        tmp_dir = os.getenv(TMP_DIR_ENV, ".")
        # First clone the repo into a local folder
        local_folder = os.path.join(tmp_dir, "repo_copy")
        try:
            # The output folder will look like this: "./repo_copy/repo-name-<commit-hash>"
            output_folder = self._context.github.clone_repo(local_folder)
        except Exception as e:
            log.error(f"Error while cloning the repo: {e}")
            raise

        try:
            tf_validate_out = run(
            ["terraform", "validate", "-no-color"],
            cwd=output_folder,
            capture_output=True,
            text=True,
            )

            tflint_out = run(
                ["tflint", "--format=compact", "--recursive"],
                cwd=output_folder,
                capture_output=True,
                text=True,
            )
        except CalledProcessError as e:
            log.error(f"Error while running static checks: {e.stderr}")
            return {}
        except FileNotFoundError:
            log.error("Terraform or tflint executables not found. Please install both tools and ensure they are in your system PATH.")
            return {}

        try:
            shutil.rmtree(output_folder)
            log.debug("Repo deleted successfully")
        except Exception as e:
            log.error(f"An error occured while removing the local copy of the repo: {e}")
            return {}

        try:
            response = self._context.chain.invoke(
                {
                    "linter_outputs": wrap_prompt(
                        "terraform validate output:",
                        f"{tf_validate_out.stderr}",
                        f"{tf_validate_out.stdout}",
                        "",
                        "tflint output:",
                        f"{tflint_out.stderr}",
                        f"{tflint_out.stdout}",)
                }
            )

        except Exception as e:
            log.error(f"Error in {self._name} while running the static analyzer chain: {e}")
            raise

        log.debug(f"""
        static_analyzer finished.
        output: {response.content}
        """)

        return {"static_analyzer_output": response.content}
