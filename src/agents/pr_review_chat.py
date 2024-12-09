import re
from typing import Any

from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.PullRequestComment import PullRequestComment
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from pydantic import BaseModel, Field

from agents.agent import Agent
from utils.github_operations import GitHubOperations
from utils.modelfactory import models
from utils.wrap_prompt import wrap_prompt

BOT_USER_TYPE = "Bot"
HUMAN_USER_TYPE = "User"

NOT_RELATED_MESSAGE = "I apologize but your question or instruction is not related to the code so I cannot provide a response."


class PRReviewChatResponse(BaseModel):
    is_addressed_to_alfred: bool = Field(description="Indicates if the response is skipped.")
    is_related_to_code: bool = Field(description="Indicates if the question or instruction is related to the code.")
    message: str = Field(description="Your answer MUST be placed here.")


class PRReviewChatAgent(Agent):
    def __init__(self, github_operations: GitHubOperations):
        super(PRReviewChatAgent, self).__init__()

        self.__github_ops = github_operations
        self.__model = models.get_vertexai()
        self.__parser = PydanticOutputParser(pydantic_object=PRReviewChatResponse)

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

        system_prompt = wrap_prompt("""\
            You are Alfred, a senior software developer and the reviewer of a pull request.
            Your review is the first message in the conversation.
            Other developers have asked you to answer question about your review or have gave instructions about your review.
            Provide a detailed explanation, focusing on the specific modification you reviewed.
            
            The code modifications you reviewed are as follows:
            ```
            {code}
            ```
            The conversation is about the modification in line {line_number}.
            
            Respond to the last message of the the conversation.
            SET `is_addressed_to_alfred` to `true` IF the question or instruction IS addressed to you.
            SET `is_related_to_code` to `true` IF the question or instruction IS related to the code.
            PLACE your answer in the `message` field.
            
            Response format:
            Output MUST be in JSON format, here are the insturctions:
            {format_instructions}
            DO NOT include anything other than the JSON object in the response.
            
            The conversation is as follows:""")

        messages = [
            SystemMessagePromptTemplate.from_template(
                system_prompt,
            )
        ]
        messages.extend(message_history)

        template = ChatPromptTemplate.from_messages(messages)

        template = template.partial(
            format_instructions=self.__parser.get_format_instructions(),
        )

        filled_template = template.invoke({"code": code, "line_number": comment["line"]})
        try:
            response = self.__model.invoke(filled_template)
        except Exception as e:
            raise ValueError(f"Error invoking LLM model: {e}")

        try:
            response = self.__parser.invoke(response)
        except OutputParserException as e:
            raise ValueError(f"Error parsing response {response}: {e}")

        if (not response.is_addressed_to_alfred and not self.__num_of_participants(messages[1:]) == 2) or self.__is_comment_tagged(messages):
            return ""
        if not response.is_related_to_code:
            return NOT_RELATED_MESSAGE
        return response.message

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
                messages.append(AIMessage(content=comment.body, id=comment.user.id))
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

    @staticmethod
    def __num_of_participants(thread: list[BaseMessage]) -> int:
        participants = set()
        for comment in thread:
            participants.add(comment.id)
        return len(participants)

    @staticmethod
    def __is_comment_tagged(thread: list[BaseMessage]) -> bool:
        comment = thread[-1]
        return re.search(r"@[a-zA-Z0-9]+", comment.content) is not None
