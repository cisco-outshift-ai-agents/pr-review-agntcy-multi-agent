import collections
import os
import json
import sys
import yaml
from github import Github, InputGitTreeElement, UnknownObjectException
import time
from datetime import datetime
import fire


class AlfredReviewGeneration:
    def __init__(self, config):
        self.config = yaml.safe_load(open(config))
        self.github = Github(self.config["github_token"])
        self.metadata = json.load(open(self.config["metadata_file"]))
        self.pr_directory_path = self.config["pr_directory_path"]
        self.pr_to_run = self.config["pr_to_run"]
        if not self.pr_to_run:
            self.pr_to_run = [value["pr_number"] for value in self.metadata["PRs"]]

    def createBranch(self, source_branch_name, new_branch_name):
        repo = self.github.get_repo(self.config["repo_name"])
        source_branch = repo.get_branch(source_branch_name)
        print(source_branch.commit.sha)
        repo.create_git_ref(
            ref=f"refs/heads/{new_branch_name}", sha=source_branch.commit.sha
        )
        print(f"Branch '{new_branch_name}' created successfully.")

    def getBranchContents(self, branch_name):
        repo = self.github.get_repo(self.config["repo_name"])
        branch_contents = repo.get_contents("", ref=branch_name)
        return branch_contents

    def createCommit(self, contents, branch_name, commit_message):
        # Create blobs for the files
        repo = self.github.get_repo(self.config["repo_name"])
        branch = repo.get_branch(branch_name)
        sha = branch.commit.sha
        blobs = []
        empty_file_list = []
        for path, content in contents.items():
            blob = repo.create_git_blob(content, "utf-8")
            if content == "":
                empty_file_list.append(path)
            blobs.append(InputGitTreeElement(path=path, mode="100644", type="blob", sha=blob.sha))
        count = 0
        try:
            # Create the tree
            tree = repo.create_git_tree(blobs, base_tree=repo.get_git_tree(sha))
            # Create the commit
            parent = repo.get_git_commit(sha)
            commit = repo.create_git_commit(commit_message, tree, [parent])
            # Update the branch reference
            ref = repo.get_git_ref(f"heads/{branch_name}")
            ref.edit(sha=commit.sha)
            return commit
        except UnknownObjectException:
            # File does not exist, create it
            commit_message = "Adding empty file."
            file_path = empty_file_list[count]
            print(file_path)

            repo.create_file(path=file_path, message=commit_message, content="", branch=branch_name)
            print(f"Empty file '{file_path}' created in branch '{branch_name}'.")
            count = count + 1

    def createPR(self, base_branch_name, new_branch_name, title, description):
        repo = self.github.get_repo(self.config["repo_name"])
        pr = repo.create_pull(
            base=base_branch_name,
            head=new_branch_name,
            title=title,
            body=description)
        print(f"Pull request created: {pr.html_url}")
        return pr

    @staticmethod
    def readContentsFromDirectory(directory):
        contents_dict = {}
        print(directory)
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        contents_dict[filename] = f.read()
                except Exception as e:
                    print("Error reading contents from directory")
        return contents_dict

    def deleteContents(self, contents, branch_name):
        repo = self.github.get_repo(self.config["repo_name"])
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "file":
                commit_message = f"Deleting {file_content.path} via PyGithub"
                repo.delete_file(file_content.path, commit_message, file_content.sha,
                                 branch=branch_name)
                print(f"Deleted {file_content.path}")
            elif file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path, ref=branch_name))

    def closeBranch(self, branch_name):
        repo = self.github.get_repo(self.config["repo_name"])
        try:
            # Get the branch reference
            ref = repo.get_git_ref(f"heads/{branch_name}")
            # Delete the branch
            ref.delete()
            print(f"Branch '{branch_name}' deleted successfully.")
        except Exception as e:
            print(f"Error deleting branch '{branch_name}': {e}")

    @staticmethod
    def wait_for_bot_comment(pr_url):
        latest_commit = pr_url.get_commits().reversed[0]
        while True:
            check_runs = latest_commit.get_check_runs()
            if check_runs.totalCount == 0:
                print("No checks found yet. Retrying...")
                time.sleep(10)
                continue
            all_done = True
            for check in check_runs:
                if check.name == 'Alfred review':
                    print(f"Check: {check.name}, Status: {check.status}, Conclusion: {check.conclusion}")
                    if check.conclusion == 'failure':
                        print(check.output)
                        return [False, check.output]
                    if check.status != "completed":
                        all_done = False
                if all_done:
                    print("✅ All checks are complete!")
                    return [True]
                time.sleep(10)

    def generateAlfredReview(self):
        results = collections.defaultdict(list)
        try:
            for values in self.metadata['PRs']:
                if str(values['pr_number']) in self.pr_to_run:
                    alfred_comments_count = 0
                    context_window_error = False
                    print("processing PR number {}".format(values["pr_number"]))
                    directory = self.config["pr_directory_path"]
                    pr_number = str(values["pr_number"])
                    title = "No title" if values["title"] is None else values["title"]
                    description = "" if values["body"] is None else values["body"]
                    if os.path.isdir(os.path.join(directory, pr_number)):
                        self.createBranch("main", "Pr_base_{}".format(pr_number))
                        main_branch_contents = self.getBranchContents("Pr_base_{}".format(pr_number))
                        base_file_directory = f"{directory}/{pr_number}/base_file"
                        final_merged_directory = f"{directory}/{pr_number}/final_merged_file"
                        if os.path.isdir(base_file_directory):
                            commit_contents = self.readContentsFromDirectory(base_file_directory)
                            self.createCommit(commit_contents, "Pr_base_{}".format(pr_number),
                                              f"Creating Base Branch for PR {pr_number}")
                            # create Modified Branch with base as Pr_base
                            self.deleteContents(main_branch_contents, "Pr_base_{}".format(pr_number))
                            self.createBranch("Pr_base_{}".format(pr_number), f"PR_changed_{pr_number}")

                            # Get final merged contents
                            if os.path.isdir(final_merged_directory):
                                final_commit_contents = self.readContentsFromDirectory(final_merged_directory)
                                self.createCommit(final_commit_contents, f"PR_changed_{pr_number}", "merged_content")
                                pr = self.createPR("Pr_base_{}".format(pr_number), f"PR_changed_{pr_number}", title,
                                                   description)
                                results['AlfredPRs'].append(
                                    {"pr_number": pr_number,
                                     "originalpr_url": values["url"],
                                     "prreviewer_url": pr.html_url})
                                Review_comment_body = "Alfred review"
                                pr.create_issue_comment(Review_comment_body)
                                alfred_review_result = self.wait_for_bot_comment(pr)
                                if not alfred_review_result[0]:
                                    if alfred_review_result[1].title == "Context Window Exceeded Error":
                                        print(
                                            f'Alfred review failed because of error {alfred_review_result[1].title}')
                                        context_window_error = True
                                        self.closeBranch("Pr_base_{}".format(pr_number))
                                        break
                                    else:
                                        print("Alfred failed at the API endpoint")
                                        break
                            else:
                                # If the merged code directory is not present
                                results['AlfredPRs'].append(
                                    {"pr_number": pr_number,
                                     "originalpr_url": values["url"],
                                     "prreviewer_url": "No Alfred PR Replay",
                                     "PR_replay_Status": "No Merged Code Directory Present",
                                     "Commit_files": []
                                     }
                                )
                                self.closeBranch("Pr_base_{}".format(pr_number))
                                self.closeBranch("PR_changed_{}".format(pr_number))
                                continue


                        else:
                            # If the base code is not present
                            results['AlfredPRs'].append(
                                {"pr_number": pr_number,
                                 "originalpr_url": values["url"],
                                 "prreviewer_url": "No Alfred PR Replay",
                                 "PR_replay_Status": "No Base Code Directory Present",
                                 "Commit_files": []
                                 }
                            )
                            self.closeBranch("Pr_base_{}".format(pr_number))
                            continue
                    else:
                        continue
                    if context_window_error:
                        # If there is a context window error close both base and changed branch
                        results['AlfredPRs'][-1][
                            "PR_replay_Status"] = "Failed At Alfred review Due to Context Window Error"
                        results['AlfredPRs'][-1]["Commit_files"] = []
                        self.closeBranch("Pr_base_{}".format(pr_number))
                        self.closeBranch(f"PR_changed_{pr_number}")

                    else:
                        # If all the commits are successfully updated
                        results['AlfredPRs'][-1]["PR_replay_Status"] = "Success"
                        results['AlfredPRs'][-1]["Commit_files"] = []
                        self.closeBranch("Pr_base_{}".format(pr_number))
                        self.closeBranch(f"PR_changed_{pr_number}")
            return results
        except Exception as e:
            if pr_number:
                print(f"The PR Replay run stopped for pr_number {pr_number} due to Error", e)
                self.closeBranch("Pr_base_{}".format(pr_number))
                self.closeBranch(f"PR_changed_{pr_number}")
                return results
            else:
                print("The PR Replay run stopped due to Error", e)
                return results


def main(config_file, **kwargs):
    """
    python3 pr_replay.py --config_file configs/replay_config.yaml
    """
    if not os.path.exists(config_file):
        print(f"Config file {config_file} does not exist.")
        sys.exit(1)
    obj = AlfredReviewGeneration(config_file)
    alfred_pr_replay = obj.generateAlfredReview()
    json.dump(alfred_pr_replay, open(f"pr_replay_{datetime.now().strftime("%d-%b-%Y")}.json", "w"))


if __name__ == '__main__':
    fire.Fire(main)
