import requests

import pytest

import utils
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_create_public_did(setup_env):
    req_header = {"api_key": "adminApiKey"}
    result = await utils.create_pub_did(req_header)

    assert result.did_object and result.did_object != {}
    assert result.did_object["posture"] == "public"
    assert result.issuer_verkey and result.issuer_verkey != {}
    assert result.issuer_endpoint and result.issuer_endpoint != {}

    url = f"{utils.ADMIN_URL}:{utils.ADMIN_PORT}/wallet/did"
    response = requests.get(url, headers={"x-api-key": "adminApiKey"})
    found = [
        r for r in response.json()["results"] if r["did"] == result.did_object["did"]
    ]

    assert len(found) == 1
    assert found[0]["verkey"] == result.did_object["verkey"]
    assert found[0]["posture"] == "public"


@pytest.mark.asyncio
async def test_create_public_did_no_api_key(setup_env):
    with pytest.raises(HTTPException) as exc:
        await utils.create_pub_did({})
    assert exc.value.status_code == 400
    assert (
        exc.value.detail
        == "Bad headers. Either provide an api_key or both wallet_id and tenant_jwt"
    )
