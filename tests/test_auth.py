import sys
from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

secret_manager_mock = Mock()
sys.modules["utils.secret_manager"] = secret_manager_mock

import pytest
from fastapi import HTTPException, Request

from auth import fastapi_validate_github_signature, create_signature, valid_github_signature, \
    lambda_validate_github_signature
from src.utils.constants import GITHUB_SIGNATURE_HEADER


@pytest.mark.parametrize(
    "payload, secret, signature_payload, signature_secret, expected",
    [
        # Valid
        (b"testpayload", "testsecret", b"testpayload", "testsecret", True),
        # Payload signed with different key
        (b"testpayload", "testsecret", b"testpayload", "invalidsecret", False),
        # Payload empty
        (b"", "testsecret", b"testpayload", "testsecret", False),
        # Secret empty
        (b"testpayload", "", b"testpayload", "testsecret", False),
    ],
)
def test_valid_github_signature(payload: bytes, signature_payload: bytes, signature_secret: str, secret: str,
                                expected: bool):
    assert valid_github_signature(payload, create_signature(signature_payload, signature_secret), secret) == expected


@patch("auth.valid_github_signature")
@pytest.mark.parametrize(
    "signature_header, gh_secret, valid_signature, expected_status",
    [
        # Valid
        ("testsignature", "testsecret", True, None),
        # No header
        (None, "testsecret", None, HTTPStatus.FORBIDDEN),
        # No secret
        ("testsignature", None, None, HTTPStatus.FORBIDDEN),
        # Invalid signature
        ("testsignature", "testsecret", False, HTTPStatus.FORBIDDEN),
    ],
)
@pytest.mark.asyncio
async def test_fastapi_validate_github_signature(
        mock_valid_github_signature: MagicMock,
    signature_header: str | None,
    gh_secret: str | None,
    valid_signature: bool,
    expected_status: int,
) -> None:
    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.return_value = signature_header
    mock_request.body = AsyncMock(return_value=b"payload")

    secret_manager_mock.secret_manager.get_github_webhook_secret.return_value = gh_secret

    mock_valid_github_signature.return_value = valid_signature

    mock_handler = AsyncMock()

    validator = fastapi_validate_github_signature(mock_handler)

    if expected_status:
        with pytest.raises(HTTPException) as excinfo:
            await validator(mock_request)
        assert excinfo.value.status_code == expected_status
    else:
        result = await validator(mock_request)
        assert result == mock_handler.return_value
        mock_handler.assert_awaited_once_with(mock_request)


@patch("auth.valid_github_signature")
@pytest.mark.parametrize(
    "signature_header, gh_secret, valid_signature, expected_status",
    [
        # Valid
        ("testsignature", "testsecret", True, None),
        # No header
        (None, "testsecret", None, HTTPStatus.FORBIDDEN),
        # No secret
        ("testsignature", None, None, HTTPStatus.INTERNAL_SERVER_ERROR),
        # Invalid signature
        ("testsignature", "testsecret", False, HTTPStatus.FORBIDDEN),
    ],
)
@pytest.mark.asyncio
async def test_lambda_validate_github_signature(
    mock_valid_github_signature: MagicMock,
    signature_header: str | None,
    gh_secret: str | None,
    valid_signature: bool,
    expected_status: int,
) -> None:
    event = MagicMock(dict[str, Any])
    event.get.side_effect = lambda key, default=None: {"headers": {GITHUB_SIGNATURE_HEADER: signature_header}, "body": "payload"}.get(
        key, MagicMock()
    )

    secret_manager_mock.secret_manager.get_github_webhook_secret.return_value = gh_secret

    mock_valid_github_signature.return_value = valid_signature

    mock_handler = Mock()

    validator = lambda_validate_github_signature(mock_handler)

    resp = validator(event, None)
    if expected_status:
        statusCode = resp.get("statusCode")
        assert statusCode == expected_status
    else:
        assert resp == mock_handler.return_value
