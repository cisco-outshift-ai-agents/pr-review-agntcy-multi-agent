import json
import os

import hcl2


def load_to_dict(filename: str) -> dict:
    with open(filename, "r") as file:
        d = hcl2.load(file)

    return d


def find_all_terraform_files(root_path: os.path) -> list[str]:
    tf_files = []

    for root, _, files in os.walk(root_path):
        for file in files:
            if file.endswith(".tf") or file.endswith(".tfvars"):
                tf_files.append(os.path.join(root, file))

    return tf_files


def build_full_dict(tf_files: list[str]) -> dict:
    full_dict = dict()

    for f in tf_files:
        full_dict[f] = load_to_dict(f)

    return full_dict


def parse(hits: dict, variable: str, path: str, values: any) -> dict:
    # find varname in 'resources' and 'output'
    if type(values) is list:
        for v in values:
            parse(hits, variable, f"{path}", v)
    elif type(values) is dict:
        for k, v in values.items():
            if variable != "" and variable[-1] != ".":
                variable = f"{variable}."
            parse(hits, f"{variable}{k}", path, v)
    elif type(values) is str:
        if path in hits:
            hits[path].append(variable)
        else:
            hits[path] = [variable]
    elif type(values) is int:
        pass
    else:
        print(f"{values}: unknown type {type(values)}")


def parse_variables(repo_root_path: str) -> str:
    tf_files = find_all_terraform_files(repo_root_path)

    full_dict = build_full_dict(tf_files)

    hits = {}
    for k, v in full_dict.items():
        parse(hits, "", k, v)

    all_hits = json.dumps(hits, indent=2)
    print(all_hits)

    return all_hits
