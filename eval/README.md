## Introduction

This eval/ subdirectory contains a tool designed to **evaluate the performance of the Multi-Agent Pull Request (PR) Reviewer**. The evaluation tool allows you to test and analyze the Multi-Agent PR Reviewer by replaying the history of any (Terraform) Git repository and then using "LLM-as-a-judge" to evaluate the results.

### How It Works

1. **Repository History Replay:** The tool extracts the historical pull requests (PRs) from a reference repository and replays the base commit and final merge commit within each PR.
2. **Automated Review:** For each replayed PR, the Multi-Agent PR Reviewer provides an automated review.
3. **Quality Assessment:** A Large Language Model (LLM) acts as an independent judge to evaluate the quality of the reviews provided by the Multi-Agent system.
4. **Report Generation:** The results are summarized into a report, giving a performance rating for the PR reviewer.


## Prerequisites for the eval tool

1. Install [pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#installation) and install Python 3.12.9
   ```bash
   brew update && brew install pyenv &&
   pyenv install 3.12.9

2. Create venv and activate
   ```bash
   ~/.pyenv/versions/3.12.9/bin/python3 -m venv .evalvenv &&
   source .evalvenv/bin/activate
   ```
3. Install dependencies of eval using eval_requirements.txt:
   
   ```sh
   cd eval
   ```
   ```sh
   pip install -r eval_requirements.txt
   ```

## Steps to Run the eval tool

### 1. Data Generation/Collection
   - If a `.tar.gz` file (e.g., `azure_terraform_dataset.tar.gz`) is present along with the corresponding metadata (e.g., `prdataset.json`), you can skip this step.
   - Otherwise, generate or collect the required data by running:
     ```sh
     python github_data_collection.py --config_file configs/gen_config.yml
     ```
   - This will create the necessary dataset and metadata files in the appropriate directory.

### 2. PR Replay
   - Replay the generated or collected data to prepare it for evaluation. (Note: the repository used for replay must have the pr-review app installed as described in [TUTORIAL: Setup Installation](../TUTORIAL.md)):
     ```sh
     python pr_replay.py --config_file configs/replay_config.yml
     ```
### 3. Replay data collection
      After replay is complete we need to collect the replay data from 1 via
      ```sh
     python github_data_collection.py --config_file configs/replay_collection_config.yml
     ```
     Please ensure to delete any cache files from previous runs.
### 4. Evaluation
   - Run the evaluation process on the replayed data:
     ```sh
     python eval_impl.py --config_file configs/eval_config.yml
     ```

## Additional Notes

- Configuration files such as `.env.example` and `lambda-env.json.example` may need to be customized for your environment. Copy and rename them as `.env` and `lambda-env.json`, respectively, and update the values as needed.
- Refer to [pr-reviewer-config.md](../pr-reviewer-config.md) for detailed configuration options.

## Troubleshooting

- If you encounter issues, ensure all dependencies are installed and the environment variables are correctly set.
- Logs for data generation and replay can be found in `generation.log` y.

## Example Commands

Here’s an example of running all steps end-to-end:
```sh
# Step 1: Data Generation (if needed)
python github_data_collection.py --config_file configs/gen_config.yml

# Step 2: Replay
python pr_replay.py --config_file configs/replay_config.yml

# Step 3: Replay Collect
python github_data_collection.py --config_file configs/replay_collection_config.yml

# Step 4: Evaluation
python eval.py --config_file configs/eval_config.yml
```
