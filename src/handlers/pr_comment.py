import json
from typing import Any

from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.PullRequestComment import PullRequestComment
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain_openai import AzureChatOpenAI

from utils.config_file_pr import GitHubOperations

BOT_USER_TYPE = "Bot"
HUMAN_USER_TYPE = "User"


def handle_pull_request_comment(
        github_operations: GitHubOperations,
        model: AzureChatOpenAI,
        payload: dict[str, Any],
        local_run: bool = True
):
    comment = payload.get("comment")
    if comment is None:
        raise ValueError("Comment is missing in the payload")
    repo_name = payload.get("repository", {}).get("full_name")
    if repo_name is None:
        raise ValueError("Repository name is missing in the payload")
    pr_number = payload.get("pull_request", {}).get("number")
    if pr_number is None:
        raise ValueError("Pull request number is missing in the payload")

    try:
        repo = github_operations.github.get_repo(repo_name)
    except Exception as e:
        raise ValueError(f"Error getting repository from GitHub: {e}")

    try:
        pr = repo.get_pull(pr_number)
    except Exception as e:
        raise ValueError(f"Error getting pull request from GitHub: {e}")

    try:
        comments = pr.get_comments()
    except Exception as e:
        raise ValueError(f"Error getting comments from GitHub: {e}")

    thread = __get_comment_thread(comment, comments)
    if not __is_root_comment_by_bot(thread):
        return
    messages = __create_llm_messages_from_thread(thread)
    code = __get_reviewed_code(pr, comment)

    try:
        response = __invoke_llm(model, messages, code, comment)
    except Exception as e:
        raise ValueError(f"Error invoking LLM model: {e}")

    if response == "":
        return

    try:
        github_operations.reply_on_pr_comment(repo_name, pr_number, payload["comment"]["in_reply_to_id"], response)
    except Exception as e:
        raise ValueError(f"Error sending reply to comment on GitHub: {e}")


def __get_comment_thread(comment: dict[str, Any], comments: PaginatedList[PullRequestComment]) -> list[
    PullRequestComment]:
    thread_comments = [c for c in comments if
                       comment["in_reply_to_id"] == c.id or
                       c.id == comment["id"] or
                       c.in_reply_to_id == comment["in_reply_to_id"]]
    thread_comments.sort(key=lambda x: x.created_at)
    return thread_comments


def __is_root_comment_by_bot(thread: list[PullRequestComment]) -> bool:
    if len(thread) == 0:
        return False
    return thread[0].user.type == BOT_USER_TYPE


def __create_llm_messages_from_thread(thread: list[PullRequestComment]) -> list[BaseMessage]:
    messages = []
    for comment in thread:
        if comment.user.type == HUMAN_USER_TYPE:
            messages.append(HumanMessage(content=comment.body, id=comment.user.id))
        elif comment.user.type == BOT_USER_TYPE:
            messages.append(AIMessage(content=comment.body))
        else:
            pass
    return messages


def __get_reviewed_code(pr: PullRequest, comment: dict[str, Any]) -> str:
    try:
        files = pr.get_files()
    except Exception as e:
        raise ValueError(f"Error getting PR's files from GitHub: {e}")

    if comment["line"] is None:
        return ""

    for file in files:
        if file.filename == comment["path"]:
            return file.patch

    raise ValueError(f"File {comment['path']} not found in the PR's files")


def __invoke_llm(model: AzureChatOpenAI, message_history: list[BaseMessage], code: str, comment: dict[str, Any]) -> str:
    if message_history is None or len(message_history) == 0:
        raise ValueError("At least the original review should be presented in the message history")
    messages = [
        SystemMessagePromptTemplate.from_template(
            """You are a senior software developer.
            You were reviewing a pull request so you are the REVIEWER.
            Other developers asked you to explain your review. 
            Give a DETAILED explanation of your review.
            Answer the question based on the code and your review and the conversation below.
            Concentrate on the modification that you reviewed.
            Skip the answer if the conversation is not related to the code.
            Skip the answer if the conversation does not contain a question or a command to you.
            Respond in the following format: {{\"skip\": true, \"response\": \"Your response here\"}}
        
            The code that you reviewed is:
            ```
            {code}
            ```
            The conversation is about the modification in line {line_number}.
        
            Your review is:
            {review}
            """
        )
    ]
    if len(message_history) > 1:
        messages.append(SystemMessage(content="The conversation is as follows:"))
        messages.append(*message_history[1:])

    template = ChatPromptTemplate.from_messages(messages)
    prompt = template.format(
        code=code,
        line_number=comment["position"],
        review=message_history[0].content
    )
    response = model.invoke(prompt)
    json_response = json.loads(response.content)

    if json_response["skip"]:
        return ""
    return json_response["response"]
