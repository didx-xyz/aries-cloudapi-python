from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import Response

from endorser.util.trust_registry import is_valid_issuer


@pytest.mark.anyio
async def test_is_valid_issuer_success():
    # Mock responses to simulate the trust registry responses
    actor_response = {"roles": ["issuer"]}
    schema_response = {"id": "test-schema-id"}

    with patch(
        "endorser.util.trust_registry.RichAsyncClient.get", new_callable=AsyncMock
    ) as mock_get:
        # Simulate successful responses for both actor and schema checks
        mock_get.side_effect = [
            Response(200, json=actor_response),  # Response for actor check
            Response(200, json=schema_response),  # Response for schema check
        ]

        result = await is_valid_issuer("did:sov:xxxx", "test-schema-id")

        assert result is True


@pytest.mark.anyio
async def test_is_valid_issuer_did_not_found():
    # Simulate a 404 response for the DID check
    with patch(
        "endorser.util.trust_registry.RichAsyncClient.get",
        side_effect=HTTPException(status_code=404, detail="Not Found"),
    ) as mock_get:
        result = await is_valid_issuer("did:sov:xxxx", "test-schema-id")

        assert result is False
        mock_get.assert_called_once()  # Ensure only the DID check was performed


@pytest.mark.anyio
@pytest.mark.parametrize("roles", [[], ["verifier"]])
async def test_is_valid_issuer_actor_not_issuer(roles):
    actor_response = {"roles": roles}

    with patch(
        "endorser.util.trust_registry.RichAsyncClient.get",
        return_value=Response(200, json=actor_response),
    ) as mock_get:
        result = await is_valid_issuer("did:sov:xxxx", "test-schema-id")

        assert result is False
        mock_get.assert_called_once()


@pytest.mark.anyio
async def test_is_valid_issuer_schema_not_registered():
    # Mock responses to simulate the trust registry responses, first for the actor, then a 404 for the schema
    actor_response = {"roles": ["issuer"]}

    with patch(
        "endorser.util.trust_registry.RichAsyncClient.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.side_effect = [
            Response(200, json=actor_response),  # Successful response for actor check
            HTTPException(status_code=404, detail="Not Found"),  # 404 for schema check
        ]

        result = await is_valid_issuer("did:sov:xxxx", "test-schema-id")

        assert result is False
        assert mock_get.call_count == 2  # Ensure both checks were performed


@pytest.mark.anyio
async def test_is_valid_issuer_http_error_on_actor():
    # Simulate an HTTP error during the actor fetch
    with patch(
        "endorser.util.trust_registry.RichAsyncClient.get",
        side_effect=HTTPException(status_code=500, detail="Server Error"),
    ) as mock_get:
        with pytest.raises(HTTPException):
            await is_valid_issuer("did:sov:xxxx", "test-schema-id")

        mock_get.assert_called_once()  # Ensure the call was made once before the exception


@pytest.mark.anyio
async def test_is_valid_issuer_http_error_on_schema():
    # Simulate an HTTP error during the schema fetch
    actor_response = {"roles": ["issuer"]}
    with patch(
        "endorser.util.trust_registry.RichAsyncClient.get",
        side_effect=[
            Response(200, json=actor_response),
            HTTPException(status_code=500, detail="Server Error"),
        ],
    ) as mock_get:
        with pytest.raises(HTTPException):
            await is_valid_issuer("did:sov:xxxx", "test-schema-id")

        assert mock_get.call_count == 2
