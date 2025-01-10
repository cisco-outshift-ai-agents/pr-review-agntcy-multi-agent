from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, Request

from src.auth import create_signature, fastapi_validate_github_signature, lambda_validate_github_signature, valid_github_signature
from src.utils.constants import GITHUB_SIGNATURE_HEADER


@pytest.mark.parametrize(
    "payload, signature, secret, expected",
    [
        # Valid
        (b"testpayload", create_signature(b"testpayload", "testsecret"), "testsecret", True),
        # Payload signed with different key
        (b"testpayload", create_signature(b"testpayload", "invalidsecret"), "testsecret", False),
        # Payload empty
        (b"", create_signature(b"testpayload", "testsecret"), "testsecret", False),
        # Secret empty
        (b"testpayload", create_signature(b"testpayload", "testsecret"), "", False),
    ],
)
def test_valid_github_signature(payload: bytes, signature: str, secret: str, expected: bool):
    assert valid_github_signature(payload, signature, secret) == expected


@patch("src.auth.os.getenv")
@patch("src.auth.valid_github_signature")
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
async def test_fastapi_validate_github_signature(
    mock_valid_github_signature: MagicMock,
    mock_getenv: MagicMock,
    signature_header: str | None,
    gh_secret: str | None,
    valid_signature: bool,
    expected_status: int,
) -> None:
    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.return_value = signature_header
    mock_getenv.return_value = gh_secret
    mock_request.body = AsyncMock(return_value=b"payload")
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


@patch("src.auth.os.getenv")
@patch("src.auth.valid_github_signature")
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
    mock_getenv: MagicMock,
    signature_header: str | None,
    gh_secret: str | None,
    valid_signature: bool,
    expected_status: int,
) -> None:
    event = MagicMock(dict[str, Any])
    event.get.side_effect = lambda key, default=None: {"headers": {GITHUB_SIGNATURE_HEADER: signature_header}, "body": "payload"}.get(
        key, MagicMock()
    )

    mock_getenv.return_value = gh_secret
    mock_valid_github_signature.return_value = valid_signature
    mock_handler = Mock()

    validator = lambda_validate_github_signature(mock_handler)

    resp = validator(event, None)
    if expected_status:
        statusCode = resp.get("statusCode")
        assert statusCode == expected_status
    else:
        assert resp == mock_handler.return_value
