import unittest
import sys
import os
from unittest.mock import patch, mock_open, MagicMock

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
ggrandparent_dir = os.path.dirname(grandparent_dir)
pkg_dir = os.path.dirname(ggrandparent_dir)

print(f"Parent dir {parent_dir} G2 {ggrandparent_dir} PGK:{pkg_dir}")
sys.path.append(pkg_dir)
from alfred.src.eval.use_case_labeling import (
    file_use_case_labeling,
    read_file,
    diff_content,
    compare_files_read,
)
import os


class TestUseCaseLabeling(unittest.TestCase):
    @patch("alfred.src.eval.use_case_labeling.AzureChatOpenAI")
    def test_file_use_case_labeling(self, MockAzureChatOpenAI):
        mock_llm = MockAzureChatOpenAI.return_value
        mock_llm.invoke.return_value.content = "1, 0, 1, 0, 1"
        config = {
            "AZURE_OPENAI_API_KEY": "fake_key",
            "AZURE_OPENAI_ENDPOINT": "fake_endpoint",
            "api_version": "v1",
        }
        file_data = "fake_diff"
        file_comment = "fake_comment"
        result = file_use_case_labeling(config, file_data, file_comment)
        self.assertEqual(
            result,
            {
                "cross_reference": 1,
                "network_configuration": 0,
                "iam_policy": 1,
                "application_best_practice": 0,
                "terraform_best_practice": 1,
            },
        )

    @patch("builtins.open", new_callable=mock_open, read_data="file content")
    def test_read_file(self, mock_file):
        l_path = "/fake/path"
        c_filename = "file.txt"
        result = read_file(l_path, c_filename)
        mock_file.assert_called_once_with(os.path.join(l_path, c_filename), "r")
        self.assertEqual(result, "file content")

    def test_diff_content(self):
        a = "line1\nline2\nline3\n"
        b = "line1\nline2 modified\nline3\n"
        result = diff_content(a, b)
        self.assertIn("+ line2 modified", result)
        self.assertIn("- line2", result)

    @patch("alfred.src.eval.use_case_labeling.read_file")
    def test_compare_files_read(self, mock_read_file):
        mock_read_file.side_effect = ["content1", "content2"]
        l_path1 = "/fake/path1"
        file_name1 = "file1.txt"
        l_path2 = "/fake/path2"
        file_name2 = "file2.txt"
        result = compare_files_read(l_path1, file_name1, l_path2, file_name2)
        mock_read_file.assert_any_call(l_path1, file_name1)
        mock_read_file.assert_any_call(l_path2, file_name2)
        self.assertIn("- content", result)
        self.assertIn("+ content", result)


if __name__ == "__main__":
    unittest.main()
