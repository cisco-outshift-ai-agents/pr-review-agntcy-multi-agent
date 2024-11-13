from functools import wraps
import hashlib
import hmac
from http import HTTPStatus
import os
from typing import Any, Awaitable, Callable
from fastapi import HTTPException, Request
from utils.logging_config import logger as log


def fastapi_validate_github_signature(handler: Callable[[Request], Awaitable[Any]]):
    """Wraps a fastapi handler to verify GitHub signature header

    Raise 500 if env var is missing, 403 if signature is invalid

    Args:
        handler: async fastapi handler
    """

    @wraps(handler)
    async def wrapper(request: Request, *args, **kwargs):
        signature_header = request.headers.get("x-hub-signature-256")
        if not signature_header:
            log.debug("Missing signature header")
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN)

        gh_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        if not gh_secret:
            log.error("GITHUB_WEBHOOK_SECRET is not set")
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        payload = await request.body()
        if not valid_github_signature(payload, signature_header, gh_secret):
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN)
        return await handler(request, *args, **kwargs)

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
