# Import necessary libraries and modules
import os
from github import Github
import json
from github import Github, UnknownObjectException
import logging
from tqdm import tqdm
import pickle
from alfred_git_data import PRDataset, PR, Comment, Commit, FileObject, CommentType
from dateutil import parser
import yaml

# Configure logging for the script
logger = logging.getLogger()
formatter = logging.Formatter("%(asctime)s | %(name)s |  %(levelname)s: %(message)s")
logger.setLevel(logging.DEBUG)

# Stream handler for console logging
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.ERROR)
stream_handler.setFormatter(formatter)

# File handler for logging to a file
logFilePath = "generation.log"
file_handler = logging.FileHandler(filename=logFilePath)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Set the default logging level
logging.basicConfig(level=logging.ERROR)


# Function to populate commit details into a PR object
def populate_commits(pr, commits_data):
    for commit in commits_data:
        try:
            # Create a Commit object and populate its attributes
            curr_commit = Commit()
            curr_commit.commit_sha = commit.sha
            curr_commit.commit_author = commit.author.login if commit.author else "None"
            curr_commit.commit_message = commit.commit.message
            curr_commit.commit_timestamp = parser.parse(str(commit.commit.author.date))
            pr.commits.append(curr_commit)
        except Exception as e:
            logger.error(f"issue with processing commit: {e}")
    return pr


# Function to populate issue comments into a PR object
def populate_issue_comments(pr, issue_comments):
    for ic in issue_comments:
        try:
            # Create a Comment object for each issue comment
            comment = Comment(id=str(ic.id), type=CommentType.issue)
            comment.user = ic.user.login
            comment.comment = ic.body
            comment.comment_timestamp = parser.parse(str(ic.created_at))
            pr.comments.append(comment)
        except Exception as e:
            logger.error(f"issue with processing issue_comment: {e}")
    return pr


# Function to populate review comments into a PR object
def populate_review_comments(pr, review_comments):
    for rev in review_comments:
        try:
            # Create a Comment object for each review comment
            comment = Comment(id=str(rev.id), type=CommentType.review)
            comment.user = rev.user.login
            comment.comment = rev.body
            comment.commit_id = str(rev.commit_id)
            comment.comment_timestamp = parser.parse(str(rev.submitted_at))
            pr.comments.append(comment)
        except Exception as e:
            logger.error(f"issue with processing review_commit: {e}")
    return pr


# Function to populate file-specific comments into a PR object
def populate_file_comments(pr, comments, filename):
    file_comments = []
    for comment in comments:
        try:
            # Skip comments not related to the specified file
            if comment.path != filename:
                continue
            # Determine the commenter
            if comment.user is not None:
                commenter = comment.user.login
            else:
                commenter = "None"
            # Create a Comment object for each file comment
            file_comment = Comment(id=str(comment.id), type=CommentType.filec)
            file_comment.comment_timestamp = parser.parse(str(comment.created_at))
            file_comment.commit_id = str(comment.commit_id)
            file_comment.original_commit_id = comment.original_commit_id
            file_comment.user = commenter
            file_comment.comment = comment.body
            file_comment.reference_filename = filename
            file_comments.append(file_comment)
            pr.comments.append(file_comment)
        except Exception as e:
            logger.error(f"Issue with processing file_comment: {e}")
    return file_comments


# Function to populate general PR details into a PR object
def populate_pr(pr: PR, pull):
    try:
        # Populate PR attributes from the pull request object
        pr.url = pull.html_url
        pr.title = pull.title
        pr.state = pull.state
        pr.body = pull.body
        pr.created_at = parser.parse(str(pull.created_at))
        pr.updated_at = parser.parse(str(pull.updated_at))
        pr.base_branch = pull.base.ref
        pr.final_merged_branch = pull.head.ref
    except Exception as e:
        logger.error(f"Problem with PR info: {e}")
    return pr


