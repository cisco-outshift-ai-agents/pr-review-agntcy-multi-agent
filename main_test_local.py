import init
from crew import PRCoachCrew


# installation_id = 54784574
# pr_number = 18
# repo_name = 'bensagi/klar'
init.initialize_environment(True)
installation_id: str = "55482007"
pr_number = 2
repo_name = "bensagi/terraform-aws-eks"
crew = PRCoachCrew()
run = crew.run(installation_id, pr_number, repo_name)
print(run)
