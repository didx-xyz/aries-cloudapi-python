from typing import Any
from aries_cloudcontroller import AcaPyClient
from httpx import AsyncClient
import pytest

import app.facades.acapy_wallet as wallet_facade
import app.facades.ledger as ledger_facade
from app.generic.wallet.wallets import (
    fetch_current_did,
    list_dids,
    set_did_endpoint,
    router,
)

from assertpy import assert_that

# This import are important for tests to run!
from app.tests.util.client_fixtures import yoma_client, yoma_acapy_client
from app.tests.util.event_loop import event_loop

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
WALLET_BASE_PATH = router.prefix


@pytest.fixture()
async def create_did_mock(yoma_client: AsyncClient):
    did_response = await yoma_client.get(
        f"{WALLET_BASE_PATH}/create-local-did",
        headers={"x-api-key": "yoma.adminApiKey"},
    )
    did_response = did_response.json()
    did = did_response["result"]["did"]
    return did


@pytest.mark.asyncio
async def test_list_dids(yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient):
    response = await yoma_client.get(f"{WALLET_BASE_PATH}/list-dids")

    assert response.status_code == 200
    response = response.json()

    res_method = await list_dids(aries_controller=yoma_acapy_client)
    assert res_method == response


@pytest.mark.asyncio
async def test_create_local_did(yoma_client: AsyncClient):
    response = await yoma_client.get(f"{WALLET_BASE_PATH}/create-local-did")

    assert_that(response.status_code).is_equal_to(200)
    response = response.json()

    assert_that(response["result"]).contains("did", "verkey")


@pytest.mark.asyncio
async def test_fetch_current_did(
    yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient
):
    response = await yoma_client.get(f"{WALLET_BASE_PATH}/fetch-current-did")

    assert_that(response.status_code).is_equal_to(200)
    response = response.json()

    assert_that(response["result"]).contains("did", "verkey")

    res_method = await fetch_current_did(aries_controller=yoma_acapy_client)
    assert res_method == response


@pytest.mark.asyncio
async def test_get_did_endpoint(yoma_client: AsyncClient, create_did_mock: Any):

    did = create_did_mock
    response = await yoma_client.get(f"{WALLET_BASE_PATH}/get-did-endpoint/{did}")
    assert_that(response.status_code).is_equal_to(200)

    response = response.json()
    assert response["did"] == did


@pytest.mark.asyncio
async def test_assign_pub_did(yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient):
    did_object = await wallet_facade.create_did(yoma_acapy_client)
    await ledger_facade.post_to_ledger(did_object=did_object)

    did = did_object.did
    response = await yoma_client.get(f"{WALLET_BASE_PATH}/assign-pub-did?did={did}")

    assert_that(response.status_code).is_equal_to(200)
    response = response.json()

    assert_that(response["result"]).contains("did", "verkey")
    assert_that(response["result"]).has_did(did)


@pytest.mark.asyncio
async def test_set_did_endpoint(
    yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient
):
    response = await yoma_client.get(f"{WALLET_BASE_PATH}/create-pub-did")
    assert_that(response.status_code).is_equal_to(200)
    response = response.json()

    endpoint = response["issuer_endpoint"]
    did = response["did_object"]["did"]
    endpoint_type = "Endpoint"

    res_method = await set_did_endpoint(
        did, endpoint, endpoint_type, aries_controller=yoma_acapy_client
    )
    assert res_method == {}


@pytest.mark.asyncio
async def test_create_pub_did(yoma_client: AsyncClient):
    response = await yoma_client.get(f"{WALLET_BASE_PATH}/create-pub-did")

    assert_that(response.status_code).is_equal_to(200)
    response = response.json()

    assert_that(response).contains(
        "did_object", "issuer_verkey", "issuer_endpoint", "did_object"
    )
