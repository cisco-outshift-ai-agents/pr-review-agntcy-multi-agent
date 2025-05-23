# PR Reviewer Configuration File

## Overview
This configuration file outlines the preferences and settings for the GenAI-powered PR review service for Terraform. The configurations specified here will guide the automated code reviews, resource optimization recommendations, and other features provided by AppOne.

## PR Title and Description
  - Replace the PR title as needed to reflect the content of the PR.
  - Add to the PR submitter's description as needed, do not make description suggestions as a comment.
  - Use this for guidance on how to write a good description for a PR: https://www.pullrequest.com/blog/writing-a-great-pull-request-description/ 

## Code Review
- **Terraform Syntax and Style Checks:**
  - Review all content of the PR for Terraform syntax and style and add a comment to the PR with results.
  - Use this file for style checks: https://github.com/<User's_Repo>/STYLE_GUIDE.md (or default to https://developer.hashicorp.com/terraform/language/style)
  - Present any findings as a comment against the PR in text form, and also create a code diff with a committable suggestion.

## Security & Compliance Policies
- **Security Requirements:**
  - See Scanning Review section below.

- **Compliance Requirements:**
  - Adhere to CIS AWS Foundations Benchmark
  - Ensure all resources are tagged with `Environment`, `Owner`, and `Project`
  - Present any findings as comments on the code with committable suggestions
