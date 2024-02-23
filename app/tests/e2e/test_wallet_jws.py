import pytest
from aries_cloudcontroller import DIDCreate
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.jws import JWSCreateRequest
from shared.util.rich_async_client import RichAsyncClient


@pytest.mark.anyio
async def test_sign_jws_success(alice_member_client: RichAsyncClient):
    # Create DID:key for Alice
    did_info = await alice_member_client.post(
        "v1/wallet/dids", json=DIDCreate(method="key").model_dump()
    )
    did = did_info.json()["did"]

    request_payload = JWSCreateRequest(
        did=did,
        headers={},
        payload={"example": "payload"},
        verification_method=None,
    )

    response = await alice_member_client.post(
        "/v1/wallet/jws/sign", json=request_payload.model_dump()
    )

    assert response.status_code == 200
    assert "jws" in response.json()


@pytest.mark.anyio
async def test_sign_jws_x(alice_member_client: RichAsyncClient):
    with pytest.raises(ValidationError):
        # Requires at least one of did or verification method
        JWSCreateRequest(
            did=None,
            headers={},
            payload={"example": "payload"},
            verification_method=None,
        )

    with pytest.raises(HTTPException) as exc_info:
        await alice_member_client.post("/v1/wallet/jws/sign", json={})
    assert exc_info.value.status_code == 422


@pytest.mark.anyio
async def test_sign_and_verify_jws_success(alice_member_client: RichAsyncClient):
    # Create DID:key for Alice
    did_info = await alice_member_client.post(
        "v1/wallet/dids", json=DIDCreate(method="key").model_dump()
    )
    did = did_info.json()["did"]

    request_payload = JWSCreateRequest(
        did=did,
        headers={},
        payload={"example": "payload"},
        verification_method=None,
    )

    sign_response = await alice_member_client.post(
        "/v1/wallet/jws/sign", json=request_payload.model_dump()
    )

    assert sign_response.status_code == 200

    verify_response = await alice_member_client.post(
        "/v1/wallet/jws/verify", json=sign_response.json()
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] == True


@pytest.mark.anyio
async def test_verify_jws_x(alice_member_client: RichAsyncClient):
    with pytest.raises(HTTPException) as exc_info:
        await alice_member_client.post("/v1/wallet/jws/verify", json={"jws": ""})
    assert (
        exc_info.value.status_code == 500
    )  # Todo: this error should be improved in ACA-Py
