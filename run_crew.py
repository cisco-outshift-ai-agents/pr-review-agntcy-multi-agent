import init
from crew import PRCoachCrew


installation_id = 55689337
pr_number = 18
repo_name = "bensagi/klar"

# installation_id:str = '55482007'
# pr_number = 1
# repo_name = 'bensagi/terraform-aws-eks'

init.initialize_environment(True)
crew = PRCoachCrew()
run = crew.run(installation_id, pr_number, repo_name)
print(run)
