import argparse
from multiprocessing import Value
import os
import sys
from langchain_openai import AzureChatOpenAI
from utils.config_file_pr import GitHubOperations
from utils.logging_config import logger as log
from langchain_core.prompts import ChatPromptTemplate


def code_reviewer():
    log.info("In code review...")

    model = AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )

    installation_id = os.getenv("INSTALLATION_ID")
    pr_number = os.getenv("PR_NUMBER")
    repo_name = os.getenv("REPO_NAME")

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--changes-file", "File with the PR diffs")
        args = parser.parse_args()
        file_path = args.changes_file
        if not file_path:
            raise ValueError("Missing changes file path")
        changes_file = open(file_path)
        changes = changes_file.read()
        if not changes:
            raise ValueError("Changes file empty")
    except Exception as e:
        log.error(f"Error with changes file: {e}")
        sys.exit(1)

    github_ops = GitHubOperations(str(installation_id))
    user_config = github_ops.retrieve_md_content_from_pr(pr_number, repo_name)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are senior developer experts in Terraform.
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
                    Issue in response object MUST be built based on changes as follows: {{"filename": "filename" field from change, "line_number": "start_line" field from change, "comment": your comment MUST be placed here, "status": "status" field from change}}
                    Status can be 'added' or 'removed'.
                    Added status is for lines that were added in the PR. Removed status is for lines that were removed in the PR.
                    DON'T USE markdown in the response.""",
            ),
            ("user", "{question}"),
        ]
    )

    chain = prompt | model
    user_input = ""
    if user_config and user_config["Code Review"]:
        user_input = user_config["Code Review"]
    result = chain.invoke(
        {
            "question": f"""
                Review the following code changes:\n{changes}.\nConfiguration: {user_input}
        """
        }
    )

    log.info(f"in code reviewer results: {result.content}")
    # data = json.loads(result.content)
    # comments = []
    # for issue in data["issues"]:
    #     comment = Comment(filename=issue["filename"], line_number=issue["line_number"], comment=issue["comment"], status=issue["status"])
    #     comments.append(comment)
    # log.info(f"""
    #     code reviewer finished.
    #     comments: {json.dumps(comments, indent=4)}
    #     """)
    # return {**state, "comments": comments}


if __name__ == "__main__":
    code_reviewer()
