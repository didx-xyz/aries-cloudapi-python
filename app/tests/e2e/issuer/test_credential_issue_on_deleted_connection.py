import asyncio
from logging import getLogger

import pytest

from app.routes.connections import router as connections_router
from app.routes.issuer import router as credentials_router
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange

CREDENTIALS_BASE_PATH = credentials_router.prefix
CONNECTIONS_BASE_PATH = connections_router.prefix


logger = getLogger()


@pytest.mark.anyio
async def test_credential_issue_on_deleted_connection(
    faber_client: RichAsyncClient,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
) -> CredentialExchange:
    alice_connection_id = faber_and_alice_connection.alice_connection_id
    delete_response = await alice_member_client.delete(
        f"{CONNECTIONS_BASE_PATH}/{alice_connection_id}"
    )
    assert delete_response.status_code == 200

    credential = {
        "protocol_version": "v2",
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "10"},
        },
    }

    # create and send credential offer- issuer
    await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )

    await asyncio.sleep(0.5)

    faber_cred_ex_recs = (await faber_client.get(f"{CREDENTIALS_BASE_PATH}")).json()

    logger.warning(f"{faber_cred_ex_recs=}")

    assert await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        state="offer-received",
        filter_map={
            "connection_id": faber_and_alice_connection.alice_connection_id,
        },
    )
