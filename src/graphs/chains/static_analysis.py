from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

from utils.wrap_prompt import wrap_prompt


def create_static_analyzer_chain(model: BaseChatModel) -> RunnableSerializable[dict, BaseMessage]:
    # TODO The below prompt is not perfect, sometimes it removes important details from the errors, fix this!

    system_message = wrap_prompt("""\
                Your are an experienced software egineer who's task is to organize Terraform related linter outputs.
                You will get different linter outputs from the user (tflint, tfsec, terraform validate etc.).
                
                Organize the issues into a list, but keep every detail!
                Remove ONLY the line numbers but keep everything else, don't remove any detail from the issue message.
                DO NOT remove any information from the issues, keep every detail! You are only allowed to delete the line numbers, nothing else!
                Each item in the list should have the following format: {{file name}}: {{full issue description}}
                                
                Only return the list of issues in your response, nothing else.
                """)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_message,
            ),
            ("user", "{linter_outputs}"),
        ]
    )

    return prompt | model
