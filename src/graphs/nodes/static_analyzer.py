# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

from subprocess import CalledProcessError, PIPE, run
from typing import Any
import os
import shutil
from .contexts import DefaultContext
from graphs.states import GitHubPRState
from langchain_core.runnables import RunnableSerializable
from utils.constants import TMP_DIR_ENV
from utils.logging_config import logger as log
from utils.wrap_prompt import wrap_prompt
from utils.models import StaticAnalyzerOutputList, StaticAnalyzerInput


def checkTofuFiles(output_folder) -> list[str]:
    # Check for tofu files in the output folder
    if os.path.isdir(output_folder):
        files_with_extension = [f for f in os.listdir(output_folder) if f.endswith(".tofu") or f.endswith(".tofuvars")]
        return files_with_extension
    return []


def convertFileExtension(output_folder, tofu_files) -> dict:
    # Convert the extension from .tofu/.tofuvars to .tf/.tfvars
    file_rename_map = {}
    new_filename = ""
    for files in tofu_files:
        if files.endswith(".tofu"):
            old_path = os.path.join(output_folder, files)
            new_filename = "modified_" + os.path.splitext(files)[0] + ".tf"
            new_path = os.path.join(output_folder, new_filename)
            os.rename(old_path, new_path)
        elif files.endswith(".tofuvars"):
            old_path = os.path.join(output_folder, files)
            new_filename = "modified_" + os.path.splitext(files)[0] + ".tfvars"
            new_path = os.path.join(output_folder, new_filename)
            os.rename(old_path, new_path)
        file_rename_map[files] = new_filename
    return file_rename_map


def modifyresponse(file_rename_map, response) -> str:
    modified_output = ""
    if response == "":
        return ""
    for old_filename, new_filename in file_rename_map.items():
        if not modified_output:
            modified_output = response.replace(new_filename, old_filename)
        else:
            modified_output = modified_output.replace(new_filename, old_filename)
    return modified_output


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
            file_rename_map = {}
            # Check for the tofu files in the repo
            tofu_files = checkTofuFiles(output_folder)
            if tofu_files:
                file_rename_map = convertFileExtension(output_folder, tofu_files)
            tf_validate_out = run(
                ["terraform", "validate", "-no-color"],
                cwd=output_folder,
                stdout=PIPE,
                stderr=PIPE,
                text=True,
            )
            lint_stdout, lint_stderr = "", ""
            # If terraform validate passes, run tflint
            if tf_validate_out.returncode == 0:
                # Need tf init to download the necessary third party
                # dependencies, otherwise most linters would fail
                run(
                    ["terraform", "init", "-backend=false"],
                    check=True,
                    cwd=output_folder,
                    capture_output=True,
                    text=True,
                )
                tflint_out = run(
                    ["tflint", "--format=compact", "--recursive"],
                    cwd=output_folder,
                    stdout=PIPE,
                    stderr=PIPE,
                    text=True,
                )
                lint_stdout = tflint_out.stdout
                lint_stderr = tflint_out.stderr
                # if some files are renamed modify the lint output with the old file name
        except CalledProcessError as e:
            log.error(f"Error while running static checks: {e.stderr}")
            return {}
        try:
            shutil.rmtree(output_folder)
            log.debug("Repo deleted successfully")
        except Exception as e:
            log.error(f"An error occured while removing the local copy of the repo: {e}")
            return {}

        try:
            if file_rename_map:
                # Replace all the modified file names in  tf_validate output, error, lint output
                tf_validate_output = modifyresponse(file_rename_map, tf_validate_out.stdout)
                tf_validate_error = modifyresponse(file_rename_map, tf_validate_out.stderr)
                tf_lint_output = modifyresponse(file_rename_map, lint_stdout)
                tf_lint_error = modifyresponse(file_rename_map, lint_stderr)
            else:
                tf_validate_output = tf_validate_out.stdout
                tf_validate_error = tf_validate_out.stderr
                tf_lint_output = lint_stdout
                tf_lint_error = lint_stderr

            staticanalyzerinput = StaticAnalyzerInput(tf_validate_out_stderr=tf_validate_error,
                                                  tf_validate_out_stdout=tf_validate_output,
                                                  tflint_output_stderr=tf_lint_error,
                                                  tflint_output_stdout=tf_lint_output)

            response: StaticAnalyzerOutputList = self._context.chain.invoke(
                {
                    "linter_outputs": wrap_prompt(
                        "terraform validate output:",
                        f"{staticanalyzerinput.tf_validate_out_stderr}",
                        f"{staticanalyzerinput.tf_validate_out_stdout}",
                        "",
                        "tflint output:",
                        f"{staticanalyzerinput.tflint_output_stderr}",
                        f"{staticanalyzerinput.tf_validate_out_stdout}",
                    )
                }
            )
        except Exception as e:
            log.error(f"Error in {self._name} while running the static analyzer chain: {e}")
            raise

        print("*******static analyzer************")
        print("*******terraform validate output************")
        print(f"{tf_validate_error}")
        print("_____________________")
        print(f"{tf_validate_output}")
        print("*******tflint output************")
        print(f"{tf_lint_error}")
        print("_____________________")
        print(f"{tf_lint_output}")
        print("_____________________")
        print("*******static analyzer output************")
        print(f"{response}")
        print(type(response))

        log.debug(f"""
        static_analyzer finished.
        output: {response}
        """)
        return {"static_analyzer_output": response}
