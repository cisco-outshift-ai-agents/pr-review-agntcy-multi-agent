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

import hashlib
import hmac
from functools import wraps
from http import HTTPStatus
from typing import Any, Awaitable, Callable

from fastapi import HTTPException, Request

from utils.constants import GITHUB_SIGNATURE_HEADER
from utils.lambda_helpers import lambdaResponse
from utils.logging_config import logger as log
from utils.secret_manager import secret_manager


def fastapi_validate_github_signature(handler: Callable[[Request], Awaitable[Any]]):
    """Wraps a fastapi handler to verify GitHub signature header

    Raise 500 if env var is missing, 403 if signature is invalid

    Args:
        handler: async fastapi handler
    """

    @wraps(handler)
    async def wrapper(request: Request):
        signature_header = request.headers.get(GITHUB_SIGNATURE_HEADER)
        if not signature_header:
            log.debug("Missing signature header")
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN)

        payload = await request.body()
        if not valid_github_signature(payload, signature_header, secret_manager.github_webhook_secret):
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN)
        return await handler(request)

    return wrapper

def lambda_validate_github_signature(handler: Callable[[dict[str, Any], Any], dict[str, Any]]):
    """Wraps an AWS lambda handler to verify GitHub signature header

    Raise 500 if env var is missing, 403 if signature is invalid

    Args:
        handler: async fastapi handler
    """

    @wraps(handler)
    def wrapper(event: dict[str, Any], context: Any):
        headers: dict[str, Any] = event.get("headers", {})
        # Sometimes headers come with camel case, sometimes they are lowercase, depending on the Lambda trigger runtime
        # sam preserves the case while AWS API GW or Function URLs in AWS don't, they send lowercase header keys
        # This makes our function compatible with any env
        headers = {key.lower(): value for key, value in headers.items()}
        event["headers"] = headers

        signature_header = headers.get(GITHUB_SIGNATURE_HEADER)
        if not signature_header:
            log.debug("Missing signature header")
            return lambdaResponse("Missing signature header", HTTPStatus.FORBIDDEN)

        payload: str = event.get("body", "")
        if not valid_github_signature(payload.encode(), signature_header, secret_manager.github_webhook_secret):
            return lambdaResponse("", HTTPStatus.FORBIDDEN)
        return handler(event, context)

    return wrapper

def valid_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify the signature of the payload with the given secret

    Args:
        payload: request body
        signature: incoming signature of the payload
        secret: the secret to generate the signature with
    """

    if not signature or not secret:
        return False

    return hmac.compare_digest(create_signature(payload, secret), signature)


def create_signature(payload: bytes, secret: str):
    """Create a signature the same way as GitHub creates is

    Args:
        payload: request body
        secret: the secret to generate the signature with
    """
    return "sha256=" + hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256).hexdigest()
