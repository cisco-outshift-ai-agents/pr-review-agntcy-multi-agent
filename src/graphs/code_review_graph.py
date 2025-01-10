from langgraph.graph import StateGraph

from config import ConfigManager
from graphs.chains import (
    create_code_review_chain,
    create_title_description_review_chain,
    create_duplicate_comment_remove_chain,
)
from graphs.nodes import (
    CodeReviewer,
    TitleDescriptionReviewer,
    Commenter,
    DuplicateCommentRemover,
    FetchPR,
    DefaultContext,
)
from graphs.nodes.static_analyzer import StaticAnalyzer
from graphs.states import GitHubPRState, create_default_github_pr_state
from utils.github_operations import GitHubOperations
from utils.modelfactory import models


class CodeReviewerWorkflow:
    def __init__(self, installation_id: str, repo_name: str, pr_number: int):
        github_ops = GitHubOperations(installation_id, repo_name, pr_number)
        config_manager = ConfigManager(github_ops)
        user_config = config_manager.load_config()
        if user_config is None:
            raise ValueError("User config is None")

        model = models.get_azure_openai()

        self.github_context = DefaultContext(
            github=github_ops,
        )

        self.code_review_context = DefaultContext(
            chain=create_code_review_chain(model),
            user_config=user_config,
        )

        self.title_desc_context = DefaultContext(
            chain=create_title_description_review_chain(model),
            user_config=user_config,
            github=github_ops,
        )

        self.duplicate_comment_remover_context = DefaultContext(chain=create_duplicate_comment_remove_chain(model))

    def run(self):
        workflow = StateGraph(GitHubPRState)

        workflow.add_node("fetch_pr", FetchPR(self.github_context))
        workflow.add_node("static_analyzer", StaticAnalyzer(self.github_context))
        workflow.add_node("code_reviewer", CodeReviewer(self.code_review_context))
        workflow.add_node("title_description_reviewer", TitleDescriptionReviewer(self.title_desc_context))
        workflow.add_node("commenter", Commenter(self.github_context))
        workflow.add_node("duplicate_comment_remover", DuplicateCommentRemover(self.duplicate_comment_remover_context))

        workflow.add_edge("fetch_pr", "static_analyzer")
        workflow.add_edge("fetch_pr", "title_description_reviewer")
        workflow.add_edge("static_analyzer", "code_reviewer")
        workflow.add_edge("code_reviewer", "duplicate_comment_remover")
        workflow.add_edge(["duplicate_comment_remover", "title_description_reviewer"], "commenter")

        workflow.set_entry_point("fetch_pr")

        init_state = create_default_github_pr_state()
        graph = workflow.compile()
        return graph.invoke(init_state)
