import pytest
import json
from admin.governance.wallet.wallets_admin import (
    create_local_did,
    list_dids,
    fetch_current_did,
    rotate_keypair,
    get_did_endpoint,
    assign_pub_did,
    set_did_endpoint,
)

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}


@pytest.fixture(name="create_did_mock")
async def fixture_create_did_mock(async_client):
    did_response = await async_client.get(
        "/admin/wallet-admin/create-local-did",
        headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
    )
    did_response = did_response.json()
    did = did_response["result"]["did"]
    return did


@pytest.mark.asyncio
async def test_list_dids(async_client, yoma_agent_mock):
    response = await async_client.get(
        "/admin/wallet-admin/list-dids",
        headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
    )

    assert response.status_code == 200
    response = response.json()

    res_method = await list_dids(aries_controller=yoma_agent_mock)

    assert res_method == response


@pytest.mark.asyncio
async def test_create_local_did(async_client, yoma_agent_mock):

    response = await async_client.get(
        "/admin/wallet-admin/create-local-did",
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
        "/admin/wallet-admin/fetch-current-did",
        headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
    )
    assert response.status_code == 200
    response = response.json()
    assert response["result"]
    assert response["result"]["did"]
    assert response["result"]["verkey"]

    res_method = await fetch_current_did(aries_controller=yoma_agent_mock)
    assert res_method == response


# --------------------------------------------
# @pytest.mark.asyncio
# async def test_get_did_endpoint(async_client, yoma_agent_mock,create_did_mock):

#     did = create_did_mock
#     response = await async_client.get(
#         "/wallet-admin/get-did-endpoint/{did}",
#         headers={"x-api-key":"adminApiKey","x-role":"yoma"},
#     )
#     # assert response.status_code == 200

#     response = response.json()
#     assert response ==''


@pytest.mark.asyncio
async def test_assign_pub_did(async_client, yoma_agent_mock, create_did_mock):
    did = create_did_mock
    assert did == ""
    response = await async_client.post(
        "/admin/wallet-admin/assign-pub-did",
        headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
        data=json.dumps(did),
    )
    assert response == ""