# Function to collect files and their comments from a pull request
def collect_files(pr: PR, pull, repo, comments, files, folder_path):
    for file in tqdm(files):
        logger.info(f"YYY File {file.filename}")
        # Process only Terraform files
        if file.filename.endswith(".tf") or file.filename.endswith(".tfvars"):
            logger.info(f"XXX{file.filename}")
            ofile = FileObject(filename=file.filename)

            # Create necessary directories for storing file data
            pr_folder = str(pull.number)
            path0 = os.path.join(folder_path, pr_folder)
            logger.info(f"path0:{path0}")
            if not os.path.exists(path0):
                os.makedirs(path0)

            path1 = os.path.join(path0, "base_file")
            path2 = os.path.join(path0, "final_merged_file")

            if not os.path.exists(path1):
                os.makedirs(path1)

            if not os.path.exists(path2):
                os.makedirs(path2)

            fname = file.filename.replace("/", "_")

            try:
                # Retrieve and save the base file content
                base_content = repo.get_contents(
                    file.filename, ref=pull.base.sha
                ).decoded_content.decode()
                logger.info(f"File: {file.filename}")
                logger.info("Original Content:")
                logger.info(base_content)
                logger.info("\n" + "=" * 80 + "\n")
                with open(os.path.join(path1, fname), "w") as f:
                    f.write(base_content)
            except UnknownObjectException:
                logger.info(f"File: {file.filename}")
                logger.info("Original Content:")
                base_content = ""
                logger.info(base_content)
                logger.info("\n" + "=" * 80 + "\n")
                with open(os.path.join(path1, fname), "w") as f:
                    f.write(base_content)
            try:
                # Retrieve and save the final merged file content
                final_merged_content = repo.get_contents(
                    file.filename, ref=pull.head.sha
                ).decoded_content.decode()
                logger.info("\nChanged Content:")
                logger.info(final_merged_content)
                logger.info("\n" + "=" * 80 + "\n")
                with open(os.path.join(path2, fname), "w") as f:
                    f.write(final_merged_content)
            except UnknownObjectException:
                final_merged_content = ""
                logger.info(f"File: {file.filename}")
                logger.info("\nChanged Content:")
                logger.info(final_merged_content)
                logger.info("\n" + "=" * 80 + "\n")
                with open(os.path.join(path2, fname), "w") as f:
                    f.write(final_merged_content)
            # Populate file comments
            file_comments = populate_file_comments(pr, comments, file.filename)
            ofile.comments = file_comments


def collect_commit_files(repo, commit_obj, loc, skip_local_file_writing=True):
    folder_path = os.path.join(loc, "commits", f"{commit_obj.sha}")
    # Get the commit object to access the raw data
    # commit_obj = repo.get_commit(commit.sha)

    # Iterate over the files modified in the commit
    for file in commit_obj.files:
        if not file.filename.endswith(".tf") or file.filename.endswith(".tfvars"):
            continue
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        else:
            if skip_local_file_writing:
                continue

        basepath = os.path.join(folder_path, "base_code")
        changedpath = os.path.join(folder_path, "changed_code")

        if not os.path.exists(basepath):
            os.makedirs(basepath)

        if not os.path.exists(changedpath):
            os.makedirs(changedpath)

        filename = file.filename
        logger.info(f"File: {filename}")
        fname = filename.replace("/", "_")
        basefilenamepath = os.path.join(basepath, fname)
        changedfilenamepath = os.path.join(changedpath, fname)

        try:
            # Get the base code (content before the change)
            base_code = (
                repo.get_contents(
                    filename, ref=f"{commit_obj.parents[0].sha}"
                ).decoded_content.decode()
                if commit_obj.parents
                else ""
            )
            logger.info("  Base Code:")
            logger.info(base_code)
            with open(basefilenamepath, "w") as file:
                file.write(base_code)
        except UnknownObjectException:
            base_code = ""
            logger.info("  Base Code:  ")
            with open(basefilenamepath, "w") as file:
                file.write(base_code)

        try:
            # Get the changed code (content after the change)
            logger.info(f"Filename: {filename}")
            changed_code = repo.get_contents(
                filename, ref=commit_obj.sha
            ).decoded_content.decode()
            logger.info("  Changed Code:")
            logger.info(changed_code)
            with open(changedfilenamepath, "w") as file:
                file.write(changed_code)
        except UnknownObjectException:
            changed_code = ""
            logger.info("  Changed Code:  ")
            logger.info(changed_code)
            with open(changedfilenamepath, "w") as file:
                file.write(changed_code)


