# PR Coach
[![Release](https://img.shields.io/github/v/release/cisco-ai-agents/tf-pr-review-agntcy-multi-agent?display_name=tag)](CHANGELOG.md)
[![Contributor-Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-fbab2c.svg)](CODE_OF_CONDUCT.md)

PR Coach is a GitHub application designed to help developers improve their pull requests by providing feedback and suggestions.

## Overview

![Overview of PR Coach](./docs/resources/overview.svg)

## Installation

### Local Run

#### Create your own PR Coach GitHub App

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
     - Issues read and write access
     - Contents read access
   - Under `Subscribe to events`:
     - Pull request
     - Pull request review
     - Pull request review comment
     - Pull request review thread
     - Issues
     - Issue comments

#### Install your own PR Coach GitHub App to a repository

1. Go to `Developer settings` under your GitHub profile settings
2. Click to your GitHub App name
3. Select `Install App` sidemenu option
4. Choose an account and click to `Install` button
5. Select your desired repository and click `Install`

#### Setup PR Coach local instance

<b>Prereq: create GitHub app before running PR coach instance locally.</b>



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

2. If planning on running remote agents, set `AGENT_MODE` to `agp` or `acp` based on your requirements.

##### Automatic way to install python environment with dependencies

Run `make setup` in this project folder

#### Run PR Coach locally

1. Start the smee webhook:
   ```bash
   npx smee -u https://smee.io/{YOUR_WEBHOOK_PATH} -t http://localhost:5500/api/webhook
    ```
2.	Activate virtual environment and start PR Coach:
   ```bash
   source .venv/bin/activate &&
   python3 main_local.py
   ```

3. Create a PR or an event on your PR (like new commit) and comment <b>Alfred review</b> on the pull request

## Evaluation

For detailed instructions on how to evaluate this repository, please refer to the [Evaluation Guide](eval/README.md).

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

For more information about our various agents, please visit the [agntcy project page](https://github.com/agntcy).
