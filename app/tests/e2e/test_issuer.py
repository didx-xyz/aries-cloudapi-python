from time import sleep
import pytest
from assertpy import assert_that
from httpx import AsyncClient
from app.generic.definitions import CredentialSchema
from app.generic.issuer.facades.acapy_issuer_utils import cred_id_no_version
from app.tests.util.ecosystem_personas import FaberAliceConnect
from app.tests.util.webhooks import get_hooks_per_topic_per_wallet, check_webhook_state

# This import are important for tests to run!

from app.tests.e2e.test_fixtures import BASE_PATH
from app.tests.e2e.test_fixtures import *  # NOQA


@pytest.mark.asyncio
async def test_send_credential(
    faber_client: AsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: AsyncClient,
):
    credential = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection["faber_connection_id"],
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "10"},
    }

    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": faber_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()

    # nothing currently in alice's records
    assert len(records) == 0

    response = await faber_client.post(
        BASE_PATH,
        json=credential,
    )
    response.raise_for_status()

    data = response.json()
    assert_that(data).contains("credential_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v1")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    credential["protocol_version"] = "v2"
    response = await faber_client.post(
        BASE_PATH,
        json=credential,
    )
    response.raise_for_status()

    data = response.json()
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v2")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    assert check_webhook_state(
        client=faber_client,
        filter_map={
            "state": "offer-sent",
            "credential_id": data["credential_id"],
        },
        topic="credentials",
    )
    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": faber_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={
            "state": "offer-received",
            "credential_id": records[-1]["credential_id"],
        },
        topic="credentials",
    )
    assert len(records) == 2

    # Expect one v1 record, one v2 record
    assert_that(records).extracting("protocol_version").contains("v1", "v2")


@pytest.mark.asyncio
async def test_get_records(alice_member_client: AsyncClient):
    records = (await alice_member_client.get(BASE_PATH)).json()
    assert records
    assert len(records) >= 1


@pytest.mark.asyncio
async def test_send_credential_request(
    alice_member_client: AsyncClient,
    faber_client: AsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    credential_definition_id: str,
):
    credential = {
        "protocol_version": "v1",
        "credential_definition_id": credential_definition_id,
        "connection_id": faber_and_alice_connection["faber_connection_id"],
        "attributes": {"speed": "10"},
    }

    response = await faber_client.post(
        BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    assert credential_exchange["protocol_version"] == "v1"

    assert check_webhook_state(
        client=faber_client,
        filter_map={
            "state": "offer-sent",
            "credential_id": credential_exchange["credential_id"],
        },
        topic="credentials",
    )

    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": faber_and_alice_connection["alice_connection_id"]},
    )
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "offer-received"},
        topic="credentials",
    )


@pytest.mark.asyncio
async def test_store_credential(
    alice_member_client: AsyncClient,
    faber_client: AsyncClient,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
):
    sleep(5)
    credential = {
        "protocol_version": "v1",
        "credential_definition_id": credential_definition_id,
        "connection_id": faber_and_alice_connection["faber_connection_id"],
        "attributes": {"speed": "10"},
    }

    response = await faber_client.post(
        BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    assert credential_exchange["protocol_version"] == "v1"

    assert check_webhook_state(
        client=faber_client,
        filter_map={
            "state": "offer-sent",
            "credential_id": credential_exchange["credential_id"],
        },
        topic="credentials",
    )

    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": faber_and_alice_connection["alice_connection_id"]},
    )
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "offer-received"},
        topic="credentials",
    )

    cred_hooks = get_hooks_per_topic_per_wallet(
        client=alice_member_client, topic="credentials"
    )

    cred_hook = [h for h in cred_hooks if h["payload"]["state"] == "offer-received"][0]
    credential_id = cred_hook["payload"]["credential_id"]

    # alice send request for that credential
    response = await alice_member_client.post(f"{BASE_PATH}/{credential_id}/request")
    response.raise_for_status()

    # Bob check he received the request; Credential is send because of using
    # 'automating the entire flow' send credential earlier.
    # See also: app/generic/issuer/issuer.py::send_credential
    assert check_webhook_state(
        client=faber_client,
        filter_map={"state": "request-received"},
        topic="credentials",
    )

    # Check alice has received the credential
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "credential-received"},
        topic="credentials",
    )

    # Alice stores credential
    response = await alice_member_client.post(f"{BASE_PATH}/{credential_id}/store")

    # Check alice has received the credential
    assert check_webhook_state(
        client=alice_member_client, filter_map={"state": "done"}, topic="credentials"
    )


@pytest.mark.asyncio
async def test_revoke_credential(
    # issue_credential_to_alice: CredentialExchange,
    faber_client: AsyncClient,
    # faber_acapy_client: AcaPyClient,
    alice_member_client: AsyncClient,
    # acme_client: AsyncClient,
    alice_tenant: Any,
    # acme_tenant: Any,
    credential_definition_id_revocable: str,
    # acme_and_alice_connection: AcmeAliceConnect,
    faber_and_alice_connection: FaberAliceConnect,
):
    credential = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection["faber_connection_id"],
        "credential_definition_id": credential_definition_id_revocable,
        "attributes": {"speed": "10"},
    }

    wait_for_event, _ = await start_listener(
        topic="credentials", wallet_id=alice_tenant["tenant_id"]
    )

    # create and send credential offer- issuer
    response = await faber_client.post(
        "/generic/issuer/credentials",
        json=credential,
    )
    credential_exchange = response.json()
    if response.is_error:
        print(credential_exchange)
    response.raise_for_status()

    payload = await wait_for_event(
        filter_map={
            "connection_id": faber_and_alice_connection["alice_connection_id"],
            "state": "offer-received",
        }
    )

    alice_credential_id = payload["credential_id"]
    wait_for_event, _ = await start_listener(
        topic="credentials", wallet_id=alice_tenant["tenant_id"]
    )

    # send credential request - holder
    response = await alice_member_client.post(
        f"/generic/issuer/credentials/{alice_credential_id}/request", json={}
    )

    await wait_for_event(
        
        filter_map={"credential_id": alice_credential_id, "state": "done"}
    )

    # records = await faber_client.get(
    #     BASE_PATH
    #     # + f"?connection_id={faber_and_alice_connection['faber_connection_id']}"
    # )
    records = (
        await faber_client.get("/generic/issuer/credentials")
    ).json()  # .credentials.get_record(credential_id=credential_exchange['credential_id'])
    print("\n\n\n")
    print(records)
    print("\n\n\n")
    record_as_issuer_for_alice = [
        rec
        for rec in records
        if (
            rec["role"] == "issuer"
            and rec["state"] == "credential-issued"
            # and rec["credential_definition_id"]
            # == issue_credential_to_alice["credential_definition_id"]
        )
    ]
    print("\n\n\n")
    print(record_as_issuer_for_alice)
    print("\n\n\n")
    record_issuer_for_alice: CredentialExchange = record_as_issuer_for_alice[0]
    cred_id = cred_id_no_version(record_issuer_for_alice["credential_id"])

    response = await faber_client.post(
        f"/generic/issuer/credentials/revoke",
        json={
            "credential_definition_id": credential_definition_id_revocable,
            "credential_exchange_id": cred_id,
        },
    )

    print(response)
    response.raise_for_status()

    assert response.status_code == 204
    # assert check_webhook_state(
    #     client=faber_client, filter_map={"state": "done"}, topic="revocation"
    # )
