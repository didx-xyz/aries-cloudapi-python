import asyncio
import json
import time

import pytest
from fastapi import HTTPException

from app.routes.issuer import router
from app.tests.util.credentials import sample_credential_attributes
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.webhooks import check_webhook_state
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
    save_exchange_record: bool,
    protocol_version: str,
) -> CredentialExchange:
    credential = {
        "protocol_version": protocol_version,
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": sample_credential_attributes,
        },
        "save_exchange_record": save_exchange_record,
    }

    # create and send credential offer- issuer
    await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )

    payload = await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        state="offer-received",
        filter_map={
            "connection_id": faber_and_alice_connection.alice_connection_id,
        },
    )

    alice_credential_id = payload["credential_id"]

    # send credential request - holder
    await alice_member_client.post(
        f"{CREDENTIALS_BASE_PATH}/{alice_credential_id}/request",
    )

    await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        state="done",
        filter_map={
            "credential_id": alice_credential_id,
        },
    )

    time.sleep(0.5)  # short sleep before fetching cred ex records; allow them to update

    # get exchange records from alice side -- should be empty regardless
    alice_cred_ex_records = (
        await alice_member_client.get(f"{CREDENTIALS_BASE_PATH}")
    ).json()

    # faber requesting auto_remove only removes their cred ex records
    # Alice cred ex records should be empty regardless
    assert len(alice_cred_ex_records) == 0

    # get exchange records from faber side:
    faber_cred_ex_records = (await faber_client.get(f"{CREDENTIALS_BASE_PATH}")).json()

    if save_exchange_record:
        assert len(faber_cred_ex_records) == 1  # Save record True, should be 1 record
        cred_ex_id = faber_cred_ex_records[0]["credential_id"]
        await faber_client.delete(f"{CREDENTIALS_BASE_PATH}/{cred_ex_id}")  # Clean up
    else:
        assert len(faber_cred_ex_records) == 0  # default is to remove records


@pytest.mark.anyio
async def test_get_cred_exchange_records(
    faber_client: RichAsyncClient,
    credential_definition_id: str,  # pylint: disable=redefined-outer-name
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
):
    credential_v1 = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": sample_credential_attributes,
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
            "attributes": {"speed": "20", "name": "Alice", "age": "44"},
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

        # wait for credential state "done" for each credential
        await check_webhook_state(
            client=alice_member_client,
            topic="credentials",
            state="done",
            filter_map={
                "credential_id": cred["credential_id"],
            },
        )

    faber_records = (await faber_client.get(CREDENTIALS_BASE_PATH)).json()

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
    assert len(json.loads(exc.value.detail)["detail"]) == 3
