import os
from langgraph.graph import StateGraph

from config import ConfigManager
from graphs.chains import (
    create_comment_filter_chain,
    create_code_reviewer_chain,
    create_static_analyzer_chain,
    create_title_description_reviewer_chain,
    create_cross_reference_generator_chain,
    create_cross_reference_reflector_chain,
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
from graphs.nodes.remote_graphs.ap.static_analyzer import stateless_remote_static_analyzer_request
from graphs.nodes.remote_graphs.ap.code_reviewer import stateless_remote_code_review_request
from graphs.nodes.remote_graphs.agp.static_analyzer import node_remote_agp
from graphs.nodes.remote_graphs.agp.code_reviewer import node_remote_agp as code_reviewer_agp
from graphs.states import GitHubPRState, create_default_github_pr_state
from utils.constants import AGENT_MODE_ENV
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

        self.cross_reference_generator_context = DefaultContext(
            chain=create_cross_reference_generator_chain(self.model),
        )

        self.cross_reference_reflector_context = DefaultContext(
            chain=create_cross_reference_reflector_chain(self.model),
        )
        self.comment_filterer_context = DefaultContext(chain=create_comment_filter_chain(self.model))

    async def run(self):
        agent_mode = os.getenv(AGENT_MODE_ENV, "local").lower()
        log.info(f"Running in {agent_mode} mode")
        workflow = StateGraph( GitHubPRState)
 
        workflow.add_node("fetch_pr", FetchPR(self.github_context))
        if agent_mode == "local":
            workflow.add_node("static_analyzer", StaticAnalyzer(self.static_analyzer_context))
            workflow.add_node("code_reviewer", CodeReviewer(self.code_review_context))
        elif agent_mode == "langchain_ap":
            workflow.add_node(
                "static_analyzer",
                lambda state: stateless_remote_static_analyzer_request(state, "http://localhost:8133/api/v1/runs")
            )
            workflow.add_node(
                "code_reviewer",
                lambda state: stateless_remote_code_review_request(state, "http://localhost:8123/api/v1/runs")
            )
        elif agent_mode == "agp":
            workflow.add_node("static_analyzer", node_remote_agp)
            workflow.add_node("code_reviewer", code_reviewer_agp)
        else:
            raise ValueError(f"Invalid agent mode: {agent_mode}. Must be one of 'local', 'langchain_ap', 'agp'")
        workflow.add_node("title_description_reviewer", TitleDescriptionReviewer(self.title_desc_context))
        workflow.add_node("comment_filterer", CommentFilterer(self.comment_filterer_context))
        workflow.add_node("cross_reference_initializer", CrossReferenceInitializer(self.github_context))
        workflow.add_node("cross_reference_generator", CrossReferenceGenerator(self.cross_reference_generator_context))
        workflow.add_node("cross_reference_reflector", CrossReferenceReflector(self.cross_reference_reflector_context))
        workflow.add_node("cross_reference_commenter", CrossReferenceCommenter())
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
        result = await graph.ainvoke(init_state)
        return result
