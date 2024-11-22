import json
from typing import Any

from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.PullRequestComment import PullRequestComment
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
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
    repo_name = payload["repository"]["full_name"]
    pr_number = payload["pull_request"]["number"]
    repo = github_operations.github.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    comments = pr.get_comments()
    thread = __get_comment_thread(payload["comment"], comments)
    if not __is_root_comment_by_bot(thread):
        return
    messages = __create_llm_messages_from_thread(thread)
    code = __get_reviewed_code(pr, payload["comment"])
    response = __invoke_llm(model, messages, code, payload["comment"])
    github_operations.reply_on_pr_comment(repo_name, pr_number, payload["comment"]["in_reply_to_id"], response)


def __get_comment_thread(comment: dict[str, Any], comments: PaginatedList[PullRequestComment]) -> list[
    PullRequestComment]:
    thread_comments = [c for c in comments if
                       comment["in_reply_to_id"] == c.id or
                       c.id == comment["id"] or
                       c.in_reply_to_id == comment["in_reply_to_id"]]
    thread_comments.sort(key=lambda x: x.created_at)
    return thread_comments


def __is_root_comment_by_bot(thread: list[PullRequestComment]) -> bool:
    return thread[0].user.type == BOT_USER_TYPE


def __create_llm_messages_from_thread(thread: list[PullRequestComment]) -> list[BaseMessage]:
    messages = []
    for comment in thread:
        if comment.user.type == HUMAN_USER_TYPE:
            messages.append(HumanMessage(content=comment.body))
        elif comment.user.type == BOT_USER_TYPE:
            messages.append(AIMessage(content=comment.body))
        else:
            pass
    return messages


def __get_reviewed_code(pr: PullRequest, comment: dict[str, Any]) -> str:
    files = pr.get_files()
    if comment["line"] is None:
        return ""
    for file in files:
        if file.filename == comment["path"]:
            return file.patch


def __invoke_llm(model: AzureChatOpenAI, message_history: list[BaseMessage], code: str, comment: dict[str, Any]) -> str:
    template = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(
                """
                You are a senior software developer.
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
                
                The conversation is:
                """
            ),
            *message_history[1:]
        ]
    )
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
