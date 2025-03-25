import json
from typing import Any, Dict
import uuid

from agp_api.agent.agent_container import AgentContainer
from agp_api.gateway.gateway_container import GatewayContainer
from langchain_core.messages import HumanMessage
from langchain_core.messages.utils import convert_to_openai_messages
from utils.models import ReviewComment

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
    remote_agent = "tf_code_reviewer"
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
    await init_client_gateway_conn(remote_agent=Config.remote_agent)

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
        "agent_id": "remote_code_reviewer_agent",
        "input": {"messages": messages},
        "model": "gpt-4o",
        "metadata": {"id": str(uuid.uuid4())},
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
        endpoint="http://127.0.0.1:46357", insecure=True
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
        # Parse result back into ReviewComment objects
        output = response_data.get("output", {})
        ai_msg = output["messages"][-1]["content"]
        parsed = json.loads(ai_msg)
        log.info(f"Decoded response: {parsed}")
        comments = [ReviewComment.model_validate(comment) for comment in parsed]


        return {
            "new_review_comments": [c for c in comments if c.line_number != 0]
        }
    except Exception as e:
        return {"error": f"Failed to decode response: {str(e)}"}