def read_and_write_file(repo, file, pull, path1, path2, fname):
    try:
        base_content = repo.get_contents(
            file.filename, ref=pull.base.sha
        ).decoded_content.decode()
        logger.info(f"File: {file.filename}")
        logger.info("Original Content:")
        logger.info(base_content)
        logger.info("\n" + "=" * 80 + "\n")
        with open(os.path.join(path1, fname), "w") as f:
            f.write(base_content)
    except UnknownObjectException:
        logger.info(f"File: {file.filename}")
        logger.info("Original Content:")
        base_content = ""
        logger.info(base_content)
        logger.info("\n" + "=" * 80 + "\n")
        with open(os.path.join(path1, fname), "w") as f:
            f.write(base_content)
    try:
        final_merged_content = repo.get_contents(
            file.filename, ref=pull.head.sha
        ).decoded_content.decode()
        logger.info("\nChanged Content:")
        logger.info(final_merged_content)
        logger.info("\n" + "=" * 80 + "\n")
        with open(os.path.join(path2, fname), "w") as f:
            f.write(final_merged_content)
    except UnknownObjectException:
        final_merged_content = ""
        logger.info(f"File: {file.filename}")
        logger.info("\nChanged Content:")
        logger.info(final_merged_content)
        logger.info("\n" + "=" * 80 + "\n")
        with open(os.path.join(path2, fname), "w") as f:
            f.write(final_merged_content)


