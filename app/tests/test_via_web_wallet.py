import httpx
import pytest
from aiohttp import ClientResponseError
from httpx import AsyncClient

import app.utils as utils
from app.main import app


@pytest.mark.asyncio
async def test_get_pub_did_via_web(setup_env):
    async with AsyncClient(app=app, base_url="http://localhost:8000") as ac:
        response = await ac.get(
            "/wallet/create-pub-did",
            headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
        )
    assert response.status_code == 200
    result = response.json()

    assert result["did_object"]["posture"] in ["posted", "public"]

    url = f"{utils.admin_url}:{utils.admin_port}/wallet/did"
    response = httpx.get(url, headers={"x-api-key": "adminApiKey", "x-role": "yoma"})
    found = [
        r for r in response.json()["results"] if r["did"] == result["did_object"]["did"]
    ]

    assert len(found) == 1
    assert found[0]["verkey"] == result["did_object"]["verkey"]
    assert found[0]["posture"] in ["posted", "public"]


@pytest.mark.asyncio
async def test_get_pub_did_via_web_no_header(setup_env):
    async with AsyncClient(app=app, base_url="http://localhost:8000") as ac:
        try:
            await ac.get("/wallet/create-pub-did", headers={})
        except ClientResponseError as error:
            assert error.status == 401
            assert error.message == "Unauthorized"
