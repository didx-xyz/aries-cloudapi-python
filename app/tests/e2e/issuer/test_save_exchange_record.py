import asyncio
import json
import time

import pytest
from fastapi import HTTPException

from app.models.tenants import CreateTenantResponse
from app.routes.issuer import router
from app.services.event_handling.sse_listener import SseListener
from app.tests.util.ecosystem_connections import FaberAliceConnect
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange

CREDENTIALS_BASE_PATH = router.prefix


@pytest.mark.anyio
@pytest.mark.parametrize("save_exchange_record", [False, True])
@pytest.mark.parametrize("protocol_version", ["v1", "v2"])
async def test_issue_credential_with_save_exchange_record(
    faber_client: RichAsyncClient,
    credential_definition_id: str,
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


@pytest.mark.anyio
async def test_get_cred_exchange_records(
    faber_client: RichAsyncClient,
    credential_definition_id: str,  # pylint: disable=redefined-outer-name
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
):
    credential_v1 = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "10"},
        },
        "save_exchange_record": True,
    }

    await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential_v1,
    )

    credential_v2 = {
        "protocol_version": "v2",
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "20"},
        },
        "save_exchange_record": True,
    }

    await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential_v2,
    )

    num_tries = 0
    num_credentials_returned = 0
    while num_credentials_returned != 2 and num_tries < 10:
        await asyncio.sleep(0.25)
        alice_cred_ex_response = (
            await alice_member_client.get(
                CREDENTIALS_BASE_PATH + "?state=offer-received"
            )
        ).json()
        num_credentials_returned = len(alice_cred_ex_response)
        num_tries += 1

    if num_credentials_returned != 2:
        raise Exception(
            f"Expected 2 credentials to be issued; only got {num_credentials_returned}"
        )

    for cred in alice_cred_ex_response:
        await alice_member_client.post(
            f"{CREDENTIALS_BASE_PATH}/{cred['credential_id']}/request", json={}
        )
        # add sse listener to wait for credential state "done" for each credential
        listener = SseListener(topic="credentials", wallet_id=alice_tenant.wallet_id)
        await listener.wait_for_event(
            field="credential_id", field_id=cred["credential_id"], desired_state="done"
        )

    response = await faber_client.get(CREDENTIALS_BASE_PATH)

    faber_records = response.json()
    faber_cred_ex_response = await faber_client.get(
        CREDENTIALS_BASE_PATH + "?state=done"
    )
    assert len(faber_cred_ex_response.json()) == 2

    faber_cred_ex_response = await faber_client.get(
        CREDENTIALS_BASE_PATH + "?role=issuer"
    )
    assert len(faber_cred_ex_response.json()) == 2

    faber_cred_ex_response = await faber_client.get(
        f"{CREDENTIALS_BASE_PATH}?thread_id={faber_records[0]['thread_id']}"
    )
    assert len(faber_cred_ex_response.json()) == 1

    with pytest.raises(HTTPException) as exc:
        faber_cred_ex_response = await faber_client.get(
            f"{CREDENTIALS_BASE_PATH}?connection_id=123&thread_id=123&role=asf&state=asd"
        )
    assert exc.value.status_code == 422
    assert len(json.loads(exc.value.detail)["detail"]) == 4
