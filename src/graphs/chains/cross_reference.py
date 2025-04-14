from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableSerializable
from langchain_core.messages import BaseMessage


def create_cross_reference_generator_chain(model: BaseChatModel) -> RunnableSerializable[dict, BaseMessage]:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system",
             "You are a senior Terraform engineer. You are given a Terraform codebase and a task to complete."),
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
                "You are a Terraform verification agent. Validate cross-reference analysis by:\n\n"
                "1. Verifying reported issues via:\n"
                "   - git diff checks\n"
                "   - confirming existence in HEAD\n"
                "   - validating file paths and references\n"
                "   - assessing severity\n\n"
                "2. For invalid/questionable issues:\n"
                "   - explain why\n"
                "   - give supporting evidence\n"
                "   - suggest improvements to the generator\n\n"
                "3. Identify false negatives in:\n"
                "   - variable references\n"
                "   - resource dependencies\n"
                "   - module interface changes\n\n"
                "Respond with:\n"
                "### Validation Results\n"
                "- Confirmed Issues: [...]\n"
                "- Incorrect Issues: [... with reasons]\n"
                "- Additional Concerns: [... if critical]\n\n"
                "Be accurate and thorough.",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    reflector = reflector_prompt | model
    return reflector
