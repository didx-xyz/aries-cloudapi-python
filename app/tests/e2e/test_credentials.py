import asyncio
import time

import pytest

from app.event_handling.sse_listener import SseListener
from app.models.tenants import CreateTenantResponse
from app.routes.issuer import router
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange

CREDENTIALS_BASE_PATH = router.prefix


@pytest.fixture(scope="function")
async def credential_exchange_id(
    faber_client: RichAsyncClient,
    credential_definition_id: str,  # pylint: disable=redefined-outer-name
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
):
    credential = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "average"},
        },
    }

    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    cred_ex_id = credential_exchange["credential_id"]
    assert credential_exchange["protocol_version"] == "v1"

    assert await check_webhook_state(
        client=faber_client,
        topic="credentials",
        filter_map={
            "state": "offer-sent",
            "credential_id": cred_ex_id,
        },
    )

    await asyncio.sleep(0.2)  # credential may take moment to reflect after webhook
    response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH,
        params={"connection_id": faber_and_alice_connection.alice_connection_id},
    )
    records = response.json()
    assert len(records) > 0

    return cred_ex_id


@pytest.mark.anyio
@pytest.mark.parametrize("save_exchange_record", [False, True])
@pytest.mark.parametrize("protocol_version", ["v1", "v2"])
async def test_issue_credential_with_save_exchange_record(
    faber_client: RichAsyncClient,
    credential_definition_id: str,  # pylint: disable=redefined-outer-name
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
    save_exchange_record: bool,
    protocol_version: str,
) -> CredentialExchange:
    credential = {
        "protocol_version": protocol_version,
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "10"},
        },
        "save_exchange_record": save_exchange_record,
    }

    alice_credentials_listener = SseListener(
        topic="credentials", wallet_id=alice_tenant.wallet_id
    )

    # create and send credential offer- issuer
    await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )

    payload = await alice_credentials_listener.wait_for_event(
        field="connection_id",
        field_id=faber_and_alice_connection.alice_connection_id,
        desired_state="offer-received",
    )

    alice_credential_id = payload["credential_id"]

    # send credential request - holder
    await alice_member_client.post(
        f"{CREDENTIALS_BASE_PATH}/{alice_credential_id}/request",
    )

    await alice_credentials_listener.wait_for_event(
        field="credential_id", field_id=alice_credential_id, desired_state="done"
    )

    time.sleep(0.5)  # short sleep before fetching cred ex records; allow them to update

    # get exchange records from alice side -- should be empty regardless
    alice_cred_ex_recs = (
        await alice_member_client.get(f"{CREDENTIALS_BASE_PATH}")
    ).json()

    # faber requesting auto_remove only removes their cred ex recs
    # Alice cred ex recs should be empty regardless
    assert len(alice_cred_ex_recs) == 0

    # get exchange records from faber side:
    faber_cred_ex_recs = (await faber_client.get(f"{CREDENTIALS_BASE_PATH}")).json()

    if save_exchange_record:
        assert len(faber_cred_ex_recs) == 1  # Save record is True, should be 1 record
        cred_ex_id = faber_cred_ex_recs[0]["credential_id"]
        await faber_client.delete(f"{CREDENTIALS_BASE_PATH}/{cred_ex_id}")  # Clean up
    else:
        assert len(faber_cred_ex_recs) == 0  # default is to remove records
