import os
import sys
from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate


def llm_initialize(AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT):

    azure_llm = AzureChatOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version="2023-05-15",
    )

    return azure_llm


def prompt_template_diff(diff, comment): #The comment can be human or alfred comment

    judge_prompt_template = """HUMAN:
    <role>You are an expert code reviewer performing a file-by-file review of a pull request. 
    You have access to the full diff of the file to understand the overall context and structure.</role>
    <task>Here is the diff for the file: {diff} </task>

    Please give a rating to the review comment: {comment} out of 5 on how good the review comment is based on accuracy, relevance etc.

    The format should be in a dictionary format with rating as one of the key and the rating score as the value. 
    The other key in the dictionary should be reasoning with value as the reason for giving this rating.

    ANSWER:"""

    judge_prompt = PromptTemplate.from_template(judge_prompt_template)
    return judge_prompt


def prompt_template_file(original_file, changed_file, comment): #The comment can be human or alfred comment

    judge_prompt_template = """HUMAN:
    <role> You are an expert code reviewer performing a file-by-file review of a pull request. 
    You have access to the original file and the file that has changes made to it in this pull request to understand the overall context and structure.</role>
    <task> Here is the original file: {original_file} and the changed file: {changed_file} </task>

    Please give a rating to the review comment: {comment} out of 5 on how good the review comment is based on accuracy, relevance etc.

    Format the output as a valid JSON with the following keys:
    rating
    reasoning

    ANSWER:"""

    judge_prompt = PromptTemplate.from_template(judge_prompt_template)
    return judge_prompt


def prompt_template_comment(comment): # The comment can be human or alfred comment

    judge_prompt_template = """HUMAN:
    <role> You are an expert code reviewer performing review of a pull request. 
    Please give a rating to the review comment: {comment} out of 5 on how good the review comment is based on accuracy, relevance etc.
    Please assume all comments provided are review comments.

    Format the output as a valid JSON with the following keys:
    rating
    reasoning

    ANSWER:"""

    judge_prompt = PromptTemplate.from_template(judge_prompt_template)
    return judge_prompt


def prompt_template_compare_merged_file(original_file, changed_file_human, changed_file_alfred):

    judge_prompt_template = """HUMAN:
    <role> You are an expert code reviewer performing a file review of a pull request.
    You have access to the original file and the file that has changes made to it in this pull request to understand the overall context and structure.
    The changed file has two different variations. </role>
    <task> Here is the original file: {original_file} and the changed file first variation : {changed_file_alfred} and changed file second variation: {changed_file_human} </task>

    Please give a detailed description on which changed file variation is better and with thorough reasoning.

    ANSWER:"""

    judge_prompt = PromptTemplate.from_template(judge_prompt_template)
    return judge_prompt


if __name__ == '__main__':

    GPT_DEPLOYMENT_NAME = os.environ.get("GPT_DEPLOYMENT_NAME")
    AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")

    if not GPT_DEPLOYMENT_NAME or not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT:
        print("Error: All GPT_DEPLOYMENT_NAME, AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables must be set.")
        sys.exit(1)

    azure_llm = llm_initialize(AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT)