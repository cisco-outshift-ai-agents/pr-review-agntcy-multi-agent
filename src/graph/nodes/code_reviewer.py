from functools import partial
from graph.state import GitHubPRState
from .contexts import CodeReviewContext
from utils.logging_config import logger as log
from graph.chains.code_review import CodeReviewResponse
import json


def create_code_reviewer_node(context: CodeReviewContext):
    def code_reviewer(state: GitHubPRState) -> GitHubPRState:
        log.info("in code reviewer")
        existing_comments = state["existing_comments"]
        result: CodeReviewResponse = context.chain.invoke(
            {
                "question": f"""
            If a comment already exists for a line in a file, DO NOT create another comment for the same line. Here are the JSON list representation of existing comments on the PR:
            {json.dumps([existing_comment.model_dump() for existing_comment in existing_comments], indent=2)}
            
            Review the following code changes and ONLY provide NEW unique comments if it has any additional information that don't duplicate the existing ones:
            {state["changes"]}
            
            Configuration:
                {context.user_config.get("Code Review", "")}
                {context.user_config.get("Security & Compliance Policies", "")}
            """
            }
        )
        comments = result.issues

        log.info(f"""
        code reviewer finished.
        comments: {json.dumps([comment.model_dump() for comment in comments], indent=4)}
        """)

        return {**state, "comments": comments}

    return partial(code_reviewer)
