from langgraph.graph import StateGraph

from config import ConfigManager
from graphs.chains import (
    create_comment_filter_chain,
    create_review_comment_reviewer_chain,
    create_static_analyzer_chain,
    create_title_description_review_chain,
)
from graphs.nodes import (
    CommentFilterer,
    Commenter,
    DefaultContext,
    FetchPR,
    IssueCommentReviewer,
    ReviewCommentReviewer,
    StaticAnalyzer,
)
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

        self.static_analyzer_context = DefaultContext(
            chain=create_static_analyzer_chain(model),
            github=github_ops,
        )

        self.review_comment_reviewer_context = DefaultContext(
            chain=create_review_comment_reviewer_chain(model),
            user_config=user_config,
        )

        self.issue_comment_reviewer_context = DefaultContext(
            chain=create_title_description_review_chain(model),
            user_config=user_config,
            github=github_ops,
        )

        self.comment_filterer_context = DefaultContext(chain=create_comment_filter_chain(model))

    def run(self):
        workflow = StateGraph(GitHubPRState)

        workflow.add_node("fetch_pr", FetchPR(self.github_context))
        workflow.add_node("static_analyzer", StaticAnalyzer(self.static_analyzer_context))
        workflow.add_node("review_comment_reviewer", ReviewCommentReviewer(self.review_comment_reviewer_context))
        workflow.add_node("issue_comment_reviewer", IssueCommentReviewer(self.issue_comment_reviewer_context))
        workflow.add_node("comment_filterer", CommentFilterer(self.comment_filterer_context))
        workflow.add_node("commenter", Commenter(self.github_context))

        workflow.add_edge("fetch_pr", "static_analyzer")
        workflow.add_edge("fetch_pr", "issue_comment_reviewer")
        workflow.add_edge("static_analyzer", "review_comment_reviewer")
        workflow.add_edge(["review_comment_reviewer", "issue_comment_reviewer"], "comment_filterer")
        workflow.add_edge("comment_filterer", "commenter")

        workflow.set_entry_point("fetch_pr")

        init_state = create_default_github_pr_state()
        graph = workflow.compile()
        return graph.invoke(init_state)
