import json
import os
from typing import Any

from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.PullRequestComment import PullRequestComment
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain_openai import AzureChatOpenAI

from agents.agent import Agent
from utils.github_operations import GitHubOperations

BOT_USER_TYPE = "Bot"
HUMAN_USER_TYPE = "User"


class PRReviewChatAgent(Agent):

    def __init__(self, github_operations: GitHubOperations):
        super(PRReviewChatAgent, self).__init__()

        self.__github_ops = github_operations

        self.__model = AzureChatOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
            openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
        )

    def invoke(self, repo_full_name: str, pr_number: int, comment: dict[str, Any]):
        try:
            repo = self.__github_ops.get_repo(repo_full_name)
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

        thread = self.__get_comment_thread(comment, comments)
        if not self.__is_root_comment_by_bot(thread):
            return
        messages = self.__create_llm_messages_from_thread(thread)

        try:
            code = self.__get_reviewed_code(pr, comment)
        except Exception as e:
            raise ValueError(f"Error getting reviewed code: {e}")

        try:
            response = self.__invoke_llm(messages, code, comment)
        except Exception as e:
            raise ValueError(f"Error invoking LLM model: {e}")

        if response == "":
            return

        try:
            self.__github_ops.reply_on_pr_comment(repo_full_name, pr_number, comment["in_reply_to_id"], response)
        except Exception as e:
            raise ValueError(f"Error sending reply to comment on GitHub: {e}")

    def __invoke_llm(self, message_history: list[BaseMessage], code: str,
                     comment: dict[str, Any]) -> str:
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
        response = self.__model.invoke(prompt)
        json_response = json.loads(response.content)

        if json_response["skip"]:
            return ""
        return json_response["response"]

    @staticmethod
    def __get_comment_thread(comment: dict[str, Any], comments: PaginatedList[PullRequestComment]) -> list[
        PullRequestComment]:
        thread_comments = [c for c in comments if
                           comment["in_reply_to_id"] == c.id or
                           c.id == comment["id"] or
                           c.in_reply_to_id == comment["in_reply_to_id"]]
        thread_comments.sort(key=lambda x: x.created_at)
        return thread_comments

    @staticmethod
    def __is_root_comment_by_bot(thread: list[PullRequestComment]) -> bool:
        if len(thread) == 0:
            return False
        return thread[0].user.type == BOT_USER_TYPE

    @staticmethod
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

    @staticmethod
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
