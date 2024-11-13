import os
from crewai import Crew, Process
from agents import PRCoachAgents
from tasks import PRCoachTasks
from azure_client import AzureClient
from utils.config_file_pr import GitHubOperations

os.environ["OTEL_SDK_DISABLED"] = "true"


class PRCoachCrew:
    def __init__(self):
        self.agents = PRCoachAgents()
        self.tasks = PRCoachTasks()
        self.llm = AzureClient().get_azure_client()

    def run(self, installation_id, pr_number, repo_name):
        github_ops = GitHubOperations(installation_id)
        result = github_ops.retrieve_md_content_from_pr(pr_number, repo_name)

        github_agent = self.agents.github_agent()
        code_reviewer = self.agents.code_reviewer()
        security_reviewer = self.agents.security_reviewer()
        title_reviewer = self.agents.title_reviewer()
        description_reviewer = self.agents.description_reviewer()
        github_commenter_agent = self.agents.github_commenter_agent()

        fetch_pull_request_info_task = self.tasks.fetch_pull_request_info_task(
            agent=github_agent, installation_id=installation_id, pr_number=pr_number, repo_name=repo_name
        )
        code_review_task = self.tasks.code_review_task(code_reviewer, [fetch_pull_request_info_task])
        security_analysis_task = self.tasks.security_analysis_task(security_reviewer, [fetch_pull_request_info_task])
        title_review_task = self.tasks.title_review_task(title_reviewer, [fetch_pull_request_info_task])
        description_review_task = self.tasks.description_review_task(description_reviewer, [fetch_pull_request_info_task])
        commenter_task = self.tasks.commenter_task(
            agent=github_commenter_agent, installation_id=installation_id, pr_number=pr_number, repo_name=repo_name, context=[code_review_task]
        )

        crew = Crew(
            agents=[github_agent, code_reviewer, github_commenter_agent, security_reviewer, title_reviewer, description_reviewer],
            tasks=[
                fetch_pull_request_info_task,
                code_review_task,
                commenter_task,
                security_analysis_task,
                title_review_task,
                description_review_task,
            ],
            verbose=True,
            process=Process.hierarchical,
            manager_llm=self.llm,
            max_rpm=5,
        )

        return crew.kickoff()