# Function to extract comments from merged pull requests that include Terraform files
def extract_terraform_pr_comments(repo_name, github_token, limit=True, cache=True):
    """
    Extracts comments from merged pull requests that include Terraform files.

    Args:
        repo_name (str): The name of the GitHub repository (e.g., "owner/repo").
        github_token (str): Your GitHub personal access token.
    """
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    logger.info(f"Starting to extract data from {repo_name}")
    # Retrieve closed pull requests
    cache_path = ".prcache"
    if cache and os.path.exists(cache_path):
        # Load data (deserialize)
        logger.info(f"loading from cache")
        with open(cache_path, "rb") as handle:
            closed_pulls = pickle.load(handle)
    else:
        closed_pulls = repo.get_pulls(state="closed")
        if cache:
            logger.info(f"Writing to cache")
            with open(cache_path, "wb") as handle:
                pickle.dump(closed_pulls, handle, protocol=pickle.HIGHEST_PROTOCOL)

    logger.info(f"We have list of closed PRs")

    # Filter for merged pull requests and sort by merge timestamp
    merged_cache_path = ".mergedcache"
    if cache and os.path.exists(merged_cache_path):
        logger.info(f"loading from merged cache")
        with open(merged_cache_path, "rb") as handle:
            merged_pulls = pickle.load(handle)
    else:
        merged_pulls = [pr for pr in closed_pulls if pr.merged]
        if cache:
            logger.info(f"Writing merged to cache")
            with open(merged_cache_path, "wb") as handle:
                pickle.dump(merged_pulls, handle, protocol=pickle.HIGHEST_PROTOCOL)

    logger.info(f"The only merged PRs are {len(merged_pulls)}")

    sorted_merged_pulls = sorted(merged_pulls, key=lambda pr: pr.merged_at)
    logger.info(len(sorted_merged_pulls))

    comm_dict = {}
    folder_path = f"dataset/pr_data_latest/{repo_name}"

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    ct = 0
    dst_prs = PRDataset()
    skip_local_file_writing = True
    for pull in tqdm(sorted_merged_pulls):
        if pull.merged:
            curr_pr = PR(pr_number=pull.number)
            path_b0 = os.path.join(folder_path, str(pull.number))
            path_b0_present = os.path.exists(path_b0)
            curr_pr = populate_pr(curr_pr, pull)
            commits_data = pull.get_commits()
            commits_list = []
            curr_pr = populate_commits(curr_pr, commits_data)
            for commit in commits_data:
                collect_commit_files(
                    repo, commit, os.path.join(folder_path, f"{curr_pr.pr_number}")
                )
                commit_sha = commit.sha
                commit_author = commit.author.login if commit.author else "None"
                commit_message = commit.commit.message
                commit_timestamp = commit.commit.author.date
                commits_list.append(
                    {
                        "commit_sha": commit_sha,
                        "commit_author": commit_author,
                        "commit_message": commit_message,
                        "commit_timestamp": commit_timestamp,
                    }
                )

            logger.info(f"Pull Request: {pull.number} - {pull.title}")
            comments = pull.get_comments()

            # Get issue comments:
            issue_comments = pull.get_issue_comments()
            curr_pr = populate_issue_comments(curr_pr, issue_comments)

            reviews = pull.get_reviews()
            curr_pr = populate_review_comments(curr_pr, reviews)
            logger.info(f"url: {pull.html_url}")
            # path0 = os.path.join(folder_path, str(pull.number))
            # if os.path.exists(path0):
            #    continue
            files = pull.get_files()
            logger.info(f"Extracting files from PR{curr_pr.pr_number}")
            for file in tqdm(files):
                logger.info(f"YYY File {file.filename}")
                if file.filename.endswith(".tf") or file.filename.endswith(".tfvars"):
                    logger.info(f"XXX{file.filename}")
                    ofile = FileObject(filename=file.filename)

                    pr_folder = str(pull.number)
                    path0 = os.path.join(folder_path, pr_folder)
                    logger.info(f"path0:{path0}")
                    if not os.path.exists(path0):
                        os.makedirs(path0)

                    path1 = os.path.join(path0, "base_file")
                    path2 = os.path.join(path0, "final_merged_file")
                    # if os.path.exists(path1):
                    #    continue
                    # if os.path.exists(path2):
                    #    continue
                    if not os.path.exists(path1):
                        os.makedirs(path1)

                    if not os.path.exists(path2):
                        os.makedirs(path2)

                    fname = file.filename.replace("/", "_")
                    logger.info(f"Path Present for {pull.number} {path_b0_present}")
                    if path_b0_present:
                        logger.info(f"Skipping writing files for {pull.number}")
                    else:
                        read_and_write_file(repo, file, pull, path1, path2, fname)
                    file_comments = populate_file_comments(
                        curr_pr, comments, file.filename
                    )
                    ofile.comments = file_comments
                    curr_pr.files.append(ofile)
            curr_pr.comments = sorted(
                curr_pr.comments, key=lambda commt: commt.comment_timestamp
            )
            dst_prs.PRs.append(curr_pr)
            logger.info("-" * 30)
            if limit and ct >= 15:
                break
    return dst_prs


if __name__ == "__main__":
    config = yaml.safe_load(open("config.yml", "r"))
    repo_name = config["repo_name"]
    if "GITHUB_TOKEN" in config:
        os.environ["GITHUB_TOKEN"] = config["GITHUB_TOKEN"]

    github_token = os.environ.get("GITHUB_TOKEN")
    if not repo_name or not github_token:
        raise ValueError(
            f"Please set the GITHUB_REPO and GITHUB_TOKEN environment variables. repo_name{repo_name} github_token {github_token}"
        )
    logger.info(f"***Processing data from REPO: {repo_name}****")
    prs_dst = extract_terraform_pr_comments(repo_name, github_token, limit=True)
    logger.info(("****@@@@@@@_____"))

    reps = repo_name.split("/")
    file_name = f"{'_'.join(reps)}v1.json".lower()
    local_dir = "dataset"
    os.makedirs(local_dir, exist_ok=True)

    with open(os.path.join(local_dir, file_name.replace("v1", "")), "w") as outfile:
        outfile.write(prs_dst.model_dump_json(indent=4))
