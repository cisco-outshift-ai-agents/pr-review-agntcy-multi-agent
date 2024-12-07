from typing import Iterable, Callable

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import SystemMessagePromptTemplate, ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableSerializable

from graphs.reviewchat.chains.models import ReviewChatResponse


def create_review_chat_assistant_chain(model: Runnable) \
        -> Callable[[Iterable[BaseMessage]], RunnableSerializable]:
    def review_chat_assistant_chain(message_history: Iterable[BaseMessage]) -> RunnableSerializable:
        system_message = SystemMessagePromptTemplate.from_template(
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
            """
        )

        messages = [system_message, *message_history]
        template = ChatPromptTemplate.from_messages(messages)

        parser = PydanticOutputParser(pydantic_object=ReviewChatResponse)

        template = template.partial(format_instructions=parser.get_format_instructions())

        return template | model | parser

    return review_chat_assistant_chain
