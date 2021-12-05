from typing import Any, Dict, Optional

import pytest
from aiohttp import ClientResponseError
from aries_cloudcontroller import AcaPyClient
from assertpy import assert_that
from httpx import AsyncClient

from app.admin.governance.multitenant_wallet.wallet_admin import (
    UpdateWalletRequest,
    get_subwallet,
    get_subwallet_auth_token,
    query_subwallet,
    router,
)

# These imports are important for tests to run!
from app.tests.util.event_loop import event_loop
from app.tests.util.string import get_random_string

WALLET_PATH = router.prefix

CREATE_WALLET_PAYLOAD = {
    "image_url": "https://aries.ca/images/sample.png",
    "label": "YOMA",
    "wallet_key": "MySecretKey1234",
    "wallet_name": "DarthVadersHolidayFunds",
}


@pytest.fixture(name="create_wallet")
async def fixture_create_wallet(
    member_admin_client: AsyncClient, member_admin_acapy_client: AcaPyClient
):
    wallet_response = await write_wallet(member_admin_client)
    wallet_id = wallet_response["wallet_id"]
    yield wallet_response

    response = await member_admin_client.delete(f"{WALLET_PATH}/{wallet_id}")
    assert response.status_code == 200
    assert response.json() == {"status": "Successfully removed wallet"}

    wallets = await query_subwallet(
        wallet_name=None, aries_controller=member_admin_acapy_client
    )
    for w in wallets.results:
        await member_admin_client.delete(f"{WALLET_PATH}/{w.wallet_id}")


async def write_wallet(
    member_admin_client: AsyncClient, wallet_name: Optional[str] = None
):
    wallet_payload = {
        **CREATE_WALLET_PAYLOAD.copy(),
        "wallet_name": wallet_name or "wallet" + get_random_string(4),
        "label": "label" + get_random_string(4),
    }

    wallet_response = await member_admin_client.post(
        WALLET_PATH + "/create-wallet",
        json=wallet_payload,
    )
    wallet_response = wallet_response.json()
    return wallet_response


@pytest.mark.asyncio
async def test_get_subwallet_auth_token(
    member_admin_client: AsyncClient,
    member_admin_acapy_client: AcaPyClient,
    create_wallet,
):
    wallet_id = create_wallet["wallet_id"]

    response = await member_admin_client.get(f"{WALLET_PATH}/{wallet_id}/auth-token")

    response = response.json()
    assert response["token"] and type(response["token"]) == str
    assert response["token"] != ""

    res_method = await get_subwallet_auth_token(
        wallet_id, aries_controller=member_admin_acapy_client
    )
    assert res_method == response


@pytest.mark.asyncio
async def test_get_subwallet(member_admin_client: AsyncClient, create_wallet):
    wallet_id = create_wallet["wallet_id"]
    response = await member_admin_client.get(f"{WALLET_PATH}/{wallet_id}")
    response = response.json()
    create_wallet.pop("token")
    assert response == create_wallet


@pytest.mark.asyncio
async def test_update_wallet(
    member_admin_client: AsyncClient,
    create_wallet,
    member_admin_acapy_client: AcaPyClient,
):
    wallet_id = create_wallet["wallet_id"]
    request = UpdateWalletRequest(image_url="update")

    assert create_wallet["settings"]["image_url"] != "update"

    await member_admin_client.post(
        f"{WALLET_PATH}/{wallet_id}",
        json=request.dict(),
    )

    res_method = await get_subwallet(
        wallet_id=wallet_id, aries_controller=member_admin_acapy_client
    )
    assert_that(res_method.settings["image_url"]).is_equal_to("update")


@pytest.mark.asyncio
async def test_query_subwallet(
    member_admin_client: AsyncClient,
    member_admin_acapy_client: AcaPyClient,
    create_wallet,
):
    query_response = await member_admin_client.get(f"{WALLET_PATH}/query-subwallet")
    query_response = query_response.json()
    res_method = await query_subwallet(aries_controller=member_admin_acapy_client)

    assert len(res_method.results) == len(query_response["results"])


@pytest.mark.asyncio
async def test_query_subwallet_with_name(
    member_admin_client: AsyncClient, create_wallet
):
    wallet_1 = await write_wallet(member_admin_client)
    wallet_2 = await write_wallet(member_admin_client)
    wallet_3 = await write_wallet(member_admin_client)

    async def validate_wallet(wallet: Optional[Dict[Any, Any]]):
        params = {"wallet_name": wallet["settings"]["wallet.name"]} if wallet else {}

        wallets = await member_admin_client.get(
            f"{WALLET_PATH}/query-subwallet", params=params
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
async def test_create_wallet(member_admin_client: AsyncClient, create_wallet):
    wallet_response = create_wallet
    assert wallet_response["settings"] and wallet_response["settings"] != {}

    wallet_id = wallet_response["wallet_id"]
    response = await member_admin_client.get(f"{WALLET_PATH}/{wallet_id}")
    response = response.json()
    assert wallet_response["settings"] == response["settings"]


@pytest.mark.asyncio
async def test_remove_by_id(
    member_admin_client: AsyncClient, member_admin_acapy_client: AcaPyClient
):
    wallet_id = (await write_wallet(member_admin_client))["wallet_id"]

    response = await member_admin_client.delete(f"{WALLET_PATH}/{wallet_id}")
    assert response.status_code == 200
    assert response.json() == {"status": "Successfully removed wallet"}

    with pytest.raises(ClientResponseError) as e:
        await get_subwallet(
            aries_controller=member_admin_acapy_client, wallet_id=wallet_id
        )
    assert e.value.status == 404
