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

from utils.logging_config import logger as log

def stateless_remote_static_analyzer_request(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends a stateless request using ACPClient to the remote static analyzer agent.
    """
    log.info(f"Static Analyzer (ACP) Called")
    if "github_details" not in state or not state["github_details"]:
        error_msg = "GraphState is missing 'github_details' key"
        log.error(json.dumps({"error": error_msg}))
        return {"error": error_msg}

    github_details = state["github_details"]
    
    log.info(f"Sending request to code analyzer remote agent: {github_details}")

    run_create = RunCreateStateless(
        agent_id="remote_agent",
        input={"github_details": github_details},
        metadata={"id": str(uuid.uuid4())},
    )

    try:
        config = ApiClientConfiguration.fromEnvPrefix("ACP_TF_CODE_ANALYZER_")
        with ApiClient(configuration=config) as api_client:
            acp_client = ACPClient(api_client=api_client)
            run_output = acp_client.create_and_wait_for_stateless_run_output(run_create)
            log.debug(f"code analyzer agent response: {run_output}")

            if run_output.output is None:
                raise ValueError("Run output is None")

            actual_output = run_output.output.actual_instance
            
            if isinstance(actual_output, RunResult):
                result: RunResult = actual_output
                sao = (
                    result.values.get("static_analyzer_output", "")
                    if result.values
                    else ""
                )
                log.debug(f"""
                static_analyzer finished.
                output: {sao}
                """)
                return {"static_analyzer_output": sao}

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