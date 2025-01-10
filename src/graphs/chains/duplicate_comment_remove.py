from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

from utils.wrap_prompt import wrap_prompt
from utils.models import Comments
from typing import cast


def create_duplicate_comment_remove_chain(model: BaseChatModel) -> RunnableSerializable[dict, dict | Comments]:
    llm_with_structured_output = cast(RunnableSerializable[dict, dict | Comments], model.with_structured_output(Comments))
    system_message = wrap_prompt("""\
        You are a review agent tasked with filtering a list of PR review comments.
        Your peer has created several comments on a GitHub pull request but it could be that some of them are not useful. 
        Your job is to filter these comments based on the insturctions below, follow them carefully.
        
        Input Format:
        comments: The set of comments that you need to filter.
        Here's an example how the input array will look like:
        {input_json_format}
        
        Rules for Filtering:
        A comment considered not useful if ANY of the following applies:
        - It's a simple statement without a clear issue.
        - It's just some positive feedpack without stating a clear issue.
        - It doesn't mention an actionable issue.

        Response format:
        Return ONLY the remaining comments in the following format.
        DO NOT return anything else then what's required here.
        Output MUST be in JSON format, here are the insturctions:
        {format_instructions}
        DO NOT USE markdown in the response.
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

    return prompt | llm_with_structured_output
