import requests

import pytest
from fastapi import HTTPException

import utils

ADMIN_URL = "http://localhost"
ADMIN_PORT = "8000"
URL = f"{ADMIN_URL}:{ADMIN_PORT}/admin/wallet/assign-pub-did"


@pytest.mark.asyncio
async def test_assign_public_did(setup_env):

    response = requests.get(URL, headers={"api-key": "adminApiKey"})

    found = response.json()
    assert len(found) == 3
    assert found["did_object"]["did"] and found["did_object"]["did"] != ""
    assert found["did_object"]["verkey"] and found["did_object"]["verkey"] != ""
    assert found["did_object"]["posture"] == "public"


@pytest.mark.asyncio
async def test_assign_public_did_no_api_key(setup_env):
    with pytest.raises(HTTPException) as exc:
        await utils.create_pub_did({})
    assert exc.value.status_code == 400
    assert (
        exc.value.detail
        == "Bad headers. Either provide an api_key or both wallet_id and tenant_jwt"
    )
