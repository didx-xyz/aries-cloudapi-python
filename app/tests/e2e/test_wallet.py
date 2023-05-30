from typing import Any
from aries_cloudcontroller import AcaPyClient
import pytest

import app.facades.acapy_wallet as wallet_facade
from app.generic.wallet.models import SetDidEndpointRequest
from app.tests.util.ledger import create_public_did, post_to_ledger
from app.generic.wallet.wallet import (
    get_public_did,
    list_dids,
    set_did_endpoint,
    get_did_endpoint,
    router,
)
from app.util.rich_async_client import RichAsyncClient

from assertpy import assert_that

WALLET_BASE_PATH = router.prefix


async def create_did_mock(governance_client: RichAsyncClient):
    did_response = await governance_client.post(WALLET_BASE_PATH)
    did_response = did_response.json()
    did = did_response["did"]
    return did


@pytest.mark.anyio
async def test_list_dids(
    governance_client: RichAsyncClient, governance_acapy_client: AcaPyClient
):
    response = await governance_client.get(WALLET_BASE_PATH)

    assert response.status_code == 200
    response = response.json()

    res_method = await list_dids(aries_controller=governance_acapy_client)
    assert res_method == response


@pytest.mark.anyio
async def test_create_local_did(governance_client: RichAsyncClient):
    response = await governance_client.post(WALLET_BASE_PATH)

    assert_that(response.status_code).is_equal_to(200)
    response = response.json()

    assert_that(response).contains("did", "verkey")


@pytest.mark.anyio
async def test_get_public_did(
    governance_client: RichAsyncClient, governance_acapy_client: AcaPyClient
):
    response = await governance_client.get(f"{WALLET_BASE_PATH}/public")

    assert_that(response.status_code).is_equal_to(200)
    response = response.json()

    assert_that(response).contains("did", "verkey")

    res_method = await get_public_did(aries_controller=governance_acapy_client)
    assert res_method == response


@pytest.mark.anyio
async def test_get_did_endpoint(governance_client: RichAsyncClient):
    did = await create_did_mock(governance_client)
    response = await governance_client.get(f"{WALLET_BASE_PATH}/{did}/endpoint")
    assert_that(response.status_code).is_equal_to(200)

    response = response.json()
    assert response["did"] == did


@pytest.mark.anyio
async def test_set_public_did(
    governance_client: RichAsyncClient, governance_acapy_client: AcaPyClient
):
    did_object = await wallet_facade.create_did(governance_acapy_client)
    await post_to_ledger(did=did_object.did, verkey=did_object.verkey)

    did = did_object.did
    response = await governance_client.put(f"{WALLET_BASE_PATH}/public?did={did}")

    assert_that(response.status_code).is_equal_to(200)

    # With endorsement the set pub dic returns None but sets the did correctly
    # So let's get it a different way and check that it is correct
    response = await governance_client.get(f"{WALLET_BASE_PATH}/public")
    assert_that(response.status_code).is_equal_to(200)
    response = response.json()

    assert_that(response).contains("did", "verkey")
    assert_that(response).has_did(did)


@pytest.mark.anyio
async def test_set_did_endpoint(governance_acapy_client: AcaPyClient):
    # Don't want us overwriting the real endpoint, so not setting as public did
    did = await create_public_did(governance_acapy_client, set_public=False)
    endpoint = "https://ssi.com"

    await set_did_endpoint(
        did.did,
        SetDidEndpointRequest(endpoint=endpoint),
        aries_controller=governance_acapy_client,
    )

    retrieved_endpoint = await get_did_endpoint(
        did.did, aries_controller=governance_acapy_client
    )

    assert_that(endpoint).is_equal_to(retrieved_endpoint.endpoint)
