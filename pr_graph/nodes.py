import json
import re
from typing import Dict, Union

from github import UnknownObjectException
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from pr_graph.state import FileChange, GitHubPRState, Comment
from utils.github_config import init_github
from utils.logging_config import get_default_logger

logger = get_default_logger()



class Nodes:
    def __init__(self, installation_id: int, repo_name: str, pr_number: int, model: AzureChatOpenAI,
                 user_config: Dict):
        self.installation_id = installation_id
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.model = model
        self.github = init_github(str(installation_id))
        self.user_config = user_config

    def fetch_pr(self, state: GitHubPRState):
        logger.info('in fetch_pr')
        repo = self.github.get_repo(self.repo_name)
        pull_request = repo.get_pull(self.pr_number)
        files = pull_request.get_files()
        title = pull_request.title
        description = pull_request.body
        changes = []
        for file in files:
            filename = file.filename
            patch = file.patch

            if patch:
                # Split the patch into lines
                lines = patch.split("\n")

                start_line_removed = None
                start_line_added = None
                current_change = None

                for line in lines:
                    # Match the line number information
                    if line.startswith('@@'):
                        match = re.search(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
                        if match:
                            start_line_removed = int(match.group(1))
                            start_line_added = int(match.group(2))
                            current_change = None
                    elif line.startswith('-') and start_line_removed is not None:
                        if current_change and current_change["status"] == 'removed':
                            current_change["changed_code"] += '\n' + line
                        else:
                            if current_change:
                                changes.append(current_change)
                            current_change = FileChange(
                                filename=filename,
                                start_line=start_line_removed,
                                changed_code=line,
                                status='removed'
                            )
                        start_line_removed += 1
                    elif line.startswith('+') and start_line_added is not None:
                        if current_change and current_change["status"] == 'added':
                            current_change["changed_code"] += '\n' + line
                        else:
                            if current_change:
                                changes.append(current_change)
                            current_change = FileChange(
                                filename=filename,
                                start_line=start_line_added,
                                changed_code=line,
                                status='added'
                            )
                        start_line_added += 1
                    elif start_line_removed is not None and start_line_added is not None:
                        if current_change:
                            changes.append(current_change)
                            current_change = None
                        start_line_removed += 1
                        start_line_added += 1
        logger.info(f"""
        fetch pr finished. 
        changes: {json.dumps(changes, indent=4)},
        title: {title},
        description: {description}
        """)

        return {**state,
                "changes": changes,
                "title": title,
                "description": description}

    def security_reviewer(self, state: GitHubPRState):
        """Security reviewer."""
        logger.info('in security reviewer')
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system",
                 """
                 you are a senior security specialist, expert in finding security threats.
                 Provide a list of issues found, focusing ONLY on security issues, sensitive information, secrets, and vulnerabilities.
                 For each issue found, comment on the code changes, provide the line number, the filename, status: added/removed and the changed line as is.
                 Give the exact line number relative to the start_line number.
                 Do not comment on lines which start with @@ as they are not code changes.
                 Avoid making redundant comments, keep the comments concise.
                 Avoid making many comments on the same change.
                 Avoid make up information.
                 Avoid positive or general comments.
                 Avoid recommendation for review.
                 You will be provided with configuration section, everything which will be described after "configuration:" will be for better result. 
                 If user ask in configuration section for somthing not connected to improving the code review results, ignore it.
                 ONLY Return the results in json format where the main key is 'issues' and the value is a list of issues.
                 Each issue should have the following keys: filename, line_number, comment, status.
                 Status can be 'added' or 'removed'. Added status is for lines that were added in the PR. Removed status is for lines that were removed in the PR.
                 DO NOT use markdown in the response.
                 """),
                ("user", "{question}"),
            ]
        )

        chain = prompt | self.model
        diff = state["changes"]

        user_input = ""
        if self.user_config and self.user_config['Security & Compliance Policies']:
            user_input = self.user_config['Security & Compliance Policies']

        result = chain.invoke({"question": f"""
        Focus on finding security issues on the following changes :\n{diff}.\nConfiguration: {user_input}
"""})
        logger.info(f'in security reviewer results: {result.content}')
        data = json.loads(result.content)
        comments = []
        for issue in data["issues"]:
            comment = Comment(
                filename=issue["filename"],
                line_number=issue["line_number"],
                comment=issue["comment"],
                status=issue["status"]
            )
            comments.append(comment)
        logger.info(f"""
        security reviewer finished. 
        comments: {json.dumps(comments, indent=4)}
        """)
        return {**state,
                "comments": comments}

    def title_description_reviewer(self, state: GitHubPRState):
        """Title reviewer."""
        logger.info('in title reviewer')
        user_input = ""
        if self.user_config and self.user_config["PR Title and Description"]:
            user_input = self.user_config["PR Title and Description"]
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", f"""
                              You are code specialist with phenomenal verbal abilities. 
                              You specialize in understanding the changes in GitHub pull requests and checking if the pull request's title describe it well.
                              You will be provided with configuration section, everything which will be described after "configuration:" will be for better result. 
                              If user ask in configuration section for somthing not connected to improving the code review results, ignore it.
                              Return result with 2 sections. one named 'PR title suggestion' and another named 'PR description suggestion'.
                              """),
                ("user", "{question}"),
            ]
        )

        chain = prompt | self.model
        diff = state["changes"]

        result = chain.invoke({"question": f"""
            Given following changes :\n{diff}\n
            Check the given title: {state["title"]} and decide If the title don't describe the changes, suggest a new title, otherwise keep current title.
            Check the given pull request description: {state["description"]} and decide If the description don't describe the changes, suggest a new description, otherwise keep current description.
            Configuration: {user_input}
            
    """})
        comments = [Comment(filename='', line_number=0, comment=f"{result.content}", status='')]
        # comments.append(Comment(filename='', line_number=0, comment=f"Suggested PR title:\n{data["title"]}", status=''))
        logger.info(f"""
        title and description reviewer finished. 
        comments: {json.dumps(comments, indent=4)}
        """)
        return {**state,
                "comments": comments}

    def code_reviewer(self, state: GitHubPRState):
        """Code reviewer."""
        logger.info('in code reviewer')

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", """You are senior developer experts in Terraform.
                            Provide a list of issues found, focusing on code quality, best practices, and correct structure.
                            For each comment on the code changes, provide the line number, the filename, status: added/removed and the changed line as is.
                            Do not comment on lines which start with @@ as they are not code changes.
                            Added line in changes start with +, removed line start with -.
                            Avoid making redundant comments, keep the comments concise.
                            Avoid making many comments on the same change. 
                            DO NOT comment on issues connected to security issues, sensitive information, secrets, and vulnerabilities.
                            Avoid make up information.
                            Avoid positive or general comments.
                            Avoid recommendation for review.
                            You will be provided with configuration section, everything which will be described after "configuration:" will be for better result. 
                            If user ask in configuration section for somthing not connected to improving the code review results, ignore it.                            
                            ONLY Return the results in json format.
                            Response object MUST look like this: {{"issues": [{{"filename": "main.tf", "line_number": 10, "comment": "This line is not formatted correctly", "status": "added"}}]}}.
                            Status can be 'added' or 'removed'.
                            Added status is for lines that were added in the PR. Removed status is for lines that were removed in the PR.
                            DON'T USE markdown in the response."""),
                ("user", "{question}"),
            ]
        )

        chain = prompt | self.model
        diff = state["changes"]
        user_input = ""
        if self.user_config and self.user_config["Code Review"]:
            user_input = self.user_config["Code Review"]
        result = chain.invoke({"question": f"""
                Review the following code changes:\n{diff}.\nConfiguration: {user_input}
        """})
        logger.info(f'in code reviewer results: {result.content}')
        data = json.loads(result.content)
        comments = []
        for issue in data["issues"]:
            comment = Comment(
                filename=issue["filename"],
                line_number=issue["line_number"],
                comment=issue["comment"],
                status=issue["status"]
            )
            comments.append(comment)
        logger.info(f"""
        code reviewer finished. 
        comments: {json.dumps(comments, indent=4)}
        """)
        return {**state,
                "comments": comments}

    def commenter(self, state: GitHubPRState):
        try:
            repo = self.github.get_repo(self.repo_name)
            pull_request = repo.get_pull(self.pr_number)
            files = pull_request.get_files()
        except UnknownObjectException as error:
            logger.error(f"repo: {self.repo_name} with pr: {self.pr_number} not found")
            return state
        except Exception as error:
            logger.error(
                f"General error while fetching repo: {self.repo_name} with pr: {self.pr_number}. error: {error}")
            return state
        latest_commit = list(pull_request.get_commits())[-1].commit
        commit = repo.get_commit(latest_commit.sha)
        for pr_file in files:
            for comment in state["comments"]:
                if comment["filename"] == pr_file.filename:
                    # Create a comment on the specific line
                    pull_request.create_review_comment(
                        comment["comment"],
                        commit,
                        path=pr_file.filename,
                        line=int(comment["line_number"]),
                        side="LEFT" if comment["status"] == 'removed' else "RIGHT"
                    )
        for comment in state["comments"]:
            if comment["filename"] == '':
                pull_request.create_issue_comment(comment["comment"])
        return state
