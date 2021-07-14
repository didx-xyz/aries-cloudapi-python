import json

import pytest
from aiohttp import ClientResponseError

from admin.governance.multitenant_wallet.wallet import (
    get_subwallet,
    get_subwallet_auth_token,
    query_subwallet,
    update_subwallet,
)
from tests.utils_test import get_random_string

WALLET_HEADERS = {"content-type": "application/json", "x-role": "member"}
WALLET_PATH = "/admin/wallets"
CREATE_WALLET_PAYLOAD = {
    "image_url": "https://aries.ca/images/sample.png",
    "label": "YOMA",
    "wallet_key": "MySecretKey1234",
    "wallet_name": "DarthVadersHolidayFunds",
}


@pytest.fixture(name="create_wallet")
async def fixture_create_wallet(async_client):
    wallet_response = await create_wallet(async_client)
    wallet_id = wallet_response["wallet_id"]
    yield wallet_response
    response = await async_client.delete(
        f"{WALLET_PATH}/{wallet_id}",
        headers={"x-api-key": "adminApiKey"},
    )
    assert response.status_code == 200
    assert response.json() == "Successfully removed wallet"


async def create_wallet(async_client):
    wallet_payload = CREATE_WALLET_PAYLOAD.copy()
    wallet_payload["wallet_name"] = "wallet" + get_random_string(4)
    wallet_payload["label"] = "label" + get_random_string(4)
    wallet_response = await async_client.post(
        WALLET_PATH + "/create-wallet",
        headers={"x-api-key": "adminApiKey", **WALLET_HEADERS},
        data=json.dumps(wallet_payload),
    )
    wallet_response = wallet_response.json()
    return wallet_response


@pytest.mark.asyncio
async def create_pub_did(async_client):
    response = await async_client.get(
        WALLET_PATH + "/create-pub-did",
        headers={"x-api-key": "adminApiKey", **WALLET_HEADERS},
    )
    assert response.status_code == 200
    response = response.json()
    assert response["did_object"] and response["did_object"] != {}
    assert response["issuer_verkey"] and response["issuer_verkey"] != {}
    assert response["issuer_endpoint"] and response["issuer_endpoint"] != {}
    assert response["did_object"]["posture"] == "public"


@pytest.mark.asyncio
async def test_get_subwallet_auth_token(
    async_client, member_admin_agent_mock, create_wallet
):
    wallet_id = create_wallet["wallet_id"]

    response = await async_client.get(
        f"{WALLET_PATH}/{wallet_id}/auth-token",
        headers={
            "x-api-key": "adminApiKey",
            **WALLET_HEADERS,
        },
    )

    response = response.json()
    assert response["token"] and type(response["token"]) == str
    assert response["token"] != ""

    res_method = await get_subwallet_auth_token(
        wallet_id, aries_controller=member_admin_agent_mock
    )
    assert res_method == response


@pytest.mark.asyncio
async def test_get_subwallet(async_client, member_admin_agent_mock, create_wallet):

    wallet_id = create_wallet["wallet_id"]
    response = await async_client.get(
        f"{WALLET_PATH}/{wallet_id}",
        headers={"x-api-key": "adminApiKey"},
    )
    response = response.json()
    assert response["wallet_id"]
    assert response["key_management_mode"]
    assert response["settings"]
    res_method = await get_subwallet(
        aries_controller=member_admin_agent_mock, wallet_id=wallet_id
    )
    assert res_method == response


@pytest.mark.asyncio
async def test_update_wallet(async_client, member_admin_agent_mock, create_wallet):
    wallet_id = create_wallet["wallet_id"]
    payload = {"image_url": "update"}
    update_response = await async_client.post(
        f"{WALLET_PATH}/{wallet_id}",
        headers={"x-api-key": "adminApiKey", **WALLET_HEADERS},
        data=json.dumps({"image_url": "update"}),
    )
    update_response = update_response.json()
    assert update_response["settings"]["image_url"] == "update"

    res_method = await update_subwallet(
        aries_controller=member_admin_agent_mock, payload=payload, wallet_id=wallet_id
    )
    assert res_method["settings"] == update_response["settings"]


@pytest.mark.asyncio
async def test_query_subwallet(async_client, member_admin_agent_mock):
    query_response = await async_client.get(
        f"{WALLET_PATH}/query-subwallet",
        headers={"x-api-key": "adminApiKey"},
    )
    query_response = query_response.json()

    res_method = await query_subwallet(aries_controller=member_admin_agent_mock)
    assert res_method == query_response


@pytest.mark.asyncio
async def test_create_wallet(async_client, create_wallet):
    wallet_response = create_wallet
    assert wallet_response["settings"] and wallet_response["settings"] != {}
    wallet_id = wallet_response["wallet_id"]
    response = await async_client.get(
        f"{WALLET_PATH}/{wallet_id}",
        headers={"x-api-key": "adminApiKey"},
    )
    response = response.json()
    assert wallet_response["settings"] == response["settings"]


@pytest.mark.asyncio
async def test_remove_by_id(async_client, member_admin_agent_mock):
    wallet_id = (await create_wallet(async_client))["wallet_id"]

    response = await async_client.delete(
        f"{WALLET_PATH}/{wallet_id}",
        headers={"x-api-key": "adminApiKey"},
    )
    assert response.status_code == 200
    assert response.json() == "Successfully removed wallet"

    with pytest.raises(ClientResponseError) as e:
        wallet = await get_subwallet(
            aries_controller=member_admin_agent_mock, wallet_id=wallet_id
        )
    assert e.value.status == 404
