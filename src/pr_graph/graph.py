from langgraph.graph import StateGraph

from config import ConfigManager
from pr_graph.nodes import Nodes
from pr_graph.state import GitHubPRState, create_default_github_pr_state
from utils.github_operations import GitHubOperations
from utils.modelfactory import models


class WorkFlow:
    def __init__(self, installation_id: int, repo_name: str, pr_number: int):
        github_ops = GitHubOperations(str(installation_id))
        config_manager = ConfigManager(github_ops)
        user_config = config_manager.load_config(pr_number, repo_name)
        if user_config is None:
            raise ValueError("User config is None")

        self.nodes = Nodes(installation_id, repo_name, pr_number, models.get_vertexai(), user_config)

    def run(self):
        workflow = StateGraph(GitHubPRState)

        workflow.add_node("fetch_pr", self.nodes.fetch_pr)
        workflow.add_node("fetch_pr_files", self.nodes.fetch_pr_files)
        workflow.add_node("code_reviewer", self.nodes.code_reviewer)
        workflow.add_node("title_description_reviewer", self.nodes.title_description_reviewer)
        workflow.add_node("commenter", self.nodes.commenter)

        workflow.add_edge("fetch_pr", "fetch_pr_files")
        workflow.add_edge("fetch_pr_files", "code_reviewer")
        workflow.add_edge("fetch_pr_files", "title_description_reviewer")
        workflow.add_edge(["code_reviewer", "title_description_reviewer"], "commenter")

        workflow.set_entry_point("fetch_pr")

        init_state = create_default_github_pr_state()
        graph = workflow.compile()

        return graph.invoke(init_state)
