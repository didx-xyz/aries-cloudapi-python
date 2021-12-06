from typing import Any
from aries_cloudcontroller import AcaPyClient
from httpx import AsyncClient
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

from assertpy import assert_that

# This import are important for tests to run!
from app.tests.util.event_loop import event_loop

WALLET_BASE_PATH = router.prefix


@pytest.fixture()
async def create_did_mock(yoma_client: AsyncClient):
    did_response = await yoma_client.post(WALLET_BASE_PATH)
    did_response = did_response.json()
    did = did_response["did"]
    return did


@pytest.mark.asyncio
async def test_list_dids(yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient):
    response = await yoma_client.get(WALLET_BASE_PATH)

    assert response.status_code == 200
    response = response.json()

    res_method = await list_dids(aries_controller=yoma_acapy_client)
    assert res_method == response


@pytest.mark.asyncio
async def test_create_local_did(yoma_client: AsyncClient):
    response = await yoma_client.post(WALLET_BASE_PATH)

    assert_that(response.status_code).is_equal_to(200)
    response = response.json()

    assert_that(response).contains("did", "verkey")


@pytest.mark.asyncio
async def test_get_public_did(yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient):
    response = await yoma_client.get(f"{WALLET_BASE_PATH}/public")

    assert_that(response.status_code).is_equal_to(200)
    response = response.json()

    assert_that(response).contains("did", "verkey")

    res_method = await get_public_did(aries_controller=yoma_acapy_client)
    assert res_method == response


@pytest.mark.asyncio
async def test_get_did_endpoint(yoma_client: AsyncClient, create_did_mock: Any):
    did = create_did_mock
    response = await yoma_client.get(f"{WALLET_BASE_PATH}/{did}/endpoint")
    assert_that(response.status_code).is_equal_to(200)

    response = response.json()
    assert response["did"] == did


@pytest.mark.asyncio
async def test_set_public_did(yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient):
    did_object = await wallet_facade.create_did(yoma_acapy_client)
    await post_to_ledger(did=did_object.did, verkey=did_object.verkey)

    did = did_object.did
    response = await yoma_client.put(f"{WALLET_BASE_PATH}/public?did={did}")

    assert_that(response.status_code).is_equal_to(200)
    response = response.json()

    assert_that(response).contains("did", "verkey")
    assert_that(response).has_did(did)


@pytest.mark.asyncio
async def test_set_did_endpoint(
    yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient
):
    did = await create_public_did(yoma_acapy_client)
    endpoint = "https://ssi.com"

    await set_did_endpoint(
        did.did,
        SetDidEndpointRequest(endpoint=endpoint),
        aries_controller=yoma_acapy_client,
    )

    endpoint = await get_did_endpoint(did.did, aries_controller=yoma_acapy_client)
