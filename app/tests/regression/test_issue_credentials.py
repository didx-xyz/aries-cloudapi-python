import pytest

from app.routes.issuer import router as issuer_router
from app.tests.regression.fixtures import IssuerHolderConnection
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.webhooks import check_webhook_state
from app.util.credentials import cred_id_no_version
from shared import RichAsyncClient

CREDENTIALS_BASE_PATH = issuer_router.prefix


@pytest.mark.anyio
@pytest.mark.parametrize("protocol_version", ["v1", "v2"])
async def test_revoke_credential(
    issuer_client: RichAsyncClient,
    holder_client: RichAsyncClient,
    credential_definition_id_revocable_regression_test: str,
    issuer_holder_connection: IssuerHolderConnection,
    protocol_version: str,
):
    faber_connection_id = issuer_holder_connection.issuer_connection_id

    credential = {
        "protocol_version": protocol_version,
        "connection_id": faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id_revocable_regression_test,
            "attributes": {"speed": "10"},
        },
    }

    # create and send credential offer: issuer
    faber_credential_id = (
        await issuer_client.post(
            CREDENTIALS_BASE_PATH,
            json=credential,
        )
    ).json()["credential_id"]

    payload = await check_webhook_state(
        client=holder_client,
        topic="credentials",
        state="offer-received",
        filter_map={
            "connection_id": issuer_holder_connection.holder_connection_id,
        },
    )

    alice_credential_id = payload["credential_id"]

    # send credential request: holder
    response = await holder_client.post(
        f"{CREDENTIALS_BASE_PATH}/{alice_credential_id}/request", json={}
    )

    await check_webhook_state(
        client=holder_client,
        topic="credentials",
        state="done",
        filter_map={
            "credential_id": alice_credential_id,
        },
    )

    cred_id = cred_id_no_version(faber_credential_id)

    response = await issuer_client.post(
        f"{CREDENTIALS_BASE_PATH}/revoke",
        json={
            "credential_exchange_id": cred_id,
        },
    )

    assert response.status_code == 204
