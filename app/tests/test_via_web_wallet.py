import pytest
import requests

from main import app
import utils

from aiohttp import ClientResponseError
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_pub_did_via_web(setup_env, async_client_bob):
    async_client = async_client_bob
    response = await async_client.get("/wallet/create-pub-did")
    assert response.status_code == 200
    result = response.json()

    assert result["did_object"]["posture"] == "public"
    print(str(result))
    response = (await async_client.get("/wallet/list-dids")).json()

    print(str(response))
    found = [r for r in response["results"] if r["did"] == result["did_object"]["did"]]

    print(str(found))
    assert len(found) == 1
    assert found[0]["verkey"] == result["did_object"]["verkey"]
    assert found[0]["posture"] in ("public", "posted")
    print(str(found))


@pytest.mark.asyncio
async def test_get_pub_did_via_web_no_header(setup_env):
    async with AsyncClient(app=app, base_url="http://localhost:8000") as ac:
        try:
            await ac.get("/wallet/create-pub-did", headers={})
        except ClientResponseError as error:
            assert error.status == 401
            assert error.message == "Unauthorized"
