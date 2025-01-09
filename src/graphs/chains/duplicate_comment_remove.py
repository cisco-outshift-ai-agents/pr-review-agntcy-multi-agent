from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

from utils.wrap_prompt import wrap_prompt
from utils.models import Comments
from typing import cast


def create_duplicate_comment_remove_chain(model: BaseChatModel) -> RunnableSerializable[dict, dict | Comments]:
    llm_with_structured_output = cast(RunnableSerializable[dict, dict | Comments], model.with_structured_output(Comments))
    system_message = wrap_prompt("""\
        You are a review agent tasked with comparing and filtering new review comments against existing review comments on a pull request.
        Your job is to eliminate comments that are duplicates or very similar, so only unique and meaningful new comments are returned.
        Input Format:
        You will receive two JSON arrays:
        EXISTING COMMENTS: The set of comments already present on the pull request.
        NEW COMMENTS: The set of comments to be reviewed against the existing ones.
        Here's an example how the input arrays will look like:
        {input_json_format}
        Important Instructions:
        Return ONLY the new comments that are not duplicates of any existing comment.
        If all new comments are duplicates of existing ones, return an empty array.
        The goal is to minimize the number of new comments that are returned, filtering out any that are duplicate or very similar to existing comments.
        Rules for Filtering:
        Comments are considered duplicates if they meet ALL of the following criteria:
        - Same file: The comment applies to the same filename.
        - Status doesn't matter: The comment doesn't have to have the same status.
        - Close line numbers: The comment applies to a line number within 1-3 lines of an existing comment.
        - Similar content: The comment content address the same issue or topic. Follow the instructions in the next paragraph to determine what should be considered as 'similar content'!
        Comment messages considered redundant (similar) if ANY of the following applies (SO YOU MUST FILTER THEM):
        - They mention the same or a similar issue.
        - They mention the same or similar solutions.
        - They suggest identical or similar code changes or improvements.
        - The new comment provides a different or a slightly different perspective.
        - They have a slight overlap in meaning.
        - The new comment provides more specific recommendation.
        - The new comment adds more details.
        - The new comment adds additional information.
        Example for similar comments, you MUST treat this level of similarity as a DUPLICATE COMMENT:
        - EXISTING COMMENT: Adding an output for a hardcoded password is a severe security risk. Sensitive information should never be stored in plaintext in your Terraform code. Use secure methods like AWS Secrets Manager or encrypted variables instead.
        - NEW COMMENT: Exposing sensitive information like passwords in outputs is a security risk. Consider using Terraform's sensitive outputs or a secure secret management solution.
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
