import requests

import pytest

import utils
from core import wallet
from fastapi import HTTPException
import routers

from facade import create_controller, create_controller_dependency


@pytest.mark.asyncio
async def test_create_public_did(setup_env, agent_controller):
    result = await wallet.create_pub_did(agent_controller)

    assert result.did_object and result.did_object != {}
    assert result.did_object["posture"] == "public"
    assert result.issuer_verkey and result.issuer_verkey != {}
    assert result.issuer_endpoint and result.issuer_endpoint != {}

    url = f"{utils.admin_url}:{utils.admin_port}/wallet/did"
    response = requests.get(url, headers={"x-api-key": "adminApiKey"})
    found = [
        r for r in response.json()["results"] if r["did"] == result.did_object["did"]
    ]

    assert len(found) == 1
    assert found[0]["verkey"] == result.did_object["verkey"]
    assert found[0]["posture"] == "public"
