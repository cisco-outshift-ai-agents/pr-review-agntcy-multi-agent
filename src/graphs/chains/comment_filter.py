from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

from utils.wrap_prompt import wrap_prompt
from utils.models import ReviewComments
from typing import cast

from langchain.schema import SystemMessage, HumanMessage


def create_comment_filter_chain(model: BaseChatModel) -> RunnableSerializable[dict, dict | ReviewComments]:

    llm_with_structured_output = cast(RunnableSerializable[dict, dict | ReviewComments], model.with_structured_output(ReviewComments))

    system_message = SystemMessage(content=" You are a review agent tasked with filtering a list of PR review comments.\
                                   Your peer has created several comments on a GitHub pull request but it could be that some of them are not useful.\
                                   Your job is to filter these comments based on the instructions below, follow them carefully. \
                                   \
                                   Rules for Filtering: \
                                   A comment is considered not useful if ANY of the following applies: \
                                   - It just states a simple statement or positive feedback or what the user changed in the code without stating a clear issue. \
                                   - It doesn't mention any actionable item. \
                                   \
                                   Input Format: \
                                   comments: The set of comments that you need to filter. \
                                   {input_json_format} \
                                   \
                                   Response format: \
                                   Return ONLY the remaining comments without changing the content or format or anything else in them. \
                                   DO NOT USE markdown in the response.")

    user_message = HumanMessage(content="{question}")

    prompt = ChatPromptTemplate.from_messages(
        messages=[system_message, user_message]
    )

    return prompt | llm_with_structured_output
