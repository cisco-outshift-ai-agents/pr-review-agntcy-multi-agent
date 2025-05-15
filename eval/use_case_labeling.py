import json
import yaml
import logging
import os
from tqdm import tqdm
from langchain_openai import AzureChatOpenAI
from pkg.alfred_git_data import PRDataset
import difflib

logging.basicConfig(level=logging.INFO)
from langchain.prompts import PromptTemplate


def file_use_case_labeling(config, file_data, file_comment):
    """
    Labels the use cases for a given file diff and associated comments using an LLM.
    """
    # Initialize the AzureChatOpenAI model with the provided configuration
    llm = AzureChatOpenAI(
        api_key=config["AZURE_OPENAI_API_KEY"],
        azure_endpoint=config["AZURE_OPENAI_ENDPOINT"],
        api_version=f"{config['api_version']}",  # unsupported param
    )
    judge_prompt3_task1_and_task2 = """HUMAN:
<role> You are an expert on Terraform code with a strong understanding of its syntax, structure, and best practices. You are adept at analyzing code changes and comments to identify key aspects such as cross-references, network configurations, IAM policies, module modifications, and coding best practices. </role>
<task 1> Analyze the provided diff for the Terraform file: {diff}. Determine which of the following diff use cases apply:
1.	The Terraform has cross-references to other files or variables.
2.	It has network configuration, IP addresses.
3.	It has changes on IAM policy.
4.	It involves modification to a module or creation of a new module.
</task 1>
<task 2> Analyze the provided comments {comment} in relation to the diff and assess the following comment use cases:
5.	References to variables.
6.	Module usage.
7.	Terraform coding best practices.
</task 2>
<output format> Provide your answer in a multi-label format (e.g., 1, 0, 1, 0, 0, 1, 0) for both diff use cases and comment use cases, where each position corresponds to a use case, and '1' indicates applicability.</output format>
ANSWER:
"""

    judge_prompt_only_task1 = """HUMAN:
<role> You are an expert on Terraform code with a strong understanding of its syntax, structure, and best practices. You are adept at analyzing code changes and comments to identify key aspects such as cross-references, network configurations, IAM policies, module modifications, and coding best practices. </role>
<task 1> Analyze the provided diff for the Terraform file: {diff}. Determine which of the following diff use cases apply:
1.	The Terraform has cross-references to other files or variables.
2.	It has network configuration, IP addresses.
3.	It has changes on IAM policy.
4.	It involves modification to a module or creation of a new module.
</task 1>
<output format> Provide your answer in a multi-label format (e.g., 1, 0, 1, 0, 0, 1, 0) for both diff use cases and comment use cases, where each position corresponds to a use case, and '1' indicates applicability.</output format>
ANSWER:
"""

    # Select the appropriate prompt template based on the presence of comments
    judge_prompt_template = judge_prompt3_task1_and_task2
    if file_comment:
        logging.debug(f"NOT Empty Comments: {file_comment}")
        judge_prompt_template = judge_prompt_only_task1
    else:
        file_comment = ""
    # Format the prompt and invoke the LLM
    judge_prompt = PromptTemplate.from_template(judge_prompt_template)
    try:
        output = llm.invoke(judge_prompt.format(diff=file_data, comment=file_comment))
    except Exception as e:
        logging.error(f"Error in invoking LLM: {e}")
        output = None
        #logging.debug(f"Output from LLM: {output}")
        label_values = (None, None, None, None, None, None, None)
    #logging.debug(output)
    
    # Define label names and parse the LLM output
    label_names = (
        "cross_reference",
        "network_configuration",
        "iam_policy",
        "modification_to_module",
        "reference_to_variable",
        "module_usage",
        "terraform_best_practice",
    )
    try:
        label_values = eval(f"({output.content})")
    except:
        logging.error(f"We had issue wr processing {output}")
        label_values = (None, None, None, None, None, None, None)
    
    # Create a result dictionary with default values and update with parsed labels
    result = dict(zip(label_names, [0 for x in range(len(label_names))]))
    result.update(dict(zip(label_names, label_values)))
    return result


