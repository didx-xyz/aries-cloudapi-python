import pytest
import requests
from httpx import AsyncClient

import utils
from main import app


@pytest.mark.asyncio
async def test_get_pub_did_via_web(setup_env):
    async with AsyncClient(app=app, base_url="http://localhost:8000") as ac:
        response = await ac.get(
            "/wallets/create-pub-did", headers={"x-api-key": "adminApiKey"}
        )
    assert response.status_code == 200
    result = response.json()

    assert result["did_object"]["posture"] == "public"

    url = f"{utils.admin_url}:{utils.admin_port}/wallet/did"
    response = requests.get(url, headers={"x-api-key": "adminApiKey"})
    found = [
        r for r in response.json()["results"] if r["did"] == result["did_object"]["did"]
    ]

    assert len(found) == 1
    assert found[0]["verkey"] == result["did_object"]["verkey"]
    assert found[0]["posture"] == "public"
