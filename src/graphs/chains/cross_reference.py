from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableSerializable
from langchain_core.messages import BaseMessage


def create_cross_reference_generator_chain(model: BaseChatModel) -> RunnableSerializable[dict, BaseMessage]:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a senior Terraform engineer. You are given a Terraform codebase and a task to complete."),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    generate = prompt | model
    return generate


def create_cross_reference_reflector_chain(model: BaseChatModel) -> RunnableSerializable[dict, BaseMessage]:
    reflector_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a Terraform verification agent. Validate cross-references by:"
                "Verify Issues:"
                "Check git diff for changes"
                "Confirm issues in the HEAD codebase"
                "Validate file paths and references"
                "Ensure severity level is appropriate"
                "Questionable Issues:"
                "Explain why issues might be incorrect"
                "Provide evidence from the codebase"
                "Suggest improvements for the generator"
                "Detect False Negatives:"
                " Check for missed variable references, resource dependencies, and module interface changes"
                "Response Format"
                "Confirmed Issues: [List]"
                "Incorrect Issues: [List with explanations]"
                "Additional Concerns: [If any critical issues were missed]"
                "Focus on accuracy and thoroughness."
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    reflector = reflector_prompt | model
    return reflector
