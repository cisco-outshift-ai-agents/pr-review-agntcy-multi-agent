# Alfred

Alfred is a GitHub application designed to help developers improve their pull requests by providing feedback and suggestions.

## Installation

### SaaS Installation

1. Log in to GitHub.
2. Go to the [GitHub App link](https://github.com/apps/pr-coach) and apply it to the desired repositories.

### Local Run

1. Log in to GitHub.
2. Go to the [GitHub App link](https://github.com/apps/pr-coach-local-run) and apply it to the desired repositories.
3. install smee-client:
   ```bash
   npm install --global smee-client
   ```
4. Run the Smee webhook:
   ```bash
   npx smee -u https://smee.io/1lmHmBA2jqIac4ET -t http://localhost:5000/api/webhook
    ```
4. Ensure you have a valid local .env file under the root of the project.
5.	From the IDE, run:test_local_github
