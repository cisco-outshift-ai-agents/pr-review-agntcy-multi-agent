from langgraph.graph import StateGraph

from config import ConfigManager
from graphs.chains import (
    create_comment_filter_chain,
    create_code_reviewer_chain,
    create_static_analyzer_chain,
    create_title_description_reviewer_chain,
)
from graphs.nodes import (
    CommentFilterer,
    Commenter,
    DefaultContext,
    FetchPR,
    TitleDescriptionReviewer,
    CodeReviewer,
    StaticAnalyzer,
    CrossReferenceGenerator,
    CrossReferenceReflector,
    CrossReferenceInitializer,
    CrossReferenceCommenter,
)
from graphs.states import GitHubPRState, create_default_github_pr_state
from utils.github_operations import GitHubOperations
from utils.logging_config import logger as log
from utils.modelfactory import models


class CodeReviewerWorkflow:
    def __init__(self, installation_id: str, repo_name: str, pr_number: int):
        github_ops = GitHubOperations(installation_id, repo_name, pr_number)
        config_manager = ConfigManager(github_ops)
        user_config = config_manager.load_config()
        if user_config is None:
            log.info("User config not found. Continuing without custom configuration.")

        self.model = models.get_azure_openai()

        self.github_context = DefaultContext(
            github=github_ops,
        )

        self.static_analyzer_context = DefaultContext(
            chain=create_static_analyzer_chain(self.model),
            github=github_ops,
        )

        self.code_review_context = DefaultContext(
            chain=create_code_reviewer_chain(self.model),
            user_config=user_config,
        )

        self.title_desc_context = DefaultContext(
            chain=create_title_description_reviewer_chain(self.model),
            user_config=user_config,
            github=github_ops,
        )

        self.comment_filterer_context = DefaultContext(chain=create_comment_filter_chain(self.model))

    def run(self):
        workflow = StateGraph(GitHubPRState)

        workflow.add_node("fetch_pr", FetchPR(self.github_context))
        workflow.add_node("static_analyzer", StaticAnalyzer(self.static_analyzer_context))
        workflow.add_node("code_reviewer", CodeReviewer(self.code_review_context))
        workflow.add_node("title_description_reviewer", TitleDescriptionReviewer(self.title_desc_context))
        workflow.add_node("comment_filterer", CommentFilterer(self.comment_filterer_context))
        workflow.add_node("cross_reference_initializer", CrossReferenceInitializer(self.github_context, self.model))
        workflow.add_node("cross_reference_generator", CrossReferenceGenerator(self.github_context, self.model))
        workflow.add_node("cross_reference_reflector", CrossReferenceReflector(self.github_context, self.model))
        workflow.add_node("cross_reference_commenter", CrossReferenceCommenter(self.github_context, self.model))
        workflow.add_node("commenter", Commenter(self.github_context))

        def should_continue(state: GitHubPRState):
            if len(state["messages"]) > 4:
                # End after 3 iterations
                return "cross_reference_commenter"
            return "cross_reference_reflector"

        workflow.add_edge("fetch_pr", "static_analyzer")
        workflow.add_edge("fetch_pr", "title_description_reviewer")
        workflow.add_edge("static_analyzer", "cross_reference_initializer")
        workflow.add_edge("static_analyzer", "code_reviewer")
        workflow.add_edge("cross_reference_initializer", "cross_reference_generator")
        workflow.add_conditional_edges("cross_reference_generator", should_continue)
        workflow.add_edge("cross_reference_reflector", "cross_reference_generator")
        workflow.add_edge(["cross_reference_commenter", "code_reviewer"], "comment_filterer")
        workflow.add_edge(["comment_filterer", "title_description_reviewer"], "commenter")

        workflow.set_entry_point("fetch_pr")

        init_state = create_default_github_pr_state()
        graph = workflow.compile()
        graph.get_graph().draw_mermaid_png(output_file_path="graph.png")
        return graph.invoke(init_state)
