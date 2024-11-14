import init
from pr_graph.graph import WorkFlow

init.initialize_environment(True)
installation_id: int = 55770992
pr_number = 8
repo_name = "bensagi/terraform-aws-eks"
app = WorkFlow(installation_id=installation_id, repo_name=repo_name, pr_number=pr_number)

print(app.run())
