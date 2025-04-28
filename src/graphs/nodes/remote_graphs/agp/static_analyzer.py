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
from typing import Any, Dict
import os

from agp_api.agent.agent_container import AgentContainer
from agp_api.gateway.gateway_container import GatewayContainer

from utils.logging_config import logger as log

class Config:
    """Configuration class for AGP (Agent Gateway Protocol) client.
    This class manages configuration settings for the AGP system, containing container
    instances for gateway and agent management, as well as remote agent specification.
    Attributes:
        gateway_container (GatewayContainer): Container instance for gateway management
        agent_container (AgentContainer): Container instance for agent management
        remote_agent (str): Specification of remote agent, defaults to "server"
    """

    gateway_container = GatewayContainer()
    agent_container = AgentContainer()
    remote_agent = "server"

async def send_and_recv(payload: Dict[str, Any], remote_agent: str) -> Dict[str, Any]:
    """
    Sends a payload to a remote agent and receives a response through the gateway container.
        payload (Dict[str, Any]): The request payload to be sent to the remote agent
        remote_agent (str): The identifier of the remote agent to send the payload to
    Returns:
        Dict[str, Any]: A dictionary containing the 'messages' key with either:
            - The last message received from the remote agent if successful
            - An error message if the request failed, wrapped in a HumanMessage
    Raises:
        May raise exceptions from gateway container operations or JSON processing
    Note:
        The response is expected to be a JSON string that can be decoded into a dictionary
        containing either an 'error' field (for failures) or an 'output' field with 'messages'
    """

    await Config.gateway_container.publish_messsage(
        payload, agent_container=Config.agent_container, remote_agent=remote_agent
    )
    _, recv = await Config.gateway_container.gateway.receive()

    response_data = json.loads(recv.decode("utf8"))

    log.info(f"Received response from remote agent: {response_data}")

    return response_data

async def node_remote_agp(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends a stateless request to the Remote Graph Server.

    Args:
        state (GraphState): The current graph state containing messages.

    Returns:
        Command[Literal["exception_node", "end_node"]]: Command to transition to the next node.
    """
    await init_client_gateway_conn()

    if "github_details" not in state or not state["github_details"]:
        error_msg = "GraphState is missing 'github_details' key"
        log.error(json.dumps({"error": error_msg}))
        return {"error": error_msg}

    payload: Dict[str,Any] = {
        "agent_id": "remote_static_analyzer_agent",
        "input": {"github_details": state["github_details"], "messages": [{"content": "is_present"}]},
        "route": "/api/v1/runs"
    }

    res = await send_and_recv(payload, remote_agent=Config.remote_agent)
    decoded_res = decode_response(res)
    return decoded_res

async def init_client_gateway_conn(remote_agent: str = "server"):
    """Initialize connection to the gateway.
    Establishes connection to a gateway service running on localhost using retry mechanism.
    Returns:
        None
    Raises:
        ConnectionError: If unable to establish connection after retries.
        TimeoutError: If connection attempts exceed max duration.
    Notes:
        - Uses default endpoint http://127.0.0.1:46357
        - Insecure connection is enabled
        - Maximum retry duration is 10 seconds
        - Initial retry delay is 1 second
        - Targets remote agent named "server"
    """

    Config.gateway_container.set_config(
        endpoint=os.getenv("AGP_GATEWAY_ENDPOINT", "http://127.0.0.1:46357"), insecure=True
    )

    # Call connect_with_retry
    _ = await Config.gateway_container.connect_with_retry(
        agent_container=Config.agent_container,
        max_duration=10,
        initial_delay=1,
        remote_agent=remote_agent,
    )

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