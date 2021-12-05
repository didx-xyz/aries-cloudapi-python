import pytest
from httpx import AsyncClient

from app.main import app
from app.tests.util.client import yoma_acapy_client, yoma_client


@pytest.mark.asyncio
async def test_get_pub_did_via_web():
    async with yoma_client(app=app) as client:
        response = await client.get("/wallet/create-pub-did")

    assert response.status_code == 200
    result = response.json()

    assert result["did_object"]["posture"] in ["posted", "public"]

    acapy_client = yoma_acapy_client()
    dids = await acapy_client.wallet.get_dids()

    found = [r for r in dids.results or [] if r.did == result["did_object"]["did"]]

    assert len(found) == 1
    assert found[0].verkey == result["did_object"]["verkey"]
    assert found[0].posture in ["posted", "public"]


@pytest.mark.asyncio
async def test_get_pub_did_via_web_no_header():
    async with AsyncClient(app=app, base_url="http://localhost:8000") as client:
        response = await client.get("/wallet/create-pub-did")
        assert response.status_code == 403
        assert response.text == '{"detail":"Not authenticated"}'
