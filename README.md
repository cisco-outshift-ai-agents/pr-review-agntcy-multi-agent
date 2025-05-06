# Multi-Agent Pull Request Reviewer
[![Release](https://img.shields.io/github/v/release/cisco-ai-agents/pr-review-agntcy-multi-agent?display_name=tag)](CHANGELOG.md)
[![Contributor-Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-fbab2c.svg)](CODE_OF_CONDUCT.md)

*A GitHub app that provides feedback on pull requests.*

This project is an example multi-agent application designed to help developers improve their Terraform code pull requests by providing feedback and suggestions. It automates parts of the PR review process, making it easier to identify potential issues, improve code quality, and adhere to best practices.

![Overview of Multi-agent Pull Request Reviewer](./docs/resources/PR-Reviewer_System.svg)

## Overview
The Multi-Agent PR Reviewer demonstrates the use of the **[AGNTCY](https://github.com/agntcy) [Agent Gateway Protocol (AGP)](https://github.com/agntcy/agp)** and **[AGP server](https://github.com/agntcy/agp/tree/main/data-plane)** for seamless interaction with remote agents. The core app, along with its remote agents, is built using LangGraph, showcasing a modular and extensible approach to multi-agent workflows.

It was originally conceived to focus on the specific needs of IaC. It is ready for use as-is or can be customized for experimentation. You can add new embedded or remote agents, modify the existing agent workflow, or tailor agent prompts to suit your specific PR review use cases.

This project is part of the [AGNTCY](https://docs.agntcy.org/pages/introduction.html) initiative — an open source collective building the infrastructure for the Internet of Agents (IoA): a secure, interoperable layer for agent-to-agent collaboration across organizations and platforms.

### Features

- Connects to your GitHub repository via a GitHub App

- Reviews and provides suggestions on the PR title and description

- Performs linting and static analysis using the Terraform Code Analyzer Agent as a remote agent via AGNTCY Agent Gateway

- Conducts a thorough code review using the Terraform Code Reviewer Agent as a remote agent via AGNTCY Agent Gateway

- Aggregates and de-duplicates feedback to avoid redundant comments across multiple triggers

- Posts both PR-level and inline comments with feedback on Terraform code

- Activated on demand by commenting "Alfred review" on a pull request

## Details

![Detailed view of complete PR Reviewer system](./docs/resources/PR-Reviewer_Flows.svg)

The Multi-Agent PR Reviewer provides GitHub integration and a set of agents capable of performing basic Terraform pull request (PR) reviews. The current agent workflow focuses on the following tasks:

- **Agent 0: Supervisor**
  Coordinates the execution of the other agents, especially the code review agent team.

- **Agent 1: PR Title and Description Review**  
  Ensures that the PR's title and description are clear, complete, and provide enough context for reviewers.  

- **Agent 2: Terraform Code Analyzer (remote)**   
  Runs Terraform linters on your code.   
  [https://github.com/cisco-outshift-ai-agents/tf-code-analyzer-agntcy-agent](https://github.com/cisco-outshift-ai-agents/tf-code-analyzer-agntcy-agent)

- **Agent 3: Terraform Code Review (remote)**  
  Examines Terraform code for common issues, such as syntax errors, security flaws, and poor structural design.     
  [https://github.com/cisco-outshift-ai-agents/tf-code-reviewer-agntcy-agen](https://github.com/cisco-outshift-ai-agents/tf-code-reviewer-agntcy-agent)

- **Agent 4: Cross-reference Reviewer**   
  Checks cross-references to ensure validity and resolve conflicts.

- **Agent 5: Code Comment Consolidator**  
  Once the code review team is done, removes any overlapping comments.

- **Agent 6: PR Commenter**   
  Constructs comments from other agent inputs to write to the Pull Request.

## How It Works

1. **GitHub Integration**  
   The Multi-Agent PR Reviewer is installed as a GitHub app. When a pull request is created or updated, the app automatically triggers the agent workflow to review the changes.

2. **Agent Workflow**  
   The workflow is managed by the supervisor, and begins with the PR Title and Description Review Agent, followed by the Code Review team. The supervisor collects feedback the code review team and sends it on to the code comment consolidator before sending to the PR commenter. The PR commenter comments directly on the GitHub PR, providing actionable insights for the developer or PR reviewer.

3. **Agent Communication to remote agents**  
   This project demonstrates the use of **both ACP (Agent Connect Protocol)** and **AGP (Agent Gateway Protocol)** for remote agent communication. These protocols come from the [AGNTCY](https://docs.agntcy.org/pages/introduction.html) ecosystem and enable the core app to interact with distributed agents in a secure and scalable way.

   **ACP – Agent Connect Protocol**

   [Documentation →](https://docs.agntcy.org/pages/syntactic_sdk/connect.html)
   
   ACP provides a standardized **HTTP-based API interface** for invoking remote agents. In this project, ACP is used to make **stateless run requests** to both:

   * [`tf-code-analyzer-agntcy-agent`](https://github.com/cisco-outshift-ai-agents/tf-code-analyzer-agntcy-agent)
   * [`tf-code-reviewer-agntcy-agent`](https://github.com/cisco-outshift-ai-agents/tf-code-reviewer-agntcy-agent)

    These agents expose ACP-compatible endpoints, allowing the PR reviewer to trigger analysis and code review over API.

    **AGP (Agent Gateway Protocol)**

    [Documentation →](https://docs.agntcy.org/pages/messaging_sdk/agp-index.html)

   AGP enables **real-time messaging** between agents via a local AGP gateway. Both remote agents are also accessible using AGP for session-based or streaming workflows. Used to connect to:

   * [`tf-code-analyzer-agntcy-agent`](https://github.com/cisco-outshift-ai-agents/tf-code-analyzer-agntcy-agent/blob/a7b555d07ba87419928f3d60b45d9e4467fdfde7/app/main.py#L184)
   * [`tf-code-reviewer-agntcy-agent`](https://github.com/cisco-outshift-ai-agents/tf-code-reviewer-agntcy-agent/blob/645d13b9e716b2f34828ce8c9dc8fdf8ac729a70/app/main.py#L278)

   Messages are sent via a gateway container, and responses are received asynchronously for rich, structured output (e.g., review comments, analysis results). Here are the [getting started](https://docs.agntcy.org/pages/messaging_sdk/agp-howto.html) instructions to run AGP data plane.

   >You can [control](https://github.com/cisco-outshift-ai-agents/pr-review-agntcy-multi-agent/blob/4ab225bd4faae3064955054769b312a08a7cd5c9/src/graphs/code_review_graph.py#L93)  which protocol is used at runtime by setting the `AGENT_MODE_ENV` environment variable. 
    >* `"acp"` – to use **HTTP-based ACP**
    >* `"agp"` – to use **real-time AGP messaging**



## Customization and Experimentation

This project is designed to be a starting point for developers who want to experiment with multi-agent workflows, remote agents, or building their own PR reviewer agents. Here’s how you can customize it:

1. **Add New Agents**  
   Create new embedded or remote agents to perform additional tasks, such as:
   - Reviewing documentation for completeness.
   - Assessing Terraform modularity and best practices.
   - Summarizing Terraform plans or results from security scans.

2. **Modify Existing Agents**  
   Customize the logic or prompts of the existing agents to better suit your specific needs. For example:
   - Update the PR Title and Description Review Agent to enforce your specific requirements.
   - Modify the checks done by the Code Review Agent.

3. **Modify the Agent Workflow**  
   Adjust the sequence of agents or introduce conditional logic to the workflow. For example:
   - Run specific agents only when certain files are modified.
   - Chain new agents into the existing workflow.

## Installation

To get started, see [TUTORIAL.md](./TUTORIAL.md)

## Evaluation

For detailed instructions on how to evaluate AI Agent, please refer to the [Evaluation Guide](eval/README.md).

## Roadmap

See the [open issues](https://github.com/cisco-ai-agents/tf-pr-review-agntcy-multi-agent/issues) for a list
of proposed features (and known issues).

## Contributing

Contributions are what make the open source community such an amazing place to
learn, inspire, and create. Any contributions you make are **greatly
appreciated**. For detailed contributing guidelines, please see
[CONTRIBUTING.md](CONTRIBUTING.md)

## License

Distributed under the Apache-2.0 License. See [LICENSE](LICENSE) for more
information.

## Contact

[cisco-outshift-ai-agents@cisco.com](mailto:cisco-outshift-ai-agents@cisco.com)

Project Link:
[https://github.com/cisco-outshift-ai-agents/pr-review-agntcy-multi-agent](https://github.com/cisco-outshift-ai-agents/pr-review-agntcy-multi-agent)


## Acknowledgements

- [Langgraph](https://github.com/langchain-ai/langgraph) for the agentic platform.
- The [AGNTCY](https://github.com/agntcy) project