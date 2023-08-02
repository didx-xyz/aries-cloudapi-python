import pytest
from fastapi import HTTPException

from app.routes import webhooks
from app.tests.util.ecosystem_connections import BobAliceConnect
from shared import RichAsyncClient
from shared.models.topics import Connection

BASE_PATH = webhooks.router.prefix


@pytest.mark.anyio
async def test_get_webhooks_for_wallet_by_topic(
    alice_member_client: RichAsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    result = (await alice_member_client.get(BASE_PATH + "/connections")).json()

    assert len(result) >= 1
    assert isinstance(result, list)
    assert [k in result[0].keys() for k in ["topic", "payload", "wallet_id"]]
    hook_modelled = Connection(**result[0]["payload"])
    assert isinstance(hook_modelled, Connection)


@pytest.mark.anyio
async def test_get_webhooks_for_wallet(
    alice_member_client: RichAsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    result = (await alice_member_client.get(BASE_PATH)).json()

    assert len(result) >= 1
    assert isinstance(result, list)
    assert [k in result[0].keys() for k in ["topic", "payload", "wallet_id"]]
    hook_modelled = Connection(**result[0]["payload"])
    assert isinstance(hook_modelled, Connection)


@pytest.mark.anyio
async def test_get_webhooks_for_wallet_by_topic_tenant_error(
    alice_member_client: RichAsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    alice_member_client.headers.pop("x-api-key")

    with pytest.raises(HTTPException) as exc:
        await alice_member_client.get(BASE_PATH + "/connections")

    assert exc.value.status_code == 403
    assert "Not authenticated" in exc.value.detail


@pytest.mark.anyio
async def test_get_webhooks_for_wallet_by_topic_admin_error(
    governance_client: RichAsyncClient,
):
    governance_client.headers.pop("x-api-key")

    with pytest.raises(HTTPException) as exc:
        await governance_client.get(BASE_PATH + "/connections")

    assert exc.value.status_code == 403
    assert "Not authenticated" in exc.value.detail
