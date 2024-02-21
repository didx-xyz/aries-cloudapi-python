import pytest
from aries_cloudcontroller import DIDCreate
from fastapi import HTTPException

from app.models.sd_jws import SDJWSCreateRequest
from shared.util.rich_async_client import RichAsyncClient


@pytest.mark.anyio
async def test_sign_sdjws_success(alice_member_client: RichAsyncClient):
    # Create DID:key for Alice
    did_info = await alice_member_client.post(
        "v1/wallet/dids", json=DIDCreate(method="key").model_dump()
    )
    did = did_info.json()["did"]

    request_payload = SDJWSCreateRequest(
        did=did,
        headers={},
        payload={"example": "payload"},
        verification_method=None,
    )

    response = await alice_member_client.post(
        "/v1/wallet/sd-jws/sign", json=request_payload.model_dump()
    )

    assert response.status_code == 200
    assert "sd_jws" in response.json()


@pytest.mark.anyio
async def test_sign_sdjws_x(alice_member_client: RichAsyncClient):
    with pytest.raises(HTTPException) as exc_info:
        # Requires at least one of did or verification method
        x_request_payload = SDJWSCreateRequest(
            did=None,
            headers={},
            payload={"example": "payload"},
            verification_method=None,
        )
        await alice_member_client.post(
            "/v1/wallet/sd-jws/sign", json=x_request_payload.model_dump()
        )
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_sign_and_verify_sdjws_success(alice_member_client: RichAsyncClient):
    # Create DID:key for Alice
    did_info = await alice_member_client.post(
        "v1/wallet/dids", json=DIDCreate(method="key").model_dump()
    )
    did = did_info.json()["did"]

    request_payload = SDJWSCreateRequest(
        did=did,
        headers={},
        payload={"example": "payload"},
        verification_method=None,
    )

    sign_response = await alice_member_client.post(
        "/v1/wallet/sd-jws/sign", json=request_payload.model_dump()
    )

    assert sign_response.status_code == 200

    verify_response = await alice_member_client.post(
        "/v1/wallet/sd-jws/verify", json=sign_response.json()
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True


@pytest.mark.anyio
async def test_verify_sdjws_x(alice_member_client: RichAsyncClient):
    with pytest.raises(HTTPException) as exc_info:
        await alice_member_client.post("/v1/wallet/sd-jws/verify", json={"sd_jws": ""})
    assert (
        exc_info.value.status_code == 500
    )  # Todo: this error should be improved in ACA-Py
