import unittest
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
ggrandparent_dir = os.path.dirname(grandparent_dir)
pkg_dir = os.path.dirname(ggrandparent_dir)

print(f"Parent dir {parent_dir} G2 {ggrandparent_dir} PGK:{pkg_dir}")
sys.path.append(parent_dir)
sys.path.append(grandparent_dir)
sys.path.append(pkg_dir)
from unittest.mock import MagicMock, patch
from github import Github, UnknownObjectException
from alfred_git_data import PR, CommentType
from dateutil import parser
from eval.github_data_collection import (
    populate_commits,
    populate_issue_comments,
    populate_review_comments,
    populate_file_comments,
    populate_pr,
    read_and_write_file,
)


class TestGithubDataCollection(unittest.TestCase):
    def setUp(self):
        self.mock_pr = PR(pr_number=1)
        self.mock_commit = MagicMock()
        self.mock_commit.sha = "abc123"
        self.mock_commit.author.login = "test_user"
        self.mock_commit.commit.message = "Test commit message"
        self.mock_commit.commit.author.date = "2023-01-01T00:00:00Z"

        self.mock_comment = MagicMock()
        self.mock_comment.id = 123
        self.mock_comment.user.login = "comment_user"
        self.mock_comment.body = "Test comment"
        self.mock_comment.created_at = "2023-01-01T00:00:00Z"

        self.mock_file_comment = MagicMock()
        self.mock_file_comment.id = 456
        self.mock_file_comment.user.login = "file_comment_user"
        self.mock_file_comment.body = "File comment"
        self.mock_file_comment.created_at = "2023-01-01T00:00:00Z"
        self.mock_file_comment.path = "test_file.tf"
        self.mock_file_comment.commit_id = "abc123"
        self.mock_file_comment.original_commit_id = "def456"

        self.mock_pull = MagicMock()
        self.mock_pull.html_url = "http://example.com"
        self.mock_pull.title = "Test PR"
        self.mock_pull.state = "open"
        self.mock_pull.body = "Test PR body"
        self.mock_pull.created_at = "2023-01-01T00:00:00Z"
        self.mock_pull.updated_at = "2023-01-02T00:00:00Z"
        self.mock_pull.base.ref = "main"
        self.mock_pull.head.ref = "feature"

    def test_populate_commits(self):
        commits_data = [self.mock_commit]
        result = populate_commits(self.mock_pr, commits_data)
        self.assertEqual(len(result.commits), 1)
        self.assertEqual(result.commits[0].commit_sha, "abc123")

    def test_populate_issue_comments(self):
        issue_comments = [self.mock_comment]
        result = populate_issue_comments(self.mock_pr, issue_comments)
        self.assertEqual(len(result.comments), 1)
        self.assertEqual(result.comments[0].user, "comment_user")

    # def test_populate_review_comments(self):
    #     review_comments = [self.mock_comment]
    #     result = populate_review_comments(self.mock_pr, review_comments)
    #     self.assertEqual(len(result.comments), 1)
    #     self.assertEqual(result.comments[0].user, "comment_user")

    def test_populate_file_comments(self):
        comments = [self.mock_file_comment]
        result = populate_file_comments(self.mock_pr, comments, "test_file.tf")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].user, "file_comment_user")

    def test_populate_pr(self):
        result = populate_pr(self.mock_pr, self.mock_pull)
        self.assertEqual(result.url, "http://example.com")
        self.assertEqual(result.title, "Test PR")
        self.assertEqual(result.base_branch, "main")

    @patch("os.path.join")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    def test_read_and_write_file(self, mock_open, mock_makedirs, mock_path_join):
        mock_repo = MagicMock()
        mock_file = MagicMock()
        mock_file.filename = "test_file.tf"
        mock_pull = MagicMock()
        mock_pull.base.sha = "base_sha"
        mock_pull.head.sha = "head_sha"

        mock_repo.get_contents.side_effect = [
            MagicMock(decoded_content=b"Base content"),
            MagicMock(decoded_content=b"Final content"),
        ]

        read_and_write_file(
            mock_repo, mock_file, mock_pull, "path1", "path2", "test_file"
        )

        # mock_open.assert_any_call("path1/test_file", "w")
        # mock_open.assert_any_call("path2/test_file", "w")
        # mock_repo.get_contents.assert_any_call("test_file.tf", ref="base_sha")
        # mock_repo.get_contents.assert_any_call("test_file.tf", ref="head_sha")


if __name__ == "__main__":
    unittest.main()