def read_file(l_path, c_filename):
    """
    Reads the content of a file given its path and filename.
    """
    full_filepath = os.path.join(l_path, c_filename)
    logging.debug(f"Full_file location: {full_filepath}")
    with open(full_filepath, "r") as file:
        file_content = file.read()
    return file_content


def diff_content(a: str, b: str) -> str:
    """
    Generates a diff between two strings and applies styling for visualization.
    """
    try:
        line_color = {"+": 32, "-": 31}  # Define colors for added and removed lines

        diffs = difflib.ndiff(a.splitlines(keepends=True), b.splitlines(keepends=True))
        diff_list = list(diffs)
        styled: list[str] = []
        for prev, next in zip(diff_list, diff_list[1:] + [""]):
            color = line_color.get(prev[0], 0)
            match prev[0]:
                case " ":
                    styled.append(prev)  # Unchanged lines
                case "+" | "-":
                    index = [i for i, c in enumerate(next) if c == "^"]
                    _prev = list(prev)
                    for idx in index:
                        _prev[idx] = f"\x1b[97;{color+10};1m{_prev[idx]}\x1b[0;{color}m"
                    styled.append(f'\x1b[{color}m{"".join(_prev)}\x1b[0m')  # Styled diff
                case "?":
                    continue  # Ignore metadata lines
        return "".join(styled)
    except Exception as e:
        logging.error(f"Error in diff_content: {e}")
        return ""
    
def compare_files_read(l_path1, file_name1, l_path2, file_name2):
    """
    Reads two files and generates a diff of their content.
    """
    content1 = read_file(l_path1, file_name1)
    content2 = read_file(l_path2, file_name2)
    content_diff = diff_content(content1, content2)
    return content_diff


def label_dataset(dst_pr: PRDataset):
    """
    Labels the dataset of pull requests with use case information.
    """
    pr_ctr = {}  # Dictionary to track file and non-empty diff counts per PR
    for pr in tqdm(dst_pr.PRs):
        if pr.pr_number not in pr_ctr:
            pr_ctr[pr.pr_number] = {"FILE": 0, "NON_EMPTY": 0}
        f1_path = os.path.join(config["local_dir"], str(pr.pr_number), config["subfolder_base"])
        f2_path = os.path.join(config["local_dir"], str(pr.pr_number), config["subfolder_change"])
        for a_file in tqdm(pr.files):
            pr_ctr[pr.pr_number]["FILE"] += 1
            file_name = a_file.filename.replace("/", "_")
            curr_diff = compare_files_read(f1_path, file_name, f2_path, file_name)
            if len(curr_diff) > 0:
                pr_ctr[pr.pr_number]["NON_EMPTY"] += 1
                comments = ""
                if len(a_file.comments) > 0:
                    comments = " ".join([cmt.comment for cmt in a_file.comments])
                content = file_use_case_labeling(config, curr_diff, comments)
                content["local_file"] = file_name
                content["original_file"] = a_file.filename
                pr.use_cases.append(content)
    return dst_pr, pr_ctr


if __name__ == "__main__":
    """
    Main entry point for the script. Loads configuration, processes the dataset, and saves results.
    """
    config = yaml.safe_load(open(os.path.join("use_case_config.yaml"), "r"))
    logging.info(config)
    logging.info(f"DDD {config['data_path']}")
    with open(config["data_path"], "r") as f:
        data = json.load(f)
    dst_pr = PRDataset(**data)

    logging.info(f"Number of Prs in dataset {len(dst_pr.PRs)}")
    dst_pr, count_stats = label_dataset(dst_pr)
    with open(config["data_path"].replace(".json", f"{config['output_append']}.json"), "w") as fp:
         fp.write(dst_pr.model_dump_json(indent=4))
         
    with open(f"{config['data_path']}".replace(".json", f"_file_stats.json"), "w") as fp:
         json.dump(count_stats, fp, indent=4)
