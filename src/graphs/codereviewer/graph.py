from langgraph.graph import StateGraph

from config import ConfigManager
from graphs.codereviewer.chains import (
    create_code_review_chain,
    create_title_description_review_chain,
)
from graphs.codereviewer.nodes.code_reviewer import create_code_reviewer_node
from graphs.codereviewer.nodes.commenter import create_commenter_node
from graphs.codereviewer.nodes.contexts import (
    GitHubContext,
    CodeReviewContext,
    TitleDescriptionContext,
)
from graphs.codereviewer.nodes.fetch_pr import create_fetch_pr_node
from graphs.codereviewer.nodes.title_description_reviewer import create_title_description_reviewer_node
from graphs.codereviewer.state import GitHubPRState, create_default_github_pr_state
from utils.github_operations import GitHubOperations
from utils.modelfactory import models


class CodeReviewerWorkflow:
    def __init__(self, installation_id: int, repo_name: str, pr_number: int):
        github_ops = GitHubOperations(str(installation_id))
        config_manager = ConfigManager(github_ops)
        user_config = config_manager.load_config(pr_number, repo_name)
        if user_config is None:
            raise ValueError("User config is None")

        model = models.get_vertexai()

        self.github_context = GitHubContext(github=github_ops, repo_name=repo_name, pr_number=pr_number)

        self.code_review_context = CodeReviewContext(chain=create_code_review_chain(model), user_config=user_config)

        self.title_desc_context = TitleDescriptionContext(chain=create_title_description_review_chain(model), user_config=user_config)

    def run(self):
        workflow = StateGraph(GitHubPRState)

        workflow.add_node("fetch_pr", create_fetch_pr_node(self.github_context))
        workflow.add_node("code_reviewer", create_code_reviewer_node(self.code_review_context))
        workflow.add_node("title_description_reviewer", create_title_description_reviewer_node(self.title_desc_context))
        workflow.add_node("commenter", create_commenter_node(self.github_context))

        workflow.add_edge("fetch_pr", "code_reviewer")
        workflow.add_edge("fetch_pr", "title_description_reviewer")
        workflow.add_edge(["code_reviewer", "title_description_reviewer"], "commenter")

        workflow.set_entry_point("fetch_pr")

        init_state = create_default_github_pr_state()
        graph = workflow.compile()
        return graph.invoke(init_state)
