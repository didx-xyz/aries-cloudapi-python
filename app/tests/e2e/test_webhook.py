import http
import time
import fastapi

from httpx import AsyncClient, HTTPError
import pytest

from app.generic.webhooks import router
from app.generic.models import ConnectionsHook

from app.tests.util.member_personas import (
    BobAliceConnect,
)

# This import are important for tests to run!
from app.tests.util.event_loop import event_loop

WALLET_BASE_PATH = router.prefix


@pytest.mark.asyncio
async def test_get_webhooks_for_wallet_by_topic_tenant(
    # bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    result = (await alice_member_client.get(WALLET_BASE_PATH + "/connections")).json()

    assert len(result) >= 1
    assert len(result) <= 100
    assert isinstance(result, list)
    assert [k in result[0].keys() for k in ["topic", "payload"]]
    hook_modelled = ConnectionsHook(**result[0]["payload"])
    assert isinstance(hook_modelled, ConnectionsHook)


@pytest.mark.asyncio
async def test_get_webhooks_for_wallet_by_topic_tenant_error(
    alice_member_client: AsyncClient,
):

    alice_member_client.headers.pop("x-api-key")
    result = await alice_member_client.get(WALLET_BASE_PATH + "/connections")

    assert result.status_code == 403
    assert result.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_get_webhooks_for_wallet_by_topic_admin(yoma_client: AsyncClient):
    result = (await yoma_client.get(WALLET_BASE_PATH + "/connections")).json()

    assert len(result) >= 1
    assert len(result) <= 100
    assert isinstance(result, list)
    assert [k in result[0].keys() for k in ["topic", "payload"]]
    hook_modelled = ConnectionsHook(**result[0]["payload"])
    assert isinstance(hook_modelled, ConnectionsHook)


@pytest.mark.asyncio
async def test_get_webhooks_for_wallet_by_topic_admin_error(yoma_client: AsyncClient):
    yoma_client.headers.pop("x-api-key")
    result = await yoma_client.get(WALLET_BASE_PATH + "/connections")

    assert result.status_code == 403
    assert result.json()["detail"] == "Not authenticated"
