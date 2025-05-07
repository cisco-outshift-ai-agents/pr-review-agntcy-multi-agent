# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0


import json
import traceback
import uuid
from typing import Any, Dict

from agntcy_acp import ACPClient, ApiClientConfiguration
from agntcy_acp.acp_v0.sync_client.api_client import ApiClient
from agntcy_acp.acp_v0.models import RunCreateStateless, RunError, RunResult
from langchain_core.messages import HumanMessage
from langchain_core.messages.utils import convert_to_openai_messages

from utils.logging_config import logger as log
from utils.models import ReviewComment


def stateless_remote_code_review_request(state: Dict[str, Any]) -> Dict[str, Any]:
    log.info(f"Code Reviewer (ACP) Called")
    
    context_files = [cf.model_dump() for cf in state["context_files"]]
    static_analyzer_output = state.get("static_analyzer_output", "No Issues Found") or "No Issues Found"

    tf_input = {
        "context_files": context_files,
        "changes": state["changes"],
        "static_analyzer_output": static_analyzer_output,
    }
    log.info(f"Sending request to code reviewer remote agent: {tf_input}")

    messages = convert_to_openai_messages([HumanMessage(content=json.dumps(tf_input))])

    run_create = RunCreateStateless(
        agent_id="remote_agent",
        input={"messages": messages},
        metadata={"id": str(uuid.uuid4())},
    )

    try:
        config = ApiClientConfiguration.fromEnvPrefix("ACP_TF_CODE_REVIEWER_")
        with ApiClient(configuration=config) as api_client:
            acp_client = ACPClient(api_client=api_client)
            run_output = acp_client.create_and_wait_for_stateless_run_output(run_create)
            log.debug(f"code reviewer agent response: {run_output}")

            if run_output.output is None:
                raise ValueError("Run output is None")

            actual_output = run_output.output.actual_instance
            if isinstance(actual_output, RunResult):
                # Extract and decode last message from assistant
                last_msg = actual_output.messages[-1].content.actual_instance
                parsed = json.loads(last_msg)
                comments = [ReviewComment.model_validate(c) for c in parsed]
                log.debug(f"""
                code reviewer finished.
                review comments: {json.dumps([comment.model_dump() for comment in comments], indent=4)}
                """)
                return {
                    "new_review_comments": [c for c in comments if c.line_number != 0]
                }

            elif isinstance(actual_output, RunError):
                raise RuntimeError(f"Run failed: {actual_output}")

            else:
                raise TypeError("Unexpected ACP response format")

    except Exception as e:
        log.error(
            json.dumps(
                {
                    "error": "Unexpected failure",
                    "exception": str(e),
                    "stack_trace": traceback.format_exc(),
                }
            )
        )
        return {"error": "Unexpected failure"}