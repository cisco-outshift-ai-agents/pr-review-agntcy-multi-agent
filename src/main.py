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
from http import HTTPStatus
from typing import Any

from auth import lambda_validate_github_signature
from handle_pr import handle_github_event
from utils.constants import GITHUB_EVENT_HEADER
from utils.env_setter import set_environment_variables
from utils.lambda_helpers import lambdaResponse
from utils.logging_config import logger as log

# TODO: Typed github event should be created with typed Payload, github.Event exists already.
#  Worth to check: https://docs.powertools.aws.dev/lambda/python/latest/utilities/parser/

# Set langchain api key as env var
set_environment_variables()


@lambda_validate_github_signature
async def handle_event(event: dict[str, Any], context):
    # The body is coming as a stringified json object, the headers is a proper dict
    body_string: str = event.get("body", "")
    headers: dict[str, Any] = event.get("headers", {})
    x_github_event = headers.get(GITHUB_EVENT_HEADER)
    if not x_github_event:
        log.debug(f"Invalid headers: {headers}")
        return lambdaResponse("Invalid headers", HTTPStatus.BAD_REQUEST)

    try:
        payload = json.loads(body_string)
    except json.JSONDecodeError as _e:
        return lambdaResponse("Invalid request body", HTTPStatus.BAD_REQUEST)

    res = await handle_github_event(payload, x_github_event)
    return lambdaResponse("", res.status_code)
