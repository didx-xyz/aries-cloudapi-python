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
async def test_send_jsonld_credential(
    faber_client: RichAsyncClient,
    faber_acapy_client: AcaPyClient,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
):
    alice_connection_id = faber_and_alice_connection.alice_connection_id
    faber_connection_id = faber_and_alice_connection.faber_connection_id
