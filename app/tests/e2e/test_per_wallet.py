import pytest
from app.models.definitions import CredentialSchema

from app.event_handling.sse_listener import SseListener
from app.routes.admin.tenants import router
from app.routes.connections import router as conn_router
from app.routes.definitions import router as def_router
from app.routes.issuer import router as issuer_router

from app.tests.util.client import get_tenant_client
from shared import RichAsyncClient

TENANTS_BASE_PATH = router.prefix
CONNECTIONS_BASE_PATH = conn_router.prefix
DEFINITIONS_BASE_PATH = def_router.prefix
ISSUER_BASE_PATH = issuer_router.prefix

@pytest.mark.anyio
async def test_extra_settings(
    tenant_admin_client: RichAsyncClient,
    schema_definition: CredentialSchema
    ):
    issuer_response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "wallet_label": "local_issuer",
            "wallet_name": "EpicGamer",
            "roles": [
                "issuer", "verifier"
            ],
            "group_id": "PerTenant",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png"
        },
    )
    assert issuer_response.status_code == 200
    issuer = issuer_response.json()

    holder_response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "wallet_label": "local_holder",
            "wallet_name": "EpicHolder",
            "group_id": "PerTenant",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
            "extra_settings":{"ACAPY_LOG_LEVEL":"debug"}
        }
    )
    assert holder_response.status_code == 200
    holder = holder_response.json()
    print("Issuer ==> ", issuer)
    print("Holder ==> ", holder)

    issuer_client = get_tenant_client(token=issuer["access_token"])
    holder_client = get_tenant_client(token=holder["access_token"])

    print("***Onboarded***")
