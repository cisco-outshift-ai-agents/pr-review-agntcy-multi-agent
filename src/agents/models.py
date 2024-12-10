from pydantic import BaseModel


class GithubDetails(BaseModel):
    installation_id: str
    repo_name: str
    branch_name: str
    pr_number: str
