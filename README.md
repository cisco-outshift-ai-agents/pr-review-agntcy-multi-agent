# Multi-Agent Pull Request Reviewer
[![Release](https://img.shields.io/github/v/release/cisco-ai-agents/tf-pr-review-agntcy-multi-agent?display_name=tag)](CHANGELOG.md)
[![Contributor-Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-fbab2c.svg)](CODE_OF_CONDUCT.md)

A GitHub app that provides feedback on pull requests that include Terraform files.

## Overview

**<NOTE: Modify "Alfred" in the diagram. Add diagram of the "Pull Request Reviewer" 
backend workflow that includes external agents>**

This project demonstrates the use of AGNTCY for building multi-agent
applications (MAA), offering a tool for exploration and experimentation. It
serves as a practical starting point for creating a GitHub bot designed to
assist with Infrastructure as Code (IaC) pull request (PR) reviews.

It includes GitHub integration and agents capable of performing basic Terraform
PR reviews. It is ready for immediate use or modification to suit your use case.
Example extentions of the framework include modifying the existing agent
workflow, adding new agents, or modifying agent prompts.

WIP: How it works. Langchain. Workflow. Agents. 

![image](https://github.com/user-attachments/assets/3c1b474b-b345-41d8-b952-d1d1fc497e2c)

![Overview of Multi-agent Pull Request Reviewer](./docs/resources/overview.svg)

## About the Project
WIP: Outline of this repository. Where to find the agent parts.

### How to modify the Project for your own PR Review use case
WIP: Here's how to take this thing and evolve it in line with the original intent, or adapt to your use case

### How to contribute agents
WIP: how would users publish agents that others can use?

## Installation
WIP: overview paragraph on the supported installation model and deployment as a GitHub application.
WIP: diagram of the model and GitHub.

### Local Run

#### Deploy your own Multi-Agent Pull Request Reviewer GitHub App

1. Start a new webhook channel on [smee.io](https://smee.io/) and save the Webhook Proxy URL for later use.
2. Log in to GitHub.
3. Register a `new GitHub App` under your profile based on the [GitHub Docs about creating apps](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app#registering-a-github-app)
   - Paste `Webhook Proxy URL` to the Webhook URL field
   - Create your own `webhook secret`
   - Generate a `private key` and download it
   - Save the `GitHub App ID` for later use
4. Go to `Permissions & events` and set the followings up
   - Under `Repository permissions`:
     - Checks read and write access
     - Contents read access
     - Pull requests read and write access
   - Under `Subscribe to events`:
     - Pull request
     - Pull request review
     - Pull request review comment
     - Pull request review thread

#### Install your own Multi-Agent PR Reviewer GitHub App to a repository

1. Go to `Developer settings` under your GitHub profile settings
2. Click to your GitHub App name
3. Select `Install App` sidemenu option
4. Choose an account and click to `Install` button
5. Select your desired repository and click `Install`

#### Set up your local instance of Multi-Agent PR Reviewer

1. Copy the .env.example file to .env and fill up with the followings:
   - GITHUB_APP_ID
   - one of:
       - `GITHUB_APP_PRIVATE_KEY`
       - `GITHUB_APP_PRIVATE_KEY_FILE` - this should point to a local file with the private key
   - `GITHUB_WEBHOOK_SECRET`
   - `GCP_SERVICE_ACCOUNT` - this should point to a local file with the GCP service account where the model is hosted
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_DEPLOYMENT`
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_API_VERSION`
   - set `ENVIRONMENT` to `"local"`

2. If planning on running remote agents, set `AGENT_MODE` to `agp` or `langchain_ap` based on your requirements.

##### Automatic way to install python environment with dependencies

Run `make setup` in this project folder

##### Manual way to install with dependencies

1. Install [pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#installation) and install Python 3.12.9
   ```bash
   brew update && brew install pyenv &&
   pyenv install 3.12.9
   ```
2. Create venv and activate
   ```bash
   ~/.pyenv/versions/3.12.9/bin/python3 -m venv .venv &&
   source .venv/bin/activate
   ```
3. Install [poetry](https://python-poetry.org/docs/#installing-manually) and install project dependencies
   ```bash
   pip install -U pip setuptools;
   pip install poetry &&
   poetry install
   ```
4. Install smee-client:
   ```bash
   npm install --global smee-client
   ```
5. [Install Terraform](https://developer.hashicorp.com/terraform/install)
   ```bash
   brew tap hashicorp/tap
   brew install hashicorp/tap/terraform
   ```
6. [Install TFlint](https://github.com/terraform-linters/tflint?tab=readme-ov-file#installation)
   ```bash
   brew install tflint
   ```

#### Run Multi-agent PR Reviewer locally

1. Start the smee webhook:
   ```bash
   npx smee -u https://smee.io/{YOUR_WEBHOOK_PATH} -t http://localhost:5500/api/webhook
    ```
2.	Activate virtual environment and start Multi-agent PR Reviewer:
   ```bash
   source .venv/bin/activate &&
   python3 main_local.py
   ```
3. Create an event on your PR (like new commit)

#### Setup Multi-Agent PR Reviewer local instance using Lambda

Multi-Agent PR Reviewer is deployed as a Lambda function so optionally you can also run this locally instead of the above mentioned webserver in `main_local.py`. For this, you need the AWS SAM CLI installed.

1. Make sure that `.env` file exists and is filled with the necessary environment variables.

2. Login to the `outshift-common-dev` AWS account using duo-sso.

3. Start the Smee client for the Lambda:
   ```bash
   make smee_id=your-smee-id start-smee-for-lambda
   ```

4. Build and start the Lambda using sam:
   ```bash
   make start-lambda
   ```


---
## Roadmap

See the [open issues](https://github.com/cisco-ai-agents/tf-pr-review-agntcy-multi-agent/issues) for a list
of proposed features (and known issues).

---
## Contributing

Contributions are what make the open source community such an amazing place to
learn, inspire, and create. Any contributions you make are **greatly
appreciated**. For detailed contributing guidelines, please see
[CONTRIBUTING.md](CONTRIBUTING.md)

---
## License

Distributed under the Apache-2.0 License. See [LICENSE](LICENSE) for more
information.

---
## Contact

[cisco-outshift-ai-agents@cisco.com](mailto:cisco-outshift-ai-agents@cisco.com)

Project Link:
[https://github.com/cisco-ai-agents/tf-pr-review-agntcy-multi-agent](https://github.com/cisco-ai-agents/tf-pr-review-agntcy-multi-agent)

---
## Acknowledgements

- [Langgraph](https://github.com/langchain-ai/langgraph) for the agentic platform.
- [https://github.com/othneildrew/Best-README-Template](https://github.com/othneildrew/Best-README-Template), from which this readme was adapted

For more information about our various agents, please visit the [agntcy project page](https://github.com/agntcy).
