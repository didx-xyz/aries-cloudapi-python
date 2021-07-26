import pytest
from admin.governance.wallet.wallets import (
    list_dids,
    fetch_current_did,
    set_did_endpoint,
)
import acapy_wallet_facade as wallet_facade
import ledger_facade

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}


@pytest.fixture(name="create_did_mock")
async def fixture_create_did_mock(async_client):
    did_response = await async_client.get(
        "/wallet/create-local-did",
        headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
    )
    did_response = did_response.json()
    did = did_response["result"]["did"]
    return did


@pytest.mark.asyncio
async def test_list_dids(async_client, yoma_agent_mock):
    response = await async_client.get(
        "/wallet/list-dids",
        headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
    )

    assert response.status_code == 200
    response = response.json()

    res_method = await list_dids(aries_controller=yoma_agent_mock)

    assert res_method == response


@pytest.mark.asyncio
async def test_create_local_did(async_client, yoma_agent_mock):
    response = await async_client.get(
        "/wallet/create-local-did",
        headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
    )

    assert response.status_code == 200
    response = response.json()
    assert response["result"]["did"]
    assert response["result"]["verkey"]
    assert response


@pytest.mark.asyncio
async def test_fetch_current_did(async_client, yoma_agent_mock):
    response = await async_client.get(
        "/wallet/fetch-current-did",
        headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
    )
    assert response.status_code == 200
    response = response.json()
    assert response["result"]
    assert response["result"]["did"]
    assert response["result"]["verkey"]

    res_method = await fetch_current_did(aries_controller=yoma_agent_mock)
    assert res_method == response


@pytest.mark.asyncio
async def test_get_did_endpoint(async_client, create_did_mock):
    did = create_did_mock
    response = await async_client.get(
        f"/wallet/get-did-endpoint/{did}",
        headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
    )
    assert response.status_code == 200

    response = response.json()
    assert response["did"] == did


@pytest.mark.asyncio
async def test_assign_pub_did(async_client, yoma_agent_mock):
    generate_did_res = await wallet_facade.create_did(yoma_agent_mock)
    did_object = generate_did_res.dict()["result"]
    await ledger_facade.post_to_ledger(did_object=did_object)
    did = did_object["did"]
    response = await async_client.get(
        f"/wallet/assign-pub-did?did={did}",
        headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
    )
    assert response.status_code == 200
    response = response.json()

    assert response["result"]["did"] == did
    assert response["result"]["verkey"]


@pytest.mark.asyncio
async def test_set_did_endpoint(async_client, yoma_agent_mock):
    response = await async_client.get(
        "/wallet/create-pub-did",
        headers={
            "x-api-key": "adminApiKey",
            "x-role": "yoma",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )
    assert response.status_code == 200
    response = response.json()

    endpoint = response["issuer_endpoint"]

    did = response["did_object"]["did"]
    endpoint_type = "Endpoint"

    response = await async_client.post(
        "/wallet/set-did-endpoint",
        headers={
            "x-api-key": "adminApiKey",
            "x-role": "yoma",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
        params={"did": did, "endpoint": endpoint, "end_point_type": endpoint_type},
    )

    assert response.json() == {}


@pytest.mark.asyncio
async def test_create_pub_did(async_client):
    response = await async_client.get(
        "/wallet/create-pub-did",
        headers={
            "x-api-key": "adminApiKey",
            "x-role": "yoma",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    assert response.status_code == 200
    response = response.json()
    assert response["did_object"] and response["did_object"] != {}
    assert response["issuer_verkey"] and response["issuer_verkey"] != {}
    assert response["issuer_endpoint"] and response["issuer_endpoint"] != {}
    assert response["did_object"]["posture"] in ["public", "posted"]
