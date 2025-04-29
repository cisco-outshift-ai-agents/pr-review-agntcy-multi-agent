# Installation and Usage Guide

This guide provides step-by-step instructions to set up and run the project.

## Prerequisites

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
   pip install -r eval_requirements.txt
   ```

## Steps to Run

### 1. Data Generation/Collection
   - If a `.tar.gz` file (e.g., `azure_terraform_dataset.tar.gz`) is present along with the corresponding metadata (e.g., `prdataset.json`), you can skip this step.
   - Otherwise, generate or collect the required data by running:
     ```sh
     python github_data_collection.py --config_file configs/gen_config.yml
     ```
   - This will create the necessary dataset and metadata files in the appropriate directory.

### 2. PR Replay
   - Replay the generated or collected data to prepare it for evaluation:
     ```sh
     python pr_replay.py --config configs/replay_config.yml
     ```
### 3. Replay data collection
      After replay is complete we need to collect the replay data from 1 via
      ```sh
     python github_data_collection.py --config configs/replay_collection_config.yml
     ```
### 4. Evaluation
   - Run the evaluation process on the replayed data:
     ```sh
     python eval_impl.py --config configs/eval_config.yml
     ```

## Additional Notes

- Configuration files such as `.env.example` and `lambda-env.json.example` may need to be customized for your environment. Copy and rename them as `.env` and `lambda-env.json`, respectively, and update the values as needed.
- Refer to [pr-coach-config.md](../pr-coach-config.md) for detailed configuration options.

## Troubleshooting

- If you encounter issues, ensure all dependencies are installed and the environment variables are correctly set.
- Logs for data generation and replay can be found in `generation.log` y.

## Example Commands

Here’s an example of running all steps end-to-end:
```sh
# Step 1: Data Generation (if needed)
python github_data_collection.py --config initial_data_collection_repo_config.yml

# Step 2: Replay
python pr_replay.py --config replay_config.yml

# Step 3: Replay Collect
python github_data_collection.py --config replay_data_collection_repo_config.yml

# Step 4: Evaluation
python eval.py --config eval_config.yml
```
