import pytest

from src.graphs.nodes.fetch_pr import validate_branch_name


def test_validates_valid_branch_name():
    valid_branch_name = "feature/valid-branch_name"
    validate_branch_name(valid_branch_name)


def test_raises_error_for_invalid_repo_name_with_special_characters():
    invalid_repo_name = "ab-&-&-c-7-d"
    with pytest.raises(ValueError, match="Invalid branch name: 'ab-&-&-c-7-d'"):
        validate_branch_name(invalid_repo_name)


def test_raises_error_for_empty_branch_name():
    invalid_branch_name = ""
    with pytest.raises(ValueError, match="Invalid branch name: ''"):
        validate_branch_name(invalid_branch_name)
