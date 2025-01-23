import shutil
from subprocess import CalledProcessError, run
from typing import Any

from langchain_core.runnables import RunnableSerializable

from graphs.states import GitHubPRState
from utils.logging_config import logger as log
from utils.wrap_prompt import wrap_prompt
from .contexts import DefaultContext


class StaticAnalyzer:
    def __init__(self, context: DefaultContext, name: str = "static_analyzer"):
        self.context = context
        self.__name = name

    def __call__(self, state: GitHubPRState) -> dict[str, Any]:
        log.info(f"{self.__name} called")

        if not self.context.chain:
            raise ValueError(f"{self.__name}: Chain is not set in the context")

        if not self.context.github:
            raise ValueError(f"{self.__name}: GithubOps is not set in the context")

        # TODO: fix this later. Chain can be a Callable[..., RunnableSerializable] or RunnableSerializable
        if not isinstance(self.context.chain, RunnableSerializable):
            raise ValueError(f"{self.__name}: Chain is not a RunnableSerializable")

        # First clone the repo into a local folder
        local_folder = "/tmp/repo_copy"
        try:
            # The output folder will look like this: "./repo_copy/repo-name-<commit-hash>"
            output_folder = self.context.github.clone_repo(local_folder)
        except Exception as e:
            log.error(f"Error while cloning the repo: {e}")
            raise

        try:
            # Need tf init to download the necessary third party dependencies, otherwise most linters would fail
            # This will fail if there are module level errors which block the build (like duplicated outputs)
            run(
                ["terraform", "init", "-backend=false"],
                # check=True,
                cwd=output_folder,
                capture_output=True,
                text=True,
            )

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
            log.error(f"Error while running static checks in the users repo: {e}")
            return {}

        try:
            shutil.rmtree(output_folder)
            log.debug("Repo deleted successfully")
        except Exception as e:
            log.error(f"An error occured while removing the local copy of the repo: {e}")
            return {}

        try:
            response = self.context.chain.invoke(
                {
                    "linter_outputs": wrap_prompt(
                        "terraform validate output:",
                        f"{tf_validate_out.stderr}",
                        f"{tf_validate_out.stdout}",
                        "",
                        "tflint output:",
                        f"{tflint_out.stderr}",
                        f"{tflint_out.stdout}",
                    )
                }
            )

        except Exception as e:
            log.error(f"Error in {self.__name} while running the static analyzer chain: {e}")
            raise

        log.debug(f"""
        static_analyzer finished.
        output: {response.content}
        """)

        return {"static_analyzer_output": response.content}
