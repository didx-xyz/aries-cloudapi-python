import asyncio
import time

import pytest

from app.dependencies.auth import AcaPyAuthVerified, acapy_auth, acapy_auth_verified
from app.event_handling.sse_listener import SseListener
from app.models.tenants import CreateTenantResponse
from app.routes.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialSchema,
    create_credential_definition,
    create_schema,
)
from app.routes.issuer import router
from app.tests.util.ecosystem_connections import FaberAliceConnect, MeldCoAliceConnect
from app.tests.util.trust_registry import register_issuer
from app.tests.util.webhooks import check_webhook_state
from app.util.string import random_version
from shared import RichAsyncClient
from shared.models.webhook_topics import CredentialExchange

CREDENTIALS_BASE_PATH = router.prefix


@pytest.fixture(scope="session")
async def schema_definition(
    mock_governance_auth: AcaPyAuthVerified,
) -> CredentialSchema:
    definition = CreateSchema(
        name="test_schema", version=random_version(), attribute_names=["speed"]
    )

    schema_definition_result = await create_schema(definition, mock_governance_auth)

    return schema_definition_result


@pytest.fixture(scope="session")
async def schema_definition_alt(
    mock_governance_auth: AcaPyAuthVerified,
) -> CredentialSchema:
    definition = CreateSchema(
        name="test_schema_alt", version=random_version(), attribute_names=["speed"]
    )

    schema_definition_result = await create_schema(definition, mock_governance_auth)

    return schema_definition_result


@pytest.fixture(scope="module")
async def credential_definition_id(
    schema_definition: CredentialSchema,  # pylint: disable=redefined-outer-name
    faber_client: RichAsyncClient,
) -> str:
    await register_issuer(faber_client, schema_definition.id)

    # Support revocation false here because revocation is tested elsewhere.
    # No revocation is a fair bit faster to run
    definition = CreateCredentialDefinition(
        tag="tag", schema_id=schema_definition.id, support_revocation=False
    )

    auth = acapy_auth_verified(acapy_auth(faber_client.headers["x-api-key"]))
    result = await create_credential_definition(definition, auth)

    return result.id


@pytest.fixture(scope="module")
async def credential_definition_id_revocable(
    schema_definition_alt: CredentialSchema,  # pylint: disable=redefined-outer-name
    faber_client: RichAsyncClient,
) -> str:
    await register_issuer(faber_client, schema_definition_alt.id)

    definition = CreateCredentialDefinition(
        tag="tag", schema_id=schema_definition_alt.id, support_revocation=True
    )

    auth = acapy_auth_verified(acapy_auth(faber_client.headers["x-api-key"]))
    result = await create_credential_definition(definition, auth)

    return result.id


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


@pytest.fixture(scope="function")
async def issue_credential_to_alice(
    faber_client: RichAsyncClient,
    credential_definition_id: str,  # pylint: disable=redefined-outer-name
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
) -> CredentialExchange:
    credential = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "10"},
        },
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
    response = await alice_member_client.post(
        f"{CREDENTIALS_BASE_PATH}/{alice_credential_id}/request", json={}
    )

    await alice_credentials_listener.wait_for_event(
        field="credential_id", field_id=alice_credential_id, desired_state="done"
    )

    return response.json()


@pytest.fixture(scope="module")
async def meld_co_credential_definition_id(
    schema_definition: CredentialSchema,  # pylint: disable=redefined-outer-name
    meld_co_client: RichAsyncClient,
) -> str:
    await register_issuer(meld_co_client, schema_definition.id)

    # Support revocation false here because revocation is tested elsewhere.
    # No revocation is a fair bit faster to run
    definition = CreateCredentialDefinition(
        tag="tag", schema_id=schema_definition.id, support_revocation=False
    )

    auth = acapy_auth_verified(acapy_auth(meld_co_client.headers["x-api-key"]))
    result = await create_credential_definition(definition, auth)

    return result.id


@pytest.fixture(scope="function")
async def meld_co_issue_credential_to_alice(
    meld_co_client: RichAsyncClient,
    meld_co_credential_definition_id: str,  # pylint: disable=redefined-outer-name
    meld_co_and_alice_connection: MeldCoAliceConnect,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
) -> CredentialExchange:
    credential = {
        "protocol_version": "v1",
        "connection_id": meld_co_and_alice_connection.meld_co_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": meld_co_credential_definition_id,
            "attributes": {"speed": "10"},
        },
    }

    alice_credentials_listener = SseListener(
        topic="credentials", wallet_id=alice_tenant.wallet_id
    )

    # create and send credential offer- issuer
    await meld_co_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )

    payload = await alice_credentials_listener.wait_for_event(
        field="connection_id",
        field_id=meld_co_and_alice_connection.alice_connection_id,
        desired_state="offer-received",
    )

    alice_credential_id = payload["credential_id"]

    # send credential request - holder
    response = await alice_member_client.post(
        f"{CREDENTIALS_BASE_PATH}/{alice_credential_id}/request", json={}
    )

    await alice_credentials_listener.wait_for_event(
        field="credential_id", field_id=alice_credential_id, desired_state="done"
    )

    return response.json()


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


@pytest.fixture(scope="function")
async def issue_revocable_credentials_to_alice_and_revoke(
    faber_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
    credential_definition_id_revocable: str,  # pylint: disable=redefined-outer-name
    faber_and_alice_connection: FaberAliceConnect,
):
    faber_conn_id = faber_and_alice_connection.faber_connection_id
    alice_conn_id = faber_and_alice_connection.alice_connection_id

    for i in range(3):
        credential = {
            "protocol_version": "v1",
            "connection_id": faber_conn_id,
            "save_exchange_record": True,
            "indy_credential_detail": {
                "credential_definition_id": credential_definition_id_revocable,
                "attributes": {"speed": str(i)},
            },
        }

        await faber_client.post(
            CREDENTIALS_BASE_PATH,
            json=credential,
        )

    alice_cred_ex_response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH + "?connection_id=" + alice_conn_id
    )

    while len(alice_cred_ex_response.json()) != 3:
        print("not 3 credentials yet")
        alice_cred_ex_response = await alice_member_client.get(
            CREDENTIALS_BASE_PATH + "?connection_id=" + alice_conn_id
        )

    listener = SseListener(topic="credentials", wallet_id=alice_tenant.wallet_id)

    for cred in alice_cred_ex_response.json():
        await alice_member_client.post(
            f"{CREDENTIALS_BASE_PATH}/{cred['credential_id']}/request", json={}
        )
        # add sse listener to wait for credential state "done" for each credential
        await listener.wait_for_event(
            field="credential_id", field_id=cred["credential_id"], desired_state="done"
        )

    cred_ex_response = await faber_client.get(
        CREDENTIALS_BASE_PATH + "?connection_id=" + faber_conn_id
    )

    cred_ex_response = cred_ex_response.json()
    assert len(cred_ex_response) == 3

    # revoke all credentials in list
    for cred in cred_ex_response:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/revoke",
            json={
                "credential_definition_id": credential_definition_id_revocable,
                "credential_exchange_id": cred["credential_id"][3:],
            },
        )

    return cred_ex_response
