import json
import re
from functools import partial

from graphs.codereviewer.state import GitHubPRState, FileChange, Comment
from utils.logging_config import logger as log
from .contexts import GitHubContext


def create_fetch_pr_node(context: GitHubContext):
    def fetch_pr(state: GitHubPRState) -> GitHubPRState:
        log.info("in fetch_pr")
        repo = context.github.get_repo(context.repo_name)
        pull_request = repo.get_pull(context.pr_number)
        files = pull_request.get_files()
        title = [pull_request.title]
        description = [pull_request.body]
        changes = []
        existing_comments = []

        try:
            pr_comments = context.github.list_comments_from_pr(context.repo_name, context.pr_number)
            for comment in pr_comments:
                existing_comments.append(
                    Comment(
                        filename=comment.path,
                        line_number=comment.position,
                        comment=comment.body,
                        status="added" if comment.position is not None else "removed",
                    )
                )
        except Exception as e:
            log.error(f"Error fetching existing comments: {e}")

        for file in files:
            filename = file.filename
            patch = file.patch

            if patch:
                lines = patch.split("\n")
                start_line_removed = None
                start_line_added = None
                current_change = None

                for line in lines:
                    if line.startswith("@@"):
                        match = re.search(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                        if match:
                            start_line_removed = int(match.group(1))
                            start_line_added = int(match.group(2))
                            current_change = None
                    elif line.startswith("-") and start_line_removed is not None:
                        if current_change and current_change["status"] == "removed":
                            current_change["changed_code"] += "\n" + line
                        else:
                            if current_change:
                                changes.append(current_change)
                            current_change = FileChange(filename=filename, start_line=start_line_removed, changed_code=line, status="removed")
                        start_line_removed += 1
                    elif line.startswith("+") and start_line_added is not None:
                        if current_change and current_change["status"] == "added":
                            current_change["changed_code"] += "\n" + line
                        else:
                            if current_change:
                                changes.append(current_change)
                            current_change = FileChange(filename=filename, start_line=start_line_added, changed_code=line, status="added")
                        start_line_added += 1
                    elif start_line_removed is not None and start_line_added is not None:
                        if current_change:
                            changes.append(current_change)
                            current_change = None
                        start_line_removed += 1
                        start_line_added += 1

        log.info(f"""
        fetch pr finished.
        changes: {json.dumps(changes, indent=4)},
        title: {title},
        description: {description},
        existing_comments: {json.dumps([comment.model_dump() for comment in existing_comments], indent=4)}
        """)

        return {
            **state,
            "changes": changes,
            "title": title,
            "description": description,
            "existing_comments": existing_comments,
            "comments": [],
        }

    return partial(fetch_pr)
