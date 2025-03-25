
import json
import traceback
import uuid

import requests
from requests.exceptions import RequestException
from typing import Any, Dict

from utils.logging_config import logger as log

def stateless_remote_static_analyzer_request(
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

    payload = {
        "agent_id": "remote_agent",
        "model": "gpt-4o",
        "metadata": {"id": str(uuid.uuid4())},
        "input": {"github_details": state["github_details"]},
    }
    log.info(f"Sending request to remote server with payload: {payload}")

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

                return {
                    "static_analyzer_output": decoded_response.get(
                        "static_analyzer_output", ""
                    )
                }
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

        # Extract messages if present
        static_analyzer_output = output.get("static_analyzer_output", [])

        return {
            "static_analyzer_output": static_analyzer_output,
        }
    except Exception as e:
        return {"error": f"Failed to decode response: {str(e)}"}