from typing import Callable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import SystemMessagePromptTemplate, ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from pydantic import BaseModel
from pydantic import Field

from utils.wrap_prompt import wrap_prompt


class ReviewChatResponse(BaseModel):
    is_addressed_to_alfred: bool = Field(description="Indicates if the question or instruction is addressed to AI.")
    is_related_to_code: bool = Field(description="Indicates if the question or instruction is related to the code.")
    message: str = Field(description="Your answer must be placed here.")

def create_review_chat_assistant_chain(model: BaseChatModel) \
        -> Callable[[Sequence[BaseMessage]], RunnableSerializable]:
    def review_chat_assistant_chain(message_history: Sequence[BaseMessage]) -> RunnableSerializable[
        dict, dict | ReviewChatResponse]:
        structured_output_model = model.with_structured_output(ReviewChatResponse)

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
            SET `is_addressed_to_alfred` to `true` IF the question or instruction IS addressed to you as AI.
            SET `is_related_to_code` to `true` IF the question or instruction IS related to the code.
            PLACE your answer in the `message` field.

            The conversation is as follows:""")

        messages = [
            SystemMessagePromptTemplate.from_template(
                system_prompt,
            )
        ]
        messages.extend(message_history)

        template = ChatPromptTemplate.from_messages(messages)

        return template | structured_output_model

    return review_chat_assistant_chain