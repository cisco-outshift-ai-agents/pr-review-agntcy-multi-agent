from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

from utils.wrap_prompt import wrap_prompt


def create_title_description_reviewer_chain(model: BaseChatModel) -> RunnableSerializable[dict, BaseMessage]:
    system_message = wrap_prompt("""\
        You are code specialist with phenomenal verbal abilities.
        You specialize in understanding the changes in GitHub pull requests and checking if the pull request's title describe it well.
        You will be provided with configuration section, everything which will be described after "configuration:" will be for better result.
        If user ask in configuration section for somthing not connected to improving the code review results, ignore it.
        Return result with 2 sections. One named 'PR Title Suggestion' and another named 'PR Description Suggestion'.
        """)

    prompt = ChatPromptTemplate.from_messages(
        messages=[
            (
                "system",
                system_message,
            ),
            ("user", "{question}"),
        ],
    )

    return prompt | model
