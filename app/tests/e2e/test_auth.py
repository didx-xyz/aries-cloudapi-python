import asyncio
from uuid import uuid4

import pytest
from aries_cloudcontroller import AcaPyClient
from aries_cloudcontroller.exceptions import UnauthorizedException

from app.routes.admin.tenants import router as tenants_router
from app.routes.connections import router as connections_router
from shared.constants import TENANT_FASTAPI_ENDPOINT
from shared.util.rich_async_client import RichAsyncClient

CONNECTIONS_BASE_PATH = connections_router.prefix
TENANTS_BASE_PATH = tenants_router.prefix

group_id = "TestGroup"


@pytest.mark.anyio
async def test_invalid_acapy_auth_header(alice_acapy_client: AcaPyClient):
    # Modify the AcaPyClient to use the wrong header -- assert ACA-Py auth error
    existing_token = alice_acapy_client.api_client.default_headers[
        "Authorization"
    ].split(" ")[1]

    alice_acapy_client.api_client.default_headers["Authorization"] = (
        f"Barer {existing_token}"
    )

    with pytest.raises(UnauthorizedException) as exc_info:
        await alice_acapy_client.connection.get_connections()
    assert exc_info.value.status == 401
    assert "Invalid Authorization header structure" == str(exc_info.value.reason)


@pytest.mark.anyio
async def test_jwt_invalid_token_error(tenant_admin_client: RichAsyncClient):
    # Step 1: Create a tenant and get a valid access token
    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "image_url": "https://image.example.com",
            "wallet_label": uuid4().hex,
            "group_id": group_id,
        },
    )
    assert response.status_code == 200
    tenant = response.json()
    wallet_id = tenant["wallet_id"]
    valid_token = tenant["access_token"].split("tenant.")[1]

    try:
        # Step 2: Corrupt the token
        # Split the token into header, payload, and signature
        token_parts = valid_token.split(".")
        assert len(token_parts) == 3, "Invalid JWT token format"

        # Corrupt the payload by altering a character
        corrupted_payload = token_parts[1][:-1] + (
            "A" if token_parts[1][-1] != "A" else "B"
        )
        corrupted_token = ".".join([token_parts[0], corrupted_payload, token_parts[2]])

        # Step 3: Attempt to use the corrupted token
        tenant_client = RichAsyncClient(
            base_url=TENANT_FASTAPI_ENDPOINT, raise_status_error=False
        )
        tenant_client.headers["x-api-key"] = f"tenant.{corrupted_token}"

        # Make a request to a protected endpoint
        response = await tenant_client.get(CONNECTIONS_BASE_PATH)

        # Step 4: Assert that the response is 401 Unauthorized
        assert response.status_code == 401
        assert response.json()["detail"] == "Unauthorized"

    finally:
        # Cleanup: Delete the created tenant
        delete_response = await tenant_admin_client.delete(
            f"{TENANTS_BASE_PATH}/{wallet_id}"
        )
        assert delete_response.status_code == 200


@pytest.mark.anyio
async def test_invalid_token_error_after_rotation(tenant_admin_client: RichAsyncClient):
    # Step 1: Create a tenant and get a valid access token
    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "image_url": "https://image.example.com",
            "wallet_label": uuid4().hex,
            "group_id": group_id,
        },
    )
    assert response.status_code == 200
    tenant = response.json()
    wallet_id = tenant["wallet_id"]

    # Prepare the tenant client
    tenant_client = RichAsyncClient(
        base_url=TENANT_FASTAPI_ENDPOINT, raise_status_error=False
    )

    try:
        # Step 2: Rotate the token (invalidate the old token)
        # Assuming there's an endpoint to rotate the token
        rotate_response = await tenant_admin_client.get(
            f"{TENANTS_BASE_PATH}/{wallet_id}/access-token?group_id={group_id}"
        )
        assert rotate_response.status_code == 200
        old_token = rotate_response.json()["access_token"]

        # Set header to original token
        tenant_client.headers["x-api-key"] = old_token

        await asyncio.sleep(0.5)  # short sleep

        # rotate again
        rotate_response = await tenant_admin_client.get(
            f"{TENANTS_BASE_PATH}/{wallet_id}/access-token?group_id={group_id}"
        )
        assert rotate_response.status_code == 200

        await asyncio.sleep(3)  # sleep, wait for storage record to update

        # Step 3: Attempt to use the old token after token rotated
        response = await tenant_client.get(CONNECTIONS_BASE_PATH)

        # Step 4: Assert that the response is 401 Unauthorized
        assert response.status_code == 401
        assert response.json()["detail"] == "Token not valid."

    finally:
        # Cleanup: Delete the created tenant
        delete_response = await tenant_admin_client.delete(
            f"{TENANTS_BASE_PATH}/{wallet_id}"
        )
        assert delete_response.status_code == 200
