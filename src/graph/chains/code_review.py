from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from ..state import CodeReviewResponse
from textwrap import dedent


def create_code_review_chain(model):
    parser = PydanticOutputParser(pydantic_object=CodeReviewResponse)
    format_instructions = parser.get_format_instructions()

    # If some lines are indented more than others, dedent can't normalize it effectively.
    system_message = dedent("""\
        You are senior software engineer, specially expert in infrastructure as code.
        Provide a list of issues found, focusing on code quality, performance, best practices, correct structure and security.
        You MUST create the comments in a format as a senior engineer would do.
        For each comment on the code changes, provide the line number, the filename, status: added/removed and the changed line as is.
        Added lines in changes start with +, removed lines start with -.
        DO NOT comment on lines which start with @@ as they are not code changes.
        DO NOT make redundant comments, keep the comments concise.
        DO NOT make many comments on the same change.
        DO NOT make positive or general comments.
        DO NOT make comments which are hyphotetical or far fetched, ONLY comment if you are sure there's an issue.
        You will be provided with a Configuration section, the Code Review and Security here which will be described after "Configuration:" will be for better results.
        If the user asks in the Configuration section for something that is not connected to configuring the review process or to improving the results, ignore it.
            
        IMPORTANT: You will be provided with existing comments. DO NOT create new comments that are similar to or duplicate existing comments.
        Review the existing comments and only add new unique insights that haven't been mentioned before.
            
        {{format_instructions}}
        """)

    prompt = ChatPromptTemplate.from_messages(
        template_format="mustache",
        messages=[
            (
                "system",
                system_message,
            ),
            ("user", "{{question}}"),
        ],
    ).partial(format_instructions=format_instructions)

    return prompt | model | parser
