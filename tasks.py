from crewai import Task


class PRCoachTasks():
  def fetch_pull_request_info_task(self, agent, installation_id, pr_number, repo_name):
    return Task(
        description=(
          f"""
          Fetch changes from pull request with installation id: {installation_id}, pr number: {pr_number} and repo name: {repo_name}.
          The changes will be described in "diff" format as used in version control systems. 
          Do not make up or add any information.
          """
        ),
        expected_output="""Pull request's title, description, file_name, and changes.""",
        agent=agent,
        async_execution=False,
    )


  def code_review_task(self, agent, context):
    return Task(
        description="""
        Perform a code review git changes in Terraform file.
        For each comment on the code changes, provide the line number and the changed line as is.
        Do not comment on lines which start with @@ as they are not code changes.
        Added line in changes start with +, removed line start with -.
        Avoid making redundant comments, keep the comments concise.
        Avoid making many comments on the same change. 
        Avoid commenting on connected to security issues, sensitive information, secrets, and vulnerabilities.
        Avoid make up information.
        Avoid positive or general comments.
        Avoid recommendation for review.
        """,
        expected_output="""
        List of review comment json objects which consist of:
        - Line number of the commented changes.
        - The precise changed line content.
        - The file path.
        - The comment itself.
        Example:
        {
          "line_number": 10,
          "changed_line": "filed1 = "kfdsnmlfksdm"",
          "file_name": some_file,
          "comment": "Resource name should be more descriptive."
        }
        """,
        agent=agent,
        async_execution=False,
        context=context
    )


  def security_analysis_task(self, agent, context):
    return Task(
        description="""
        Analyse the git changes in Terraform file for security issues, sensitive information, secrets, and vulnerabilities.
        Do not comment on lines which start with @@ as they are not code changes.
        Added line in changes start with +, removed line start with -.
        Avoid comments on lines which don't start with + or -.
        Avoid making redundant comments, keep the comments concise.
        Aggregate comments on the same change. 
        Avoid commenting on code structure, code best practices and code correctness.
        Avoid make up information.
        Avoid positive or general comments.
        Avoid comments which start with words: review or consider.
        """,
        expected_output="""
        Security review comments in bullets only. 
        Example:
        - IAM policy should be more restrictive.
        - Role should not have full admin access.
        """,
        agent=agent,
        async_execution=False,
        context=context
    )


  def title_review_task(self, agent, context):
    return Task(
        description="""
        Analyse the title and the changes in the git pull request.
        If the title don't describe the changes, suggest a new title, otherwise keep current title. 
        Do not analyse lines which start with @@ as they are not code changes.
        Added line in changes start with +, removed line start with -.
        Avoid redundant and long titles, keep it concise.
        """,
        expected_output="""
        Title: current title or new title. 
        Example:
        Title: Update IAM policy
        """,
        agent=agent,
        async_execution=False,
        context=context
    )


  def description_review_task(self, agent, context):
    return Task(
        description="""
        Analyse the description and the changes in the git pull request.
        If the description don't describe the changes, suggest a new description, otherwise keep current description. 
        Do not analyse lines which start with @@ as they are not code changes.
        Added line in changes start with +, removed line start with -.
        Avoid redundant and long descriptions, keep it concise.
        """,
        expected_output="""
        Description: current description or new description. 
        Example:
        Description: Update IAM policy
        """,
        agent=agent,
        async_execution=False,
        context=context
    )

  def commenter_task(self, agent, installation_id, pr_number, repo_name, context):
    return Task(
        description=f"""
        Receive code review comments and add them to the GitHub pull request.
        To comment on GitHub pull request use: installation_id : {installation_id}, pr_number: {pr_number}, repo_name: {repo_name} and line_number, file_name, comment_content, and changed_line from the context.
        """,
        expected_output="",
        async_execution=False,
        agent=agent,
        context=context
    )