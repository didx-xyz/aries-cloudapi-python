import asyncio
from logging import getLogger

import pytest

from app.models.tenants import CreateTenantResponse
from app.routes.connections import router as connections_router
from app.routes.issuer import router as credentials_router
from app.services.event_handling.sse_listener import SseListener
from app.tests.util.ecosystem_connections import FaberAliceConnect
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange

CREDENTIALS_BASE_PATH = credentials_router.prefix
CONNECTIONS_BASE_PATH = connections_router.prefix


logger = getLogger()


@pytest.mark.anyio
async def test_credential_issue_on_deleted_connection(
    faber_client: RichAsyncClient,
    credential_definition_id: str,  # pylint: disable=redefined-outer-name
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
) -> CredentialExchange:
    alice_connection_id = faber_and_alice_connection.alice_connection_id
    delete_response = await alice_member_client.delete(
        f"{CONNECTIONS_BASE_PATH}/{alice_connection_id}"
    )
    assert delete_response.status_code == 200

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

    await asyncio.sleep(0.5)

    faber_cred_ex_recs = (await faber_client.get(f"{CREDENTIALS_BASE_PATH}")).json()

    logger.warning(f"{faber_cred_ex_recs=}")

    payload = await alice_credentials_listener.wait_for_event(
        field="connection_id",
        field_id=faber_and_alice_connection.alice_connection_id,
        desired_state="offer-received",
    )

    # alice_credential_id = payload["credential_id"]

    # # send credential request - holder
    # response = await alice_member_client.post(
    #     f"{CREDENTIALS_BASE_PATH}/{alice_credential_id}/request", json={}
    # )

    # await alice_credentials_listener.wait_for_event(
    #     field="credential_id", field_id=alice_credential_id, desired_state="done"
    # )

    # return response.json()
