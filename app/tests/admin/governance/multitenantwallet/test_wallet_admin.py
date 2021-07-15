from typing import Dict, Union

import json

import pytest
from aiohttp import ClientResponseError
from assertpy import assert_that

from admin.governance.multitenant_wallet.wallet_admin import (
    get_subwallet_auth_token,
    UpdateWalletRequest,
    get_subwallet,
    query_subwallet,
)
from tests.utils_test import get_random_string

WALLET_HEADERS = {
    "content-type": "application/json",
    "x-role": "member",
    "x-api-key": "adminApiKey",
}
WALLET_PATH = "/admin/wallet-multitenant"
CREATE_WALLET_PAYLOAD = {
    "image_url": "https://aries.ca/images/sample.png",
    "label": "YOMA",
    "wallet_key": "MySecretKey1234",
    "wallet_name": "DarthVadersHolidayFunds",
}


@pytest.fixture(name="create_wallet")
async def fixture_create_wallet(async_client, member_admin_agent_mock):
    wallet_response = await write_wallet(async_client)
    wallet_id = wallet_response["wallet_id"]
    yield wallet_response
    response = await async_client.delete(
        f"{WALLET_PATH}/{wallet_id}",
        headers=WALLET_HEADERS,
    )
    assert response.status_code == 200
    assert response.json() == {"status": "Successfully removed wallet"}

    wallets = await query_subwallet(
        wallet_name=None, aries_controller=member_admin_agent_mock
    )
    for w in wallets["results"]:
        await async_client.delete(
            f"{WALLET_PATH}/{w['wallet_id']}",
            headers=WALLET_HEADERS,
        )


async def write_wallet(async_client, wallet_name=None):
    wallet_payload = CREATE_WALLET_PAYLOAD.copy()
    wallet_payload["wallet_name"] = wallet_name or "wallet" + get_random_string(4)
    wallet_payload["label"] = "label" + get_random_string(4)
    wallet_response = await async_client.post(
        WALLET_PATH + "/create-wallet",
        headers=WALLET_HEADERS,
        data=json.dumps(wallet_payload),
    )
    wallet_response = wallet_response.json()
    return wallet_response


@pytest.mark.asyncio
async def test_get_subwallet_auth_token(
    async_client, member_admin_agent_mock, create_wallet
):
    wallet_id = create_wallet["wallet_id"]

    response = await async_client.get(
        f"{WALLET_PATH}/{wallet_id}/auth-token", headers=WALLET_HEADERS
    )

    response = response.json()
    assert response["token"] and type(response["token"]) == str
    assert response["token"] != ""

    res_method = await get_subwallet_auth_token(
        wallet_id, aries_controller=member_admin_agent_mock
    )
    assert res_method == response


@pytest.mark.asyncio
async def test_get_subwallet(async_client, create_wallet):
    wallet_id = create_wallet["wallet_id"]
    response = await async_client.get(
        f"{WALLET_PATH}/{wallet_id}",
        headers={"x-api-key": "adminApiKey"},
    )
    response = response.json()
    create_wallet.pop("token")
    assert response == create_wallet


@pytest.mark.asyncio
async def test_update_wallet(async_client, create_wallet, member_admin_agent_mock):
    wallet_id = create_wallet["wallet_id"]
    assert create_wallet["settings"]["image_url"] != "update"
    request = UpdateWalletRequest(image_url="update")
    await async_client.post(
        f"{WALLET_PATH}/{wallet_id}",
        headers=WALLET_HEADERS,
        data=request.json(),
    )

    res_method = await get_subwallet(
        wallet_id=wallet_id, aries_controller=member_admin_agent_mock
    )
    assert_that(res_method["settings"]["image_url"]).is_equal_to("update")


@pytest.mark.asyncio
async def test_query_subwallet(async_client, member_admin_agent_mock, create_wallet):
    query_response = await async_client.get(
        f"{WALLET_PATH}/query-subwallet",
        headers=WALLET_HEADERS,
    )
    query_response = query_response.json()
    res_method = await query_subwallet(aries_controller=member_admin_agent_mock)
    assert len(res_method["results"]) == len(query_response["results"])


# @pytest.mark.skip(reason="until wallet_name is honoured by cloudcontroller")
@pytest.mark.asyncio
async def test_query_subwallet_with_name(async_client, create_wallet):
    wallet_1 = await write_wallet(async_client)
    wallet_2 = await write_wallet(async_client)
    wallet_3 = await write_wallet(async_client)

    async def validate_wallet(wallet: Union[Dict, None]):
        if not wallet:
            params = {}
        else:
            params = {"wallet_name": wallet["settings"]["wallet.name"]}
        wallets = await async_client.get(
            f"{WALLET_PATH}/query-subwallet", headers=WALLET_HEADERS, params=params
        )
        results = wallets.json()["results"]
        if wallet:
            assert len(results) == 1
            assert results[0]["wallet_id"] == wallet["wallet_id"]
        else:
            assert_that(results).extracting("wallet_id").contains(
                wallet_1["wallet_id"],
                wallet_2["wallet_id"],
                wallet_3["wallet_id"],
                create_wallet["wallet_id"],
            )

    await validate_wallet(wallet_1)
    await validate_wallet(wallet_2)
    await validate_wallet(wallet_3)
    await validate_wallet(None)


@pytest.mark.asyncio
async def test_create_wallet(async_client, create_wallet):
    wallet_response = create_wallet
    assert wallet_response["settings"] and wallet_response["settings"] != {}
    wallet_id = wallet_response["wallet_id"]
    response = await async_client.get(
        f"{WALLET_PATH}/{wallet_id}",
        headers=WALLET_HEADERS,
    )
    response = response.json()
    assert wallet_response["settings"] == response["settings"]


@pytest.mark.asyncio
async def test_remove_by_id(async_client, member_admin_agent_mock):
    wallet_id = (await write_wallet(async_client))["wallet_id"]

    response = await async_client.delete(
        f"{WALLET_PATH}/{wallet_id}",
        headers=WALLET_HEADERS,
    )
    assert response.status_code == 200
    assert response.json() == {"status": "Successfully removed wallet"}

    with pytest.raises(ClientResponseError) as e:
        await get_subwallet(
            aries_controller=member_admin_agent_mock, wallet_id=wallet_id
        )
    assert e.value.status == 404
