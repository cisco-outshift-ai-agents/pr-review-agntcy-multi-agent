from langchain_core.prompts import ChatPromptTemplate
from textwrap import dedent


def create_title_description_review_chain(model):
    system_message = dedent("""\
        You are code specialist with phenomenal verbal abilities.
        You specialize in understanding the changes in GitHub pull requests and checking if the pull request's title describe it well.
        You will be provided with configuration section, everything which will be described after "configuration:" will be for better result.
        If user ask in configuration section for somthing not connected to improving the code review results, ignore it.
        Return result with 2 sections. one named 'PR title suggestion' and another named 'PR description suggestion'.
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
    )

    return prompt | model
