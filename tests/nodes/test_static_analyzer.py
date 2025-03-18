import os
from subprocess import CompletedProcess
from typing import Optional
from unittest.mock import MagicMock, patch
import pytest
from graphs.chains.static_analysis import create_static_analyzer_chain
from graphs.nodes.contexts import DefaultContext
from graphs.nodes.static_analyzer import StaticAnalyzer

from graphs.states import GitHubPRState, create_default_github_pr_state
from tests.nodes.utils import vector_based_similarity
from utils.constants import AZURE_OPENAI_API_KEY_ENV
from utils.github_operations import GitHubOperations
from utils.modelfactory import models

_mock_output_folder = "./repo_copy/test-repo"

_expected_summary = """\
1. main.tf: "10.0.2.0.12/24" is not a valid CIDR block: invalid CIDR address: 10.0.2.0.12/24 with aws_subnet.private_subnet, on main.tf, in resource "aws_subnet" "private_subnet": cidr_block = "10.0.2.0.12/24"
2. main.tf: Reference to undeclared resource on main.tf, in resource "aws_route_table_association" "public_rt_assoc": route_table_id = aws_route_table.public_rt.id. A managed resource "aws_route_table" "public_rt" has not been declared in the root module.
3. main.tf: Reference to undeclared resource on main.tf, in resource "aws_instance" "web_server": security_groups = [aws_security_group.main_sg.name]. A managed resource "aws_security_group" "main_sg" has not been declared in the root module.
"""

_tf_validate_args = ["terraform", "validate", "-no-color"]
_tflint_args = ["tflint", "--format=compact", "--recursive"]


@pytest.fixture
def mock_context() -> DefaultContext:
    # In other tests the secret manager is mocked and set to None by default, so we have to patch it here with a real SM instance
    with patch("utils.modelfactory.secret_manager") as mock_secret_manager:
        mock_secret_manager.azure_openai_api_key = os.getenv(AZURE_OPENAI_API_KEY_ENV)
        model = models.get_azure_openai()

    context = DefaultContext()
    context.chain = create_static_analyzer_chain(model)

    github = MagicMock(spec=GitHubOperations)
    github.clone_repo.return_value = _mock_output_folder

    context.github = github

    return context


@pytest.fixture
def mock_state() -> GitHubPRState:
    state = create_default_github_pr_state()
    return state


def mock_run_logic(args, **kwargs) -> Optional[CompletedProcess]:
    match args:
        case x if x == _tf_validate_args:
            return CompletedProcess(
                args=_tf_validate_args,
                returncode=1,
                stdout="",
                stderr="""
                Error: "10.0.2.0.12/24" is not a valid CIDR block: invalid CIDR address: 10.0.2.0.12/24
                  with aws_subnet.private_subnet,
                  on main.tf line 28, in resource "aws_subnet" "private_subnet":
                  28:   cidr_block        = "10.0.2.0.12/24"
                Error: Reference to undeclared resource
                  on main.tf line 48, in resource "aws_route_table_association" "public_rt_assoc":
                  48:   route_table_id = aws_route_table.public_rt.id
                A managed resource "aws_route_table" "public_rt" has not been declared in the
                root module.
                Error: Reference to undeclared resource
                  on main.tf line 57, in resource "aws_instance" "web_server":
                  57:   security_groups = [aws_security_group.main_sg.name]
                A managed resource "aws_security_group" "main_sg" has not been declared in
                the root module.
                """,
            )
        case x if x == _tflint_args:
            return CompletedProcess(
                args=_tflint_args,
                returncode=2,
                stdout="""4 issue(s) found:
                main.tf:53:1: Warning - Missing version constraint for provider "aws" in `required_providers` (terraform_required_providers)
                main.tf:1:1: Warning - terraform "required_version" attribute is required (terraform_required_version)
                variables.tf:7:1: Warning - variable "vpc_cidr" is declared but not used (terraform_unused_declarations)
                variables.tf:13:1: Warning - variable "public_subnet_cidr" is declared but not used (terraform_unused_declarations)
                """,
                stderr="",
            )
        case _:
            return


def test_static_analyzer_init(mock_context):
    name = "test_static_analyzer"
    cf = StaticAnalyzer(mock_context, name)
    assert cf._context == mock_context
    assert cf._name == name


def test_static_analyzer_call_chain_error(mock_context, mock_state):
    mock_context.chain = None
    cf = StaticAnalyzer(mock_context)

    with pytest.raises(ValueError):
        cf(mock_state)

    mock_context.chain = MagicMock(spec=list)
    cf = StaticAnalyzer(mock_context)

    with pytest.raises(ValueError):
        cf(mock_state)


@patch("graphs.nodes.static_analyzer.shutil.rmtree")
@patch("graphs.nodes.static_analyzer.run")
def test_static_analyzer_call(mock_run, mock_rmtree, mock_context, mock_state):
    mock_run.side_effect = mock_run_logic

    cf = StaticAnalyzer(mock_context)
    resp = cf(mock_state)

    mock_run.assert_any_call(_tf_validate_args, cwd=_mock_output_folder, capture_output=True, text=True)
    mock_run.assert_any_call(_tflint_args, cwd=_mock_output_folder, capture_output=True, text=True)
    mock_rmtree.assert_called_with(_mock_output_folder)

    summary = resp["static_analyzer_output"]
    assert vector_based_similarity(summary, _expected_summary) > 0.90
