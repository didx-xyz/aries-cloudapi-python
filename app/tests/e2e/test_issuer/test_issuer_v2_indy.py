import pytest
from aries_cloudcontroller import AcaPyClient
from assertpy import assert_that

from app.event_handling.sse_listener import SseListener
from app.models.tenants import CreateTenantResponse
from app.routes.definitions import CredentialSchema
from app.routes.issuer import router as issuer_router
from app.routes.oob import router as oob_router
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.webhooks import check_webhook_state, get_wallet_id_from_async_client
from app.util.credentials import cred_id_no_version
from shared import RichAsyncClient

CREDENTIALS_BASE_PATH = issuer_router.prefix
OOB_BASE_PATH = oob_router.prefix

@pytest.mark.anyio
async def test_send_credential_oob_v2(
    faber_client: RichAsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
    alice_member_client: RichAsyncClient,
):
    wallet_id = get_wallet_id_from_async_client(alice_member_client)
    alice_credentials_listener = SseListener(topic="credentials", wallet_id=wallet_id)

    credential = {
        "protocol_version": "v2",
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "10"},
        },
    }

    create_offer_response = await faber_client.post(
        CREDENTIALS_BASE_PATH + "/create-offer",
        json=credential,
    )
