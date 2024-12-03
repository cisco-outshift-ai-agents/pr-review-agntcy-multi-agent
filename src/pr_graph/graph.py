from langgraph.graph import StateGraph
from pr_graph.nodes import Nodes
from pr_graph.state import GitHubPRState
from utils.github_operations import GitHubOperations
from utils.modelfactory import models
from config import ConfigManager


class WorkFlow:
    def __init__(self, installation_id: int, repo_name: str, pr_number: int):
        github_ops = GitHubOperations(str(installation_id))
        config_manager = ConfigManager(github_ops)
        user_config = config_manager.load_config(pr_number, repo_name)
        self.nodes = Nodes(installation_id, repo_name, pr_number, models.get_vertexai(), user_config)

    def run(self):
        workflow = StateGraph(GitHubPRState)

        workflow.add_node("code_reviewer", self.nodes.code_reviewer)
        workflow.add_node("commenter", self.nodes.commenter)
        workflow.add_node("security_reviewer", self.nodes.security_reviewer)
        workflow.add_node("title_description_reviewer", self.nodes.title_description_reviewer)

        workflow.set_entry_point("code_reviewer")
        workflow.set_entry_point("security_reviewer")
        workflow.set_entry_point("title_description_reviewer")

        workflow.add_edge("code_reviewer", "commenter")
        workflow.add_edge("security_reviewer", "commenter")
        workflow.add_edge("title_description_reviewer", "commenter")

        init_state: GitHubPRState = {**self.nodes.fetch_pr()}

        return workflow.compile().invoke(init_state)
