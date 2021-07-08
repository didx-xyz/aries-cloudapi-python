import pytest
import json
from contextlib import asynccontextmanager
from aiohttp import ClientResponseError

from admin.governance.multitenant_wallet.wallet import query_subwallet
from generic.connections import (
    create_invite,
    accept_invite,
    get_connections,
    get_connection_by_id,
    delete_connection_by_id,
)

import dependencies

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
BASE_PATH = "/generic/connections"
CREATE_WALLET_PAYLOAD_YODA = {
    "image_url": "https://aries.ca/images/sample.png",
    "key_management_mode": "managed",
    "label": "YOMA",
    "wallet_dispatch_type": "default",
    "wallet_key": "MySecretKey1234",
    "wallet_name": "YodaJediPokerFunds",
    "wallet_type": "indy",
}
CREATE_WALLET_PAYLOAD_HAN = {
    "image_url": "https://aries.ca/images/sample.png",
    "key_management_mode": "managed",
    "label": "YOMA",
    "wallet_dispatch_type": "default",
    "wallet_key": "MySecretKey1234",
    "wallet_name": "HanSolosCocktailFunds",
    "wallet_type": "indy",
}


async def remove_wallets(yoda_wallet_id, han_wallet_id, async_client):
    yoda_response = await async_client.delete(
        f"/wallets/{yoda_wallet_id}",
        headers={"x-api-key": "adminApiKey"},
    )
    han_response = await async_client.delete(
        f"/wallets/{han_wallet_id}",
        headers={"x-api-key": "adminApiKey"},
    )
    return yoda_response, han_response


@pytest.fixture(name="create_wallets_mock")
async def fixture_create_wallets_mock(async_client, member_admin_agent_mock):
    # Create two wallets
    yoda_wallet_id = ""
    han_wallet_id = ""
    try:
        yoda_wallet_response = await async_client.post(
            "/wallets/create-wallet",
            headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
            data=json.dumps(CREATE_WALLET_PAYLOAD_YODA),
        )
        yoda_wallet_response = yoda_wallet_response.json()
        yoda_wallet_id = yoda_wallet_response["wallet_id"]
        han_wallet_response = await async_client.post(
            "/wallets/create-wallet",
            headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
            data=json.dumps(CREATE_WALLET_PAYLOAD_HAN),
        )
        han_wallet_response = han_wallet_response.json()
        han_wallet_id = han_wallet_response["wallet_id"]
        yield yoda_wallet_response, han_wallet_response
    except ClientResponseError:
        yoda_wallet_response = await query_subwallet(
            wallet_name="YodaJediPokerFunds", aries_controller=member_admin_agent_mock
        )
        han_wallet_response = await query_subwallet(
            wallet_name="HanSolosCocktailFunds",
            aries_controller=member_admin_agent_mock,
        )
        yoda_wallet_id = yoda_wallet_response["wallet_id"]
        han_wallet_id = han_wallet_response["wallet_id"]
        yield yoda_wallet_response, han_wallet_response
    finally:
        yoda_response, han_response = await remove_wallets(
            yoda_wallet_id, han_wallet_id, async_client
        )
        assert yoda_response.status_code == 200
        assert yoda_response.json() == "Successfully removed wallet"
        assert han_response.status_code == 200
        assert han_response.json() == "Successfully removed wallet"


