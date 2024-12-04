from typing import Any

from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.PullRequestComment import PullRequestComment
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from pydantic import BaseModel, Field

from agents.agent import Agent
from utils.github_operations import GitHubOperations
from utils.modelfactory import models

BOT_USER_TYPE = "Bot"
HUMAN_USER_TYPE = "User"


class PRReviewChatResponse(BaseModel):
    isSkipped: bool = Field(description="Indicates if the response is skipped. Set to true if the response is skipped.")
    response: str = Field(description="Your response based on the conversation.")


class PRReviewChatAgent(Agent):
    def __init__(self, github_operations: GitHubOperations):
        super(PRReviewChatAgent, self).__init__()

        self.__github_ops = github_operations
        self.__model = models.get_vertexai()

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

    def __invoke_llm(self, message_history: list[BaseMessage], code: str, comment: dict[str, Any]) -> str:
        if message_history is None or len(message_history) < 2:
            raise ValueError("At least the original review and a comment should be presented in the message history")
        messages = [
            SystemMessagePromptTemplate.from_template(
                """You are a senior software developer.
                Your name is Alfred.
                You were reviewing a pull request so you are the REVIEWER.
                Your review is the FIRST message in the CONVERSATION.
                Other developers asked you to explain your review. 
                Give a DETAILED explanation of your review.
                Concentrate on the modification that you reviewed.
                The code you reviewed is the following:
                ```
                {code}
                ```

                Respond to the LAST message in the CONVERSATION.
                Respond ONLY IF the message is LOOSELY related to the modification in the code.
                Respond ONLY IF the message is a question or an instruction that is put to you.
                If the last message is not a question, but an instruction, follow the instruction.
                The conversation is about the modification in line {line_number}.
                If you skip the response, explain why you skipped it in the response field.
                {format_instructions}
                
                The CONVERSATION is as follows:
                """,
            )
        ]
        messages.extend(message_history)

        template = ChatPromptTemplate.from_messages(messages)
        parser = JsonOutputParser(pydantic_object=PRReviewChatResponse)
        template = template.partial(format_instructions=parser.get_format_instructions())

        chain = template | self.__model | parser

        response: PRReviewChatResponse = chain.invoke({"code": code, "line_number": comment["line"]})
        if response["isSkipped"]:
            return ""
        return response["response"]

    @staticmethod
    def __get_comment_thread(comment: dict[str, Any], comments: PaginatedList[PullRequestComment]) -> list[PullRequestComment]:
        thread_comments = [
            c for c in comments if comment["in_reply_to_id"] == c.id or c.id == comment["id"] or c.in_reply_to_id == comment["in_reply_to_id"]
        ]
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
