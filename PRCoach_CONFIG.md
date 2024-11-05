# PRCoach Configuration File

## Overview
This configuration file outlines the preferences and settings for the GenAI-powered PR review service for Terraform. The configurations specified here will guide the automated code reviews, resource optimization recommendations, and other features provided by AppOne.

## PR Title and Description
  - Replace the PR title as needed to reflect the content of the PR.
  - Add to the PR submitter's description as needed, do not make description suggestions as a comment.
  - Use this for guidance on how to write a good description for a PR: https://www.pullrequest.com/blog/writing-a-great-pull-request-description/ 

## PR Summary of Changes
  - Add a comment to the PR with a summary of changes in the PR. It should include: 
      - one paragraph to help reviewers understand changes under heading "Summary of Changes"
      -  a suggestion to reviewers with any key changes to focus on under heading "Focus areas for reviewers"
      -  a table of what changes were made in the PR by file under heading "Changes by File"; the table should have 2 columns, first column is filename that had changes, 2nd column is the changes that were made
      -  a table of Related Issues under heading "Related Issues" with a check against the requirements listed in each related issue

## Code Review
- **Terraform Syntax and Style Checks:**
  - Review all content of the PR for Terraform syntax and style and add a comment to the PR with results.
  - Use this file for style checks: https://github.com/<User's_Repo>/STYLE_GUIDE.md (or default to https://developer.hashicorp.com/terraform/language/style)
  - Present any findings as a comment against the PR in text form, and also create a code diff with a committable suggestion.
 
## Documentation and Explanation
- **Auto-Documentation:**
  - Check documentation for all new and modified resources, generate new docs wherever dd
  - Include explanations for why certain configurations were chosen
  - Present any findings as comments on relevant markdown files in the repo with committable suggestions

- **Code Comments:**
  - Suggest meaningful comments for complex code sections
  - Highlight areas where additional context is needed
  - Present any findings as comments on the code with committable suggestions

## File Structure Review
- **Consistency Checks:**
  - Ensure PRs conform to the current repository structure for the use of modules and variables
  - Present any findings as comments on the PR, and where possible provide comments on the code with committable suggestions

- **Best Practices Comparison:**
  - Compare the current structure to best practices and provide recommendations for improvement
  - Present any findings as comments on the PR, and where possible provide comments on the code with committable suggestions

## Cloud Environment (as discovered by the system from your repo)
- **Primary Cloud Provider:** AWS
  - Confirm version alignment against pinned version and present any findings as comments on the code with committable suggestions
  - Review latest AWS feature set and module availability and make any suggestions as comments on the code
- **Secondary Cloud Providers:** None

## Security & Compliance Policies
- **Security Requirements:**
  - See Scanning Review section below.

- **Compliance Requirements:**
  - Adhere to CIS AWS Foundations Benchmark
  - Ensure all resources are tagged with `Environment`, `Owner`, and `Project`
  - Present any findings as comments on the code with committable suggestions


## Change Impact Analysis
- **Dependency Analysis:**
  - Analyze dependencies between resources and modules
  - Highlight potential impacts of changes on existing infrastructure
  - Present any findings as a comment on the PR

- **Risk Assessment:**
  - Add a comment after all other comments to provide a risk score for each PR based on the scope and nature of changes
  - Highlight high-risk changes that require additional review
  - Add any findings to the "PR Summary of Changes" comment, under the heading "Risk Assessment"

## Continuous review
  - When a PR is created, automatically trigger all reviews
  - When a PR is updated, automatically trigger all reviews. Update the PR Title and Description to match the changes. Update the PR Summary of Changes by File to match the changes. Add a comment for all other suggestions.

- **Linting Review:**
  - Review any linter test failures and provide suggestions to get PR to pass linter.
  - This repo uses `terraform fmt` for automatic code formatting
  - This repo uses `tflint` with the following rules:
    - AWS provider rules enabled
    - Ensure all variables have descriptions
    - Check for deprecated resource types

- **Scanning Review:**
  - Review any scanner test failures and provide suggestions to get PR to pass scanner.
  - This repo uses `checkov` for security review. Review security findings from checkov scan and provide fixes to any critical or high priority issues found.

## Learning and Improvement
- **Knowledge Base:**
  - Build a knowledge base of common issues and solutions encountered in past reviews
 
- **KPI Tracking:**
  - Build dataset of total PR review cycle time: time from PR opening to close
  - Build dataset of fixes done by PR submitter after PR submission, before expert reviewer starts review
  - Build dataset of human reviewer cycle time: time from point of expert reviewer start to finish time


## Expert Reviewers
- **Designated Expert Reviewers:**
  - See file MAINTAINERS.md

## Continuous Improvement
The system will open Pull Requests against this configuration file to make updates based on learnings.
- **Feedback Loop:**
  - Incorporate feedback from expert reviewers to continuously improve recommendations


---

This configuration file is automatically generated by PRCoach and reflects the current preferences and settings for the PR review service. Please review and update this file as needed to ensure it aligns with your team's requirements and best practices.
