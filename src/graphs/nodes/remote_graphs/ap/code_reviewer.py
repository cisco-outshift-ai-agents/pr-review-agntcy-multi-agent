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

import requests
from requests.exceptions import RequestException
from typing import Any, Dict
from langchain_core.messages import HumanMessage
from langchain_core.messages.utils import convert_to_openai_messages
from utils.models import ReviewComment

from utils.logging_config import logger as log

def stateless_remote_code_review_request(
    state: Dict[str, Any], remote_server_url: str
) -> Dict[str, Any]:
    """
    Handles a stateless request to the Static Analyzer Remote Graph Server.

    with requests.Session() as session:
        try:
            response = session.post(remote_server_url, headers=headers, json=payload)
            response.raise_for_status()

    Returns:
        Dict[str, Any]: The updated state of the graph after processing the request.
    """
    if "github_details" not in state or not state["github_details"]:
        error_msg = "GraphState is missing 'github' key"
        log.error(json.dumps({"error": error_msg}))
        return {"error": error_msg}

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    context_files = [cf.model_dump() for cf in state["context_files"]]
    
    static_analyzer_output = state.get("static_analyzer_output", "No Issues Found") or "No Issues Found"

    tf_input = {
                "context_files": context_files,
                "changes": state["changes"],
                "static_analyzer_output": static_analyzer_output
            }
    log.info(f"Sending request to code reviewer remote agent: {tf_input}")
    
    messages = [HumanMessage(content=json.dumps(tf_input))]

    messages = convert_to_openai_messages(messages)

    payload: Dict[str,Any] = {
        "agent_id": "remote_agent",
        "input": {"messages": messages},
        "model": "gpt-4o",
        "metadata": {"id": str(uuid.uuid4())},
        "route": "/api/v1/runs"
    }

    log.info(f"Sending request to code reviewer remote server with payload: {payload}")

    # Use a session for efficiency
    with requests.Session() as session:
        try:
            response = session.post(remote_server_url, headers=headers, json=payload)
            response.raise_for_status()  # Raises HTTPError for 4xx and 5xx

            try:
                # Parse response as JSON
                response_data = response.json()
                # Decode JSON response
                decoded_response = decode_response(response_data)
                log.info(decoded_response)

                return decoded_response
            except json.JSONDecodeError as json_err:
                error_msg = "Invalid JSON response from server"
                log.error(
                    json.dumps({"error": error_msg, "exception": str(json_err)})
                )
                return {"error": error_msg}
        except (requests.Timeout, ConnectionError) as conn_err:
            error_msg = "Connection timeout or failure"
            log.error(json.dumps({"error": error_msg, "exception": str(conn_err)}))
            return {"error": error_msg}

        except requests.HTTPError as http_err:
            error_msg = f"HTTP request failed with status {response.status_code}"
            log.error(json.dumps({"error": error_msg, "exception": str(http_err)}))
            return {"error": error_msg}

        except RequestException as req_err:
            error_msg = "Request failed"
            log.error(json.dumps({"error": error_msg, "exception": str(req_err)}))
            return {"error": error_msg}

        except Exception as e:
            error_msg = "Unexpected failure"
            log.error(
                json.dumps(
                    {
                        "error": error_msg,
                        "exception": str(e),
                        "stack_trace": traceback.format_exc(),
                    }
                )
            )
            return {"error": error_msg}
        
def decode_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decodes the JSON response from the remote server and extracts relevant information.

    Args:
        response_data (Dict[str, Any]): The JSON response from the server.

    Returns:
        Dict[str, Any]: A structured dictionary containing extracted response fields.
    """
    try:
        output = response_data.get("output", {})

        ai_msg = output["messages"][-1]["content"]  # Get assistant message
        parsed = json.loads(ai_msg)
        log.info(f"Decoded response: {parsed}")
        comments = [ReviewComment.model_validate(comment) for comment in parsed]


        return {
            "new_review_comments": [c for c in comments if c.line_number != 0]
        }
    except Exception as e:
        return {"error": f"Failed to decode response: {str(e)}"}