import os
from typing import Union

from google.cloud import aiplatform
from langgraph.graph import StateGraph

from pr_graph.nodes import Nodes
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from langchain_openai import AzureChatOpenAI

from pr_graph.state import GitHubPRState
from utils.config_file_pr import GitHubOperations


class WorkFlow:
    def __init__(self, installation_id: int, repo_name: str, pr_number: int):
        # Initialize the AI model
        model = AzureChatOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
            openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
        )
        github_ops = GitHubOperations(str(installation_id))
        user_config = github_ops.retrieve_md_content_from_pr(pr_number, repo_name)
        self.nodes = Nodes(installation_id, repo_name, pr_number, model, user_config)

    def run(self):
        workflow = StateGraph(GitHubPRState)

        workflow.add_node("fetch_pr", self.nodes.fetch_pr)
        workflow.add_node("code_reviewer", self.nodes.code_reviewer)
        workflow.add_node("commenter", self.nodes.commenter)
        workflow.add_node("security_reviewer", self.nodes.security_reviewer)
        workflow.add_node("title_description_reviewer", self.nodes.title_description_reviewer)

        workflow.set_entry_point("fetch_pr")

        workflow.add_edge("fetch_pr", "code_reviewer")
        workflow.add_edge("code_reviewer", "security_reviewer")
        workflow.add_edge("security_reviewer", "title_description_reviewer")
        workflow.add_edge("title_description_reviewer", "commenter")
        # workflow.add_edge('security_reviewer', 'commenter')
        # workflow.add_edge('title_description_reviewer', 'commenter')
        return workflow.compile().invoke({"changes": [], "comments": [], "title": None, "description": None})