@pytest.mark.asyncio
async def test_create_invite(async_client, create_wallets_mock):
    yoda, han = create_wallets_mock

    yoda_wallet_id = yoda["wallet_id"]
    han_wallet_id = han["wallet_id"]

    yoda_token_response = await async_client.get(
        f"/wallets/{yoda_wallet_id}/auth-token",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    yoda_token_response = yoda_token_response.json()
    yoda_token = yoda_token_response["token"]

    async with asynccontextmanager(dependencies.member_agent)(
        authorization=f"Bearer {yoda_token}", x_wallet_id=yoda_wallet_id
    ) as member_agent:
        invite_creation_response = await create_invite(member_agent)
    assert (
        invite_creation_response["connection_id"]
        and invite_creation_response["connection_id"] != {}
    )
    assert (
        invite_creation_response["invitation"]
        and invite_creation_response["invitation"] != {}
    )
    assert (
        invite_creation_response["invitation"]["@id"]
        and invite_creation_response["invitation"]["@id"] != {}
    )


@pytest.mark.asyncio
async def test_accept_invite(async_client, create_wallets_mock):
    yoda, han = create_wallets_mock

    yoda_wallet_id = yoda["wallet_id"]
    han_wallet_id = han["wallet_id"]

    yoda_token_response = await async_client.get(
        f"/wallets/{yoda_wallet_id}/auth-token",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    han_token_response = await async_client.get(
        f"/wallets/{han_wallet_id}/auth-token",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    yoda_token_response = yoda_token_response.json()
    yoda_token = yoda_token_response["token"]
    han_token_response = han_token_response.json()
    han_token = han_token_response["token"]

    invite_creation_response = await async_client.get(
        f"/generic/connections/create-invite",
        headers={
            "authorization": f"Bearer {yoda_token}",
            "x-wallet-id": yoda_wallet_id,
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    invite_creation_response = invite_creation_response.json()
    invite = invite_creation_response["invitation"]

    async with asynccontextmanager(dependencies.member_agent)(
        authorization=f"Bearer {han_token}", x_wallet_id=han_wallet_id
    ) as member_agent:
        accept_invite_response = await accept_invite(
            invite=invite, aries_controller=member_agent
        )

    assert (
        accept_invite_response["accept"] and accept_invite_response["accept"] == "auto"
    )
    assert (
        accept_invite_response["created_at"]
        and accept_invite_response["created_at"] != ""
    )
    assert (
        accept_invite_response["invitation_key"]
        and accept_invite_response["invitation_key"] != ""
    )


@pytest.mark.asyncio
async def test_get_connections(async_client, create_wallets_mock):
    yoda, han = create_wallets_mock

    yoda_wallet_id = yoda["wallet_id"]
    han_wallet_id = han["wallet_id"]

    yoda_token_response = await async_client.get(
        f"/wallets/{yoda_wallet_id}/auth-token",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    han_token_response = await async_client.get(
        f"/wallets/{han_wallet_id}/auth-token",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    yoda_token_response = yoda_token_response.json()
    yoda_token = yoda_token_response["token"]
    han_token_response = han_token_response.json()
    han_token = han_token_response["token"]

    invite_creation_response = await async_client.get(
        f"/generic/connections/create-invite",
        headers={
            "authorization": f"Bearer {yoda_token}",
            "x-wallet-id": yoda_wallet_id,
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    invite_creation_response = invite_creation_response.json()
    invite = invite_creation_response["invitation"]

    async with asynccontextmanager(dependencies.member_agent)(
        authorization=f"Bearer {han_token}", x_wallet_id=han_wallet_id
    ) as member_agent:
        await accept_invite(invite=invite, aries_controller=member_agent)
        connection = await get_connections(aries_controller=member_agent)

    assert connection["results"] and len(connection["results"]) >= 1
    assert (
        connection["results"][0]["accept"]
        and connection["results"][0]["accept"] == "auto"
    )
    assert (
        connection["results"][0]["connection_id"]
        and connection["results"][0]["connection_id"] != ""
    )
    assert (
        connection["results"][0]["created_at"]
        and connection["results"][0]["created_at"] != ""
    )
    assert (
        connection["results"][0]["invitation_key"]
        and connection["results"][0]["invitation_key"] != ""
    )


@pytest.mark.asyncio
async def test_get_connection_by_id(async_client, create_wallets_mock):
    yoda, han = create_wallets_mock

    yoda_wallet_id = yoda["wallet_id"]
    han_wallet_id = han["wallet_id"]

    yoda_token_response = await async_client.get(
        f"/wallets/{yoda_wallet_id}/auth-token",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    han_token_response = await async_client.get(
        f"/wallets/{han_wallet_id}/auth-token",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    yoda_token_response = yoda_token_response.json()
    yoda_token = yoda_token_response["token"]
    han_token_response = han_token_response.json()
    han_token = han_token_response["token"]

    invite_creation_response = await async_client.get(
        f"/generic/connections/create-invite",
        headers={
            "authorization": f"Bearer {yoda_token}",
            "x-wallet-id": yoda_wallet_id,
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    invite_creation_response = invite_creation_response.json()
    invite = invite_creation_response["invitation"]

    async with asynccontextmanager(dependencies.member_agent)(
        authorization=f"Bearer {han_token}", x_wallet_id=han_wallet_id
    ) as member_agent:
        await accept_invite(invite=invite, aries_controller=member_agent)
        connection = await get_connections(aries_controller=member_agent)
        connection_id = connection["results"][0]["connection_id"]
        connection_from_method = await get_connection_by_id(
            connection_id=connection_id, aries_controller=member_agent
        )

    assert connection["results"][0] == connection_from_method


@pytest.mark.asyncio
async def test_delete_connection(async_client, create_wallets_mock):
    yoda, han = create_wallets_mock

    yoda_wallet_id = yoda["wallet_id"]
    han_wallet_id = han["wallet_id"]

    yoda_token_response = await async_client.get(
        f"/wallets/{yoda_wallet_id}/auth-token",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    han_token_response = await async_client.get(
        f"/wallets/{han_wallet_id}/auth-token",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    yoda_token_response = yoda_token_response.json()
    yoda_token = yoda_token_response["token"]
    han_token_response = han_token_response.json()
    han_token = han_token_response["token"]

    invite_creation_response = await async_client.get(
        f"/generic/connections/create-invite",
        headers={
            "authorization": f"Bearer {yoda_token}",
            "x-wallet-id": yoda_wallet_id,
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    invite_creation_response = invite_creation_response.json()
    invite = invite_creation_response["invitation"]

    async with asynccontextmanager(dependencies.member_agent)(
        authorization=f"Bearer {han_token}", x_wallet_id=han_wallet_id
    ) as member_agent:
        await accept_invite(invite=invite, aries_controller=member_agent)
        connection = await get_connections(aries_controller=member_agent)
        connection_id = connection["results"][0]["connection_id"]
        await delete_connection_by_id(
            connection_id=connection_id, aries_controller=member_agent
        )
        connection = await get_connections(aries_controller=member_agent)

    assert connection["results"] == []
