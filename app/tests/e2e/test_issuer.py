import pytest
from httpx import AsyncClient
from app.tests.util.ecosystem_personas import FaberAliceConnect
from app.tests.util.webhooks import get_wallet_id_from_async_client

# This import are important for tests to run!
from app.tests.util.event_loop import event_loop

from app.tests.e2e.test_fixtures import BASE_PATH
from app.tests.e2e.test_fixtures import *
from app.webhook_listener import start_listener  # NOQA


@pytest.mark.asyncio
async def test_credential_exchange_v1(
    alice_member_client: AsyncClient,
    faber_client: AsyncClient,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
):
    credential = {
        "protocol_version": "v1",
        "credential_definition_id": credential_definition_id,
        "connection_id": faber_and_alice_connection["faber_connection_id"],
        "attributes": {"speed": "average"},
    }

    faber_wallet_id = get_wallet_id_from_async_client(faber_client)
    wait_for_faber_event, stop_faber_listener = await start_listener(
        topic="credentials", wallet_id=faber_wallet_id, auto_close_after_success=False
    )

    alice_wallet_id = get_wallet_id_from_async_client(alice_member_client)
    wait_for_alice_event, stop_alice_listener = await start_listener(
        topic="credentials", wallet_id=alice_wallet_id, auto_close_after_success=False
    )

    response = await faber_client.post(
        BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    assert credential_exchange["protocol_version"] == "v1"

    await wait_for_faber_event(
        filter_map={
            "state": "offer-sent",
            "credential_id": credential_exchange["credential_id"],
        }
    )

    await wait_for_alice_event(
        filter_map={"state": "offer-received"},
    )

    response = await alice_member_client.get(
        BASE_PATH,
        params={},
    )
    records = response.json()
    alice_credential_id = records[-1]["credential_id"]

    # alice send request for that credential
    response = await alice_member_client.post(
        f"{BASE_PATH}/{alice_credential_id}/request"
    )
    response.raise_for_status()

    # Faber check he received the request; Credential is send because of using
    # 'automating the entire flow' send credential earlier.
    # See also: app/generic/issuer/issuer.py::send_credential
    await wait_for_faber_event(
        filter_map={
            "state": "request-received",
            "credential_id": credential_exchange["credential_id"],
        }
    )

    await wait_for_alice_event(
        filter_map={
            "state": "credential-received",
            "credential_id": alice_credential_id,
        },
    )

    # Alice stores credential
    response = await alice_member_client.post(
        f"{BASE_PATH}/{alice_credential_id}/store"
    )

    # Check alice and faber have acked the credential
    await wait_for_faber_event(
        filter_map={
            "state": "done",
            "credential_id": credential_exchange["credential_id"],
        },
    )
    await wait_for_alice_event(
        filter_map={"state": "done", "credential_id": alice_credential_id},
    )

    await stop_faber_listener()
    await stop_alice_listener()


@pytest.mark.asyncio
async def test_credential_exchange_v2(
    alice_member_client: AsyncClient,
    faber_client: AsyncClient,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
):
    credential = {
        "protocol_version": "v2",
        "credential_definition_id": credential_definition_id,
        "connection_id": faber_and_alice_connection["faber_connection_id"],
        "attributes": {"speed": "average"},
    }

    faber_wallet_id = get_wallet_id_from_async_client(faber_client)
    wait_for_faber_event, stop_faber_listener = await start_listener(
        topic="credentials", wallet_id=faber_wallet_id, auto_close_after_success=False
    )

    alice_wallet_id = get_wallet_id_from_async_client(alice_member_client)
    wait_for_alice_event, stop_alice_listener = await start_listener(
        topic="credentials", wallet_id=alice_wallet_id, auto_close_after_success=False
    )

    response = await faber_client.post(
        BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    assert credential_exchange["protocol_version"] == "v2"

    await wait_for_faber_event(
        filter_map={
            "state": "offer-sent",
            "credential_id": credential_exchange["credential_id"],
        }
    )

    await wait_for_alice_event(
        filter_map={"state": "offer-received"},
    )

    response = await alice_member_client.get(
        BASE_PATH,
        params={},
    )
    records = response.json()
    alice_credential_id = records[-1]["credential_id"]

    # alice send request for that credential
    response = await alice_member_client.post(
        f"{BASE_PATH}/{alice_credential_id}/request"
    )
    response.raise_for_status()

    # Faber check he received the request; Credential is send because of using
    # 'automating the entire flow' send credential earlier.
    # See also: app/generic/issuer/issuer.py::send_credential
    await wait_for_faber_event(
        filter_map={
            "state": "request-received",
            "credential_id": credential_exchange["credential_id"],
        }
    )

    await wait_for_alice_event(
        filter_map={
            "state": "credential-received",
            "credential_id": alice_credential_id,
        },
    )

    # Alice stores credential
    response = await alice_member_client.post(
        f"{BASE_PATH}/{alice_credential_id}/store"
    )

    # Check alice and faber have acked the credential
    await wait_for_faber_event(
        filter_map={
            "state": "done",
            "credential_id": credential_exchange["credential_id"],
        },
    )
    await wait_for_alice_event(
        filter_map={"state": "done", "credential_id": alice_credential_id},
    )

    await stop_faber_listener()
    await stop_alice_listener()


@pytest.mark.asyncio
async def test_get_records(alice_member_client: AsyncClient):
    records = (await alice_member_client.get(BASE_PATH)).json()
    assert records
    assert len(records) >= 1
