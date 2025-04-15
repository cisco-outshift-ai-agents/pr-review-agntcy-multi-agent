from llm_judge import prompt_template_file, llm_initialize, prompt_template_comment
import os
import sys
import json
import logging


imp_list = []
error_list = []


def get_list_prs(alfred_comments):

    """
    Gets the keys from dictionary.

    Args:
        alfred_comments (dict): The alfred comments dictionary.

    Returns:
        list of keys of PR numbers.
    """

    key_to_extract = 'pr_number'
    extracted_values = [d[key_to_extract] for d in alfred_comments]
    return extracted_values


def check_if_folder_exists(path):

    """
    Check if the given folder path exists.

    Args:
        path (str): The folder path.

    Returns:
        Boolean value if the given folder path exists.
    """

    return os.path.isdir(path)


def get_list_files_from_folder(base_folder):

    """
    Get the list of files from the folder.

    Args:
        base_folder: The folder path.

    Returns:
        List of files in the folder.
    """

    files = [f for f in os.listdir(base_folder) if os.path.isfile(os.path.join(base_folder, f))]
    return files


def get_llm_rating(azure_llm, alfredcomment, pr, base_folder, final_merged_folder, file):

    """
    Get the rating of comment with the code files given as context.

    Args:
        azure_llm: The azure llm instance.
        alfredcomment: The alfred comment for which the comment needs to get a rating.
        pr: The PR number associated with the comment.
        base_folder: The initial context folder.
        final_merged_folder: The final context folder.
        file: The context file name.

    Returns:
        A dictionary with rating for the comment provided.

    """

    azure_llm = azure_llm.with_structured_output(None, method="json_mode")
    try:
        if file is None:
            judge_prompt = prompt_template_comment(alfredcomment)
            alfred_content = azure_llm.invoke(judge_prompt.format(comment=alfredcomment))
            keys = list(alfred_content.keys())
            key_0 = keys[0].strip()
            key_1 = keys[1].strip()
            op = {"comment": alfredcomment, "rating": alfred_content[key_0], "reasoning": alfred_content[key_1]}
            return op
        else:
            base_file_path = base_folder + file
            final_merged_path = final_merged_folder + file
            base_file_content = get_file_contents(base_file_path)
            final_merged_content = get_file_contents(final_merged_path)

            judge_prompt = prompt_template_file(base_file_content, final_merged_content, alfredcomment)
            alfred_content = azure_llm.invoke(judge_prompt.format(original_file=base_file_content, changed_file=final_merged_content, comment=alfredcomment))
            keys = list(alfred_content.keys())
            key_0 = keys[0].strip()
            key_1 = keys[1].strip()
            op = {"comment": alfredcomment, "rating": alfred_content[key_0], "reasoning": alfred_content[key_1]}
            return op
    except Exception as e:
        imp_list.append(alfredcomment)
        error_list.append(e)


def get_file_contents(filepath):

    """
    Returns the file content after reading it

    Args:
        filepath (str): The path to the file.

    Returns:
        content (str): Content of the file.
    """

    with open(filepath, 'r') as file:
        content = file.read()
        return content


def read_alfred_comments_json(code_dir, filename):
    """
    Reads a JSON file and returns its content as a Python dictionary.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: A dictionary representing the JSON data, or None if an error occurs.
    """

    file_path = os.path.join(code_dir, filename)

    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        logging.info(f"Error: File not found at '{file_path}'")
        return None
    except json.JSONDecodeError:
        logging.info(f"Error: Invalid JSON format in '{file_path}'")
        return None


def get_dictionary_by_key_value(dict_list, key, value):

    """
    Returns the dictonary based on a certain key value pair.

    Args:
        dict_list (list): The list of dictionaries.
        key:  The key in the required dictionary.
        value: The value in the required dictionary.

    Returns:
        dictionary (dict): dictionary from the list of dictionaries containing the key value pair.
    """

    for dictionary in dict_list:
        if dictionary.get(key) == value:
            return dictionary
    return None


if __name__ == '__main__':

    GPT_DEPLOYMENT_NAME = os.environ.get("GPT_DEPLOYMENT_NAME")
    AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")

    if not GPT_DEPLOYMENT_NAME or not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT:
        print("Error: All GPT_DEPLOYMENT_NAME, AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables must be set.")
        sys.exit(1)

    azure_llm = llm_initialize(AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT)

    code_dir = "./eval/dataset"
    alfred_comments_json = "anusha-1209_cisco-eti-prreplay.json"

    alfred_comments = read_alfred_comments_json(code_dir, alfred_comments_json)

    pr_list = get_list_prs(alfred_comments["PRs"])

    outer_folder_path = "pr_data_latest"
    repo_name = "Anusha-1209/Cisco-ETI-PRReplay"

    dataset_pr_path = code_dir + "/" + outer_folder_path + "/" + repo_name

    rating_dictionary = {}

    for pr in pr_list:
        pr_folder_path = dataset_pr_path + "/" + str(pr)
        pr_number = "pr_number"
        alfred_com = get_dictionary_by_key_value(alfred_comments["PRs"], pr_number, pr)
        alfred_comments_list = alfred_com["comments"]
        for cts in alfred_comments_list:
            single_comm = cts["comment"]
            file = cts["reference_filename"]
            if file is not None:
                file = file.replace("/", "_")
            if check_if_folder_exists(pr_folder_path):
                base_folder = pr_folder_path + "/" + "base_file/"
                final_merged_folder = pr_folder_path + "/" + "final_merged_file/"
            rating_com = get_llm_rating(azure_llm, single_comm, pr, base_folder, final_merged_folder, file)
            pr_num = f"pr_number_{pr}"
            if file is None:
                file = cts["id"]
            if pr_num not in rating_dictionary:
                rating_dictionary[pr_num] = {f"{file}": [rating_com]}
            else:
                file_comm = rating_dictionary[pr_num]
                if file not in file_comm:
                    rating_dictionary[pr_num][file] = [rating_com]
                else:
                    rating_dictionary[pr_num][file].append(rating_com)

    rating_file_path = './rating_new_both.json'
    except_file_path = './except_file_path.json'
    error_file_path = './error_file_path.json'

    with open(rating_file_path, 'w') as json_file:
        json.dump(rating_dictionary, json_file, indent=4)

    with open(except_file_path, 'w') as file:
        for item in imp_list:
            file.write(f"{item}\n")

    with open(error_file_path, 'w') as file:
        for item in error_list:
            file.write(f"{item}\n")
