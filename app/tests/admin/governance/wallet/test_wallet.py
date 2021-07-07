import pytest
import json
from admin.governance.multitenant_wallet.wallet import (
    create_pub_did,
    create_wallet,
    remove_wallet_by_id,
    get_subwallet_auth_token,
    update_subwallet,
    get_subwallet,
    query_subwallet,
)

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
BASE_PATH = "/admin/governance/wallet"


@pytest.fixture(name="create_wallet_mock")
async def fixture_create_wallet_mock(async_client):

    wallet_response = await async_client.post(
        "/wallets/create-wallet",
        headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
        data=json.dumps(
            {
                "image_url": "https://aries.ca/images/sample.png",
                "key_management_mode": "managed",
                "label": "YOMA",
                "wallet_dispatch_type": "default",
                "wallet_key": "MySecretKey1234",
                "wallet_name": "YOMAWallet420",
                "wallet_type": "indy",
            }
        ),
    )
    wallet_response = wallet_response.json()
    wallet_id = wallet_response["wallet_id"]
    yield wallet_response
    remove_response = await async_client.get(
        f"/wallets/remove-wallet/{wallet_id}",
        headers={"x-api-key": "adminApiKey"},
    )
    assert remove_response.status_code == 200
    assert remove_response.json() == "Successfully removed wallet"


@pytest.mark.asyncio
async def test_create_pub_did(async_client, yoma_agent_mock):
    response = await async_client.get(
        "/wallets/create-pub-did",
        headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
    )

    assert response.status_code == 200
    response = response.json()
    # assert response == ''
    assert response["did_object"] and response["did_object"] != {}
    assert response["issuer_verkey"] and response["issuer_verkey"] != {}
    assert response["issuer_endpoint"] and response["issuer_endpoint"] != {}

    assert response["did_object"]["posture"] == "public"


@pytest.mark.asyncio
async def test_get_subwallet_auth_token(
    async_client, member_admin_agent_mock, create_wallet_mock
):

    wallet_response = create_wallet_mock

    wallet_id = wallet_response["wallet_id"]

    response = await async_client.get(
        f"/wallets/get-subwallet-auth-token/{wallet_id}",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
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
async def test_get_subwallet(async_client, member_admin_agent_mock, create_wallet_mock):
    wallet_response = create_wallet_mock

    wallet_id = wallet_response["wallet_id"]
    response = await async_client.get(
        f"/wallets/{wallet_id}",
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
async def test_update_wallet(async_client, member_admin_agent_mock, create_wallet_mock):

    wallet_response = create_wallet_mock
    wallet_id = wallet_response["wallet_id"]
    payload = {"image_url": "update"}
    update_response = await async_client.post(
        f"/wallets/update-subwallet/{wallet_id}",
        headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
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
        f"/wallets/query-subwallet",
        headers={"x-api-key": "adminApiKey"},
    )
    query_response = query_response.json()

    res_method = await query_subwallet(aries_controller=member_admin_agent_mock)
    assert res_method == query_response


@pytest.mark.asyncio
async def test_create_wallet(async_client):

    wallet_response = await async_client.post(
        "/wallets/create-wallet",
        headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
        data=json.dumps(
            {
                "image_url": "https://aries.ca/images/sample.png",
                "key_management_mode": "managed",
                "label": "YOMA",
                "wallet_dispatch_type": "default",
                "wallet_key": "MySecretKey1234",
                "wallet_name": "YOMAWallet413",
                "wallet_type": "indy",
            }
        ),
    )
    wallet_response = wallet_response.json()
    assert wallet_response["settings"] and wallet_response["settings"] != {}
    wallet_id = wallet_response["wallet_id"]
    response = await async_client.get(
        f"/wallets/{wallet_id}",
        headers={"x-api-key": "adminApiKey"},
    )
    response = response.json()
    assert wallet_response["settings"] == response["settings"]

    remove_response = await async_client.get(
        f"/wallets/remove-wallet/{wallet_id}",
        headers={"x-api-key": "adminApiKey"},
    )


@pytest.mark.asyncio
async def test_remove_by_id(async_client):

    wallet_response = await async_client.post(
        "/wallets/create-wallet",
        headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
        data=json.dumps(
            {
                "image_url": "https://aries.ca/images/sample.png",
                "key_management_mode": "managed",
                "label": "YOMA",
                "wallet_dispatch_type": "default",
                "wallet_key": "MySecretKey1234",
                "wallet_name": "YOMAWallet420",
                "wallet_type": "indy",
            }
        ),
    )
    wallet_response = wallet_response.json()
    wallet_id = wallet_response["wallet_id"]

    response = await async_client.get(
        f"/wallets/remove-wallet/{wallet_id}",
        headers={"x-api-key": "adminApiKey"},
    )
    assert response.status_code == 200
    assert response.json() == "Successfully removed wallet"
