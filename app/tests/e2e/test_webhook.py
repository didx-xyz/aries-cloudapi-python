from httpx import AsyncClient
import pytest

from app.generic.webhooks import router

from app.tests.util.member_personas import BobAliceConnect
from shared_models import Connection

WALLET_BASE_PATH = router.prefix


@pytest.mark.asyncio
async def test_get_webhooks_for_wallet_by_topic(
    alice_member_client: AsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    result = (await alice_member_client.get(WALLET_BASE_PATH + "/connections")).json()

    assert len(result) >= 1
    assert isinstance(result, list)
    assert [k in result[0].keys() for k in ["topic", "payload", "wallet_id"]]
    hook_modelled = Connection(**result[0]["payload"])
    assert isinstance(hook_modelled, Connection)


@pytest.mark.asyncio
async def test_get_webhooks_for_wallet(
    alice_member_client: AsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    result = (await alice_member_client.get(WALLET_BASE_PATH + "/")).json()

    assert len(result) >= 1
    assert isinstance(result, list)
    assert [k in result[0].keys() for k in ["topic", "payload", "wallet_id"]]
    hook_modelled = Connection(**result[0]["payload"])
    assert isinstance(hook_modelled, Connection)


@pytest.mark.asyncio
async def test_get_webhooks_for_wallet_by_topic_tenant_error(
    alice_member_client: AsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):

    alice_member_client.headers.pop("x-api-key")
    result = await alice_member_client.get(WALLET_BASE_PATH + "/connections")

    assert result.status_code == 403
    assert result.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_get_webhooks_for_wallet_by_topic_admin_error(
    yoma_client: AsyncClient,
):
    yoma_client.headers.pop("x-api-key")
    result = await yoma_client.get(WALLET_BASE_PATH + "/connections")

    assert result.status_code == 403
    assert result.json()["detail"] == "Not authenticated"
